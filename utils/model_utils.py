import requests
import os

def get_active_models():
    try:
        r = requests.get("http://127.0.0.1:5001/api/active-models")
        return r.json()
    except Exception as e:
        print("❌ خطا در دریافت مدل‌ها:", e)
        return []

def get_api_key():
    return os.getenv("OPENROUTER_API_KEY")
