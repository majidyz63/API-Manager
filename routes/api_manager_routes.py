from flask import Blueprint, render_template, request, redirect, jsonify, current_app, url_for
import json
import os
import requests

api_manager_bp = Blueprint("api_manager", __name__)

CONFIG_FILE = "api_config.json"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {}
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)


def save_config(data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=2)


@api_manager_bp.route("/", methods=["GET", "POST"])
def manage_models():
    config = load_config()
    if request.method == "POST":
        model = request.form.get("model").strip()
        active = request.form.get("active") == "on"
        if model:
            config[model] = {"active": active}
            save_config(config)
        return redirect(url_for("api_manager.manage_models"))
    return render_template("api_manager.html", config=config)


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


@api_manager_bp.route("/api/active-models")
def get_active_models():
    config = load_config()
    active = [name for name, info in config.items() if info.get("active")]
    return jsonify(active)


@api_manager_bp.route("/api/models", methods=["GET"])
def get_models():
    config = load_config()
    return jsonify(config)


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


@api_manager_bp.route("/api/complete", methods=["POST"])
def complete():
    data = request.json
    model = data.get("model")
    messages = data.get("messages", [])

    config = load_config()
    if model not in config or not config[model].get("active", False):
        return jsonify({"error": "❌ Model not active or not found"}), 400

    api_key = os.environ.get("OPENROUTER_API_KEY") or getattr(current_app, "openrouter_api_key", None)
    if not api_key:
        return jsonify({"error": "❌ No OPENROUTER_API_KEY set"}), 500

    try:
        resp = requests.post(
            OPENROUTER_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "Referer": "http://localhost:8000",
                "X-Title": "API Manager Central"
            },
            json={"model": model, "messages": messages},
            timeout=30
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
    
@api_manager_bp.route("/api/models", methods=["GET"])
def get_models():
    config = load_config()
    return jsonify(config or {})

@api_manager_bp.route("/models", methods=["GET"])
def models_alias():
    return get_models()
