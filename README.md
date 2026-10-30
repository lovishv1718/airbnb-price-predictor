# PriceScope: Airbnb Price Prediction (10 European cities)

End-to-end ML project: data cleaning → EDA → model training (LightGBM, XGBoost and CatBoost ensemble) → Flask web app with interactive maps.

**Accuracy on unseen listings:** R² 0.857 (log price) · median error 17.1% · 74% of predictions within ±30%.

## Run
```bash
pip install -r requirements-ml.txt   # full stack (training + ensemble serving)
python run_pipeline.py               # optional: rebuilds data, figures, model and report (~7 min)
python app.py                        # http://127.0.0.1:5000
```
The trained model is already in `models/`, so `python app.py` works immediately.

## Deployment (Vercel)
`requirements.txt` holds only the web runtime (Flask, numpy, pandas, markdown). Without the ML libraries
the app automatically serves the LightGBM model from `models/lgbm_lite.npz`, a numpy-only export of the same
trees (identical predictions, R² 0.854), which keeps the serverless bundle small. Deploy with `vercel --prod`.

## Pages
- **Dashboard**: KPIs, Europe price map, charts and a city scorecard
- **Map Explorer**: all listings per city; points, price heatmap and density layers; filters
- **Price Predictor**: click the map, describe the listing, get a price with an interval, SHAP drivers and comparable listings
- **Route Planner**: pick the Airbnbs to visit; shortest paths by Dijkstra and Bellman-Ford, and the best visiting order by the Travelling Salesman algorithms (Held-Karp exact, nearest neighbour + 2-opt). All implemented from scratch in `src/algorithms.py`, tested with `python -m unittest discover tests`
- **Model Performance**: leaderboard, feature importance, per-city accuracy
- **Project Report**: full write-up (also in `reports/REPORT.md` and `reports/REPORT.docx`)
