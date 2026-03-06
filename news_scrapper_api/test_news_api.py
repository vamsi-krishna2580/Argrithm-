"""
test_news_api.py  —  v2
========================
Tests the advanced farmer news scraper.
Run from inside news_scrapper_api/ folder:

    python test_news_api.py
"""

from news_api import get_farmer_news

PASS = "✅"
FAIL = "❌"
WARN = "⚠️ "

REQUIRED_KEYS    = ["weather", "crop_news", "weather_news", "market_news",
                    "pest_alerts", "govt_schemes", "llm_summary"]
REQUIRED_WEATHER = ["temperature", "humidity", "condition"]
CATEGORY_KEYS    = ["crop_news", "weather_news", "market_news",
                    "pest_alerts", "govt_schemes"]
ARTICLE_KEYS     = ["title", "url", "source", "published", "score"]

TEST_CASES = [
    {"city": "Ongole",   "crop": "rice",   "state": "Andhra Pradesh",  "language": "te"},
    {"city": "Nashik",   "crop": "grapes", "state": "Maharashtra",     "language": "mr"},
    {"city": "Ludhiana", "crop": "wheat",  "state": "Punjab",          "language": "hi"},
    {"city": "Coimbatore","crop": "cotton","state": "Tamil Nadu",      "language": "ta"},
]


def run_tests():
    all_passed = True

    for tc in TEST_CASES:
        city, crop = tc["city"], tc["crop"]
        state, lang = tc["state"], tc["language"]

        print(f"\n{'─'*65}")
        print(f"  TESTING  city={city!r}  crop={crop!r}  lang={lang!r}")
        print(f"{'─'*65}")

        try:
            result = get_farmer_news(city=city, crop=crop, state=state,
                                     language=lang, limit=5)
            # ── Structure checks ──────────────────────────────────────────
            for key in REQUIRED_KEYS:
                assert key in result, f"Missing top-level key: '{key}'"

            # ── Weather block ─────────────────────────────────────────────
            weather = result["weather"]
            if weather:
                for wk in REQUIRED_WEATHER:
                    assert wk in weather, f"Missing weather key: '{wk}'"
                print(f"  {PASS}  Weather: {weather['condition']}, "
                      f"{weather['temperature']}°C, "
                      f"humidity {weather['humidity']}%")
                if weather.get("forecast"):
                    print(f"       Forecast: {weather['forecast'][0]}")
            else:
                print(f"  {WARN}  Weather unavailable (API may be rate-limited)")

            # ── Categories ───────────────────────────────────────────────
            total = 0
            for cat in CATEGORY_KEYS:
                items = result[cat]
                total += len(items)
                if items:
                    for art in items:
                        for ak in ARTICLE_KEYS:
                            assert ak in art, f"[{cat}] Missing article key: '{ak}'"
                    top = items[0]
                    print(f"  {PASS}  {cat:<15} ({len(items)} articles) "
                          f"| top score={top['score']} | {top['title'][:55]}")
                else:
                    print(f"  {WARN}  {cat:<15} — 0 articles (OK if niche query)")

            assert total > 0, "No articles returned across ALL categories"

            # ── LLM summary ───────────────────────────────────────────────
            summary = result["llm_summary"]
            assert isinstance(summary, str) and len(summary) > 20, \
                "llm_summary is empty or too short"
            print(f"\n  {PASS}  LLM SUMMARY ({len(summary)} chars):")
            print(f"       \"{summary[:200]}{'...' if len(summary)>200 else ''}\"")

        except AssertionError as e:
            print(f"  {FAIL}  ASSERTION FAILED: {e}")
            all_passed = False
        except Exception as e:
            print(f"  {FAIL}  ERROR: {e}")
            all_passed = False

    print(f"\n{'═'*65}")
    if all_passed:
        print(f"  {PASS}  ALL TESTS PASSED — news_scrapper_api v2 is ready!")
    else:
        print(f"  {FAIL}  SOME TESTS FAILED — check output above.")
    print(f"{'═'*65}\n")


if __name__ == "__main__":
    run_tests()
