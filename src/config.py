"""Shared paths and constants for the Airbnb price prediction project."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW_CSV = ROOT / "Cleaned_data.csv"
DATA_DIR = ROOT / "data"
PROCESSED_CSV = DATA_DIR / "processed.csv"
MODELS_DIR = ROOT / "models"
REPORTS_DIR = ROOT / "reports"
FIG_DIR = ROOT / "static" / "figures"
ARTIFACTS = MODELS_DIR / "artifacts.json"

TARGET = "price_total"
RANDOM_STATE = 42

CITY_COLS = [
    "Crime_Index", "Safety_Index", "Monthly_Average_Net_salary",
    "Taxi_price_per_Km", "Monthly_Basic_Utilities",
]

# Features the user controls directly in the UI
LISTING_FEATURES = [
    "room_type", "max_guests", "num_bedrooms", "is_superhost",
    "is_multi_listing", "is_business_listing", "cleanliness_score",
    "guest_satisfaction_score", "day_type",
]

# Features derived from the location (lat/lon) of the listing
LOCATION_FEATURES = [
    "city", "latitude", "longitude", "distance_city_center", "distance_metro",
    "attraction_index_norm", "restaurant_index_norm", "proximity_index",
]
