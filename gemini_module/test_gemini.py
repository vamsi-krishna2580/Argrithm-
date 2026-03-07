"""
test_gemini.py  —  Gemini Flash integration tests
==================================================
Run from Voice_app/ folder with the server running:

    uvicorn server:app --reload --port 8000
    python gemini_module/test_gemini.py
"""

import requests
import json

BASE = "http://127.0.0.1:8000"
PASS = "✅"
FAIL = "❌"
WARN = "⚠️ "


def test_advisory():
    print("\n── TEST: POST /gemini/advisory ──────────────────────────")
    payload = {
        "city":     "Ongole",
        "crop":     "rice",
        "state":    "Andhra Pradesh",
        "language": "en",
    }
    try:
        r = requests.post(f"{BASE}/gemini/advisory", json=payload, timeout=30)
        r.raise_for_status()
        data = r.json()
        assert "advisory_text" in data, "Missing advisory_text"
        assert len(data["advisory_text"]) > 20, "Advisory too short"
        print(f"  {PASS} Advisory received ({len(data['advisory_text'])} chars)")
        print(f"       \"{data['advisory_text'][:120]}...\"")
        if data.get("weather"):
            print(f"  {PASS} Weather: {data['weather'].get('condition')}, {data['weather'].get('temperature')}°C")
        if data.get("news_summary"):
            print(f"  {PASS} News summary: {data['news_summary'][:80]}...")
        if data.get("audio_url"):
            print(f"  {PASS} Audio URL: {data['audio_url']}")
        return True
    except Exception as e:
        print(f"  {FAIL} Error: {e}")
        return False


def test_advisory_hindi():
    print("\n── TEST: Hindi farmer advisory ──────────────────────────")
    payload = {
        "city":     "Ludhiana",
        "crop":     "wheat",
        "state":    "Punjab",
        "language": "hi",
    }
    try:
        r = requests.post(f"{BASE}/gemini/advisory", json=payload, timeout=30)
        r.raise_for_status()
        data = r.json()
        assert "advisory_text" in data
        print(f"  {PASS} Hindi advisory: \"{data['advisory_text'][:100]}...\"")
        return True
    except Exception as e:
        print(f"  {FAIL} Error: {e}")
        return False


def test_bad_language():
    print("\n── TEST: invalid language code ──────────────────────────")
    payload = {"city": "Ongole", "crop": "rice", "language": "xx"}
    try:
        r = requests.post(f"{BASE}/gemini/advisory", json=payload, timeout=10)
        if r.status_code == 400:
            print(f"  {PASS} Correctly rejected invalid language (400)")
            return True
        else:
            print(f"  {FAIL} Expected 400, got {r.status_code}")
            return False
    except Exception as e:
        print(f"  {FAIL} Error: {e}")
        return False


def test_docs_reachable():
    print("\n── TEST: /docs endpoint reachable ───────────────────────")
    try:
        r = requests.get(f"{BASE}/docs", timeout=5)
        if r.status_code == 200:
            print(f"  {PASS} Swagger docs live at {BASE}/docs")
            return True
        else:
            print(f"  {WARN} /docs returned {r.status_code}")
            return False
    except Exception as e:
        print(f"  {FAIL} Server not reachable: {e}")
        return False


if __name__ == "__main__":
    print("═" * 60)
    print("  Gemini Flash Integration Test Suite")
    print("═" * 60)

    results = [
        test_docs_reachable(),
        test_advisory(),
        test_advisory_hindi(),
        test_bad_language(),
    ]

    print("\n" + "═" * 60)
    passed = sum(results)
    total  = len(results)
    if passed == total:
        print(f"  {PASS}  ALL {total} TESTS PASSED")
    else:
        print(f"  {FAIL}  {passed}/{total} TESTS PASSED")
    print("═" * 60 + "\n")
