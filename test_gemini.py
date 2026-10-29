"""
PortfolioAI - Google Gemini API Live Verification Script
Run directly from terminal: python test_gemini.py
"""

import os
import sys
import requests
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

# Load .env file
env_path = BASE_DIR / ".env"
load_dotenv(env_path)

api_key = os.environ.get("GEMINI_API_KEY", "").strip()
model_name = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite").strip()

print("=" * 65, flush=True)
print("PORTFOLIOAI - GOOGLE GEMINI API LIVE HEALTH CHECK", flush=True)
print("=" * 65, flush=True)
print(f"Loaded config from:  {env_path}", flush=True)
print(f"Configured Model:    {model_name}", flush=True)

if not api_key or api_key == "your_gemini_api_key_here":
    print("\n[ERROR] GEMINI_API_KEY is not configured in .env.", flush=True)
    print("Please add your key from: https://aistudio.google.com/app/apikey", flush=True)
    sys.exit(1)

masked_key = api_key[:6] + "..." + api_key[-4:] if len(api_key) > 10 else "***"
print(f"API Key:             {masked_key} (length: {len(api_key)})", flush=True)

# List of models to test in priority order
models = [model_name, "gemini-3.5-flash-lite", "gemini-3-flash-preview", "gemini-3.1-flash-lite-preview"]
models = list(dict.fromkeys(models))  # Deduplicate

test_prompt = "Hello! Please confirm: 'Gemini API is active and working perfectly!'"
endpoint_base = "https://generativelanguage.googleapis.com/v1beta/models"

success = False
for model in models:
    url = f"{endpoint_base}/{model}:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": test_prompt}]}]
    }

    print(f"\n[->] Testing model '{model}'...", flush=True)
    try:
        response = requests.post(url, json=payload, timeout=12)
        if response.status_code == 200:
            data = response.json()
            reply = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
            print(f"[SUCCESS] HTTP 200 OK! Connection established.", flush=True)
            print(f"Response from Gemini:\n\"{reply.strip()}\"", flush=True)
            success = True
            break
        elif response.status_code == 400:
            print(f"[FAILED] HTTP 400 - Invalid request or API key is not recognized.", flush=True)
            print(f"Details: {response.text}", flush=True)
            break
        elif response.status_code == 403:
            print(f"[FAILED] HTTP 403 - Permission denied or API key unauthorized.", flush=True)
            print(f"Details: {response.text}", flush=True)
            break
        elif response.status_code == 404:
            print(f"[NOTE] Model '{model}' is not available for this key/region (HTTP 404). Trying next...", flush=True)
        elif response.status_code == 429:
            print(f"[NOTE] Model '{model}' rate limit / quota exceeded (HTTP 429).", flush=True)
        else:
            print(f"[FAILED] HTTP {response.status_code}: {response.text}", flush=True)

    except requests.exceptions.ConnectionError as ce:
        print(f"[FAILED] Network connection error: {ce}", flush=True)
        print("Note: Ensure you have active internet connectivity to generativelanguage.googleapis.com.", flush=True)
        break
    except Exception as e:
        print(f"[FAILED] Unexpected error: {e}", flush=True)
        break

print("\n" + "=" * 65, flush=True)
if success:
    print("STATUS: PASS - Google Gemini API key is verified and operational!", flush=True)
    print("=" * 65, flush=True)
    sys.exit(0)
else:
    print("STATUS: FAIL - Could not complete generation.", flush=True)
    print("=" * 65, flush=True)
    sys.exit(1)
