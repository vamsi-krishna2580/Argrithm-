"""
gemini_handler.py  —  Gemini Flash 2.0 Integration
=====================================================
Provides three capabilities powered by Google Gemini Flash:
  1. STT  : transcribe_audio(audio_bytes)         → text
  2. LLM  : generate_advisory(...)                → advisory text
  3. TTS  : text_to_speech(text, language)        → saves WAV, returns path
  4. FLOW : run_full_flow(audio_bytes, language)  → full pipeline dict

Integrates with:
  - weather API   (OpenWeatherMap via weather.py)
  - news scraper  (news_scrapper_api.news_api.get_farmer_news)
"""

import os
import re
import sys
import base64
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

from google import genai
from google.genai import types

# ── API key setup ──────────────────────────────────────────────────────────────
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY is not set in your .env file!")

client = genai.Client(api_key=GEMINI_API_KEY)

# ── Model names ────────────────────────────────────────────────────────────────
STT_MODEL = "gemini-2.0-flash"          # audio input → text
LLM_MODEL = "gemini-2.0-flash"          # text advisory generation
TTS_MODEL = "gemini-2.5-flash-preview-tts"  # text → audio

# ── Language → spoken name map ─────────────────────────────────────────────────
LANG_NAMES = {
    "en": "English", "te": "Telugu",  "hi": "Hindi",
    "mr": "Marathi", "ta": "Tamil",   "kn": "Kannada", "ml": "Malayalam",
}

# ── Audio output directory ─────────────────────────────────────────────────────
AUDIO_DIR = Path(__file__).parent.parent / "audio_output"
AUDIO_DIR.mkdir(exist_ok=True)


# ─────────────────────────────────────────────────────────────────────────────
# 1. STT — Speech to Text
# ─────────────────────────────────────────────────────────────────────────────

def transcribe_audio(audio_bytes: bytes, mime_type: str = "audio/wav") -> str:
    """Transcribe farmer's audio using Gemini Flash."""
    prompt = (
        "You are a speech transcription assistant for Indian farmers. "
        "Transcribe the following audio exactly as spoken. "
        "The farmer may speak Telugu, Hindi, Marathi, Tamil, Kannada, Malayalam, or English. "
        "Return ONLY the transcribed text, nothing else."
    )
    response = client.models.generate_content(
        model=STT_MODEL,
        contents=[
            prompt,
            types.Part.from_bytes(data=audio_bytes, mime_type=mime_type),
        ],
    )
    return response.text.strip()


# ─────────────────────────────────────────────────────────────────────────────
# 2. LLM — Generate Farmer Advisory
# ─────────────────────────────────────────────────────────────────────────────

def generate_advisory(
    city: str,
    crop: str,
    state: str = "India",
    language: str = "en",
    weather: Optional[dict] = None,
    news_summary: Optional[str] = None,
) -> str:
    """
    Generate a contextual farming advisory using Gemini Flash with live weather + news data.
    """
    lang_name = LANG_NAMES.get(language, "English")

    context_parts = []
    if weather:
        context_parts.append(
            f"WEATHER in {city}:\n"
            f"  Condition  : {weather.get('condition', 'N/A')}\n"
            f"  Temperature: {weather.get('temperature', 'N/A')}°C\n"
            f"  Humidity   : {weather.get('humidity', 'N/A')}%\n"
            f"  Wind Speed : {weather.get('wind_speed', 'N/A')} m/s\n"
            + (f"  Forecast   : {'; '.join(weather['forecast'][:2])}" if weather.get('forecast') else "")
        )
    if news_summary:
        context_parts.append(f"LATEST AGRICULTURAL NEWS:\n{news_summary}")

    context_block = "\n\n".join(context_parts) if context_parts else "No live data available."

    prompt = f"""You are a friendly agricultural advisory AI for Indian farmers.
A farmer from {city}, {state} grows {crop}.

Live data:
{context_block}

Task: Give a SHORT, PRACTICAL farming advisory in {lang_name} (2–4 sentences).
- Start with weather and how it affects {crop}.
- Mention any pest/market alert if relevant.
- End with ONE actionable tip for today.
- Speak directly to the farmer. Simple words only. Under 100 words.

Advisory:"""

    response = client.models.generate_content(model=LLM_MODEL, contents=prompt)
    return response.text.strip()


# ─────────────────────────────────────────────────────────────────────────────
# 3. TTS — Text to Speech
# ─────────────────────────────────────────────────────────────────────────────

def text_to_speech(text: str, language: str = "en", filename: str = "advisory.wav") -> str:
    """Convert advisory text to speech using Gemini TTS. Returns path to saved WAV file."""
    lang_name = LANG_NAMES.get(language, "English")

    tts_prompt = (
        f"Speak the following farming advisory to an Indian farmer in {lang_name}. "
        f"Use a warm, clear, and calm voice:\n\n{text}"
    )

    response = client.models.generate_content(
        model=TTS_MODEL,
        contents=tts_prompt,
        config=types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Kore")
                )
            ),
        ),
    )

    # Extract and save audio
    audio_data = response.candidates[0].content.parts[0].inline_data.data
    if isinstance(audio_data, str):
        audio_bytes = base64.b64decode(audio_data)
    else:
        audio_bytes = audio_data

    out_path = AUDIO_DIR / filename
    with open(out_path, "wb") as f:
        f.write(audio_bytes)

    return str(out_path)


# ─────────────────────────────────────────────────────────────────────────────
# 4. FULL FLOW — Audio in → Advisory Audio out
# ─────────────────────────────────────────────────────────────────────────────

def run_full_flow(
    audio_bytes: bytes,
    mime_type: str = "audio/wav",
    language: str = "en",
    city: Optional[str] = None,
    crop: Optional[str] = None,
    state: Optional[str] = None,
) -> dict:
    """
    Full pipeline: audio_bytes → STT → fetch weather+news → advisory → TTS → return dict.
    """
    # Step 1: Transcribe
    transcription = transcribe_audio(audio_bytes, mime_type)

    # Step 2: Extract city/crop if not provided
    if not city or not crop:
        city, crop, state = _extract_farmer_info(transcription, state)
    state = state or "India"

    # Step 3: Fetch weather
    weather_data = {}
    try:
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from weather import get_weather
        weather_data = get_weather(city)
    except Exception as e:
        print(f"[WARN] Weather: {e}")

    # Step 4: Fetch news
    news_summary = ""
    try:
        from news_scrapper_api.news_api import get_farmer_news
        news_result  = get_farmer_news(city=city, crop=crop, state=state, language=language, limit=5)
        news_summary = news_result.get("llm_summary", "")
        if not weather_data:
            weather_data = news_result.get("weather", {})
    except Exception as e:
        print(f"[WARN] News: {e}")

    # Step 5: Generate advisory
    advisory_text = generate_advisory(
        city=city, crop=crop, state=state, language=language,
        weather=weather_data, news_summary=news_summary,
    )

    # Step 6: TTS
    audio_path = ""
    try:
        audio_path = text_to_speech(advisory_text, language=language, filename="advisory_output.wav")
    except Exception as e:
        print(f"[WARN] TTS: {e}")

    return {
        "transcription": transcription,
        "city":          city,
        "crop":          crop,
        "state":         state,
        "advisory_text": advisory_text,
        "audio_path":    audio_path,
        "weather":       weather_data,
        "news_summary":  news_summary,
    }


# ─────────────────────────────────────────────────────────────────────────────
# INTERNAL: Extract city/crop using Gemini
# ─────────────────────────────────────────────────────────────────────────────

def _extract_farmer_info(transcription: str, state: Optional[str] = None) -> tuple:
    """Use Gemini to pull city, crop, state from transcription."""
    prompt = f"""Extract farming details from this speech.
Speech: "{transcription}"

Return ONLY valid JSON with keys city, crop, state (null if not found):
{{"city": "...", "crop": "...", "state": "..."}}

JSON:"""

    response = client.models.generate_content(model=LLM_MODEL, contents=prompt)
    raw = response.text.strip()

    try:
        import json
        match = re.search(r'\{.*?\}', raw, re.DOTALL)
        if match:
            data  = json.loads(match.group())
            city  = data.get("city")  or "Unknown"
            crop  = data.get("crop")  or "crops"
            state = data.get("state") or state or "India"
            return city, crop, state
    except Exception:
        pass

    return "Unknown", "crops", state or "India"
