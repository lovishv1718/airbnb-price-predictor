"""Step 2 - Exploratory data analysis.

Produces static figures for the report (static/figures/*.png) and a compact
JSON summary (models/eda.json) that powers the interactive dashboard.
"""
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from config import FIG_DIR, MODELS_DIR, PROCESSED_CSV, TARGET

PALETTE = ["#FF385C", "#2563EB", "#10B981", "#F59E0B", "#8B5CF6",
           "#06B6D4", "#EC4899", "#84CC16", "#F97316", "#64748B"]
sns.set_theme(style="whitegrid", font_scale=1.0)
plt.rcParams.update({"figure.dpi": 110, "savefig.bbox": "tight",
                     "axes.spines.top": False, "axes.spines.right": False})


def save(fig, name):
    fig.savefig(FIG_DIR / f"{name}.png")
    plt.close(fig)


def figures(df):
    order = df.groupby("city")[TARGET].median().sort_values(ascending=False).index

    fig, ax = plt.subplots(1, 2, figsize=(13, 4.2))
    sns.histplot(df[TARGET].clip(upper=2000), bins=80, ax=ax[0], color=PALETTE[0])
    ax[0].set(title="Price distribution (clipped at 2,000 EUR)", xlabel="Price (EUR)")
    sns.histplot(np.log1p(df[TARGET]), bins=80, ax=ax[1], color=PALETTE[1])
    ax[1].set(title="log(1 + price) - near-normal, used as model target", xlabel="log(1+price)")
    save(fig, "01_price_distribution")

    fig, ax = plt.subplots(figsize=(13, 4.8))
    sns.boxplot(data=df, x="city", y=TARGET, order=order, showfliers=False, ax=ax,
                hue="city", palette=PALETTE, legend=False)
    ax.set(title="Price by city (outliers hidden)", ylabel="Price (EUR)", xlabel="")
    save(fig, "02_price_by_city")

    fig, ax = plt.subplots(figsize=(13, 4.8))
    sns.barplot(data=df, x="city", y=TARGET, hue="room_type", order=order,
                estimator=np.median, errorbar=None, ax=ax, palette=PALETTE[:3])
    ax.set(title="Median price by city and room type", ylabel="Median price (EUR)", xlabel="")
    save(fig, "03_city_roomtype")

    fig, ax = plt.subplots(figsize=(13, 4.8))
    sns.barplot(data=df, x="city", y=TARGET, hue="day_type", order=order,
                estimator=np.median, errorbar=None, ax=ax, palette=[PALETTE[1], PALETTE[0]])
    ax.set(title="Weekday vs weekend median price", ylabel="Median price (EUR)", xlabel="")
    save(fig, "04_weekday_weekend")

    fig, axes = plt.subplots(1, 3, figsize=(15, 4.2))
    s = df.sample(min(len(df), 12000), random_state=0)
    for ax, col in zip(axes, ["distance_city_center", "attraction_index_norm", "restaurant_index_norm"]):
        ax.scatter(s[col], np.log1p(s[TARGET]), s=4, alpha=.25, color=PALETTE[0])
        ax.set(xlabel=col, ylabel="log(1+price)", title=f"log price vs {col}")
    save(fig, "05_location_effects")

    fig, axes = plt.subplots(1, 2, figsize=(13, 4.2))
    sns.boxplot(data=df, x="max_guests", y=TARGET, showfliers=False, ax=axes[0], color=PALETTE[2])
    axes[0].set(title="Price by guest capacity", ylabel="Price (EUR)")
    sns.boxplot(data=df[df.num_bedrooms <= 5], x="num_bedrooms", y=TARGET, showfliers=False,
                ax=axes[1], color=PALETTE[3])
    axes[1].set(title="Price by number of bedrooms", ylabel="Price (EUR)")
    save(fig, "06_capacity")

    num = df.select_dtypes("number").drop(columns=["listing_id"]).copy()
    num["log_price"] = np.log1p(num.pop(TARGET))
    corr = num.corr()
    fig, ax = plt.subplots(figsize=(13, 10))
    sns.heatmap(corr, cmap="RdBu_r", center=0, annot=True, fmt=".2f", annot_kws={"size": 7},
                ax=ax, cbar_kws={"shrink": .7})
    ax.set_title("Correlation matrix (numeric features)")
    save(fig, "07_correlation")

    fig, axes = plt.subplots(1, 2, figsize=(13, 4.2))
    sns.boxplot(data=df, x="is_superhost", y=TARGET, showfliers=False, ax=axes[0],
                hue="is_superhost", palette=PALETTE[:2], legend=False)
    axes[0].set(title="Superhost vs regular host", xticks=[0, 1], xticklabels=["Regular", "Superhost"], xlabel="")
    s2 = df.assign(sat=pd.cut(df.guest_satisfaction_score, [0, 80, 90, 95, 100]))
    sns.boxplot(data=s2, x="sat", y=TARGET, showfliers=False, ax=axes[1], color=PALETTE[4])
    axes[1].set(title="Price by guest satisfaction band", xlabel="Satisfaction score", ylabel="Price (EUR)")
    save(fig, "08_host_quality")

    city = df.groupby("city").agg(price=(TARGET, "median"), salary=("Monthly_Average_Net_salary", "first"),
                                  n=(TARGET, "size"))
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.scatter(city.salary, city.price, s=city.n / 25, color=PALETTE[0], alpha=.7)
    for c, r in city.iterrows():
        ax.annotate(c, (r.salary, r.price), xytext=(6, 4), textcoords="offset points")
    ax.set(xlabel="Monthly average net salary (EUR)", ylabel="Median price (EUR)",
           title="City affluence vs Airbnb price (bubble = #listings)")
    save(fig, "09_salary_vs_price")


def summary(df):
    g = df.groupby("city")
    cities = []
    for c, d in g:
        cities.append({
            "city": c, "country": d.country_name.iloc[0], "listings": int(len(d)),
            "median_price": round(float(d[TARGET].median()), 2),
            "mean_price": round(float(d[TARGET].mean()), 2),
            "p25": round(float(d[TARGET].quantile(.25)), 2), "p75": round(float(d[TARGET].quantile(.75)), 2),
            "lat": round(float(d.latitude.mean()), 4), "lon": round(float(d.longitude.mean()), 4),
            "superhost_pct": round(float(d.is_superhost.mean() * 100), 1),
            "entire_home_pct": round(float((d.room_type == "Entire home/apt").mean() * 100), 1),
            "satisfaction": round(float(d.guest_satisfaction_score.mean()), 1),
            "weekday_median": round(float(d.loc[d.day_type == "weekday", TARGET].median()), 2),
            "weekend_median": round(float(d.loc[d.day_type == "weekend", TARGET].median()), 2),
            "safety_index": float(d.Safety_Index.iloc[0]),
            "crime_index": float(d.Crime_Index.iloc[0]),
            "salary": float(d.Monthly_Average_Net_salary.iloc[0]),
        })
    cities.sort(key=lambda x: -x["median_price"])
    rt = df.pivot_table(index="city", columns="room_type", values=TARGET, aggfunc="median").round(2)
    hist_counts, edges = np.histogram(df[TARGET].clip(upper=2000), bins=60)
    dist_bins = pd.cut(df.distance_city_center, [0, 1, 2, 3, 4, 6, 8, 12, 30])
    by_dist = df.groupby([dist_bins, "city"], observed=True)[TARGET].median().unstack().round(1)
    return {
        "kpis": {
            "listings": int(len(df)), "cities": int(df.city.nunique()),
            "median_price": round(float(df[TARGET].median()), 2),
            "mean_price": round(float(df[TARGET].mean()), 2),
            "superhost_pct": round(float(df.is_superhost.mean() * 100), 1),
            "satisfaction": round(float(df.guest_satisfaction_score.mean()), 1),
            "weekend_premium_pct": round(float(
                df[df.day_type == "weekend"][TARGET].median() / df[df.day_type == "weekday"][TARGET].median() * 100 - 100), 1),
        },
        "cities": cities,
        "room_type": {"index": rt.index.tolist(), "columns": rt.columns.tolist(),
                      "values": rt.fillna(0).values.tolist()},
        "room_type_share": df.room_type.value_counts().to_dict(),
        "histogram": {"counts": hist_counts.tolist(), "edges": edges.round(1).tolist()},
        "by_distance": {"bins": [str(b) for b in by_dist.index], "cities": by_dist.columns.tolist(),
                        "values": by_dist.where(by_dist.notna(), None).values.tolist()},
        "guests": df.groupby("max_guests")[TARGET].median().round(1).to_dict(),
        "bedrooms": df[df.num_bedrooms <= 5].groupby("num_bedrooms")[TARGET].median().round(1).to_dict(),
    }


def main():
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    MODELS_DIR.mkdir(exist_ok=True)
    df = pd.read_csv(PROCESSED_CSV)
    figures(df)
    s = summary(df)
    (MODELS_DIR / "eda.json").write_text(json.dumps(s, indent=1, default=str))
    print("EDA KPIs:", s["kpis"])
    for c in s["cities"]:
        print(f"  {c['city']:<10} n={c['listings']:<5} median={c['median_price']}")


if __name__ == "__main__":
    main()
