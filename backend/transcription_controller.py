import os
import tempfile
import shutil
from fastapi import UploadFile, HTTPException
from config import logger, whisper_model

class TranscriptionController:
    async def transcribe(self, audio: UploadFile):
        if whisper_model is None:
            raise HTTPException(status_code=503, detail="Whisper model is not loaded.")
            
        try:
            # Save to a temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as tmp:
                shutil.copyfileobj(audio.file, tmp)
                tmp_path = tmp.name

            # Transcribe with fixed Brazilian Portuguese language
            segments, info = whisper_model.transcribe(tmp_path, beam_size=5, language="pt")
            text = "".join([segment.text for segment in segments])
            
            # Cleanup
            os.remove(tmp_path)
            
            return {"text": text.strip()}
        except Exception as e:
            logger.error(f"Error transcribing audio: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to transcribe audio.")
