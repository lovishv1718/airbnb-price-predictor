"""Feature engineering shared by training and the Flask app."""
import numpy as np
import pandas as pd

EARTH_KM = 6371.0

NUMERIC = [
    "max_guests", "num_bedrooms", "is_superhost", "is_multi_listing", "is_business_listing",
    "cleanliness_score", "guest_satisfaction_score", "distance_city_center", "distance_metro",
    "attraction_index_norm", "restaurant_index_norm", "proximity_index", "latitude", "longitude",
    "Crime_Index", "Safety_Index", "Monthly_Average_Net_salary", "Taxi_price_per_Km",
    "Monthly_Basic_Utilities",
    # engineered
    "is_weekend", "guests_per_bedroom", "log_dist_center", "log_dist_metro",
    "attr_x_rest", "quality_score",
]
CATEGORICAL = ["city", "room_type"]
FEATURES = NUMERIC + CATEGORICAL


def base_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["is_weekend"] = (out["day_type"] == "weekend").astype(int)
    out["guests_per_bedroom"] = out["max_guests"] / out["num_bedrooms"].clip(lower=1)
    out["log_dist_center"] = np.log1p(out["distance_city_center"])
    out["log_dist_metro"] = np.log1p(out["distance_metro"])
    out["attr_x_rest"] = out["attraction_index_norm"] * out["restaurant_index_norm"] / 100
    out["quality_score"] = out["cleanliness_score"] * 10 * 0.4 + out["guest_satisfaction_score"] * 0.6
    for c in CATEGORICAL:
        out[c] = out[c].astype("category")
    return out


def haversine_km(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(np.radians, (lat1, lon1, lat2, lon2))
    a = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    return 2 * EARTH_KM * np.arcsin(np.sqrt(a))
