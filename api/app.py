import os, json, joblib
import numpy as np
import pandas as pd
import redis
from flask import Flask, request, jsonify
import psycopg2

app = Flask(__name__)

# ── Load models once at startup ───────────────────────────────────────────
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
clf  = joblib.load(os.path.join(BASE, "models/aqi_classifier.pkl"))
reg  = joblib.load(os.path.join(BASE, "models/pm25_forecaster.pkl"))
with open(os.path.join(BASE, "models/features.json")) as f:
    FEATURES = json.load(f)

# ── Redis connection ──────────────────────────────────────────────────────
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

def get_redis():
    try:
        r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT,
                        decode_responses=True, socket_timeout=2)
        r.ping()
        return r
    except Exception:
        return None

# ── PostgreSQL connection ─────────────────────────────────────────────────
DB_URL = os.getenv("DATABASE_URL", "")

def get_db():
    if not DB_URL:
        return None
    try:
        return psycopg2.connect(DB_URL)
    except Exception:
        return None

def log_to_db(endpoint, city, result):
    conn = get_db()
    if not conn:
        return
    try:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS predictions (
                id SERIAL PRIMARY KEY,
                endpoint TEXT,
                city TEXT,
                result TEXT,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        cur.execute(
            "INSERT INTO predictions (endpoint, city, result) VALUES (%s, %s, %s)",
            (endpoint, city, json.dumps(result))
        )
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"DB log error: {e}")

def build_features(city, hour, month, pm25_recent):
    recent = pm25_recent[-6:] if len(pm25_recent) >= 6 else pm25_recent
    while len(recent) < 6:
        recent = [recent[0]] + recent

    city_map = {"Los Angeles": 0, "Chicago": 1, "Denver": 2}
    city_code = city_map.get(city, 0)

    lag1       = recent[-1]
    lag2       = recent[-2]
    lag3       = recent[-3]
    roll_mean6 = float(np.mean(recent))
    roll_std6  = float(np.std(recent))

    # Return as DataFrame so sklearn doesn't warn about feature names
    return pd.DataFrame([[lag1, lag2, lag3, roll_mean6, roll_std6,
                          hour, month, city_code]], columns=FEATURES)

# ── ENDPOINT 1: /predict_aqi ──────────────────────────────────────────────
@app.route("/predict_aqi", methods=["POST"])
def predict_aqi():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No JSON body sent"}), 400

    city        = data.get("city", "Los Angeles")
    hour        = int(data.get("hour", 12))
    month       = int(data.get("month", 6))
    pm25_recent = data.get("pm25_recent", [15.0, 16.0, 14.0, 15.5, 17.0, 15.0])

    # Check Redis cache first
    r = get_redis()
    cache_key = f"aqi:{city}:{hour}:{month}:{pm25_recent[-1]}"
    if r:
        cached = r.get(cache_key)
        if cached:
            result = json.loads(cached)
            result["source"] = "cache"
            return jsonify(result)

    X          = build_features(city, hour, month, pm25_recent)
    category   = clf.predict(X)[0]
    proba      = clf.predict_proba(X)[0]
    confidence = round(float(max(proba)), 3)

    result = {
        "city": city,
        "aqi_category": category,
        "confidence": confidence,
        "source": "model"
    }

    if r:
        r.setex(cache_key, 600, json.dumps(result))

    log_to_db("predict_aqi", city, result)
    return jsonify(result)

# ── ENDPOINT 2: /forecast ─────────────────────────────────────────────────
@app.route("/forecast", methods=["POST"])
def forecast():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No JSON body sent"}), 400

    city        = data.get("city", "Los Angeles")
    hour        = int(data.get("hour", 12))
    month       = int(data.get("month", 6))
    pm25_recent = data.get("pm25_recent", [15.0, 16.0, 14.0, 15.5, 17.0, 15.0])

    r = get_redis()
    cache_key = f"forecast:{city}:{hour}:{month}:{pm25_recent[-1]}"
    if r:
        cached = r.get(cache_key)
        if cached:
            result = json.loads(cached)
            result["source"] = "cache"
            return jsonify(result)

    predictions = []
    current = list(pm25_recent)
    for h_offset in range(1, 7):
        future_hour = (hour + h_offset) % 24
        X    = build_features(city, future_hour, month, current)
        pred = float(reg.predict(X)[0])
        pred = round(max(0, pred), 2)
        predictions.append({"hour_offset": h_offset, "pm25": pred})
        current.append(pred)

    trend = "rising" if predictions[-1]["pm25"] > predictions[0]["pm25"] else "falling"

    result = {
        "city": city,
        "forecast": predictions,
        "trend": trend,
        "source": "model"
    }

    if r:
        r.setex(cache_key, 600, json.dumps(result))

    log_to_db("forecast", city, result)
    return jsonify(result)

# ── ENDPOINT 3: /stats ────────────────────────────────────────────────────
@app.route("/stats", methods=["GET"])
def stats():
    r = get_redis()
    total_keys = 0
    if r:
        try:
            keys = r.keys("aqi:*") + r.keys("forecast:*")
            total_keys = len(keys)
        except Exception:
            pass

    conn = get_db()
    db_count = 0
    if conn:
        try:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM predictions")
            db_count = cur.fetchone()[0]
            cur.close()
            conn.close()
        except Exception:
            pass

    return jsonify({
        "cached_results": total_keys,
        "total_predictions_logged": db_count,
        "redis_connected": r is not None,
        "db_connected": conn is not None
    })

# ── Health check ──────────────────────────────────────────────────────────
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "models_loaded": True})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
