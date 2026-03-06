"""
news_api.py  —  Farmer News Scraper v2
=======================================
Advanced, multi-source, multi-language, categorized news scraper.

Designed to serve an LLM that voices news to farmers over a toll-free call.

Inputs  : city, crop, state, language (from LLM conversation with farmer)
Outputs : Categorized news + llm_summary (ready to read aloud)

Sources:
  1. Google News RSS  — English (hyperlocal + state + national)
  2. Google News RSS  — Farmer's local language (Telugu, Hindi, Marathi …)
  3. Krishi Jagran RSS — Dedicated Indian agri news
  4. The Hindu Agri RSS — Quality agri journalism
  5. IMD Nowcast RSS   — Official weather/disaster alerts
  6. OpenWeatherMap    — Current weather + forecast (reuses existing API key)
"""

import feedparser
import requests
from urllib.parse import quote
from datetime import datetime, timezone
from typing import Optional

# ── Weather API key (already in project) ──────────────────────────────────────
OPENWEATHER_API_KEY = "REMOVED_API_KEY"

# ── Language → Google News locale map ─────────────────────────────────────────
LANGUAGE_MAP = {
    "te": ("te-IN", "IN"),   # Telugu
    "hi": ("hi-IN", "IN"),   # Hindi
    "mr": ("mr-IN", "IN"),   # Marathi
    "ta": ("ta-IN", "IN"),   # Tamil
    "kn": ("kn-IN", "IN"),   # Kannada
    "ml": ("ml-IN", "IN"),   # Malayalam
    "en": ("en-IN", "IN"),   # English (default)
}

# ── Static RSS sources (no API key needed) ────────────────────────────────────
STATIC_SOURCES = {
    "krishi_jagran": "https://krishijagran.com/feed/",
    "the_hindu_agri": "https://www.thehindu.com/sci-tech/agriculture/?service=rss",
    "imd_nowcast":   "https://mausam.imd.gov.in/imd_latest/contents/dist_nowcast_rss.php",
}

# ── Category keyword maps (used to bucket articles) ───────────────────────────
CATEGORY_KEYWORDS = {
    "weather_news": [
        "rain", "rainfall", "flood", "drought", "cyclone", "monsoon",
        "weather", "temperature", "heatwave", "cold wave", "imd", "alert",
        "warning", "storm", "forecast", "humidity", "wind", "thunderstorm",
        "बारिश", "बाढ़", "सूखा", "मानसून",   # Hindi
        "వర్షం", "వరద", "వాతావరణం",           # Telugu
    ],
    "market_news": [
        "mandi", "price", "msp", "market", "rate", "quintal", "apmc",
        "agmarket", "procurement", "export", "import", "commodity",
        "भाव", "मंडी", "दाम",                  # Hindi
        "ధర", "మార్కెట్", "మండి",              # Telugu
    ],
    "pest_alerts": [
        "pest", "disease", "blight", "fungus", "wilt", "infestation",
        "aphid", "locust", "caterpillar", "insect", "spray", "pesticide",
        "कीट", "रोग", "कीटनाशक",               # Hindi
        "చీడ", "వ్యాధి", "పురుగు",             # Telugu
    ],
    "govt_schemes": [
        "scheme", "subsidy", "pm kisan", "fasal bima", "kcc",
        "government", "ministry", "agriculture department", "krishi",
        "loan", "compensation", "relief", "yojana", "mission",
        "योजना", "सब्सिडी", "सरकार",            # Hindi
        "పథకం", "సబ్సిడీ", "ప్రభుత్వం",        # Telugu
    ],
}

# ─────────────────────────────────────────────────────────────────────────────
# INTERNAL HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _google_news_url(query: str, hl: str = "en-IN", gl: str = "IN") -> str:
    lang = hl.split("-")[0]
    return (
        f"https://news.google.com/rss/search"
        f"?q={quote(query)}&hl={hl}&gl={gl}&ceid={gl}:{lang}"
    )


def _parse_date(entry) -> str:
    try:
        t = entry.get("published_parsed") or entry.get("updated_parsed")
        if t:
            return datetime(*t[:6]).strftime("%Y-%m-%d %H:%M")
    except Exception:
        pass
    return entry.get("published", "")


def _fetch_rss(url: str, max_items: int = 20) -> list[dict]:
    """Parse any RSS feed and return a list of raw article dicts."""
    try:
        feed = feedparser.parse(url, request_headers={"User-Agent": "FarmerNewsBot/2.0"})
        articles = []
        for entry in feed.entries[:max_items]:
            articles.append({
                "title":     entry.get("title", "").strip(),
                "url":       entry.get("link", ""),
                "source":    entry.get("source", {}).get("title", "")
                             or feed.feed.get("title", "News"),
                "published": _parse_date(entry),
                "body":      entry.get("summary", "")[:500],
                "category":  "crop_news",   # default, overridden in bucketing
                "score":     0,
            })
        return articles
    except Exception:
        return []


def _score_and_bucket(
    articles: list[dict],
    city: str,
    crop: str,
    state: str,
) -> list[dict]:
    """
    Score each article for relevance and assign it to a category bucket.
    Modifies articles in place.
    """
    city_l  = city.lower()
    crop_l  = crop.lower()
    state_l = state.lower()

    general_agri = [
        "farmer", "farming", "agriculture", "crop", "kisan", "harvest",
        "sowing", "irrigation", "fertilizer", "agrarian", "field", "खेती",
        "किसान", "రైతు", "వ్యవసాయం",
    ]

    for a in articles:
        text = (a["title"] + " " + a["body"]).lower()

        # Relevance score
        score = 0
        if city_l  in text: score += 4
        if crop_l  in text: score += 4
        if state_l in text: score += 2
        for w in general_agri:
            if w in text: score += 1
        a["score"] = score

        # Category bucketing (first match wins, else stays crop_news)
        for cat, keywords in CATEGORY_KEYWORDS.items():
            if any(kw in text for kw in keywords):
                a["category"] = cat
                break

        # Cleanup: remove body (was only needed for scoring/bucketing)
        a.pop("body", None)

    return articles


def _get_weather_summary(city: str, state: str) -> dict:
    """Fetch current weather + 5-day forecast from OpenWeatherMap."""
    try:
        # Geocode city
        geo_url = (
            f"http://api.openweathermap.org/geo/1.0/direct"
            f"?q={quote(city)},IN&limit=1&appid={OPENWEATHER_API_KEY}"
        )
        geo = requests.get(geo_url, timeout=5).json()
        if not geo:
            return {}
        lat, lon = geo[0]["lat"], geo[0]["lon"]

        # Current weather
        cur_url = (
            f"https://api.openweathermap.org/data/2.5/weather"
            f"?lat={lat}&lon={lon}&appid={OPENWEATHER_API_KEY}&units=metric"
        )
        cur = requests.get(cur_url, timeout=5).json()

        # 5-day forecast (every 3 hrs, we pick next 3 slots = ~9 hrs)
        fc_url = (
            f"https://api.openweathermap.org/data/2.5/forecast"
            f"?lat={lat}&lon={lon}&appid={OPENWEATHER_API_KEY}&units=metric&cnt=4"
        )
        fc = requests.get(fc_url, timeout=5).json()
        forecast_items = fc.get("list", [])

        forecast_desc = []
        for slot in forecast_items:
            dt  = datetime.fromtimestamp(slot["dt"]).strftime("%d %b %H:%M")
            cond = slot["weather"][0]["description"].capitalize()
            temp = slot["main"]["temp"]
            forecast_desc.append(f"{dt}: {cond}, {temp}°C")

        return {
            "city":        city,
            "temperature": cur["main"]["temp"],
            "feels_like":  cur["main"]["feels_like"],
            "humidity":    cur["main"]["humidity"],
            "condition":   cur["weather"][0]["description"].capitalize(),
            "wind_speed":  cur["wind"]["speed"],
            "forecast":    forecast_desc,
        }
    except Exception:
        return {}


def _build_llm_summary(
    weather: dict,
    categorized: dict[str, list],
    city: str,
    crop: str,
    language: str,
) -> str:
    """
    Build a short, plain-language paragraph the LLM can read aloud to the farmer.
    Always in English (LLM will translate if needed based on farmer's language).
    """
    parts = []

    # Weather block
    if weather:
        parts.append(
            f"Current weather in {city}: {weather['condition']}, "
            f"{weather['temperature']}°C, humidity {weather['humidity']}%."
        )
        if weather.get("forecast"):
            parts.append(f"Forecast: {weather['forecast'][0]}.")

    # Top crop news
    crop_items = categorized.get("crop_news", [])
    if crop_items:
        parts.append(f"Latest {crop} news: {crop_items[0]['title']}.")

    # Market price news
    market_items = categorized.get("market_news", [])
    if market_items:
        parts.append(f"Market update: {market_items[0]['title']}.")

    # Pest alert
    pest_items = categorized.get("pest_alerts", [])
    if pest_items:
        parts.append(f"Pest alert: {pest_items[0]['title']}.")

    # Weather news (separate from OWM)
    wx_items = categorized.get("weather_news", [])
    if wx_items:
        parts.append(f"Weather advisory: {wx_items[0]['title']}.")

    # Govt scheme
    govt_items = categorized.get("govt_schemes", [])
    if govt_items:
        parts.append(f"Government update: {govt_items[0]['title']}.")

    if not parts:
        return f"No specific news found for {crop} farmers in {city} right now."

    return " ".join(parts)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN PUBLIC FUNCTION
# ─────────────────────────────────────────────────────────────────────────────

def get_farmer_news(
    city: str,
    crop: str,
    state: Optional[str] = None,
    language: str = "en",
    limit: int = 10,
) -> dict:
    """
    Fetch hyperlocal, categorized agricultural news for a farmer.

    Args:
        city     : Farmer's city/village (e.g. "Ongole")
        crop     : Crop the farmer grows (e.g. "rice")
        state    : Farmer's state — improves regional relevance (e.g. "Andhra Pradesh")
        language : Farmer's language code: 'te', 'hi', 'mr', 'ta', 'kn', 'ml', 'en'
        limit    : Max articles per category (default 10, total capped at limit*5)

    Returns:
        {
          "weather":      { city, temperature, humidity, condition, forecast },
          "crop_news":    [ {title, url, source, published, score}, ... ],
          "weather_news": [ ... ],
          "market_news":  [ ... ],
          "pest_alerts":  [ ... ],
          "govt_schemes": [ ... ],
          "llm_summary":  "Plain English paragraph for LLM to read aloud"
        }
    """
    if not city or not crop:
        raise ValueError("Both 'city' and 'crop' are required.")

    state_str = state or "India"
    hl, gl    = LANGUAGE_MAP.get(language, ("en-IN", "IN"))

    all_articles:  list[dict] = []
    seen_urls:     set[str]   = set()

    # ── 1. Google News — English queries (hyperlocal → state → national) ──────
    en_queries = [
        f'"{crop}" farming "{city}"',
        f'"{crop}" agriculture "{state_str}"',
        f'agriculture farming "{city}" OR "{state_str}"',
        f'{crop} crop pest disease alert India',
        f'{crop} mandi price market India',
        f'PM Kisan farmer scheme {state_str}',
        f'weather alert flood drought {state_str} farmer',
    ]
    for q in en_queries:
        for art in _fetch_rss(_google_news_url(q, hl="en-IN", gl="IN"), max_items=10):
            if art["url"] not in seen_urls:
                seen_urls.add(art["url"])
                all_articles.append(art)

    # ── 2. Google News — Farmer's local language (if not English) ─────────────
    if language != "en":
        local_queries = [
            f"{crop} {city}",
            f"{crop} {state_str} కొత్త వార్తలు" if language == "te"
            else f"{crop} {state_str} ताजा खबर" if language == "hi"
            else f"{crop} {state_str} agriculture",
        ]
        for q in local_queries:
            for art in _fetch_rss(_google_news_url(q, hl=hl, gl=gl), max_items=10):
                if art["url"] not in seen_urls:
                    seen_urls.add(art["url"])
                    all_articles.append(art)

    # ── 3. Krishi Jagran — dedicated Indian agri RSS ──────────────────────────
    for art in _fetch_rss(STATIC_SOURCES["krishi_jagran"], max_items=15):
        if art["url"] not in seen_urls:
            seen_urls.add(art["url"])
            all_articles.append(art)

    # ── 4. The Hindu Agriculture section ─────────────────────────────────────
    for art in _fetch_rss(STATIC_SOURCES["the_hindu_agri"], max_items=10):
        if art["url"] not in seen_urls:
            seen_urls.add(art["url"])
            all_articles.append(art)

    # ── 5. IMD District Nowcast (weather/disaster alerts) ────────────────────
    for art in _fetch_rss(STATIC_SOURCES["imd_nowcast"], max_items=10):
        if art["url"] not in seen_urls:
            seen_urls.add(art["url"])
            all_articles.append(art)

    # ── Score + bucket all articles ───────────────────────────────────────────
    _score_and_bucket(all_articles, city, crop, state_str)

    # Sort by score globally, then split into categories
    all_articles.sort(key=lambda x: x["score"], reverse=True)

    categorized: dict[str, list] = {
        "crop_news":    [],
        "weather_news": [],
        "market_news":  [],
        "pest_alerts":  [],
        "govt_schemes": [],
    }
    for art in all_articles:
        cat = art.get("category", "crop_news")
        bucket = categorized.get(cat, categorized["crop_news"])
        if len(bucket) < limit:
            bucket.append({k: v for k, v in art.items() if k != "category"})

    # ── Weather from OpenWeatherMap ───────────────────────────────────────────
    weather = _get_weather_summary(city, state_str)

    # ── Build LLM summary ─────────────────────────────────────────────────────
    llm_summary = _build_llm_summary(weather, categorized, city, crop, language)

    return {
        "weather":      weather,
        "crop_news":    categorized["crop_news"],
        "weather_news": categorized["weather_news"],
        "market_news":  categorized["market_news"],
        "pest_alerts":  categorized["pest_alerts"],
        "govt_schemes": categorized["govt_schemes"],
        "llm_summary":  llm_summary,
    }
