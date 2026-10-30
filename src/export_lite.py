"""Export the trained LightGBM model to flat numpy arrays (models/lgbm_lite.npz).

The lite model needs only numpy at inference time, which keeps the serverless
deployment (Vercel) far below its bundle size limit.
"""
import json

import joblib
import numpy as np
import pandas as pd
from scipy.optimize import minimize

from config import MODELS_DIR, PROCESSED_CSV
from features import haversine_km


def estimate_centers():
    """City centre = point whose haversine distance best reproduces distance_city_center."""
    centers = {}
    for city, d in pd.read_csv(PROCESSED_CSV).groupby("city"):
        lat, lon, dist = d.latitude.values, d.longitude.values, d.distance_city_center.values
        x0 = [lat[dist.argmin()], lon[dist.argmin()]]
        res = minimize(lambda c: np.mean((haversine_km(lat, lon, c[0], c[1]) - dist) ** 2), x0, method="Nelder-Mead")
        centers[city] = [round(float(res.x[0]), 5), round(float(res.x[1]), 5)]
    return centers


def main():
    bundle = joblib.load(MODELS_DIR / "model.joblib")
    booster = bundle["models"]["LightGBM"].booster_
    dump = booster.dump_model()
    feat_names = dump["feature_names"]

    roots = []
    feature, threshold, left, right, value, is_cat = [], [], [], [], [], []
    node_cats = []

    def add(node):
        i = len(feature)
        feature.append(-1); threshold.append(0.0); left.append(-1); right.append(-1); is_cat.append(0)
        node_cats.append([])
        if "leaf_value" in node:
            value.append(node["leaf_value"])
            return i
        value.append(node["internal_value"])
        feature[i] = node["split_feature"]
        if node["decision_type"] == "==":
            is_cat[i] = 1
            node_cats[i] = [int(c) for c in str(node["threshold"]).split("||")]
        else:
            threshold[i] = float(node["threshold"])
        left[i] = add(node["left_child"])
        right[i] = add(node["right_child"])
        return i

    for t in dump["tree_info"]:
        roots.append(add(t["tree_structure"]))

    lens = np.array([len(c) for c in node_cats])
    np.savez_compressed(
        MODELS_DIR / "lgbm_lite.npz",
        feature=np.array(feature, np.int16), threshold=np.array(threshold, np.float64),
        left=np.array(left, np.int32), right=np.array(right, np.int32), value=np.array(value, np.float64),
        is_cat=np.array(is_cat, np.int8), cat_ptr=np.concatenate([[0], np.cumsum(lens)]).astype(np.int32),
        cats=np.array([c for cs in node_cats for c in cs], np.int16), roots=np.array(roots, np.int32),
    )
    (MODELS_DIR / "lite_meta.json").write_text(json.dumps({
        "features": feat_names, "categories": bundle["categories"]}, indent=1))
    (MODELS_DIR / "centers.json").write_text(json.dumps(estimate_centers(), indent=1))
    print(f"Exported {len(roots)} trees / {len(feature)} nodes -> models/lgbm_lite.npz")


if __name__ == "__main__":
    main()
