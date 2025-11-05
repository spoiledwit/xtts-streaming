import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from model.model import Model

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global model instance
model_instance = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load model on startup and cleanup on shutdown"""
    global model_instance
    logger.info("Loading XTTS model...")
    model_instance = Model()
    model_instance.load()
    logger.info("Model loaded successfully")
    yield
    logger.info("Shutting down...")


app = FastAPI(
    title="XTTS Streaming API",
    description="Text-to-Speech API with streaming support using XTTS v2",
    version="1.0.0",
    lifespan=lifespan,
)


class TTSRequest(BaseModel):
    text: str = Field(..., description="Text to convert to speech")
    language: str = Field(default="en", description="Language code (e.g., 'en', 'es', 'fr')")
    chunk_size: int = Field(default=20, ge=1, le=100, description="Chunk size for streaming")


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "XTTS Streaming API",
        "model": "xtts_v2"
    }


@app.post("/synthesize")
async def synthesize_speech(request: TTSRequest):
    """
    Synthesize speech from text with streaming response.

    Returns raw PCM audio (16-bit, 24000Hz, mono).
    """
    logger.info(f"Synthesizing text: {request.text[:50]}...")

    def generate_audio():
        """Generator function for streaming audio chunks"""
        try:
            model_input = {
                "text": request.text,
                "language": request.language,
                "chunk_size": request.chunk_size,
            }

            for chunk in model_instance.predict(model_input):
                yield chunk

        except Exception as e:
            logger.error(f"Error during synthesis: {str(e)}")
            raise

    return StreamingResponse(
        generate_audio(),
        media_type="audio/pcm",
        headers={
            "X-Sample-Rate": "24000",
            "X-Bit-Depth": "16",
            "X-Channels": "1",
        },
    )


@app.post("/synthesize-wav")
async def synthesize_speech_wav(request: TTSRequest):
    """
    Synthesize speech from text and return as WAV format.

    Returns WAV audio file.
    """
    import io
    import wave

    logger.info(f"Synthesizing WAV text: {request.text[:50]}...")

    def generate_wav():
        """Generator function for streaming WAV audio"""
        buffer = io.BytesIO()

        # Create WAV file in memory
        with wave.open(buffer, 'wb') as wav_file:
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(24000)  # 24kHz

            model_input = {
                "text": request.text,
                "language": request.language,
                "chunk_size": request.chunk_size,
            }

            for chunk in model_instance.predict(model_input):
                wav_file.writeframes(chunk)

        # Get the complete WAV file
        buffer.seek(0)
        return buffer.read()

    wav_data = generate_wav()

    return StreamingResponse(
        io.BytesIO(wav_data),
        media_type="audio/wav",
        headers={
            "Content-Disposition": "attachment; filename=speech.wav"
        },
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)