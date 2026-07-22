import os
import tempfile
import shutil
from fastapi import UploadFile, HTTPException
import yt_dlp
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
            result = whisper_model.transcribe(tmp_path, language="pt")
            text = result["text"]
            
            # Cleanup
            os.remove(tmp_path)
            
            return {"text": text.strip()}
        except Exception as e:
            logger.error(f"Error transcribing audio: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to transcribe audio.")

    async def transcribe_youtube(self, url: str):
        if whisper_model is None:
            raise HTTPException(status_code=503, detail="Whisper model is not loaded.")
            
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                ydl_opts = {
                    'format': 'bestaudio/best',
                    'outtmpl': os.path.join(tmpdir, 'audio.%(ext)s'),
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '192',
                    }],
                    'quiet': True
                }
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])
                
                audio_path = os.path.join(tmpdir, 'audio.mp3')
                
                result = whisper_model.transcribe(audio_path, language="pt")
                text = result["text"]
                
                return {"text": text.strip()}
        except Exception as e:
            logger.error(f"Error transcribing YouTube URL: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to transcribe YouTube video.")
