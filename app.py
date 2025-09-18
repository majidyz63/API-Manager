import os
from flask import Flask, render_template
from routes.api_manager_routes import api_manager_bp
from dotenv import load_dotenv

# بارگذاری env
load_dotenv()

app = Flask(__name__)
app.secret_key = "supersecretkey"

# ثبت Blueprint
app.register_blueprint(api_manager_bp)

# ---------- Serve UI ----------
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/manifest.json")
def manifest():
    return app.send_static_file("manifest.json")

@app.route("/service-worker.js")
def service_worker():
    return app.send_static_file("service-worker.js")

@app.route("/api/debug")
def debug():
    return {
        "OPENROUTER_API_KEY": "SET" if os.getenv("OPENROUTER_API_KEY") else "NOT SET",
        "OPENROUTER_URL": os.getenv("OPENROUTER_URL", "https://openrouter.ai/api/v1/chat/completions"),
        "PORT": os.getenv("PORT", "not defined")
    }

if __name__ == "__main__":
    # در لوکال فقط برای تست (Flask dev server)
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
