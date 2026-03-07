"""
news_router.py  —  FastAPI Router v2
=====================================
Exposes the advanced farmer news scraper as a REST endpoint.

Endpoint:
    GET /news

Query Parameters:
    city     (required) : Farmer's city or village
    crop     (required) : Crop the farmer grows
    state    (optional) : Farmer's state
    language (optional) : Language code — 'te','hi','mr','ta','kn','ml','en' (default: 'en')
    limit    (optional) : Articles per category (default: 5, max: 15)

Response (v2 — categorized):
    {
      "query":        { city, crop, state, language },
      "weather":      { temperature, humidity, condition, forecast },
      "crop_news":    [ {title, url, source, published, score} ],
      "weather_news": [ ... ],
      "market_news":  [ ... ],
      "pest_alerts":  [ ... ],
      "govt_schemes": [ ... ],
      "llm_summary":  "Ready-to-read paragraph for the LLM voice assistant"
    }
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional, Literal
from .news_api import get_farmer_news

router = APIRouter(prefix="/news", tags=["Farmer News"])

LANGUAGE_CHOICES = Literal["en", "te", "hi", "mr", "ta", "kn", "ml"]
LANGUAGE_NAMES = {
    "en": "English", "te": "Telugu", "hi": "Hindi",
    "mr": "Marathi",  "ta": "Tamil",  "kn": "Kannada", "ml": "Malayalam",
}


@router.get("/", summary="Get hyperlocal, categorized agri-news for a farmer")
def fetch_news(
    city: str = Query(
        ..., description="Farmer's city or village name", examples=["Ongole", "Nashik"]
    ),
    crop: str = Query(
        ..., description="Crop the farmer is growing", examples=["rice", "wheat", "cotton"]
    ),
    state: Optional[str] = Query(
        None, description="Farmer's state for regional news", examples=["Andhra Pradesh", "Punjab"]
    ),
    language: str = Query(
        "en",
        description="Farmer's language code: en / te / hi / mr / ta / kn / ml",
        examples=["te", "hi", "en"],
    ),
    limit: int = Query(
        5, ge=1, le=15,
        description="Max articles per category"
    ),
):
    """
    Fetch **hyperlocal, categorized agricultural news** tailored to a farmer's
    city, crop, state, and language.

    Returns five category buckets plus a **`llm_summary`** — a plain paragraph
    your LLM voice assistant can read directly to the farmer over the call.

    **Category buckets:**
    - `crop_news`    — news specific to the farmer's crop
    - `weather_news` — rain, flood, drought, cyclone alerts
    - `market_news`  — mandi prices, MSP, market trends
    - `pest_alerts`  — pest/disease warnings
    - `govt_schemes` — subsidies, PM Kisan, Fasal Bima, etc.
    """
    if language not in LANGUAGE_NAMES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid language '{language}'. Choose from: {list(LANGUAGE_NAMES.keys())}",
        )

    try:
        result = get_farmer_news(
            city=city.strip(),
            crop=crop.strip(),
            state=state.strip() if state else None,
            language=language,
            limit=limit,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"News fetch failed: {str(e)}")

    total_articles = sum(
        len(result.get(cat, []))
        for cat in ["crop_news", "weather_news", "market_news", "pest_alerts", "govt_schemes"]
    )

    return {
        "query": {
            "city":     city,
            "crop":     crop,
            "state":    state or "India (national)",
            "language": LANGUAGE_NAMES.get(language, language),
        },
        "total_articles": total_articles,
        "weather":      result.get("weather", {}),
        "llm_summary":  result.get("llm_summary", ""),
        "crop_news":    result.get("crop_news", []),
        "weather_news": result.get("weather_news", []),
        "market_news":  result.get("market_news", []),
        "pest_alerts":  result.get("pest_alerts", []),
        "govt_schemes": result.get("govt_schemes", []),
    }
