"""
gemini_router.py  —  FastAPI Router for Gemini Flash
=====================================================
Endpoints:
  POST /gemini/advisory    — text inputs → advisory text + audio
  POST /gemini/transcribe  — audio upload → transcribed text
  POST /gemini/full-flow   — audio upload → full STT+LLM+TTS pipeline
  GET  /gemini/audio/{filename} — serve generated audio files

Usage:
  Register in server.py:
    from gemini_module.gemini_router import router as gemini_router
    app.include_router(gemini_router)
"""

import os
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel

from .gemini_handler import (
    transcribe_audio,
    generate_advisory,
    text_to_speech,
    run_full_flow,
)

router = APIRouter(prefix="/gemini", tags=["Gemini Flash AI"])

AUDIO_DIR = Path(__file__).parent.parent / "audio_output"
AUDIO_DIR.mkdir(exist_ok=True)

LANGUAGE_CHOICES = ["en", "te", "hi", "mr", "ta", "kn", "ml"]


# ─────────────────────────────────────────────────────────────────────────────
# Request / Response Models
# ─────────────────────────────────────────────────────────────────────────────

class AdvisoryRequest(BaseModel):
    city:     str
    crop:     str
    state:    Optional[str] = "India"
    language: Optional[str] = "en"

class AdvisoryResponse(BaseModel):
    city:          str
    crop:          str
    state:         str
    language:      str
    advisory_text: str
    audio_url:     str
    weather:       dict
    news_summary:  str


# ─────────────────────────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/advisory",
    summary="Generate farmer advisory (text input → advisory text + audio)",
    response_model=AdvisoryResponse,
)
async def advisory_endpoint(req: AdvisoryRequest):
    """
    Provide **city + crop** (+ optional state/language) and receive:
    - A contextual farming advisory powered by Gemini Flash
    - Live weather data for the farmer's location
    - Top news summary from the news scraper
    - A generated audio file (WAV) with the advisory spoken aloud

    This is the **main endpoint** for the voice assistant backend.
    """
    if req.language not in LANGUAGE_CHOICES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid language '{req.language}'. Choose from: {LANGUAGE_CHOICES}"
        )

    # Fetch weather
    weather_data = {}
    try:
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from weather import get_weather
        weather_data = get_weather(req.city)
    except Exception as e:
        print(f"[WARN] Weather fetch failed: {e}")

    # Fetch news
    news_summary = ""
    try:
        from news_scrapper_api.news_api import get_farmer_news
        news_result  = get_farmer_news(
            city=req.city, crop=req.crop,
            state=req.state, language=req.language, limit=5
        )
        news_summary = news_result.get("llm_summary", "")
        if not weather_data:
            weather_data = news_result.get("weather", {})
    except Exception as e:
        print(f"[WARN] News fetch failed: {e}")

    # Generate advisory text
    try:
        advisory_text = generate_advisory(
            city=req.city,
            crop=req.crop,
            state=req.state,
            language=req.language,
            weather=weather_data,
            news_summary=news_summary,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Advisory generation failed: {e}")

    # Generate TTS audio
    try:
        audio_path = text_to_speech(
            advisory_text,
            language=req.language,
            filename="advisory_output.wav"
        )
        audio_url = "/gemini/audio/advisory_output.wav"
    except Exception as e:
        print(f"[WARN] TTS failed: {e}")
        audio_url = ""

    return AdvisoryResponse(
        city=req.city,
        crop=req.crop,
        state=req.state or "India",
        language=req.language,
        advisory_text=advisory_text,
        audio_url=audio_url,
        weather=weather_data,
        news_summary=news_summary,
    )


@router.post(
    "/transcribe",
    summary="Transcribe farmer audio to text (STT)",
)
async def transcribe_endpoint(
    audio: UploadFile = File(..., description="Audio file (WAV/MP3/OGG/WEBM)"),
):
    """
    Upload a farmer's audio clip and receive the transcribed text.
    Supports Telugu, Hindi, Marathi, Tamil, Kannada, Malayalam, and English.
    """
    audio_bytes = await audio.read()
    mime_type   = audio.content_type or "audio/wav"

    try:
        text = transcribe_audio(audio_bytes, mime_type)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {e}")

    return {"transcription": text, "filename": audio.filename}


@router.post(
    "/full-flow",
    summary="Full pipeline: audio → STT → weather+news → advisory → TTS audio",
)
async def full_flow_endpoint(
    audio:    UploadFile = File(..., description="Farmer's audio clip"),
    language: str        = Query("en", description="Language code: en/te/hi/mr/ta/kn/ml"),
    city:     Optional[str] = Query(None, description="Override city (skip extraction from audio)"),
    crop:     Optional[str] = Query(None, description="Override crop (skip extraction from audio)"),
    state:    Optional[str] = Query(None, description="Farmer's state"),
):
    """
    **One-stop endpoint for the full farmer advisory pipeline:**

    1. 🎙️ **STT** — Transcribes the farmer's audio
    2. 🌾 **Extract** — Detects city, crop, state from speech (or use query params)
    3. 🌤️ **Weather** — Fetches live weather for the farmer's location
    4. 📰 **News** — Gets hyperlocal agri news relevant to their crop
    5. 🤖 **Advisory** — Gemini Flash generates a contextual advisory
    6. 🔊 **TTS** — Converts advisory to spoken audio

    Returns all data + a link to the generated audio file.
    """
    if language not in LANGUAGE_CHOICES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid language '{language}'. Choose from: {LANGUAGE_CHOICES}"
        )

    audio_bytes = await audio.read()
    mime_type   = audio.content_type or "audio/wav"

    try:
        result = run_full_flow(
            audio_bytes=audio_bytes,
            mime_type=mime_type,
            language=language,
            city=city,
            crop=crop,
            state=state,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Full flow failed: {e}")

    result["audio_url"] = "/gemini/audio/advisory_output.wav"
    return result


@router.get(
    "/audio/{filename}",
    summary="Download a generated audio advisory file",
)
async def serve_audio(filename: str):
    """Serve generated audio files from the audio_output/ directory."""
    # Sanitize filename (no path traversal)
    safe_name = Path(filename).name
    file_path = AUDIO_DIR / safe_name

    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"Audio file '{safe_name}' not found.")

    return FileResponse(
        path=str(file_path),
        media_type="audio/wav",
        filename=safe_name,
    )
