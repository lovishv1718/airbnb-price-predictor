"""Step 3 - Model training, evaluation and export.

* Target: log1p(price_total)
* Split: GroupShuffleSplit on listing_id (80/20) so the weekday and weekend
  rows of the same listing never sit on both sides -> no leakage.
* Models: Ridge, Random Forest, XGBoost, LightGBM, CatBoost + weighted ensemble.
* The final ensemble is refit on 100% of the data and saved for the Flask app.
"""
import json
import time

import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shap
from catboost import CatBoostRegressor
from lightgbm import LGBMRegressor, early_stopping, log_evaluation
from scipy.optimize import minimize
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GroupKFold, GroupShuffleSplit
from sklearn.preprocessing import StandardScaler
from xgboost import XGBRegressor

from config import FIG_DIR, MODELS_DIR, PROCESSED_CSV, RANDOM_STATE, TARGET
from features import CATEGORICAL, FEATURES, base_features

plt.rcParams.update({"figure.dpi": 110, "savefig.bbox": "tight",
                     "axes.spines.top": False, "axes.spines.right": False})


def metrics(y_true_log, y_pred_log):
    yt, yp = np.expm1(y_true_log), np.expm1(y_pred_log)
    ape = np.abs(yp - yt) / yt
    return {
        "r2_log": round(float(r2_score(y_true_log, y_pred_log)), 4),
        "r2_eur": round(float(r2_score(yt, yp)), 4),
        "mae_eur": round(float(mean_absolute_error(yt, yp)), 2),
        "rmse_eur": round(float(np.sqrt(mean_squared_error(yt, yp))), 2),
        "mape_pct": round(float(ape.mean() * 100), 2),
        "median_ape_pct": round(float(np.median(ape) * 100), 2),
        "within_20pct": round(float((ape <= .2).mean() * 100), 2),
        "within_30pct": round(float((ape <= .3).mean() * 100), 2),
    }


def onehot(X, columns=None):
    d = pd.get_dummies(X, columns=CATEGORICAL, dtype=float)
    return d.reindex(columns=columns, fill_value=0.0) if columns is not None else d


def cat_frame(X):
    X = X.copy()
    for c in CATEGORICAL:
        X[c] = X[c].astype(str)
    return X


def make_models():
    return {
        "LightGBM": LGBMRegressor(n_estimators=4000, learning_rate=0.02, num_leaves=63, min_child_samples=20,
                                  subsample=0.8, subsample_freq=1, colsample_bytree=0.7, reg_lambda=1.0,
                                  random_state=RANDOM_STATE, verbose=-1),
        "XGBoost": XGBRegressor(n_estimators=4000, learning_rate=0.02, max_depth=8, min_child_weight=3,
                                subsample=0.8, colsample_bytree=0.7, reg_lambda=1.0, tree_method="hist",
                                enable_categorical=True, early_stopping_rounds=200,
                                random_state=RANDOM_STATE, n_jobs=-1),
        "CatBoost": CatBoostRegressor(iterations=5000, learning_rate=0.04, depth=8, l2_leaf_reg=3,
                                      loss_function="RMSE", random_seed=RANDOM_STATE, verbose=0,
                                      early_stopping_rounds=200, cat_features=CATEGORICAL),
    }


def fit_gbms(Xtr, ytr, Xva, yva):
    models, best_iter, preds, times = make_models(), {}, {}, {}
    for name, m in models.items():
        t = time.time()
        if name == "LightGBM":
            m.fit(Xtr, ytr, eval_set=[(Xva, yva)], callbacks=[early_stopping(200, verbose=False), log_evaluation(0)])
            best_iter[name] = int(m.best_iteration_)
            preds[name] = m.predict(Xva)
        elif name == "XGBoost":
            m.fit(Xtr, ytr, eval_set=[(Xva, yva)], verbose=False)
            best_iter[name] = int(m.best_iteration + 1)
            preds[name] = m.predict(Xva)
        else:
            m.fit(cat_frame(Xtr), ytr, eval_set=(cat_frame(Xva), yva))
            best_iter[name] = int(m.get_best_iteration() + 1)
            preds[name] = m.predict(cat_frame(Xva))
        times[name] = round(time.time() - t, 1)
        print(f"    {name:<9} iters={best_iter[name]:<5} val R2(log)={r2_score(yva, preds[name]):.4f} ({times[name]}s)")
    return models, best_iter, preds, times


def ensemble_weights(preds, y):
    names = list(preds)
    P = np.column_stack([preds[n] for n in names])
    loss = lambda w: np.mean((P @ (np.abs(w) / np.abs(w).sum()) - y) ** 2)
    w = minimize(loss, np.ones(len(names)) / len(names), method="Nelder-Mead").x
    w = np.abs(w) / np.abs(w).sum()
    return dict(zip(names, np.round(w, 4).tolist()))


def refit_final(models_proto, best_iter, X, y):
    final = {}
    for name in models_proto:
        n = max(100, int(best_iter[name] * 1.1))  # ~10% more rounds for 25% more data
        if name == "LightGBM":
            m = make_models()["LightGBM"].set_params(n_estimators=n)
            m.fit(X, y)
        elif name == "XGBoost":
            m = make_models()["XGBoost"].set_params(n_estimators=n, early_stopping_rounds=None)
            m.fit(X, y, verbose=False)
        else:
            m = CatBoostRegressor(**{**make_models()["CatBoost"].get_params(), "iterations": n,
                                     "early_stopping_rounds": None})
            m.fit(cat_frame(X), y)
        final[name] = m
    return final


def predict_ensemble(models, weights, X):
    out = np.zeros(len(X))
    for name, w in weights.items():
        Xi = cat_frame(X) if name == "CatBoost" else X
        out += w * models[name].predict(Xi)
    return out


def plots(test, y_log, pred_log, lgbm, X_test, imp):
    yt, yp = np.expm1(y_log), np.expm1(pred_log)
    fig, ax = plt.subplots(1, 2, figsize=(13, 5))
    ax[0].scatter(yt, yp, s=4, alpha=.25, color="#FF385C")
    lim = np.percentile(yt, 99.5)
    ax[0].plot([0, lim], [0, lim], "k--", lw=1)
    ax[0].set(xlim=(0, lim), ylim=(0, lim), xlabel="Actual price (EUR)", ylabel="Predicted price (EUR)",
              title="Actual vs predicted (hold-out set)")
    res = y_log - pred_log
    ax[1].hist(res, bins=80, color="#2563EB")
    ax[1].set(title="Residuals on log scale", xlabel="log(actual) - log(predicted)")
    fig.savefig(FIG_DIR / "10_actual_vs_pred.png"); plt.close(fig)

    top = imp.head(20)[::-1]
    fig, ax = plt.subplots(figsize=(9, 7))
    ax.barh(top.index, top.values, color="#FF385C")
    ax.set(title="LightGBM feature importance (gain, top 20)", xlabel="Relative gain")
    fig.savefig(FIG_DIR / "11_feature_importance.png"); plt.close(fig)

    sample = X_test.sample(min(3000, len(X_test)), random_state=0)
    sv = shap.TreeExplainer(lgbm).shap_values(sample)
    shap.summary_plot(sv, sample, show=False, max_display=18)
    plt.title("SHAP summary - impact on log(price)")
    plt.savefig(FIG_DIR / "12_shap_summary.png"); plt.close("all")

    per_city = test.assign(ape=np.abs(yp - yt) / yt).groupby("city", observed=True)["ape"].median().sort_values() * 100
    fig, ax = plt.subplots(figsize=(10, 4.5))
    ax.bar(per_city.index, per_city.values, color="#10B981")
    ax.set(title="Median absolute % error by city (hold-out)", ylabel="Median APE (%)")
    fig.savefig(FIG_DIR / "13_error_by_city.png"); plt.close(fig)


def main():
    t0 = time.time()
    df = base_features(pd.read_csv(PROCESSED_CSV))
    y = np.log1p(df[TARGET])
    groups = df["listing_id"]

    tr_idx, te_idx = next(GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=RANDOM_STATE)
                          .split(df, groups=groups))
    train, test = df.iloc[tr_idx], df.iloc[te_idx]
    ytr, yte = y.iloc[tr_idx], y.iloc[te_idx]
    print(f"Train {len(train)} rows / Test {len(test)} rows (grouped by listing, no overlap: "
          f"{len(set(train.listing_id) & set(test.listing_id)) == 0})")

    Xtr, Xte = train[FEATURES], test[FEATURES]

    # internal validation split (grouped) for early stopping + ensemble weights
    a, b = next(GroupShuffleSplit(n_splits=1, test_size=0.15, random_state=1).split(Xtr, groups=train.listing_id))
    Xa, Xb, ya, yb = Xtr.iloc[a], Xtr.iloc[b], ytr.iloc[a], ytr.iloc[b]

    results = {}
    print("Baselines ...")
    results["City median (baseline)"] = metrics(yte, test.city.astype(str).map(ytr.groupby(train.city.astype(str)).median()).values)
    oh_tr = onehot(Xtr); oh_te = onehot(Xte, oh_tr.columns)
    sc = StandardScaler().fit(oh_tr)
    ridge = Ridge(alpha=1.0).fit(sc.transform(oh_tr), ytr)
    results["Ridge regression"] = metrics(yte, ridge.predict(sc.transform(oh_te)))
    rf = RandomForestRegressor(n_estimators=300, min_samples_leaf=2, max_features=0.5, n_jobs=-1,
                               random_state=RANDOM_STATE).fit(oh_tr, ytr)
    results["Random Forest"] = metrics(yte, rf.predict(oh_te))
    for k in ["Ridge regression", "Random Forest"]:
        print(f"    {k:<17} test R2(log)={results[k]['r2_log']}")

    print("Gradient boosting (early stopping on grouped validation) ...")
    models, best_iter, val_preds, times = fit_gbms(Xa, ya, Xb, yb)
    weights = ensemble_weights(val_preds, yb.values)
    print("    ensemble weights:", weights)

    # refit on full training split, evaluate on untouched test set
    train_models = refit_final(models, best_iter, Xtr, ytr)
    test_preds = {}
    for name, m in train_models.items():
        test_preds[name] = m.predict(cat_frame(Xte) if name == "CatBoost" else Xte)
        results[name] = metrics(yte, test_preds[name])
    ens = sum(weights[n] * test_preds[n] for n in weights)
    results["Weighted ensemble"] = metrics(yte, ens)

    # Reference only: a naive random row split leaks the weekday/weekend twin of each
    # listing into training and looks better than it really is.
    rtr, rte = next(GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=RANDOM_STATE)
                    .split(df, groups=np.arange(len(df))))
    leak = make_models()["LightGBM"].set_params(n_estimators=best_iter["LightGBM"])
    leak.fit(df.iloc[rtr][FEATURES], y.iloc[rtr])
    leaky = metrics(y.iloc[rte], leak.predict(df.iloc[rte][FEATURES]))
    print("    random-split LightGBM (leaky reference):", leaky)

    print("\nHold-out test results:")
    print(pd.DataFrame(results).T.to_string())

    lgbm = train_models["LightGBM"]
    imp = pd.Series(lgbm.booster_.feature_importance("gain"), index=FEATURES)
    imp = (imp / imp.sum()).sort_values(ascending=False)
    plots(test, yte.values, ens, lgbm, Xte, imp)

    per_city = {}
    for c, d in test.assign(p=ens).groupby("city", observed=True):
        per_city[str(c)] = metrics(np.log1p(d[TARGET]), d.p)

    # residual spread per city for the app's prediction interval (log scale, 10th/90th pct)
    resid = pd.Series(yte.values - ens, index=test.index)
    interval = {str(c): [round(float(r.quantile(.1)), 4), round(float(r.quantile(.9)), 4)]
                for c, r in resid.groupby(test.city.astype(str))}

    print("\nRefitting final ensemble on 100% of the data ...")
    final_models = refit_final(models, best_iter, df[FEATURES], y)

    MODELS_DIR.mkdir(exist_ok=True)
    joblib.dump({"models": final_models, "weights": weights,
                 "features": FEATURES, "categories": {c: df[c].cat.categories.tolist() for c in CATEGORICAL}},
                MODELS_DIR / "model.joblib", compress=3)
    report = {
        "split": {"train_rows": int(len(train)), "test_rows": int(len(test)), "strategy": "GroupShuffleSplit by listing_id (80/20)"},
        "results": results, "best_model": "Weighted ensemble", "random_split_reference": leaky, "weights": weights,
        "best_iterations": best_iter, "train_seconds": times,
        "per_city": per_city, "interval_log_resid": interval,
        "feature_importance": imp.round(5).to_dict(),
        "n_features": len(FEATURES), "features": FEATURES,
        "total_seconds": round(time.time() - t0, 1),
    }
    (MODELS_DIR / "metrics.json").write_text(json.dumps(report, indent=2))
    print(f"Saved model + metrics in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
