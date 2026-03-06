# 📡 Farmer News Scraper API — Full Documentation

**Version:** 2.0  
**Base URL:** `http://127.0.0.1:8000`  
**Module:** `news_scrapper_api/`  
**Purpose:** Provides hyperlocal, multilingual, categorized agricultural news to the LLM voice assistant that speaks with farmers over a toll-free call.

---

## Table of Contents
1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Endpoint Reference](#endpoint-reference)
4. [Response Schema](#response-schema)
5. [Language Codes](#language-codes)
6. [News Categories Explained](#news-categories-explained)
7. [How Relevance Scoring Works](#how-relevance-scoring-works)
8. [News Sources](#news-sources)
9. [Integration with LLM Voice Flow](#integration-with-llm-voice-flow)
10. [Error Reference](#error-reference)
11. [File Reference](#file-reference)
12. [Running & Testing](#running--testing)

---

## Overview

This API scrapes and ranks agriculture-specific news for a farmer given three inputs from a voice conversation:

| Input | Example | Where it comes from |
|-------|---------|---------------------|
| `city` | `"Ongole"` | Farmer says their village/city |
| `crop` | `"rice"` | Farmer says the crop they grow |
| `language` | `"te"` | Detected from farmer's speech |
| `state` | `"Andhra Pradesh"` | Inferred or spoken |

The response includes **live weather**, **5 categorized news buckets**, and a **`llm_summary`** — a single plain-English paragraph the LLM can read aloud directly to the farmer.

---

## Architecture

```
Farmer calls toll-free
        │
        ▼
  LLM voice assistant
  (extracts city, crop, language)
        │
        ▼
  GET /news?city=Ongole&crop=rice&language=te&state=Andhra+Pradesh
        │
        ▼
  ┌─────────────────────────────────────┐
  │         news_api.py                 │
  │                                     │
  │  ┌──────────────────┐               │
  │  │ Google News RSS  │ ← EN queries  │
  │  │ Google News RSS  │ ← Telugu/local│
  │  │ Krishi Jagran    │ ← Indian agri │
  │  │ The Hindu Agri   │ ← Quality news│
  │  │ IMD Nowcast RSS  │ ← Weather alert│
  │  │ OpenWeatherMap   │ ← Live weather │
  │  └──────────────────┘               │
  │          │                          │
  │     Score + Deduplicate             │
  │          │                          │
  │     Bucket into categories          │
  │          │                          │
  │     Build llm_summary               │
  └─────────────────────────────────────┘
        │
        ▼
  Categorized JSON response
        │
        ▼
  LLM reads llm_summary aloud to farmer
```

---

## Endpoint Reference

### `GET /news`

Fetch hyperlocal, categorized agricultural news for a specific farmer.

```
GET /news?city={city}&crop={crop}&state={state}&language={lang}&limit={n}
```

#### Query Parameters

| Parameter  | Type    | Required | Default  | Description |
|------------|---------|----------|----------|-------------|
| `city`     | string  | ✅ Yes   | —        | Farmer's city or village name |
| `crop`     | string  | ✅ Yes   | —        | Crop the farmer is growing |
| `state`    | string  | ❌ No    | India    | State name — improves regional accuracy |
| `language` | string  | ❌ No    | `en`     | Farmer's language code (see table below) |
| `limit`    | integer | ❌ No    | `5`      | Max articles per category (1–15) |

#### Example Requests

**Basic:**
```
GET /news?city=Ongole&crop=rice
```

**With state and language (recommended):**
```
GET /news?city=Ongole&crop=rice&state=Andhra Pradesh&language=te&limit=5
```

**More articles per category:**
```
GET /news?city=Nashik&crop=grapes&state=Maharashtra&language=mr&limit=10
```

**Hindi-speaking wheat farmer:**
```
GET /news?city=Ludhiana&crop=wheat&state=Punjab&language=hi
```

---

## Response Schema

```json
{
  "query": {
    "city":     "Ongole",
    "crop":     "rice",
    "state":    "Andhra Pradesh",
    "language": "Telugu"
  },
  "total_articles": 18,
  "weather": {
    "city":        "Ongole",
    "temperature": 25.27,
    "feels_like":  26.1,
    "humidity":    82,
    "condition":   "Few clouds",
    "wind_speed":  3.2,
    "forecast": [
      "06 Mar 23:30: Clear sky, 24.46°C",
      "07 Mar 02:30: Clear sky, 23.1°C",
      "07 Mar 05:30: Clear sky, 22.8°C",
      "07 Mar 08:30: Haze, 24.1°C"
    ]
  },
  "llm_summary": "Current weather in Ongole: Few clouds, 25.27°C, humidity 82%. Forecast: 06 Mar 23:30: Clear sky, 24.46°C. Latest rice news: Andhra Pradesh Farmer Revives 110 Nutrient-Rich Indigenous Rice Varieties. Government update: Andhra Pradesh Agriculture Department inks MoU with Waddle.",
  "crop_news": [
    {
      "title":     "Andhra Pradesh Farmer Revives 110 Nutrient-Rich Indigenous Rice Varieties",
      "url":       "https://...",
      "source":    "ETV Bharat",
      "published": "2026-02-03 08:00",
      "score":     8
    }
  ],
  "weather_news": [ ... ],
  "market_news":  [ ... ],
  "pest_alerts":  [ ... ],
  "govt_schemes": [ ... ]
}
```

### Article Object

Each item in a news category array has:

| Field       | Type    | Description |
|-------------|---------|-------------|
| `title`     | string  | Headline of the article |
| `url`       | string  | Full link to the original article |
| `source`    | string  | Publication name (e.g. "ETV Bharat") |
| `published` | string  | Date/time string: `"YYYY-MM-DD HH:MM"` |
| `score`     | integer | Relevance score (higher = more relevant to this farmer) |

---

## Language Codes

| Code | Language   | Google News Locale |
|------|------------|--------------------|
| `en` | English    | `en-IN`            |
| `te` | Telugu     | `te-IN`            |
| `hi` | Hindi      | `hi-IN`            |
| `mr` | Marathi    | `mr-IN`            |
| `ta` | Tamil      | `ta-IN`            |
| `kn` | Kannada    | `kn-IN`            |
| `ml` | Malayalam  | `ml-IN`            |

> When a non-English language is given, the API fetches news in **both English and the local language** and merges them. All 6 Indian languages (te, hi, mr, ta, kn, ml) have native-script search phrases built in.

---

## News Categories Explained

| Category      | What it contains | Example |
|---------------|-----------------|---------|
| `crop_news`   | News about the farmer's specific crop — harvests, yields, research, local crop stories | *"Andhra Pradesh Farmer Revives Indigenous Rice Varieties"* |
| `weather_news`| Rain, flood, drought, cyclone, cold wave alerts from IMD and media | *"IMD issues orange alert for heavy rainfall in coastal AP"* |
| `market_news` | Mandi prices, MSP updates, commodity rates, export/import news | *"Rice MSP raised to ₹2183/quintal for Kharif season"* |
| `pest_alerts` | Pest infestations, crop disease warnings, pesticide advisories | *"Brown planthopper alert for paddy farmers in Krishna delta"* |
| `govt_schemes`| PM Kisan, Fasal Bima, subsidies, loans, state schemes | *"PM Kisan 21st instalment released — ₹2000 per farmer"* |

> Articles are assigned to a category based on keyword matching. If no specific category matches, the article goes into `crop_news` as the default.

---

## How Relevance Scoring Works

Each article gets an integer `score`. Higher = more relevant to this farmer.

| Match | Points |
|-------|--------|
| City/village name in title or text | +4 |
| Crop name in title or text | +4 |
| State name in title or text | +2 |
| General agri keywords (farmer, harvest, irrigation, kisan, etc.) | +1 each |

Articles are sorted by score before being returned, so the most directly relevant news always appears first.

---

## News Sources

| Source | Type | What it provides |
|--------|------|-----------------|
| **Google News RSS (English)** | RSS | Hyperlocal city+crop, state-level, national agri, mandi, pest, govt queries — 7 targeted queries |
| **Google News RSS (Local language)** | RSS | Same queries but in farmer's native language (te/hi/mr etc.) |
| **Krishi Jagran** | RSS | Leading Indian agricultural news site — pest alerts, schemes, crop advice |
| **The Hindu Agriculture** | RSS | High-quality agriculture journalism, policy news |
| **IMD District Nowcast** | RSS | Official India Meteorological Department district-level weather alerts |
| **OpenWeatherMap** | REST API | Live current weather + **12-hour** forecast (4 slots × 3 hrs), reuses existing `weather.py` API key |

> **No additional API keys needed** — Google News RSS, Krishi Jagran, The Hindu, and IMD feeds are free. OpenWeatherMap uses the key already present in `weather.py`.

---

## Integration with LLM Voice Flow

The `llm_summary` field is specifically designed for your voice assistant flow:

```
1. Farmer calls toll-free number
2. LLM greets and asks city, crop, language
3. LLM extracts: { city: "Ongole", crop: "rice", language: "te" }
4. Backend calls: GET /news?city=Ongole&crop=rice&language=te&state=Andhra Pradesh
5. LLM receives response and reads llm_summary aloud:

   "Current weather in Ongole: Few clouds, 25°C, humidity 82%.
    Latest rice news: Andhra Pradesh Farmer Revives Indigenous Rice Varieties.
    Market update: Rice MSP raised to ₹2183 per quintal.
    Government update: PM Kisan 21st instalment released."

6. LLM can ask: "Do you want more details on any of these?"
7. If yes, use specific category arrays (crop_news, market_news, etc.)
```

### Suggested LLM Prompt Snippet

```
You have received the following news data for this farmer:
{llm_summary}

Read this to the farmer in their language ({language}).
Keep the tone simple, friendly, and direct — as if speaking to a village farmer.
After reading, ask if they want more details on any topic.
```

---

## Error Reference

| HTTP Code | Reason | Fix |
|-----------|--------|-----|
| `400` | `city` or `crop` is missing | Provide both required query params |
| `400` | Invalid `language` code | Use one of: en, te, hi, mr, ta, kn, ml |
| `500` | News fetch failed (network issue) | Retry — external RSS feeds may be briefly down |

---

## File Reference

```
news_scrapper_api/
├── __init__.py          # Python package marker
├── news_api.py          # Core scraper: multi-source fetch, scoring, bucketing, llm_summary
├── news_router.py       # FastAPI router: GET /news endpoint
├── test_news_api.py     # Test script: 4 real farmer combos
├── requirements.txt     # Python dependencies
├── DOCS.md              # ← This file
└── README.md            # Quick-start summary
```

### Key Functions in `news_api.py`

| Function | Description |
|----------|-------------|
| `get_farmer_news(city, crop, state, language, limit)` | **Main entry point** — call this from the LLM backend |
| `_fetch_rss(url, max_items)` | Parse any RSS feed into article dicts |
| `_score_and_bucket(articles, city, crop, state)` | Score relevance + assign category to each article |
| `_get_weather_summary(city, state)` | Fetch live weather + forecast from OpenWeatherMap |
| `_build_llm_summary(weather, categorized, city, crop, language)` | Build the plain-English read-aloud paragraph |
| `_google_news_url(query, hl, gl)` | Build a Google News RSS URL for a search query |

---

## Running & Testing

### Install dependencies
```bash
pip install -r news_scrapper_api/requirements.txt
```

### Start the server
```bash
# From Voice_app/ folder
uvicorn server:app --reload --port 8000
```

### Interactive API explorer
```
http://127.0.0.1:8000/docs
```

### Run the test suite
```bash
# From news_scrapper_api/ folder
python test_news_api.py
```

### Quick curl test
```bash
curl "http://127.0.0.1:8000/news?city=Ongole&crop=rice&state=Andhra+Pradesh&language=te"
```

---

*Built for the Argrithm hackathon project — farmer advisory voice system.*
