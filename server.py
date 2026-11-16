import os
import io
import json
import time
import threading
import urllib.request
import urllib.error
from collections import defaultdict, deque
from flask import Flask, request, jsonify, send_file, make_response

app = Flask(__name__)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash").strip()
ALLOWED_ORIGINS = {x.strip().rstrip("/") for x in os.environ.get("ALLOWED_ORIGINS", "http://127.0.0.1:5000,http://localhost:5000").split(",") if x.strip()}
ENABLE_KOKORO = os.environ.get("ENABLE_KOKORO", "false").lower() == "true"
VOICE = "im_nicola"
VOICE_PIPELINE = None
VOICE_LOCK = threading.Lock()
BUCKETS = defaultdict(deque)
RATE_LOCK = threading.Lock()

if ENABLE_KOKORO:
    try:
        import numpy as np
        import soundfile as sf
        from kokoro import KPipeline
        VOICE_PIPELINE = KPipeline(lang_code="i", repo_id="hexgrad/Kokoro-82M")
        print("Voce Kokoro Nicola disponibile")
    except Exception as exc:
        print("Kokoro non disponibile:", repr(exc))

@app.after_request
def cors(response):
    origin = request.headers.get("Origin", "").rstrip("/")
    if origin in ALLOWED_ORIGINS:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Vary"] = "Origin"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        response.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response

@app.before_request
def handle_preflight():
    if request.method == "OPTIONS":
        return make_response("", 204)

@app.route("/")
def home():
    return jsonify({"service": "NOVA AI backend", "status": "online"})

@app.route("/api/status")
def status():
    return jsonify({
        "online": True, "version": "1.6", "ai_available": bool(GEMINI_API_KEY),
        "voice_available": VOICE_PIPELINE is not None,
        "voice": VOICE if VOICE_PIPELINE else "browser-italian"
    })

def rate_limit():
    ip = request.remote_addr or "unknown"
    now = time.monotonic()
    with RATE_LOCK:
        bucket = BUCKETS[ip]
        while bucket and now - bucket[0] > 60:
            bucket.popleft()
        if len(bucket) >= 12:
            return False
        bucket.append(now)
    return True

@app.route("/api/chat", methods=["POST"])
def chat():
    if not rate_limit():
        return jsonify({"error": "Troppi messaggi, riprova tra un minuto."}), 429
    if not GEMINI_API_KEY:
        return jsonify({"error": "GEMINI_API_KEY non configurata su Render."}), 503
    payload = request.get_json(silent=True) or {}
    text = payload.get("message", "")
    if not isinstance(text, str) or not 1 <= len(text.strip()) <= 2000:
        return jsonify({"error": "Messaggio non valido (1-2000 caratteri)."}), 400
    history = payload.get("history", [])
    contents = []
    if isinstance(history, list):
        for item in history[-12:]:
            if isinstance(item, dict) and item.get("role") in ("user", "model") and isinstance(item.get("text"), str):
                contents.append({"role": item["role"], "parts": [{"text": item["text"][:2000]}]})
    contents.append({"role": "user", "parts": [{"text": text.strip()}]})
    body = {
        "systemInstruction": {"parts": [{"text": "Sei NOVA, un assistente digitale in italiano. Rispondi in modo chiaro, accurato e naturale. Se un'informazione è incerta, dichiaralo. Per risposte vocali evita testi inutilmente lunghi."}]},
        "contents": contents,
        "generationConfig": {"maxOutputTokens": 500, "temperature": 0.65}
    }
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
    req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), headers={"Content-Type": "application/json", "x-goog-api-key": GEMINI_API_KEY}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=45) as response:
            answer = json.load(response)
        parts = answer.get("candidates", [{}])[0].get("content", {}).get("parts", [])
        reply = "".join(part.get("text", "") for part in parts if isinstance(part, dict)).strip()
        if not reply:
            return jsonify({"error": "Il modello non ha prodotto una risposta testuale."}), 502
        return jsonify({"reply": reply})
    except urllib.error.HTTPError as exc:
        print("Gemini HTTP error:", exc.code, exc.read(300))
        if exc.code == 429:
            return jsonify({"error": "Limite richieste Gemini raggiunto."}), 429
        return jsonify({"error": f"Errore del servizio AI ({exc.code})."}), 502
    except Exception as exc:
        print("AI error:", repr(exc))
        return jsonify({"error": "Servizio AI temporaneamente non disponibile."}), 502

@app.route("/api/voice", methods=["POST"])
def voice():
    if VOICE_PIPELINE is None:
        return jsonify({"error": "Kokoro disabilitato: usa la voce del browser."}), 503
    if not rate_limit():
        return jsonify({"error": "Limite richieste vocali raggiunto."}), 429
    payload = request.get_json(silent=True) or {}
    text = payload.get("text", "")
    if not isinstance(text, str) or not 1 <= len(text.strip()) <= 700:
        return jsonify({"error": "Testo vocale non valido."}), 400
    try:
        start = time.perf_counter()
        with VOICE_LOCK:
            parts = [np.asarray(audio, dtype=np.float32) for _, _, audio in VOICE_PIPELINE(text.strip(), voice=VOICE, speed=0.98) if audio is not None]
        if not parts:
            raise RuntimeError("Nessun audio")
        buffer = io.BytesIO()
        sf.write(buffer, np.concatenate(parts), 24000, format="WAV", subtype="PCM_16")
        buffer.seek(0)
        response = send_file(buffer, mimetype="audio/wav", download_name="nova_nicola.wav")
        response.headers["X-Nova-Generation-Ms"] = str(round((time.perf_counter()-start)*1000))
        return response
    except Exception as exc:
        print("Voice error:", repr(exc))
        return jsonify({"error": "Generazione vocale non riuscita."}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=False)
