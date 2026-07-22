import os
import json
import logging
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx

app = FastAPI()

# Allow CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ChatRequest(BaseModel):
    model: str
    messages: list[dict]

@app.get("/api/models")
async def get_models():
    """Fetch available models from Ollama."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{OLLAMA_URL}/api/tags", timeout=5.0)
            response.raise_for_status()
            data = response.json()
            return {"models": data.get("models", [])}
    except Exception as e:
        logger.error(f"Error fetching models from Ollama: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to communicate with Ollama to fetch models.")

@app.post("/api/chat")
async def chat(request: ChatRequest):
    """Send chat messages to Ollama and stream the response."""
    if not request.model:
        raise HTTPException(status_code=400, detail="Model is required.")

    async def stream_generator():
        try:
            async with httpx.AsyncClient() as client:
                payload = {
                    "model": request.model,
                    "messages": request.messages,
                    "stream": True
                }
                async with client.stream("POST", f"{OLLAMA_URL}/api/chat", json=payload, timeout=None) as response:
                    if response.status_code != 200:
                        error_text = await response.aread()
                        logger.error(f"Ollama chat error: {error_text}")
                        yield json.dumps({"error": "Failed to communicate with Ollama during chat."}) + "\n"
                        return

                    async for line in response.aiter_lines():
                        if line:
                            yield line + "\n"
        except Exception as e:
            logger.error(f"Error during streaming chat: {str(e)}")
            yield json.dumps({"error": "An unexpected error occurred during chat."}) + "\n"

    return StreamingResponse(stream_generator(), media_type="application/x-ndjson")

@app.get("/health")
def health():
    return {"status": "ok"}
