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
import io

# Document processing imports
from PyPDF2 import PdfReader
from docx import Document as DocxDocument
from openpyxl import load_workbook
from pptx import Presentation
import xlrd  # For legacy .xls files

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

# ==================== Knowledge Base Models ====================

class KnowledgeDocument(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    file_type: str  # pdf, docx, xlsx, pptx, txt
    content: str  # Extracted text content
    storage_type: str = "persistent"  # "persistent" or "session"
    session_id: Optional[str] = None  # Only set if storage_type is "session"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    file_size: int = 0

class KnowledgeNote(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    content: str
    storage_type: str = "persistent"
    session_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class KnowledgeBaseResponse(BaseModel):
    documents: List[KnowledgeDocument]
    notes: List[KnowledgeNote]

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

# ==================== Document Extraction Functions ====================

def extract_text_from_pdf(file_content: bytes) -> str:
    """Extract text from PDF file"""
    try:
        pdf_reader = PdfReader(io.BytesIO(file_content))
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() or ""
        return text.strip()
    except Exception as e:
        logger.error(f"PDF extraction error: {e}")
        return ""

def extract_text_from_docx(file_content: bytes) -> str:
    """Extract text from Word document"""
    try:
        doc = DocxDocument(io.BytesIO(file_content))
        text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
        return text.strip()
    except Exception as e:
        logger.error(f"DOCX extraction error: {e}")
        return ""

def extract_text_from_xlsx(file_content: bytes) -> str:
    """Extract text from Excel file"""
    try:
        wb = load_workbook(io.BytesIO(file_content), data_only=True)
        text_parts = []
        for sheet in wb.worksheets:
            text_parts.append(f"Sheet: {sheet.title}")
            for row in sheet.iter_rows(values_only=True):
                row_text = " | ".join([str(cell) if cell is not None else "" for cell in row])
                if row_text.strip():
                    text_parts.append(row_text)
        return "\n".join(text_parts).strip()
    except Exception as e:
        logger.error(f"XLSX extraction error: {e}")
        return ""

def extract_text_from_pptx(file_content: bytes) -> str:
    """Extract text from PowerPoint file"""
    try:
        prs = Presentation(io.BytesIO(file_content))
        text_parts = []
        for slide_num, slide in enumerate(prs.slides, 1):
            text_parts.append(f"Slide {slide_num}:")
            for shape in slide.shapes:
                if hasattr(shape, "text") and shape.text:
                    text_parts.append(shape.text)
        return "\n".join(text_parts).strip()
    except Exception as e:
        logger.error(f"PPTX extraction error: {e}")
        return ""

def extract_text_from_file(file_content: bytes, file_type: str) -> str:
    """Extract text from various file types"""
    extractors = {
        "pdf": extract_text_from_pdf,
        "docx": extract_text_from_docx,
        "xlsx": extract_text_from_xlsx,
        "pptx": extract_text_from_pptx,
        "txt": lambda x: x.decode("utf-8", errors="ignore")
    }
    extractor = extractors.get(file_type.lower())
    if extractor:
        return extractor(file_content)
    return ""

async def get_knowledge_context(session_id: Optional[str] = None) -> str:
    """Get all relevant knowledge base content for AI context"""
    context_parts = []
    
    # Get persistent documents
    persistent_docs = await db.knowledge_documents.find({"storage_type": "persistent"}).to_list(100)
    for doc in persistent_docs:
        if doc.get("content"):
            context_parts.append(f"[Document: {doc['name']}]\n{doc['content'][:2000]}")
    
    # Get session-specific documents if session_id provided
    if session_id:
        session_docs = await db.knowledge_documents.find({
            "storage_type": "session",
            "session_id": session_id
        }).to_list(50)
        for doc in session_docs:
            if doc.get("content"):
                context_parts.append(f"[Session Document: {doc['name']}]\n{doc['content'][:2000]}")
    
    # Get persistent notes
    persistent_notes = await db.knowledge_notes.find({"storage_type": "persistent"}).to_list(100)
    for note in persistent_notes:
        if note.get("content"):
            context_parts.append(f"[Note: {note['title']}]\n{note['content']}")
    
    # Get session-specific notes
    if session_id:
        session_notes = await db.knowledge_notes.find({
            "storage_type": "session",
            "session_id": session_id
        }).to_list(50)
        for note in session_notes:
            if note.get("content"):
                context_parts.append(f"[Session Note: {note['title']}]\n{note['content']}")
    
    if context_parts:
        return "\n\n--- KNOWLEDGE BASE REFERENCE ---\n" + "\n\n".join(context_parts) + "\n--- END KNOWLEDGE BASE ---\n\n"
    return ""

async def get_ai_suggestions(transcript: str, mode: str, context: List[str], session_id: str, preferences: Optional[ResponsePreferences] = None) -> dict:
    """Generate AI-powered response suggestions"""
    try:
        mode_prompt = MODE_PROMPTS.get(mode, MODE_PROMPTS["general"])
        preference_prompt = build_preference_prompt(preferences, mode)
        
        # Get knowledge base context
        knowledge_context = await get_knowledge_context(session_id)
        
        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(mode_prompt=mode_prompt) + preference_prompt
        if knowledge_context:
            system_prompt += "\n\nYou have access to the user's knowledge base. Use this information to provide more accurate and contextual responses."
        
        # Build context string
        context_str = ""
        if context:
            context_str = "Previous conversation context:\n" + "\n".join(context[-5:])  # Last 5 lines
        
        user_message = f"""{knowledge_context}{context_str}

Current transcript:
{transcript}

Provide 3 response suggestions based on the conversation above. Use any relevant information from the knowledge base to make your suggestions more accurate and specific."""
        
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
        audio_format = data.get("format", "m4a")  # Support both m4a (mobile) and webm (web)
        
        logger.info(f"Received transcription request. Audio base64 length: {len(audio_base64) if audio_base64 else 0}, format: {audio_format}")
        
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
        
        # Determine file extension based on format
        # Whisper supports: mp3, mp4, mpeg, mpga, m4a, wav, webm
        file_ext = ".webm" if audio_format == "webm" else ".m4a"
        
        # Save to temporary file for Whisper API
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp_file:
            tmp_file.write(audio_bytes)
            tmp_file_path = tmp_file.name
        
        try:
            logger.info(f"Sending audio ({file_ext}) to OpenAI Whisper API...")
            
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
    
    # Get all session IDs first
    session_ids = [session['id'] for session in sessions if 'id' in session]
    
    # Batch fetch counts using aggregation (fixes N+1 query issue)
    suggestions_pipeline = [
        {"$match": {"session_id": {"$in": session_ids}}},
        {"$group": {"_id": "$session_id", "count": {"$sum": 1}}}
    ]
    notes_pipeline = [
        {"$match": {"session_id": {"$in": session_ids}}},
        {"$group": {"_id": "$session_id", "count": {"$sum": 1}}}
    ]
    
    suggestions_counts = {doc['_id']: doc['count'] for doc in await db.saved_suggestions.aggregate(suggestions_pipeline).to_list(None)}
    notes_counts = {doc['_id']: doc['count'] for doc in await db.notes.aggregate(notes_pipeline).to_list(None)}
    
    for session in sessions:
        # Skip sessions without required fields (old/incomplete data)
        if 'mode' not in session or 'id' not in session:
            continue
        
        # Use pre-fetched counts (O(1) lookup instead of O(n) queries)
        suggestions_count = suggestions_counts.get(session['id'], 0)
        notes_count = notes_counts.get(session['id'], 0)
        
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
async def get_suggestions(input_data: TranscriptInputWithPreferences):
    """Generate response suggestions based on transcript with user preferences"""
    if not input_data.transcript.strip():
        raise HTTPException(status_code=400, detail="Transcript cannot be empty")
    
    # Get or create session context
    context = input_data.context or []
    
    # Get AI suggestions with preferences
    ai_result = await get_ai_suggestions(
        transcript=input_data.transcript,
        mode=input_data.mode,
        context=context,
        session_id=input_data.session_id,
        preferences=input_data.preferences
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

# ==================== Meeting Summary Routes ====================

SUMMARY_SYSTEM_PROMPT = """You are a professional meeting summarizer. Your task is to analyze meeting transcripts and generate:
1. A concise meeting summary (4-6 bullet points)
2. Action items with task, owner (if mentioned), and due date (if mentioned)
3. Key highlights including risks, blockers, or important follow-ups

RULES:
- Use ONLY information from the provided transcript
- Do NOT fabricate actions, owners, or deadlines
- Leave owner/due_date as null if not explicitly mentioned
- Be concise and professional
- Focus on decisions made, topics discussed, and outcomes

Respond in this exact JSON format:
{
    "summary_points": ["Point 1", "Point 2", "Point 3", "Point 4"],
    "action_items": [
        {"task": "Description of action", "owner": "Person name or null", "due_date": "Date or null"}
    ],
    "key_highlights": ["Highlight 1", "Highlight 2"]
}
"""

INTERVIEW_SUMMARY_PROMPT = """You are an interview feedback analyzer. Your task is to analyze interview transcripts and generate:
1. A summary of the interview (4-6 bullet points covering questions asked and topics discussed)
2. Action items (follow-up tasks, thank you notes to send, skills to brush up on)
3. Key highlights (strong answers, areas for improvement, feedback signals)

RULES:
- Use ONLY information from the provided transcript
- Be objective and constructive
- Focus on actionable insights for the interviewee

Respond in this exact JSON format:
{
    "summary_points": ["Point 1", "Point 2", "Point 3", "Point 4"],
    "action_items": [
        {"task": "Description of action", "owner": null, "due_date": null}
    ],
    "key_highlights": ["Highlight 1", "Highlight 2"]
}
"""

@api_router.post("/generate-summary", response_model=MeetingSummary)
async def generate_meeting_summary(input_data: GenerateSummaryInput):
    """Generate post-meeting summary with action items"""
    if not input_data.full_transcript.strip():
        raise HTTPException(status_code=400, detail="Transcript cannot be empty")
    
    try:
        # Choose appropriate prompt based on mode
        system_prompt = INTERVIEW_SUMMARY_PROMPT if input_data.mode == "interview" else SUMMARY_SYSTEM_PROMPT
        
        user_message = f"""Please analyze the following {input_data.mode} transcript and generate a summary:

TRANSCRIPT:
{input_data.full_transcript}

Generate the summary, action items, and key highlights."""
        
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"summary_{input_data.session_id}",
            system_message=system_prompt
        ).with_model("openai", "gpt-4o")
        
        response = await chat.send_message(UserMessage(text=user_message))
        
        # Parse JSON response
        import json
        clean_response = response.strip()
        if clean_response.startswith("```json"):
            clean_response = clean_response[7:]
        if clean_response.startswith("```"):
            clean_response = clean_response[3:]
        if clean_response.endswith("```"):
            clean_response = clean_response[:-3]
        clean_response = clean_response.strip()
        
        result = json.loads(clean_response)
        
        # Build action items
        action_items = [
            ActionItem(
                task=item.get("task", ""),
                owner=item.get("owner"),
                due_date=item.get("due_date")
            )
            for item in result.get("action_items", [])
        ]
        
        # Save summary to database
        summary_doc = {
            "session_id": input_data.session_id,
            "summary_points": result.get("summary_points", []),
            "action_items": [ai.model_dump() for ai in action_items],
            "key_highlights": result.get("key_highlights", []),
            "mode": input_data.mode,
            "duration": input_data.duration,
            "generated_at": datetime.utcnow()
        }
        await db.meeting_summaries.update_one(
            {"session_id": input_data.session_id},
            {"$set": summary_doc},
            upsert=True
        )
        
        return MeetingSummary(
            summary_points=result.get("summary_points", []),
            action_items=action_items,
            key_highlights=result.get("key_highlights", []),
            mode=input_data.mode,
            duration=input_data.duration
        )
        
    except Exception as e:
        logger.error(f"Summary generation error: {str(e)}")
        # Return a basic summary on error
        return MeetingSummary(
            summary_points=["Meeting summary could not be generated. Please try again."],
            action_items=[],
            key_highlights=[],
            mode=input_data.mode,
            duration=input_data.duration
        )

@api_router.get("/summary/{session_id}", response_model=MeetingSummary)
async def get_meeting_summary(session_id: str):
    """Retrieve a previously generated meeting summary"""
    summary = await db.meeting_summaries.find_one({"session_id": session_id})
    if not summary:
        raise HTTPException(status_code=404, detail="Summary not found")
    
    action_items = [
        ActionItem(**item) for item in summary.get("action_items", [])
    ]
    
    return MeetingSummary(
        summary_points=summary.get("summary_points", []),
        action_items=action_items,
        key_highlights=summary.get("key_highlights", []),
        mode=summary.get("mode", "general"),
        duration=summary.get("duration", 0),
        generated_at=summary.get("generated_at", datetime.utcnow())
    )

# ==================== Knowledge Base Routes ====================

@api_router.post("/knowledge/document")
async def upload_document(
    file: UploadFile = File(...),
    storage_type: str = Form("persistent"),
    session_id: Optional[str] = Form(None)
):
    """Upload a document to the knowledge base"""
    # Check file size (10MB limit)
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File size exceeds 10MB limit")
    
    # Determine file type
    filename = file.filename or "unknown"
    file_ext = filename.split(".")[-1].lower() if "." in filename else ""
    
    supported_types = ["pdf", "docx", "xlsx", "pptx", "txt"]
    if file_ext not in supported_types:
        raise HTTPException(status_code=400, detail=f"Unsupported file type. Supported: {', '.join(supported_types)}")
    
    # Extract text from file
    extracted_text = extract_text_from_file(content, file_ext)
    if not extracted_text:
        raise HTTPException(status_code=400, detail="Could not extract text from file")
    
    # Create document record
    doc = KnowledgeDocument(
        name=filename,
        file_type=file_ext,
        content=extracted_text,
        storage_type=storage_type,
        session_id=session_id if storage_type == "session" else None,
        file_size=len(content)
    )
    
    doc_dict = doc.model_dump()
    doc_dict['_id'] = doc_dict['id']
    await db.knowledge_documents.insert_one(doc_dict)
    
    logger.info(f"Uploaded document: {filename}, type: {file_ext}, size: {len(content)} bytes, extracted: {len(extracted_text)} chars")
    
    return {
        "id": doc.id,
        "name": doc.name,
        "file_type": doc.file_type,
        "storage_type": doc.storage_type,
        "content_length": len(extracted_text),
        "file_size": doc.file_size,
        "created_at": doc.created_at.isoformat()
    }

@api_router.post("/knowledge/note")
async def create_knowledge_note(
    title: str = Form(...),
    content: str = Form(...),
    storage_type: str = Form("persistent"),
    session_id: Optional[str] = Form(None)
):
    """Create a text note in the knowledge base"""
    if not content.strip():
        raise HTTPException(status_code=400, detail="Note content cannot be empty")
    
    note = KnowledgeNote(
        title=title,
        content=content,
        storage_type=storage_type,
        session_id=session_id if storage_type == "session" else None
    )
    
    note_dict = note.model_dump()
    note_dict['_id'] = note_dict['id']
    await db.knowledge_notes.insert_one(note_dict)
    
    return {
        "id": note.id,
        "title": note.title,
        "storage_type": note.storage_type,
        "content_length": len(content),
        "created_at": note.created_at.isoformat()
    }

@api_router.get("/knowledge")
async def get_knowledge_base(session_id: Optional[str] = None):
    """Get all knowledge base items"""
    # Get persistent documents
    persistent_docs = await db.knowledge_documents.find({"storage_type": "persistent"}).to_list(100)
    
    # Get session documents if session_id provided
    session_docs = []
    if session_id:
        session_docs = await db.knowledge_documents.find({
            "storage_type": "session",
            "session_id": session_id
        }).to_list(50)
    
    # Get persistent notes
    persistent_notes = await db.knowledge_notes.find({"storage_type": "persistent"}).to_list(100)
    
    # Get session notes
    session_notes = []
    if session_id:
        session_notes = await db.knowledge_notes.find({
            "storage_type": "session",
            "session_id": session_id
        }).to_list(50)
    
    # Format response
    documents = []
    for doc in persistent_docs + session_docs:
        documents.append({
            "id": doc.get("id"),
            "name": doc.get("name"),
            "file_type": doc.get("file_type"),
            "storage_type": doc.get("storage_type"),
            "content_preview": doc.get("content", "")[:200] + "..." if len(doc.get("content", "")) > 200 else doc.get("content", ""),
            "file_size": doc.get("file_size", 0),
            "created_at": doc.get("created_at").isoformat() if doc.get("created_at") else None
        })
    
    notes = []
    for note in persistent_notes + session_notes:
        notes.append({
            "id": note.get("id"),
            "title": note.get("title"),
            "storage_type": note.get("storage_type"),
            "content_preview": note.get("content", "")[:200] + "..." if len(note.get("content", "")) > 200 else note.get("content", ""),
            "created_at": note.get("created_at").isoformat() if note.get("created_at") else None
        })
    
    return {
        "documents": documents,
        "notes": notes,
        "total_documents": len(documents),
        "total_notes": len(notes)
    }

@api_router.delete("/knowledge/document/{doc_id}")
async def delete_knowledge_document(doc_id: str):
    """Delete a document from knowledge base"""
    result = await db.knowledge_documents.delete_one({"id": doc_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"message": "Document deleted successfully"}

@api_router.delete("/knowledge/note/{note_id}")
async def delete_knowledge_note(note_id: str):
    """Delete a note from knowledge base"""
    result = await db.knowledge_notes.delete_one({"id": note_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Note not found")
    return {"message": "Note deleted successfully"}

@api_router.delete("/knowledge/session/{session_id}")
async def clear_session_knowledge(session_id: str):
    """Clear all session-specific knowledge base items"""
    await db.knowledge_documents.delete_many({"storage_type": "session", "session_id": session_id})
    await db.knowledge_notes.delete_many({"storage_type": "session", "session_id": session_id})
    return {"message": "Session knowledge cleared"}

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
