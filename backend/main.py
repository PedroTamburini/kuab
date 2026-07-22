import os
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from config import logger
from llm_controller import LLMController
from transcription_controller import TranscriptionController

app = FastAPI()
llm_controller = LLMController()
transcription_controller = TranscriptionController()

# Allow CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    model: str
    messages: list[dict]

@app.get("/api/models")
async def get_models():
    """Fetch available models from Ollama via the LLM Controller."""
    try:
        models = await llm_controller.get_models()
        return {"models": models}
    except Exception as e:
        logger.error(f"Error fetching models from Ollama: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to communicate with Ollama to fetch models.")

@app.post("/api/chat")
async def chat(request: ChatRequest):
    """Send chat messages to Ollama and stream the response."""
    if not request.model:
        raise HTTPException(status_code=400, detail="Model is required.")

    return StreamingResponse(
        llm_controller.stream_chat(request.model, request.messages),
        media_type="application/x-ndjson"
    )

@app.post("/api/transcribe")
async def transcribe_audio(audio: UploadFile = File(...)):
    """Transcribe an uploaded audio file using Whisper."""
    return await transcription_controller.transcribe(audio)

class YoutubeRequest(BaseModel):
    url: str

@app.post("/api/transcribe-youtube")
async def transcribe_youtube(request: YoutubeRequest):
    """Transcribe a YouTube video audio using Whisper."""
    return await transcription_controller.transcribe_youtube(request.url)

@app.get("/health")
def health():
    return {"status": "ok"}
