from fastapi import FastAPI, APIRouter, HTTPException, UploadFile, File, Form
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
from datetime import datetime
from emergentintegrations.llm.chat import LlmChat, UserMessage
import openai
import base64
import tempfile

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Get the Emergent LLM Key (for chat/suggestions)
EMERGENT_LLM_KEY = os.environ.get('EMERGENT_LLM_KEY', '')

# Get the OpenAI API Key (for Whisper transcription)
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')

# Initialize OpenAI client for Whisper transcription
openai_client = openai.OpenAI(
    api_key=OPENAI_API_KEY
)

# ==================== Models ====================

class ConversationMode(BaseModel):
    mode: str  # interview, business, sales, general

class TranscriptInput(BaseModel):
    transcript: str
    mode: str = "general"  # interview, business, sales, general
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    context: Optional[List[str]] = None  # Previous context lines

class Suggestion(BaseModel):
    text: str
    tone: str  # confident, empathetic, professional, etc.
    priority: int  # 1 = highest priority

class SuggestionsResponse(BaseModel):
    suggestions: List[Suggestion]
    detected_question: bool
    question_context: Optional[str] = None
    session_id: str

class TranscriptionResponse(BaseModel):
    text: str
    success: bool
    error: Optional[str] = None

class Session(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    mode: str
    context: List[str] = []
    duration: int = 0  # Duration in seconds
    transcript_enabled: bool = False  # Privacy: user must opt-in
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class SavedSuggestion(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    text: str
    tone: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    tags: List[str] = []

class Note(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    text: str
    suggestion_ids: List[str] = []  # Links to saved suggestions
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class SessionHistory(BaseModel):
    id: str
    mode: str
    duration: int
    transcript_enabled: bool
    saved_suggestions_count: int
    notes_count: int
    created_at: datetime

class SaveSuggestionInput(BaseModel):
    session_id: str
    text: str
    tone: str
    tags: Optional[List[str]] = []

class CreateNoteInput(BaseModel):
    session_id: str
    text: str
    suggestion_ids: Optional[List[str]] = []

class UpdateNoteInput(BaseModel):
    text: Optional[str] = None
    suggestion_ids: Optional[List[str]] = None

class UpdateSessionInput(BaseModel):
    transcript_enabled: Optional[bool] = None
    duration: Optional[int] = None

class StatusCheck(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class StatusCheckCreate(BaseModel):
    client_name: str

# ==================== New Models for Response Preferences ====================

class ResponsePreferences(BaseModel):
    tone: str = "neutral"  # confident, neutral, executive, friendly, concise
    style: str = "direct"  # direct, explanation, followup, star
    risk_level: str = "balanced"  # conservative, balanced, assertive
    # Interview-specific settings
    role_type: Optional[str] = None  # product_manager, engineer, grc, sales, etc.
    seniority_level: Optional[str] = None  # ic, manager, director
    preferred_frameworks: Optional[List[str]] = None

class TranscriptInputWithPreferences(BaseModel):
    transcript: str
    mode: str = "general"
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    context: Optional[List[str]] = None
    preferences: Optional[ResponsePreferences] = None

class ActionItem(BaseModel):
    task: str
    owner: Optional[str] = None
    due_date: Optional[str] = None

class MeetingSummary(BaseModel):
    summary_points: List[str]
    action_items: List[ActionItem]
    key_highlights: List[str]
    mode: str
    duration: int
    generated_at: datetime = Field(default_factory=datetime.utcnow)

class GenerateSummaryInput(BaseModel):
    session_id: str
    full_transcript: str
    mode: str
    duration: int

# ==================== System Prompts ====================

# Tone modifiers for response preferences
TONE_MODIFIERS = {
    "confident": "Be assertive and self-assured. Use decisive language.",
    "neutral": "Maintain a balanced, professional tone without strong emotions.",
    "executive": "Use executive-level language. Be strategic and high-level.",
    "friendly": "Be warm and approachable while staying professional.",
    "concise": "Be extremely brief. Maximum 1-2 sentences per suggestion."
}

STYLE_MODIFIERS = {
    "direct": "Give direct answers only. No elaboration unless necessary.",
    "explanation": "Provide the answer followed by a brief explanation of reasoning.",
    "followup": "Give the answer and suggest a follow-up question to deepen the conversation.",
    "star": "Structure responses using STAR format (Situation, Task, Action, Result) when applicable."
}

RISK_MODIFIERS = {
    "conservative": "Be cautious and policy-aware. Avoid controversial or risky statements.",
    "balanced": "Balance between being helpful and being careful. Use measured language.",
    "assertive": "Be bold and take clear positions. Don't hedge unnecessarily."
}

MODE_PROMPTS = {
    "interview": """You are an expert interview coach providing silent, real-time response suggestions.
Focus on:
- Demonstrating competence and confidence
- Using STAR method when appropriate (Situation, Task, Action, Result)
- Highlighting achievements concisely
- Asking thoughtful clarifying questions when needed
Tone: Professional, confident, articulate""",

    "business": """You are a business communication expert providing silent, real-time response suggestions.
Focus on:
- Clear, actionable communication
- Professional diplomacy
- Moving discussions toward decisions
- Building consensus
Tone: Professional, decisive, collaborative""",

    "sales": """You are a sales expert providing silent, real-time response suggestions.
Focus on:
- Understanding customer needs through questions
- Addressing objections gracefully
- Highlighting value propositions
- Moving toward next steps
Tone: Confident, enthusiastic, helpful""",

    "general": """You are a conversation assistant providing silent, real-time response suggestions.
Focus on:
- Natural, flowing conversation
- Active listening cues
- Thoughtful engagement
- Appropriate tone matching
Tone: Friendly, natural, adaptable"""
}

SYSTEM_PROMPT_TEMPLATE = """{mode_prompt}

Your role is to analyze live conversation transcripts and provide response suggestions.

RULES:
1. Provide EXACTLY 3 response suggestions
2. Each suggestion must be under 3 sentences
3. Prioritize clarity and confidence
4. Detect if a question is directed at the user
5. Infer intent from partial questions
6. Maintain awareness of conversational context
7. Avoid verbosity - be concise
8. NEVER mention listening, transcription, or AI
9. Suggestions should be ready to speak naturally

Respond in this exact JSON format:
{{
    "detected_question": true/false,
    "question_context": "Brief summary of what was asked (if question detected)",
    "suggestions": [
        {{"text": "Your first suggestion", "tone": "confident", "priority": 1}},
        {{"text": "Your second suggestion", "tone": "empathetic", "priority": 2}},
        {{"text": "Your third suggestion", "tone": "professional", "priority": 3}}
    ]
}}
"""

# ==================== Helper Functions ====================

def build_preference_prompt(preferences: Optional[ResponsePreferences], mode: str) -> str:
    """Build additional prompt instructions based on user preferences"""
    if not preferences:
        return ""
    
    parts = []
    
    # Tone
    if preferences.tone and preferences.tone in TONE_MODIFIERS:
        parts.append(f"TONE: {TONE_MODIFIERS[preferences.tone]}")
    
    # Style
    if preferences.style and preferences.style in STYLE_MODIFIERS:
        parts.append(f"STYLE: {STYLE_MODIFIERS[preferences.style]}")
    
    # Risk level
    if preferences.risk_level and preferences.risk_level in RISK_MODIFIERS:
        parts.append(f"APPROACH: {RISK_MODIFIERS[preferences.risk_level]}")
    
    # Interview-specific settings
    if mode == "interview":
        if preferences.role_type:
            parts.append(f"TARGET ROLE: {preferences.role_type.replace('_', ' ').title()}")
        if preferences.seniority_level:
            level_map = {"ic": "Individual Contributor", "manager": "Manager", "director": "Director/Executive"}
            parts.append(f"SENIORITY: {level_map.get(preferences.seniority_level, preferences.seniority_level)}")
        if preferences.preferred_frameworks:
            parts.append(f"USE FRAMEWORKS: {', '.join(preferences.preferred_frameworks)}")
    
    if parts:
        return "\n\nUSER PREFERENCES:\n" + "\n".join(parts)
    return ""

async def get_ai_suggestions(transcript: str, mode: str, context: List[str], session_id: str, preferences: Optional[ResponsePreferences] = None) -> dict:
    """Generate AI-powered response suggestions"""
    try:
        mode_prompt = MODE_PROMPTS.get(mode, MODE_PROMPTS["general"])
        preference_prompt = build_preference_prompt(preferences, mode)
        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(mode_prompt=mode_prompt) + preference_prompt
        
        # Build context string
        context_str = ""
        if context:
            context_str = "Previous conversation context:\n" + "\n".join(context[-5:])  # Last 5 lines
        
        user_message = f"""{context_str}

Current transcript:
{transcript}

Provide 3 response suggestions based on the conversation above."""
        
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"whisprly_{session_id}",
            system_message=system_prompt
        ).with_model("openai", "gpt-4o")
        
        response = await chat.send_message(UserMessage(text=user_message))
        
        # Parse JSON response
        import json
        # Clean response - remove markdown code blocks if present
        clean_response = response.strip()
        if clean_response.startswith("```json"):
            clean_response = clean_response[7:]
        if clean_response.startswith("```"):
            clean_response = clean_response[3:]
        if clean_response.endswith("```"):
            clean_response = clean_response[:-3]
        clean_response = clean_response.strip()
        
        result = json.loads(clean_response)
        return result
        
    except Exception as e:
        logger.error(f"AI suggestion error: {str(e)}")
        # Return fallback suggestions
        return {
            "detected_question": False,
            "question_context": None,
            "suggestions": [
                {"text": "I understand. Could you elaborate on that point?", "tone": "curious", "priority": 1},
                {"text": "That's a great point. Let me share my perspective.", "tone": "confident", "priority": 2},
                {"text": "I appreciate you sharing that. Here's my take.", "tone": "appreciative", "priority": 3}
            ]
        }

# ==================== API Routes ====================

@api_router.get("/")
async def root():
    return {"message": "Whisprly API is running", "version": "2.0.0"}

@api_router.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

# ==================== Transcription Routes ====================

@api_router.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe_audio(
    audio: UploadFile = File(...),
    language: str = Form(default="en")
):
    """Transcribe audio using OpenAI gpt-4o-mini-transcribe model"""
    try:
        # Read audio content
        audio_content = await audio.read()
        
        # Create a temporary file to save the audio
        with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as tmp_file:
            tmp_file.write(audio_content)
            tmp_file_path = tmp_file.name
        
        try:
            # Use OpenAI transcription API
            with open(tmp_file_path, "rb") as audio_file:
                transcription = openai_client.audio.transcriptions.create(
                    model="gpt-4o-mini-transcribe",
                    file=audio_file,
                    language=language,
                    response_format="text"
                )
            
            return TranscriptionResponse(
                text=transcription if isinstance(transcription, str) else transcription.text,
                success=True
            )
        finally:
            # Clean up temp file
            os.unlink(tmp_file_path)
            
    except Exception as e:
        logger.error(f"Transcription error: {str(e)}")
        return TranscriptionResponse(
            text="",
            success=False,
            error=str(e)
        )

@api_router.post("/transcribe-base64", response_model=TranscriptionResponse)
async def transcribe_audio_base64(data: dict):
    """Transcribe base64 encoded audio using OpenAI Whisper API"""
    try:
        audio_base64 = data.get("audio", "")
        language = data.get("language", "en")
        
        logger.info(f"Received transcription request. Audio base64 length: {len(audio_base64) if audio_base64 else 0}")
        
        if not audio_base64:
            logger.warning("No audio data provided in request")
            return TranscriptionResponse(
                text="",
                success=False,
                error="No audio data provided"
            )
        
        # Check minimum length (1000 chars ~ 750 bytes, very short audio)
        if len(audio_base64) < 1000:
            logger.warning(f"Audio too short: {len(audio_base64)} characters")
            return TranscriptionResponse(
                text="",
                success=False,
                error=f"Audio too short ({len(audio_base64)} chars, need at least 1000)"
            )
        
        logger.info("Decoding base64 audio and preparing for Whisper API...")
        
        # Decode base64 to bytes
        try:
            audio_bytes = base64.b64decode(audio_base64)
            logger.info(f"Decoded audio size: {len(audio_bytes)} bytes")
        except Exception as decode_error:
            logger.error(f"Failed to decode base64: {decode_error}")
            return TranscriptionResponse(
                text="",
                success=False,
                error=f"Invalid base64 audio data: {str(decode_error)}"
            )
        
        # Save to temporary file for Whisper API
        with tempfile.NamedTemporaryFile(delete=False, suffix=".m4a") as tmp_file:
            tmp_file.write(audio_bytes)
            tmp_file_path = tmp_file.name
        
        try:
            logger.info(f"Sending audio to OpenAI Whisper API...")
            
            # Use OpenAI Whisper API for transcription
            with open(tmp_file_path, "rb") as audio_file:
                transcription = openai_client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language=language,
                    response_format="text"
                )
            
            result_text = transcription if isinstance(transcription, str) else transcription.text
            result_text = result_text.strip() if result_text else ""
            
            logger.info(f"Whisper transcription result: '{result_text[:100]}...' (length: {len(result_text)})")
            
            return TranscriptionResponse(
                text=result_text,
                success=True if result_text else False,
                error=None if result_text else "No speech detected"
            )
            
        finally:
            # Clean up temp file
            try:
                os.unlink(tmp_file_path)
            except:
                pass
            
    except Exception as e:
        logger.error(f"Transcription error: {str(e)}")
        return TranscriptionResponse(
            text="",
            success=False,
            error=str(e)
        )

# ==================== Session Routes ====================

@api_router.post("/sessions", response_model=Session)
async def create_session(mode_input: ConversationMode):
    """Create a new conversation session"""
    session = Session(mode=mode_input.mode)
    session_dict = session.model_dump()
    session_dict['_id'] = session_dict['id']
    await db.sessions.insert_one(session_dict)
    return session

@api_router.get("/sessions/{session_id}", response_model=Session)
async def get_session(session_id: str):
    """Get a session by ID"""
    session = await db.sessions.find_one({"id": session_id})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return Session(**session)

@api_router.patch("/sessions/{session_id}", response_model=Session)
async def update_session(session_id: str, update_data: UpdateSessionInput):
    """Update session settings (e.g., enable transcript saving)"""
    update_dict = {k: v for k, v in update_data.model_dump().items() if v is not None}
    update_dict['updated_at'] = datetime.utcnow()
    
    result = await db.sessions.update_one(
        {"id": session_id},
        {"$set": update_dict}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = await db.sessions.find_one({"id": session_id})
    return Session(**session)

@api_router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a session and all associated data"""
    # Delete session
    result = await db.sessions.delete_one({"id": session_id})
    
    # Delete associated suggestions and notes
    await db.saved_suggestions.delete_many({"session_id": session_id})
    await db.notes.delete_many({"session_id": session_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"message": "Session and associated data deleted successfully"}

@api_router.get("/sessions", response_model=List[SessionHistory])
async def get_session_history():
    """Get all session history with counts"""
    sessions = await db.sessions.find().sort("created_at", -1).to_list(100)
    
    history = []
    for session in sessions:
        # Skip sessions without required fields (old/incomplete data)
        if 'mode' not in session or 'id' not in session:
            continue
            
        suggestions_count = await db.saved_suggestions.count_documents({"session_id": session['id']})
        notes_count = await db.notes.count_documents({"session_id": session['id']})
        
        history.append(SessionHistory(
            id=session['id'],
            mode=session['mode'],
            duration=session.get('duration', 0),
            transcript_enabled=session.get('transcript_enabled', False),
            saved_suggestions_count=suggestions_count,
            notes_count=notes_count,
            created_at=session.get('created_at', datetime.utcnow())
        ))
    
    return history

@api_router.delete("/sessions")
async def delete_all_sessions():
    """Delete all user data (sessions, suggestions, notes)"""
    await db.sessions.delete_many({})
    await db.saved_suggestions.delete_many({})
    await db.notes.delete_many({})
    return {"message": "All data deleted successfully"}

# ==================== Suggestions Routes ====================

@api_router.post("/suggestions", response_model=SuggestionsResponse)
async def get_suggestions(input_data: TranscriptInput):
    """Generate response suggestions based on transcript"""
    if not input_data.transcript.strip():
        raise HTTPException(status_code=400, detail="Transcript cannot be empty")
    
    # Get or create session context
    context = input_data.context or []
    
    # Get AI suggestions
    ai_result = await get_ai_suggestions(
        transcript=input_data.transcript,
        mode=input_data.mode,
        context=context,
        session_id=input_data.session_id
    )
    
    # Build response
    suggestions = [
        Suggestion(
            text=s.get("text", ""),
            tone=s.get("tone", "neutral"),
            priority=s.get("priority", i+1)
        )
        for i, s in enumerate(ai_result.get("suggestions", [])[:3])
    ]
    
    # Update session context in DB
    new_context = context + [input_data.transcript]
    await db.sessions.update_one(
        {"id": input_data.session_id},
        {
            "$set": {
                "context": new_context[-10:],  # Keep last 10 entries
                "updated_at": datetime.utcnow()
            }
        },
        upsert=True
    )
    
    return SuggestionsResponse(
        suggestions=suggestions,
        detected_question=ai_result.get("detected_question", False),
        question_context=ai_result.get("question_context"),
        session_id=input_data.session_id
    )

@api_router.post("/suggestions/save", response_model=SavedSuggestion)
async def save_suggestion(input_data: SaveSuggestionInput):
    """Save a suggestion for later reference"""
    suggestion = SavedSuggestion(
        session_id=input_data.session_id,
        text=input_data.text,
        tone=input_data.tone,
        tags=input_data.tags or []
    )
    
    suggestion_dict = suggestion.model_dump()
    suggestion_dict['_id'] = suggestion_dict['id']
    await db.saved_suggestions.insert_one(suggestion_dict)
    
    return suggestion

@api_router.get("/suggestions/saved/{session_id}", response_model=List[SavedSuggestion])
async def get_saved_suggestions(session_id: str):
    """Get all saved suggestions for a session"""
    suggestions = await db.saved_suggestions.find({"session_id": session_id}).to_list(100)
    return [SavedSuggestion(**s) for s in suggestions]

@api_router.delete("/suggestions/saved/{suggestion_id}")
async def delete_saved_suggestion(suggestion_id: str):
    """Delete a saved suggestion"""
    result = await db.saved_suggestions.delete_one({"id": suggestion_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Suggestion not found")
    return {"message": "Suggestion deleted successfully"}

# ==================== Notes Routes ====================

@api_router.post("/notes", response_model=Note)
async def create_note(input_data: CreateNoteInput):
    """Create a new note"""
    note = Note(
        session_id=input_data.session_id,
        text=input_data.text,
        suggestion_ids=input_data.suggestion_ids or []
    )
    
    note_dict = note.model_dump()
    note_dict['_id'] = note_dict['id']
    await db.notes.insert_one(note_dict)
    
    return note

@api_router.get("/notes/{session_id}", response_model=List[Note])
async def get_notes(session_id: str):
    """Get all notes for a session"""
    notes = await db.notes.find({"session_id": session_id}).to_list(100)
    return [Note(**n) for n in notes]

@api_router.patch("/notes/{note_id}", response_model=Note)
async def update_note(note_id: str, update_data: UpdateNoteInput):
    """Update a note"""
    update_dict = {k: v for k, v in update_data.model_dump().items() if v is not None}
    update_dict['updated_at'] = datetime.utcnow()
    
    result = await db.notes.update_one(
        {"id": note_id},
        {"$set": update_dict}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Note not found")
    
    note = await db.notes.find_one({"id": note_id})
    return Note(**note)

@api_router.delete("/notes/{note_id}")
async def delete_note(note_id: str):
    """Delete a note"""
    result = await db.notes.delete_one({"id": note_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Note not found")
    return {"message": "Note deleted successfully"}

# ==================== Legacy Routes ====================

@api_router.post("/status", response_model=StatusCheck)
async def create_status_check(input: StatusCheckCreate):
    status_dict = input.model_dump()
    status_obj = StatusCheck(**status_dict)
    _ = await db.status_checks.insert_one(status_obj.model_dump())
    return status_obj

@api_router.get("/status", response_model=List[StatusCheck])
async def get_status_checks():
    status_checks = await db.status_checks.find().to_list(1000)
    return [StatusCheck(**status_check) for status_check in status_checks]

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
