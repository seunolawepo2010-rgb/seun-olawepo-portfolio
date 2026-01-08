from fastapi import FastAPI, APIRouter, HTTPException
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

# Get the Emergent LLM Key
EMERGENT_LLM_KEY = os.environ.get('EMERGENT_LLM_KEY', '')

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

class Session(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    mode: str
    context: List[str] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class StatusCheck(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class StatusCheckCreate(BaseModel):
    client_name: str

# ==================== System Prompts ====================

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

async def get_ai_suggestions(transcript: str, mode: str, context: List[str], session_id: str) -> dict:
    """Generate AI-powered response suggestions"""
    try:
        mode_prompt = MODE_PROMPTS.get(mode, MODE_PROMPTS["general"])
        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(mode_prompt=mode_prompt)
        
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
    return {"message": "Whisprly API is running", "version": "1.0.0"}

@api_router.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

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

@api_router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a session"""
    result = await db.sessions.delete_one({"id": session_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"message": "Session deleted successfully"}

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
