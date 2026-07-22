import os
import logging
import whisper

# Logging configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("kuab_backend")

# Ollama settings
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")

# Initialize Whisper Model (Global Context)
logger.info("Loading Whisper model (base)...")
try:
    whisper_model = whisper.load_model("base", device="cpu")
    logger.info("Whisper model loaded successfully.")
except Exception as e:
    logger.error(f"Failed to load whisper model: {e}")
    whisper_model = None
