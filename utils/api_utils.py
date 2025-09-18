import os
import json

def get_api_key():
    return os.getenv("OPENROUTER_API_KEY")

def get_active_models():
    with open("api_config.json", "r") as f:
        data = json.load(f)
    return [name for name, info in data.items() if info.get("active")]
