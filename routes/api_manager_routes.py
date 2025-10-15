from flask import Blueprint, render_template, request, redirect, jsonify, current_app, url_for
import json
import os
import requests

api_manager_bp = Blueprint("api_manager", __name__)

CONFIG_FILE = "api_config.json"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


# ----------------- Helper functions -----------------
def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {}
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)


def save_config(data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=2)


# ----------------- UI -----------------
@api_manager_bp.route("/", methods=["GET", "POST"])
def manage_models():
    config = load_config()
    if request.method == "POST":
        model = request.form.get("model", "").strip()
        active = request.form.get("active") == "on"
        if model:
            config[model] = {"active": active}
            save_config(config)
        return redirect(url_for("api_manager.manage_models"))
    return render_template("api_manager.html", config=config)


# ----------------- Model management -----------------
@api_manager_bp.route("/delete")
def delete_model():
    model = request.args.get("model")
    config = load_config()
    if model in config:
        config.pop(model, None)
        save_config(config)
    return redirect(url_for("api_manager.manage_models"))


@api_manager_bp.route("/toggle")
def toggle_model():
    model = request.args.get("model")
    config = load_config()
    if model in config:
        current_status = config[model].get("active", False)
        config[model]["active"] = not current_status
        save_config(config)
    return redirect(url_for("api_manager.manage_models"))

# ----------------- API -----------------
@api_manager_bp.route("/api/active-models")
def get_active_models():
    config = load_config()
    active = [{"id": name, "object": "model"} for name, info in config.items() if info.get("active")]
    return jsonify({"data": active})

@api_manager_bp.route("/api/models", methods=["GET"])
def get_models():
    try:
        config = load_config()
        models = [{"id": name, "object": "model", "active": info.get("active", False)} 
                  for name, info in config.items()]
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
    if model not in config or not config[model].get("active", False):
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
