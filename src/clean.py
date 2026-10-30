"""Step 1 - Data cleaning & validation.

Reads the raw CSV, fixes inconsistencies, removes duplicates and extreme
price outliers, and writes data/processed.csv plus a cleaning log.
"""
import json

import numpy as np
import pandas as pd

from config import DATA_DIR, PROCESSED_CSV, RAW_CSV, REPORTS_DIR, TARGET


def clean(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    log = {"raw_rows": int(len(df)), "raw_cols": int(df.shape[1]), "steps": []}

    def step(name, before, after, note=""):
        log["steps"].append({"step": name, "rows_before": int(before),
                             "rows_after": int(after), "removed": int(before - after),
                             "note": note})

    # 1. Drop the exported index column
    df = df.drop(columns=[c for c in df.columns if c.startswith("Unnamed")])
    step("Drop index column", len(df), len(df), "'Unnamed: 0' was a pandas export index")

    # 2. Missing values
    n = len(df)
    missing = int(df.isna().sum().sum())
    df = df.dropna(subset=[TARGET])
    step("Missing values check", n, len(df), f"{missing} missing cells found")

    # 3. Exact duplicates
    n = len(df)
    df = df.drop_duplicates()
    step("Remove exact duplicates", n, len(df))

    # 4. Fix geocoding errors: some Rome listings were reverse-geocoded to the Vatican
    vatican = int((df["country_name"] != "Italy").where(df["city"] == "Rome", False).sum())
    df.loc[df["city"] == "Rome", "country_name"] = "Italy"
    step("Fix country label for Rome", len(df), len(df),
         f"{vatican} rows labelled 'Holy See (Vatican City State)' -> 'Italy'")

    # 5. Type consistency
    df["max_guests"] = df["max_guests"].round().astype(int)
    df["room_type"] = df["room_type"].str.strip()
    flags_ok = ((df["room_type"] == "Shared room") == (df["is_shared_room"] == 1)) & \
               ((df["room_type"] == "Private room") == (df["is_private_room"] == 1))
    n = len(df)
    df = df[flags_ok]
    step("Room-type flag consistency", n, len(df), "room_type must agree with is_*_room flags")

    # 6. Domain validity
    n = len(df)
    df = df[(df[TARGET] > 0) & df["cleanliness_score"].between(0, 10)
            & df["guest_satisfaction_score"].between(0, 100)
            & (df["distance_city_center"] >= 0) & (df["distance_metro"] >= 0)]
    step("Domain range checks", n, len(df))

    # 7. Price outliers - per-city IQR fences on log price (3 x IQR, very conservative)
    n = len(df)
    lp = np.log(df[TARGET])
    g = lp.groupby(df["city"])
    q1, q3 = g.transform(lambda s: s.quantile(0.25)), g.transform(lambda s: s.quantile(0.75))
    iqr = q3 - q1
    keep = lp.between(q1 - 3 * iqr, q3 + 3 * iqr)
    df = df[keep]
    step("Remove extreme price outliers", n, len(df),
         "per-city 3xIQR fence on log(price); removes data-entry errors such as 43,955 EUR")

    # 8. Listing id: the same listing appears once for weekday and once for weekend.
    # It is used to build a leakage-free grouped train/test split.
    key = ["city", "latitude", "longitude", "room_type", "max_guests", "num_bedrooms",
           "distance_city_center", "distance_metro"]
    df["listing_id"] = df.groupby(key, sort=False).ngroup()
    log["listings_in_both_day_types"] = int((df.groupby("listing_id")["day_type"].nunique() > 1).sum())

    df = df.reset_index(drop=True)
    log["clean_rows"] = int(len(df))
    log["clean_cols"] = int(df.shape[1])
    log["rows_removed_total"] = log["raw_rows"] - log["clean_rows"]
    return df, log


def main():
    DATA_DIR.mkdir(exist_ok=True)
    REPORTS_DIR.mkdir(exist_ok=True)
    raw = pd.read_csv(RAW_CSV)
    df, log = clean(raw)
    df.to_csv(PROCESSED_CSV, index=False)
    (REPORTS_DIR / "cleaning_log.json").write_text(json.dumps(log, indent=2))
    for s in log["steps"]:
        print(f"  {s['step']:<35} removed={s['removed']:<5} {s['note']}")
    print(f"Clean dataset: {df.shape} -> {PROCESSED_CSV}")


if __name__ == "__main__":
    main()
