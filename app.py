"""Altitude - Airbnb price intelligence for 10 European cities (Flask app)."""
import json
import sys
from pathlib import Path

import markdown
import numpy as np
from flask import Flask, abort, jsonify, render_template, request

sys.path.insert(0, str(Path(__file__).parent / "src"))
from algorithms import EXACT_TSP_LIMIT, plan_routes  # noqa: E402
from config import MODELS_DIR, REPORTS_DIR, TARGET  # noqa: E402
from predictor import Predictor  # noqa: E402

app = Flask(__name__)
predictor = Predictor()
EDA = json.loads((MODELS_DIR / "eda.json").read_text())
METRICS = predictor.metrics
CITIES = sorted(predictor.city_data)
ROOM_TYPES = ["Entire home/apt", "Private room", "Shared room"]


@app.context_processor
def inject():
    served = "LightGBM" if predictor.lite else METRICS["best_model"]
    return {"cities": CITIES, "room_types": ROOM_TYPES, "best": METRICS["results"][served],
            "serving": predictor.serving, "lite": predictor.lite}


@app.route("/")
def dashboard():
    return render_template("dashboard.html", eda=EDA, page="dashboard")


@app.route("/explorer")
def explorer():
    return render_template("explorer.html", centers=predictor.centers, page="explorer")


@app.route("/predict")
def predict_page():
    return render_template("predict.html", centers=predictor.centers, page="predict")


@app.route("/route")
def route_page():
    return render_template("route.html", centers=predictor.centers, exact_limit=EXACT_TSP_LIMIT, page="route")


@app.route("/model")
def model_page():
    return render_template("model.html", m=METRICS, page="model")


@app.route("/report")
def report_page():
    md = (REPORTS_DIR / "REPORT.md").read_text(encoding="utf-8").replace("../static/", "/static/")
    html = markdown.markdown(md, extensions=["tables", "fenced_code", "toc"])
    return render_template("report.html", content=html, page="report")


# ---------------------------------------------------------------- API
@app.route("/api/listings/<city>")
def api_listings(city):
    if city not in predictor.city_data:
        abort(404)
    d = predictor.city_data[city]
    rng = np.random.default_rng(0)  # source lat/lon is rounded to 0.01 deg -> jitter for display
    lat = d.latitude.values + rng.uniform(-.0045, .0045, len(d))
    lon = d.longitude.values + rng.uniform(-.0045, .0045, len(d))
    rt = d.room_type.map({r: i for i, r in enumerate(ROOM_TYPES)}).values
    rows = np.column_stack([lat.round(5), lon.round(5), d[TARGET].round(1), rt,
                            (d.day_type == "weekend").astype(int), d.max_guests, d.num_bedrooms,
                            d.guest_satisfaction_score, d.is_superhost, d.distance_city_center.round(2)])
    return jsonify({"city": city, "center": predictor.centers[city],
                    "cols": ["lat", "lon", "price", "room", "weekend", "guests", "bedrooms", "sat", "superhost", "dist"],
                    "rows": rows.tolist()})


@app.route("/api/predict", methods=["POST"])
def api_predict():
    req = request.get_json(force=True)
    if req.get("city") not in predictor.city_data:
        return jsonify({"error": "Unknown city"}), 400
    try:
        return jsonify(predictor.predict(req))
    except (ValueError, KeyError) as e:
        return jsonify({"error": str(e)}), 400


MAX_ROUTE_STOPS = 20


@app.route("/api/route", methods=["POST"])
def api_route():
    req = request.get_json(force=True)
    try:
        points = [(float(p["lat"]), float(p["lon"])) for p in req["points"]]
        start, target, k = int(req.get("start", 0)), int(req.get("target", len(points) - 1)), int(req.get("k", 3))
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "Send points as [{lat, lon}, ...] plus optional start, target and k"}), 400
    if not 2 <= len(points) <= MAX_ROUTE_STOPS:
        return jsonify({"error": f"Select between 2 and {MAX_ROUTE_STOPS} listings"}), 400
    if not (0 <= start < len(points) and 0 <= target < len(points)) or not 1 <= k <= 8:
        return jsonify({"error": "start/target out of range or k not in 1-8"}), 400
    return jsonify(plan_routes(points, start=start, target=target, k=min(k, len(points) - 1)))


@app.route("/api/health")
def health():
    served = "LightGBM" if predictor.lite else METRICS["best_model"]
    return jsonify({"status": "ok", "model": predictor.serving, "r2_log": METRICS["results"][served]["r2_log"]})


if __name__ == "__main__":
    app.run(debug=False, port=5000)
