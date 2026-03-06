from fastapi import FastAPI, Request
from weather import get_weather
from news_scrapping import get_local_agri_news
from community_reports import generate_community_alert
from voice import generate_voice
from logger import write_log
from twilio.twiml.voice_response import VoiceResponse, Gather
from news_scrapper_api.news_router import router as news_router   # ← Farmer News Scraper API

app = FastAPI(
    title="AI Farmer Advisory",
    description="Voice + Advisory + News API for farmers",
    version="1.0.0"
)

# Register news scraper API
app.include_router(news_router)


@app.get("/farmer-advisory")
def farmer_advisory(city: str, crop: str):

    write_log("API_REQUEST", {"city": city, "crop": crop})

    weather = get_weather(city)
    write_log("WEATHER_FETCHED", weather)

    news = get_local_agri_news(city)
    write_log("NEWS_FETCHED", news)

    community_alert = generate_community_alert(city)
    write_log("COMMUNITY_ALERT", {"alert": community_alert})

    response = {
        "weather": weather,
        "news": news,
        "community_alert": community_alert
    }

    text = f"""
    Weather condition: {weather['condition']}.
    Temperature {weather['temperature']} degree.

    Community alert: {community_alert}

    Latest news: {news[0]}
    """

    audio = generate_voice(text)

    write_log("VOICE_GENERATED", {"city": city})

    return {"audio": audio, "text": text}


# -----------------------------
# IVR START POINT
# -----------------------------
@app.post("/ivr")
async def ivr(request: Request):

    response = VoiceResponse()

    gather = Gather(
        input="speech",
        action="/process-speech",
        method="POST",
        speechTimeout="auto"
    )

    gather.say(
        "Welcome to AI Farmer Advisory. Please say your city name after the beep.",
        voice="alice"
    )

    response.append(gather)

    return str(response)


# -----------------------------
# PROCESS FARMER SPEECH
# -----------------------------
@app.post("/process-speech")
async def process_speech(request: Request):

    form_data = await request.form()
    city = form_data.get("SpeechResult", "unknown")

    write_log("IVR_SPEECH", {"city_detected": city})

    weather = get_weather(city)
    news = get_local_agri_news(city)
    community_alert = generate_community_alert(city)

    advisory = f"""
    Weather condition in {city} is {weather['condition']}.
    Temperature {weather['temperature']} degree.

    Community alert: {community_alert}

    Latest news: {news[0]}
    """

    response = VoiceResponse()
    response.say(advisory, voice="alice")

    return str(response)