"""Extra figures for the PDF report: per-city price maps and hold-out error analysis.

Error analysis retrains LightGBM on the same grouped 80/20 split used in train.py,
so every number here comes from listings the model did not see.
"""
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from lightgbm import LGBMRegressor
from sklearn.model_selection import GroupShuffleSplit

from config import MODELS_DIR, PROCESSED_CSV, RANDOM_STATE, REPORTS_DIR, TARGET
from features import FEATURES, base_features

OUT = REPORTS_DIR / "figures"
plt.rcParams.update({"figure.dpi": 130, "savefig.bbox": "tight", "font.size": 10,
                     "axes.spines.top": False, "axes.spines.right": False,
                     "figure.facecolor": "white", "axes.facecolor": "white"})


def city_maps(df):
    for city, d in df.groupby("city"):
        fig, ax = plt.subplots(1, 2, figsize=(12, 4.6), gridspec_kw={"width_ratios": [1.25, 1]})
        rng = np.random.default_rng(0)
        lon = d.longitude + rng.uniform(-.0045, .0045, len(d))
        lat = d.latitude + rng.uniform(-.0045, .0045, len(d))
        vmax = d[TARGET].quantile(.95)
        sc = ax[0].scatter(lon, lat, c=d[TARGET].clip(upper=vmax), s=5, cmap="turbo", alpha=.7)
        fig.colorbar(sc, ax=ax[0], label="Price (EUR, clipped at p95)")
        ax[0].set(title=f"{city}: listing locations coloured by price", xlabel="Longitude", ylabel="Latitude")
        ax[0].set_aspect(1 / np.cos(np.radians(d.latitude.mean())))
        bins = pd.cut(d.distance_city_center, [0, .5, 1, 2, 3, 4, 6, 10, 30])
        g = d.groupby([bins, "room_type"], observed=True)[TARGET].median().unstack()
        for col, c in zip(g.columns, ["#FF385C", "#2563EB", "#10B981"]):
            ax[1].plot(range(len(g)), g[col], marker="o", label=col, color=c)
        ax[1].set_xticks(range(len(g)), [str(i) for i in g.index], rotation=35, fontsize=8)
        ax[1].set(title="Median price by distance to centre (km)", ylabel="Median price (EUR)")
        ax[1].legend(fontsize=8)
        fig.savefig(OUT / f"city_{city}.png")
        plt.close(fig)


def error_analysis(df):
    y = np.log1p(df[TARGET])
    tr, te = next(GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=RANDOM_STATE)
                  .split(df, groups=df["listing_id"]))
    it = json.loads((MODELS_DIR / "metrics.json").read_text())["best_iterations"]["LightGBM"]
    m = LGBMRegressor(n_estimators=it, learning_rate=0.02, num_leaves=63, subsample=0.8, subsample_freq=1,
                      colsample_bytree=0.7, reg_lambda=1.0, random_state=RANDOM_STATE, verbose=-1)
    m.fit(df.iloc[tr][FEATURES], y.iloc[tr])
    t = df.iloc[te].copy()
    t["pred"] = np.expm1(m.predict(t[FEATURES]))
    t["ape"] = (t.pred - t[TARGET]).abs() / t[TARGET] * 100
    t["band"] = pd.qcut(t[TARGET], 5, labels=["Q1 cheapest", "Q2", "Q3", "Q4", "Q5 priciest"])

    fig, ax = plt.subplots(1, 2, figsize=(12, 4.2))
    b = t.groupby("band", observed=True).agg(ape=("ape", "median"),
                                              bias=("pred", "median"), actual=(TARGET, "median"))
    ax[0].bar(b.index.astype(str), b.ape, color="#FF385C")
    ax[0].set(title="Median absolute % error by price quintile", ylabel="Median APE (%)")
    ax[1].bar(b.index.astype(str), (b.bias / b.actual - 1) * 100, color="#2563EB")
    ax[1].axhline(0, color="k", lw=.8)
    ax[1].set(title="Bias: median predicted vs actual (%)", ylabel="% over (+) / under (-)")
    fig.savefig(OUT / "err_price_band.png"); plt.close(fig)

    fig, ax = plt.subplots(1, 3, figsize=(13, 4))
    for a, col in zip(ax, ["room_type", "day_type", "max_guests"]):
        g = t.groupby(col, observed=True).ape.median()
        a.bar(g.index.astype(str), g.values, color="#10B981")
        a.set(title=f"Median APE by {col}", ylabel="%")
        a.tick_params(axis="x", rotation=20)
    fig.savefig(OUT / "err_segments.png"); plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 4))
    s = np.sort(t.ape.values)
    ax.plot(s, np.arange(1, len(s) + 1) / len(s) * 100, color="#FF385C", lw=2)
    for x in [10, 20, 30, 50]:
        ax.axvline(x, color="#ccc", lw=.8, ls="--")
        ax.text(x + 1, 5, f"{(t.ape <= x).mean() * 100:.0f}%", fontsize=9)
    ax.set(xlim=(0, 100), xlabel="Absolute % error", ylabel="% of predictions",
           title="Cumulative error distribution (hold-out)")
    fig.savefig(OUT / "err_cdf.png"); plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 4))
    res = np.log(t[TARGET]) - np.log(t.pred)
    ax.scatter(np.log(t.pred), res, s=3, alpha=.2, color="#2563EB")
    ax.axhline(0, color="k", lw=.8)
    ax.set(xlabel="log(predicted price)", ylabel="log residual", title="Residuals vs fitted values")
    fig.savefig(OUT / "err_resid_fitted.png"); plt.close(fig)

    worst = t.sort_values("ape", ascending=False).head(12)[
        ["city", "room_type", "max_guests", "num_bedrooms", "distance_city_center", TARGET, "pred", "ape"]]
    summary = {
        "by_band": b.round(2).reset_index().astype({"band": str}).to_dict("records"),
        "by_room": t.groupby("room_type").ape.median().round(2).to_dict(),
        "by_day": t.groupby("day_type").ape.median().round(2).to_dict(),
        "worst": worst.round(2).to_dict("records"),
        "within": {str(x): round(float((t.ape <= x).mean() * 100), 1) for x in [10, 20, 30, 50]},
    }
    (REPORTS_DIR / "error_analysis.json").write_text(json.dumps(summary, indent=1, default=str))


def model_compare():
    r = json.loads((MODELS_DIR / "metrics.json").read_text())["results"]
    names = list(r)
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.2))
    ax[0].barh(names, [r[n]["r2_log"] for n in names], color=["#9CA3AF"] * 3 + ["#FDA4B4"] * 3 + ["#FF385C"])
    ax[0].set(xlim=(0, 1), title="R² on log price (hold-out)")
    for i, n in enumerate(names):
        ax[0].text(r[n]["r2_log"] + .01, i, f"{r[n]['r2_log']:.3f}", va="center", fontsize=8)
    ax[1].barh(names, [r[n]["median_ape_pct"] for n in names], color="#2563EB")
    ax[1].set(title="Median absolute % error (lower is better)")
    ax[1].set_yticks([])
    fig.savefig(OUT / "model_compare.png"); plt.close(fig)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    df = base_features(pd.read_csv(PROCESSED_CSV))
    city_maps(df)
    error_analysis(df)
    model_compare()
    print("Report figures saved to", OUT)


if __name__ == "__main__":
    main()
