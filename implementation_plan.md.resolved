# Advanced Hyperlocal Farmer News Scraper — v2

Rebuild [news_api.py](file:///c:/Users/vamsi/Documents/Voice_app/news_api.py) and [news_router.py](file:///c:/Users/vamsi/Documents/Voice_app/news_router.py) with multi-source, multi-language, and categorized output — designed to feed an LLM that voices news to farmers over a toll-free call.

## What Changes

### news_api.py — Full Rebuild

**Inputs from LLM (what the farmer told us):**
```
city, crop, state, language_code
```

**Output — categorized, LLM-ready:**
```json
{
  "crop_news":    [...],   // news about their specific crop
  "weather_news": [...],   // weather, rain, flood, drought alerts
  "market_news":  [...],   // mandi prices, crop market trends
  "pest_alerts":  [...],   // pest/disease alerts for their crop
  "govt_schemes": [...],   // government schemes, subsidies
  "llm_summary":  "..."    // single paragraph the LLM can read directly to farmer
}
```

---

## Sources Used (No API Key Needed)

| Source | What it gives | Method |
|--------|--------------|--------|
| Google News RSS (English) | General agri news local to city/crop | RSS feedparser |
| Google News RSS (Local language) | Same but in farmer's language (Telugu, Hindi, Marathi etc.) | RSS feedparser with `hl=te-IN` |
| Krishi Jagran RSS | Dedicated Indian agri news, pest alerts, govt schemes | RSS feedparser |
| The Hindu Agri RSS | Quality agriculture news India | RSS feedparser |
| IMD District Nowcast RSS | Official weather alerts by district | RSS feedparser |
| OpenWeatherMap (already in project) | Current weather + 5-day forecast summary | REST API (key exists) |

---

## Language Support

| Farmer Language | Google News `hl` code |
|-----------------|----------------------|
| Telugu          | `te-IN`              |
| Hindi           | `hi-IN`              |
| Marathi         | `mr-IN`              |
| Tamil           | `ta-IN`              |
| Kannada         | `kn-IN`              |
| English         | `en-IN`              |

---

## Proposed File Changes

### [MODIFY] news_scrapper_api/news_api.py

Complete rewrite with:
- `get_farmer_news(city, crop, state, language, limit)` — main function
- `_fetch_categorized_news()` — pulls from all sources and buckets into categories
- `_fetch_weather_summary()` — from OpenWeatherMap (reuses existing [weather.py](file:///c:/Users/vamsi/Documents/Voice_app/weather.py) key)
- `_build_llm_summary()` — builds a concise paragraph for the LLM to read aloud
- Language-aware Google News queries (local language + English fallback)

### [MODIFY] news_scrapper_api/news_router.py

Update endpoint signature:
```
GET /news?city=Ongole&crop=rice&state=AndhraPradesh&language=te&limit=5
```

Adds `language` param. Returns categorized response structure.

### [MODIFY] news_scrapper_api/test_news_api.py

Updated tests for new response structure (categorized dict).

---

## Verification Plan

### Automated
```bash
python test_news_api.py
```
Verify each category has at least 1 article and `llm_summary` is non-empty.

### Manual
Start server and hit:
```
http://127.0.0.1:8000/news?city=Ongole&crop=rice&state=Andhra Pradesh&language=te
```
Check `llm_summary` makes sense as something readable aloud to a farmer.
