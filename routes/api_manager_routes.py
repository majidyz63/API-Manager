from flask import Blueprint, render_template, request, redirect, jsonify, current_app, url_for
import json
import os
import requests

api_manager_bp = Blueprint("api_manager", __name__)

# مسیر کامل فایل config در کنار app.py
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_FILE = os.path.join(BASE_DIR, "api_config.json")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


# ----------------- Helper functions -----------------
def load_config():
    """بارگذاری تنظیمات از فایل JSON"""
    try:
        if not os.path.exists(CONFIG_FILE):
            print(f"[INFO] Config file not found at {CONFIG_FILE}, returning empty config")
            return {}
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config = json.load(f)
            print(f"[INFO] Config loaded successfully from {CONFIG_FILE}")
            return config
    except Exception as e:
        print(f"[ERROR] Failed to load config: {e}")
        return {}


def save_config(data):
    """ذخیره تنظیمات در فایل JSON"""
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"[INFO] Config saved successfully to {CONFIG_FILE}")
        print(f"[DEBUG] Saved data: {data}")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to save config: {e}")
        return False


# ----------------- UI -----------------
@api_manager_bp.route("/", methods=["GET", "POST"])
def manage_models():
    config = load_config()
    if request.method == "POST":
        model = request.form.get("model", "").strip()
        active = request.form.get("active") == "on"
        if model:
            # جست‌وجو برای مدل در لیست
            model_exists = False
            for item in config:
                if isinstance(item, dict) and item.get("id") == model:
                    item["active"] = active
                    model_exists = True
                    break
            
            # اگر مدل جدید است، اضافه کن
            if not model_exists:
                config.append({"id": model, "active": active})
            
            save_config(config)
        return redirect(url_for("api_manager.manage_models"))
    return render_template("api_manager.html", config=config)


# ----------------- Model management -----------------
@api_manager_bp.route("/delete")
def delete_model():
    """حذف مدل از فایل config (لیست)"""
    model = request.args.get("model")
    print(f"[INFO] Delete request received for model: {model}")
    
    if not model:
        print("[WARNING] No model parameter provided for delete")
        return redirect(url_for("api_manager.manage_models"))
    
    config = load_config()
    print(f"[DEBUG] Current config before delete (type: {type(config).__name__}): {config}")
    
    # پیدا کردن و حذف مدل از لیست
    model_found = False
    new_config = []
    
    for item in config:
        if isinstance(item, dict) and item.get("id") == model:
            model_found = True
            print(f"[INFO] Model '{model}' found and will be removed")
        else:
            new_config.append(item)
    
    if model_found:
        if save_config(new_config):
            print(f"[SUCCESS] Model '{model}' deleted and config saved successfully")
        else:
            print(f"[ERROR] Failed to save config after deleting model '{model}'")
    else:
        print(f"[WARNING] Model '{model}' not found in config list")
    
    return redirect(url_for("api_manager.manage_models"))


@api_manager_bp.route("/toggle")
def toggle_model():
    """تغییر وضعیت فعال/غیرفعال مدل (در لیست)"""
    model = request.args.get("model")
    print(f"[INFO] Toggle request received for model: {model}")
    
    if not model:
        print("[WARNING] No model parameter provided for toggle")
        return redirect(url_for("api_manager.manage_models"))
    
    config = load_config()
    print(f"[DEBUG] Current config before toggle (type: {type(config).__name__}): {config}")
    
    # پیدا کردن و toggle کردن مدل در لیست
    model_found = False
    
    for item in config:
        if isinstance(item, dict) and item.get("id") == model:
            model_found = True
            current_status = item.get("active", False)
            new_status = not current_status
            item["active"] = new_status
            
            print(f"[INFO] Toggling model '{model}': {current_status} -> {new_status}")
            
            if save_config(config):
                print(f"[SUCCESS] Model '{model}' toggled and config saved successfully")
            else:
                print(f"[ERROR] Failed to save config after toggling model '{model}'")
            break
    
    if not model_found:
        print(f"[WARNING] Model '{model}' not found in config list")
    
    return redirect(url_for("api_manager.manage_models"))

# ----------------- API -----------------
@api_manager_bp.route("/api/active-models")
def get_active_models():
    config = load_config()
    # فیلتر مدل‌های فعال از لیست
    active = [{"id": item.get("id"), "object": "model"} 
              for item in config if isinstance(item, dict) and item.get("active")]
    return jsonify({"data": active})

@api_manager_bp.route("/api/models", methods=["GET"])
def get_models():
    try:
        config = load_config()
        # تبدیل لیست به فرمت مناسب با اضافه کردن object
        models = [{"id": item.get("id"), "object": "model", "active": item.get("active", False)} 
                  for item in config if isinstance(item, dict)]
        return jsonify({"data": models})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# OpenAI-compatible /v1/models endpoint for Neo_AutoDev
@api_manager_bp.route("/v1/models", methods=["GET"])
def get_v1_models():
    return get_active_models()


# alias برای سازگاری با UI
@api_manager_bp.route("/models", methods=["GET"])
def models_alias():
    try:
        config = load_config()
        return jsonify(config or {})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_manager_bp.route("/api/test/<path:model>", methods=["GET"])
def test_model(model):
    api_key = os.environ.get("OPENROUTER_API_KEY") or getattr(current_app, "openrouter_api_key", None)
    if not api_key:
        return jsonify({"error": "❌ No OPENROUTER_API_KEY set"}), 400

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "Hello, are you working?"}]
    }

    try:
        resp = requests.post(
            OPENROUTER_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "Referer": "http://localhost:8000",
                "X-Title": "API Manager Central"
            },
            json=payload,
            timeout=20
        )
        raw = resp.json()

        output = None
        if isinstance(raw, dict):
            if "choices" in raw and raw["choices"]:
                output = raw["choices"][0]["message"]["content"]
            elif "error" in raw:
                output = f"❌ Error: {raw['error']}"
            else:
                output = str(raw)

        return jsonify({
            "model": model,
            "output": output or "⚠️ No content returned from model",
            "raw": raw
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def _handle_completion_request():
    """Shared completion logic for both /api/complete and /v1/chat/completions"""
    data = request.json
    model = data.get("model")
    messages = data.get("messages", [])

    config = load_config()
    
    # بررسی فعال بودن مدل در لیست
    model_active = False
    for item in config:
        if isinstance(item, dict) and item.get("id") == model and item.get("active", False):
            model_active = True
            break
    
    if not model_active:
        return jsonify({"error": {"message": "Model not active or not found", "type": "invalid_request_error"}}), 400

    api_key = os.environ.get("OPENROUTER_API_KEY") or getattr(current_app, "openrouter_api_key", None)
    if not api_key:
        return jsonify({"error": {"message": "No OPENROUTER_API_KEY set", "type": "authentication_error"}}), 500

    try:
        # Forward all request parameters to OpenRouter
        payload = {
            "model": model,
            "messages": messages
        }
        
        # Pass through any additional parameters (temperature, max_tokens, etc.)
        for key in ["temperature", "max_tokens", "top_p", "frequency_penalty", "presence_penalty", "stream"]:
            if key in data:
                payload[key] = data[key]
        
        resp = requests.post(
            OPENROUTER_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": request.headers.get("Referer", "https://neo-autodev.koyeb.app"),
                "X-Title": "API Manager Central"
            },
            json=payload,
            timeout=30
        )
        
        # Return the raw OpenRouter response directly for Neo_AutoDev compatibility
        return jsonify(resp.json()), resp.status_code
        
    except requests.exceptions.RequestException as e:
        return jsonify({"error": {"message": str(e), "type": "api_error"}}), 500
    except Exception as e:
        return jsonify({"error": {"message": str(e), "type": "internal_error"}}), 500


@api_manager_bp.route("/api/complete", methods=["POST"])
def complete():
    return _handle_completion_request()


# OpenAI-compatible /v1/chat/completions endpoint for Neo_AutoDev
@api_manager_bp.route("/v1/chat/completions", methods=["POST"])
def chat_completions():
    return _handle_completion_request()
