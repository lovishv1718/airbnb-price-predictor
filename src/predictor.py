"""Inference service used by the Flask app.

Turns a (city, lat, lon, listing details) request into a full feature row:
location features that a host would not know (distance to metro, attraction
and restaurant indices, ...) are estimated from the nearest real listings.
"""
import json
import os

import numpy as np
import pandas as pd

from config import CITY_COLS, MODELS_DIR, PROCESSED_CSV, TARGET
from features import CATEGORICAL, base_features, haversine_km

LOCAL_COLS = ["distance_metro", "attraction_index_norm", "restaurant_index_norm", "proximity_index"]


class LiteLGBM:
    """Numpy-only evaluator for the exported LightGBM trees (see export_lite.py)."""

    def __init__(self, path):
        z = np.load(path)
        self.__dict__.update({k: z[k] for k in z.files})
        self.cat_sets = {int(i): set(self.cats[self.cat_ptr[i]:self.cat_ptr[i + 1]].tolist())
                         for i in np.flatnonzero(self.is_cat)}

    def predict_contrib(self, x):
        """Return (prediction, per-feature contributions) using path attribution."""
        contrib = np.zeros(len(x))
        pred = 0.0
        feature, thr, left, right, value = self.feature, self.threshold, self.left, self.right, self.value
        for n in self.roots.tolist():
            while left[n] != -1:
                f = feature[n]
                go_left = (int(x[f]) in self.cat_sets[n]) if self.is_cat[n] else x[f] <= thr[n]
                child = left[n] if go_left else right[n]
                contrib[f] += value[child] - value[n]
                n = child
            pred += value[n]
        return pred, contrib


class Predictor:
    """Serves the full ensemble when the ML libraries are installed, otherwise the
    numpy-only LightGBM export (used for the serverless deployment)."""

    def __init__(self):
        self.lite = os.environ.get("PRICESCOPE_LITE") == "1"
        if not self.lite:
            try:
                import joblib
                bundle = joblib.load(MODELS_DIR / "model.joblib")
                self.models, self.weights = bundle["models"], bundle["weights"]
                self.features, self.categories = bundle["features"], bundle["categories"]
            except (ImportError, FileNotFoundError):
                self.lite = True
        if self.lite:
            meta = json.loads((MODELS_DIR / "lite_meta.json").read_text())
            self.features, self.categories = meta["features"], meta["categories"]
            self.lgbm = LiteLGBM(MODELS_DIR / "lgbm_lite.npz")
        self.metrics = json.loads((MODELS_DIR / "metrics.json").read_text())
        self.serving = "LightGBM (lite)" if self.lite else self.metrics["best_model"]
        self.df = pd.read_csv(PROCESSED_CSV)
        self.city_info = self.df.groupby("city")[CITY_COLS + ["country_name"]].first()
        self.centers = json.loads((MODELS_DIR / "centers.json").read_text())
        self.city_data = {city: d.reset_index(drop=True) for city, d in self.df.groupby("city")}

    def location_features(self, city, lat, lon, k=25):
        d = self.city_data[city]
        dist_km = haversine_km(lat, lon, d.latitude.values, d.longitude.values)
        idx = np.argsort(dist_km, kind="stable")[:k]
        dist_km = dist_km[idx]
        nb = d.iloc[idx]
        w = 1.0 / (dist_km + 0.3)
        feats = {c: float(np.average(nb[c], weights=w)) for c in LOCAL_COLS}
        c_lat, c_lon = self.centers[city]
        feats["distance_city_center"] = float(haversine_km(lat, lon, c_lat, c_lon))
        return feats, nb, float(dist_km.mean())

    def predict(self, req: dict) -> dict:
        city = req["city"]
        lat, lon = float(req["latitude"]), float(req["longitude"])
        loc, nb, nb_dist = self.location_features(city, lat, lon)
        row = {
            "city": city, "latitude": lat, "longitude": lon,
            "room_type": req.get("room_type", "Entire home/apt"),
            "max_guests": int(req.get("max_guests", 2)),
            "num_bedrooms": int(req.get("num_bedrooms", 1)),
            "is_superhost": int(bool(req.get("is_superhost", 0))),
            "is_multi_listing": int(bool(req.get("is_multi_listing", 0))),
            "is_business_listing": int(bool(req.get("is_business_listing", 0))),
            "cleanliness_score": float(req.get("cleanliness_score", 9.5)),
            "guest_satisfaction_score": float(req.get("guest_satisfaction_score", 93)),
            "day_type": req.get("day_type", "weekday"),
            **loc, **self.city_info.loc[city, CITY_COLS].to_dict(),
        }
        # manual overrides from the "advanced" panel
        for c in ["distance_city_center", "distance_metro", "attraction_index_norm", "restaurant_index_norm"]:
            if req.get(c) not in (None, ""):
                row[c] = float(req[c])
        X = base_features(pd.DataFrame([row]))
        for c in CATEGORICAL:
            X[c] = pd.Categorical(X[c].astype(str), categories=self.categories[c])
        X = X[self.features]

        if self.lite:
            x = np.array([X[c].cat.codes.iloc[0] if c in CATEGORICAL else X[c].iloc[0] for c in self.features], float)
            log_pred, contrib = self.lgbm.predict_contrib(x)
            per_model = {"LightGBM": round(float(np.expm1(log_pred)), 2)}
        else:
            log_pred, per_model = 0.0, {}
            for name, w in self.weights.items():
                Xi = X.astype({c: str for c in CATEGORICAL}) if name == "CatBoost" else X
                p = float(self.models[name].predict(Xi)[0])
                per_model[name] = round(float(np.expm1(p)), 2)
                log_pred += w * p
            contrib = self.models["LightGBM"].booster_.predict(X, pred_contrib=True)[0]
        price = float(np.expm1(log_pred))
        lo, hi = self.metrics["interval_log_resid"][city]

        # explanation: LightGBM feature contributions grouped into readable drivers
        names = self.features + ["_base"]
        groups = {
            "Room type": ["room_type"], "Guest capacity & bedrooms": ["max_guests", "num_bedrooms", "guests_per_bedroom"],
            "Distance to centre": ["distance_city_center", "log_dist_center"],
            "Metro access": ["distance_metro", "log_dist_metro"],
            "Attractions & restaurants": ["attraction_index_norm", "restaurant_index_norm", "attr_x_rest", "proximity_index"],
            "Exact location (lat/lon)": ["latitude", "longitude"],
            "City": ["city", "Crime_Index", "Safety_Index", "Monthly_Average_Net_salary", "Taxi_price_per_Km",
                     "Monthly_Basic_Utilities"],
            "Host & reviews": ["is_superhost", "is_multi_listing", "is_business_listing", "cleanliness_score",
                               "guest_satisfaction_score", "quality_score"],
            "Weekday / weekend": ["is_weekend"],
        }
        cmap = dict(zip(names, contrib))
        drivers = sorted(({"name": g, "pct": round(float((np.exp(sum(cmap.get(c, 0) for c in cols)) - 1) * 100), 1)}
                          for g, cols in groups.items()), key=lambda d: -abs(d["pct"]))

        city_df = self.df[self.df.city == city]
        same = city_df[city_df.room_type == row["room_type"]][TARGET]
        comps = nb.assign(km=haversine_km(lat, lon, nb.latitude.values, nb.longitude.values))
        comps = (comps[comps.room_type == row["room_type"]]
                 .drop_duplicates(subset=[TARGET, "max_guests", "num_bedrooms"]).head(8))
        return {
            "price": round(price, 2),
            "per_night": round(price / 2, 2),
            "low": round(float(np.expm1(log_pred + lo)), 2),
            "high": round(float(np.expm1(log_pred + hi)), 2),
            "per_model": per_model,
            "city_median": round(float(city_df[TARGET].median()), 2),
            "city_room_median": round(float(same.median()), 2) if len(same) else None,
            "percentile_in_city": round(float((same < price).mean() * 100), 1) if len(same) else None,
            "neighbourhood_median": round(float(nb[TARGET].median()), 2),
            "drivers": drivers,
            "location": {k: round(v, 3) for k, v in loc.items()},
            "center": self.centers[city],
            "comps": [{"price": round(float(r[TARGET]), 2), "room_type": r.room_type, "guests": int(r.max_guests),
                       "bedrooms": int(r.num_bedrooms), "day_type": r.day_type, "km": round(float(r.km), 2),
                       "lat": float(r.latitude), "lon": float(r.longitude)} for _, r in comps.iterrows()],
            "neighbour_radius_km": round(nb_dist, 2),
        }
