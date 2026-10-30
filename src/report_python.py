"""Python report: reports/Altitude_Python_Report.pdf (target 15-20 pages)."""
import catboost
import flask
import lightgbm
import matplotlib
import numpy
import pandas
import seaborn
import shap
import sklearn
import xgboost

from pdf_common import *  # noqa: F403  (layout helpers, styles, data)

DOC.update(title="Altitude - Python Project Report", header="Altitude - Airbnb Price Intelligence in Python",
           subject="Python Report")


def build():
    cover("PYTHON PROJECT REPORT", "Altitude: Airbnb Price Intelligence in Python",
          "An end-to-end Python application: data cleaning with pandas, analysis with matplotlib, machine learning "
          "with scikit-learn and gradient boosting, and a Flask web app with interactive maps",
          [["Subject", "Python programming"],
           ["Dataset", f"{LOG['raw_rows']:,} Airbnb listings, 10 European cities, 29 columns"],
           ["Best model", f"Weighted ensemble, R² {BEST['r2_log']:.3f}, median error {pct(BEST['median_ape_pct'])}"]])

    # ---------------------------------------------------------------- 1
    chapter("1. Introduction")
    P("Altitude is a complete Python application that predicts the price of an Airbnb listing in ten European "
      "cities (Amsterdam, Athens, Barcelona, Berlin, Budapest, Lisbon, London, Paris, Rome and Vienna) and lets "
      "users explore the market on interactive maps. Every part of it, from the data pipeline to the "
      "machine-learning models, the algorithms and the web server, is written in Python.")
    H2("1.1 Objectives")
    bullets(["Load, validate and clean a real 51,707-row dataset with pandas, documenting every change.",
             "Analyse the data and produce publication-quality charts with matplotlib and seaborn.",
             "Train, compare and explain six regression models with scikit-learn, LightGBM, XGBoost and CatBoost.",
             "Package the model in object-oriented Python and serve it through a Flask web application and REST API.",
             "Test the code with unittest, automate screenshots with Playwright, and deploy the app publicly."])
    H2("1.2 Technology stack")
    table([["Library", "Version", "Used for"],
           ["Python", "3.13", "Language for every component"],
           ["pandas", pandas.__version__, "Loading, cleaning, grouping and aggregating the data"],
           ["NumPy", numpy.__version__, "Vectorised maths, haversine distances, the numpy model evaluator"],
           ["matplotlib / seaborn", f"{matplotlib.__version__} / {seaborn.__version__}", "All report figures"],
           ["scikit-learn", sklearn.__version__, "Ridge, Random Forest, grouped splits, metrics"],
           ["LightGBM / XGBoost / CatBoost", f"{lightgbm.__version__} / {xgboost.__version__} / {catboost.__version__}",
            "Gradient-boosted tree models"],
           ["SHAP", shap.__version__, "Model explanations"],
           ["Flask", flask.__version__, "Web server, page routes and JSON API"],
           ["unittest, Playwright, ReportLab", "-", "Testing, screenshot automation, this PDF"]],
          col_w=[5 * cm, 3.4 * cm, CONTENT_W - 8.4 * cm])
    H2("1.3 Project structure")
    story.append(Preformatted(
        "altitude/\n"
        "  app.py                  Flask app: page routes + REST API\n"
        "  run_pipeline.py         runs every pipeline step with subprocess\n"
        "  src/config.py           shared paths and constants (pathlib)\n"
        "  src/clean.py            step 1: cleaning and validation\n"
        "  src/eda.py              step 2: figures + dashboard data\n"
        "  src/features.py         feature engineering shared by training and serving\n"
        "  src/train.py            step 3: training, evaluation, model export\n"
        "  src/export_lite.py      LightGBM -> numpy arrays for serverless hosting\n"
        "  src/predictor.py        Predictor and LiteLGBM classes (inference)\n"
        "  src/algorithms.py       graph algorithms for the Route Planner\n"
        "  templates/, static/     Jinja2 HTML templates, CSS, JavaScript\n"
        "  tests/                  unittest test suite\n"
        "  models/, reports/       trained models, metrics, figures, reports", S["code"]))
    P("Each step is a separate module with a <font face='Mono'>main()</font> function guarded by "
      "<font face='Mono'>if __name__ == \"__main__\"</font>, so it can be run on its own or imported. "
      "All paths come from one module, <font face='Mono'>config.py</font>, built with "
      "<font face='Mono'>pathlib</font>, so the project runs from any folder.")
    story.append(Preformatted((ROOT / "src/config.py").read_text(encoding="utf-8").split("CITY_COLS")[0].strip(),
                              S["code"]))

    # ---------------------------------------------------------------- 2
    H1("2. Data Handling with pandas")
    P(f"The raw file has {LOG['raw_rows']:,} rows and {LOG['raw_cols']} columns. Each row is one listing on a "
      "weekday or a weekend, with its price (a 2-night stay for 2 people, in euros), room type, capacity, host "
      "flags, review scores, location measures (distance to the centre and the metro, attraction and restaurant "
      "indices) and city-level economic indicators.")
    H2("2.1 The cleaning function")
    P("<font face='Mono'>clean()</font> returns the cleaned DataFrame and a log. A nested helper function, "
      "<font face='Mono'>step()</font>, records the row count before and after each stage. The log is saved as "
      "JSON, so the cleaning is fully documented and reproducible.")
    code("src/clean.py", "clean", 38, "Listing 2.1 - src/clean.py: the first half of clean().")
    H2("2.2 Results")
    rows = [["Step", "Removed", "Detail"]]
    for s in LOG["steps"]:
        rows.append([s["step"], s["removed"], s["note"] or "-"])
    table(rows, col_w=[4.6 * cm, 1.8 * cm, CONTENT_W - 6.4 * cm])
    P("Several pandas idioms do the work. <font face='Mono'>drop_duplicates()</font> removes 63 copies, a "
      "boolean <font face='Mono'>.loc</font> assignment fixes 4,580 Rome rows mislabelled as the Vatican, and "
      "<font face='Mono'>groupby(...).transform()</font> computes per-city quartiles for the outlier fence "
      "without a Python loop. <font face='Mono'>groupby(...).ngroup()</font> gives every listing an id. That "
      f"revealed that {LOG['listings_in_both_day_types']:,} listings appear twice, once on a weekday and once on "
      "a weekend, which matters for honest model evaluation (Chapter 4).", "callout")

    # ---------------------------------------------------------------- 3
    H1("3. Data Analysis and Visualisation")
    P(f"<font face='Mono'>eda.py</font> turns the cleaned data into figures and a JSON summary for the "
      f"dashboard. The median stay costs {eur(K['median_price'])} and the mean {eur(K['mean_price'])}. Prices "
      "are right-skewed, so the models predict log price.")
    img(FIG_DIR / "03_city_roomtype.png", "Figure 3.1 - Median price by city and room type (seaborn barplot).",
        max_h=CONTENT_H * .28)
    img(FIG_DIR / "05_location_effects.png", "Figure 3.2 - Log price against distance to centre, attraction and "
        "restaurant indices (matplotlib scatter).", max_h=CONTENT_H * .24)
    P("Location is the strongest signal: price falls steeply in the first 1 to 2 km from the centre and rises "
      "with the attraction and restaurant indices. Amsterdam and Paris are the most expensive cities and "
      "Athens the cheapest. Superhost status and reviews make little difference to price.")
    code("src/eda.py", "save", 6, "Listing 3.1 - A small helper keeps every figure consistent; the global style "
         "is set once with sns.set_theme() and plt.rcParams.")
    P("The dashboard summary is built with <font face='Mono'>groupby</font>, "
      "<font face='Mono'>pivot_table</font>, <font face='Mono'>pd.cut</font> for distance bands and "
      "<font face='Mono'>np.histogram</font>, then written with <font face='Mono'>json.dumps</font>. The web "
      "app reads this file at start-up instead of recomputing it on every request.")

    # ---------------------------------------------------------------- 4
    H1("4. Machine Learning in Python")
    H2("4.1 Feature engineering")
    P("One function, used by both training and the web app, adds six engineered features. Because it is "
      "shared, the features are always computed exactly the same way in both places.")
    code("src/features.py", "base_features", 14, "Listing 4.1 - src/features.py: vectorised pandas feature engineering.")
    H2("4.2 Leakage-free evaluation")
    P(f"<font face='Mono'>GroupShuffleSplit</font> from scikit-learn holds out 20% of listings "
      f"({M['split']['test_rows']:,} rows), grouped by <font face='Mono'>listing_id</font>, so the weekday and "
      "weekend copies of a listing are never split between training and test. A random split would report "
      f"R² {M['random_split_reference']['r2_log']:.3f}; the honest grouped score is {BEST['r2_log']:.3f}.")
    code("src/train.py", "metrics", 15, "Listing 4.2 - src/train.py: all evaluation metrics in one function "
         "returning a dictionary.")
    H2("4.3 Models and results")
    rows = [["Model", "R² log", "MAE €", "Median error", "Within ±30%"]]
    for n, r in M["results"].items():
        rows.append([("<b>%s</b>" % n) if n == M["best_model"] else n, f"{r['r2_log']:.4f}", f"{r['mae_eur']:.1f}",
                     pct(r["median_ape_pct"]), pct(r["within_30pct"])])
    table(rows, col_w=[5 * cm] + [(CONTENT_W - 5 * cm) / 4] * 4)
    P("Six models were compared: a city-median baseline, Ridge regression, Random Forest, LightGBM, XGBoost and "
      "CatBoost. The three boosting models use early stopping on a grouped validation fold. The final "
      "ensemble averages them with weights found by <font face='Mono'>scipy.optimize.minimize</font> ("
      + ", ".join(f"{k} {v * 100:.0f}%" for k, v in M["weights"].items()) + "). It explains 85.7% of the "
      "variation in log price on unseen listings, with a typical error of 17%.")
    img(FIG_DIR / "10_actual_vs_pred.png", "Figure 4.1 - Predicted against actual price on the hold-out set.",
        max_h=CONTENT_H * .26)
    img(FIG_DIR / "12_shap_summary.png", "Figure 4.2 - SHAP summary: how each feature moves the price.",
        max_h=CONTENT_H * .34)
    P("The most important features describe how central a location is (proximity, attractions and restaurants), "
      "followed by city, room type and capacity.")

    # ---------------------------------------------------------------- 5
    H1("5. Object-Oriented Design")
    P("Inference lives in two classes in <font face='Mono'>src/predictor.py</font>. "
      "<font face='Mono'>Predictor</font> loads everything once when the app starts and exposes one public "
      "method, <font face='Mono'>predict(request_dict)</font>. It hides where the model comes from:")
    bullets(["<b>Full mode:</b> loads the ensemble with joblib when the ML libraries are installed.",
             "<b>Lite mode:</b> if importing them raises <font face='Mono'>ImportError</font> (as on Vercel), it "
             "falls back to <font face='Mono'>LiteLGBM</font>, which evaluates the exported LightGBM trees with "
             "numpy alone. Its predictions match LightGBM exactly."])
    code("src/predictor.py", "LiteLGBM", 30, "Listing 5.1 - src/predictor.py: the LiteLGBM class walks each decision "
         "tree and accumulates path contributions for the explanation.")
    P("A user only gives a map location, so <font face='Mono'>location_features()</font> derives the rest. It "
      "computes vectorised haversine distances to every listing in the city, sorts them with "
      "<font face='Mono'>np.argsort</font>, and takes a distance-weighted average of the 25 nearest:")
    code("src/predictor.py", "location_features", 14, "Listing 5.2 - Deriving location features from the nearest "
         "real listings.")

    # ---------------------------------------------------------------- 6
    H1("6. Web Application with Flask")
    P("<font face='Mono'>app.py</font> creates the Flask app, builds one <font face='Mono'>Predictor</font> at "
      "start-up and defines six page routes plus a JSON API. Pages are Jinja2 templates that extend a shared "
      "<font face='Mono'>base.html</font>; a context processor injects the city list and model metrics into "
      "every page.")
    table([["Route", "Method", "Purpose"],
           ["/", "GET", "Market dashboard"], ["/explorer", "GET", "Map of every listing"],
           ["/predict", "GET", "Price predictor"], ["/route", "GET", "Route Planner (graph algorithms)"],
           ["/model", "GET", "Model performance"], ["/report", "GET", "Report rendered from Markdown"],
           ["/api/listings/&lt;city&gt;", "GET", "Listings of one city as compact JSON"],
           ["/api/predict", "POST", "Price prediction with explanation"],
           ["/api/route", "POST", "Shortest paths and TSP tours"], ["/api/health", "GET", "Status check"]],
          col_w=[4.4 * cm, 1.8 * cm, CONTENT_W - 6.2 * cm])
    code("app.py", "api_predict", 12, "Listing 6.1 - app.py: a JSON endpoint with input validation and error handling.")
    H2("6.1 Dashboard and map explorer", need=CONTENT_H * .45)
    img(SHOTS / "01_dashboard_top.png", "Screenshot 6.1 - Dashboard: KPI cards, Europe price map, median price by city.",
        max_h=CONTENT_H * .38)
    pair(["03_explorer_paris_points.png", "04_explorer_paris_heatmap.png"], ["Listings layer", "Price heatmap layer"],
         "Screenshot 6.2 - Map Explorer, Paris: every listing coloured by price, and the price heatmap.",
         CONTENT_H * .3)
    H2("6.2 Price predictor", need=CONTENT_H * .8)
    img(SHOTS / "09_predict_paris_full.png", "Screenshot 6.3 - Prediction for a central Paris apartment: price, "
        "interval, drivers, model agreement and comparable listings.", max_h=CONTENT_H * .78)
    P("The browser sends the form as JSON with <font face='Mono'>fetch()</font>. Flask passes it to "
      "<font face='Mono'>Predictor.predict()</font>, and <font face='Mono'>jsonify()</font> returns the "
      "result. The page then draws the drivers chart and the comparable listings on the Leaflet map.")
    H2("6.3 Route Planner and responsive design", need=CONTENT_H * .45)
    img(SHOTS / "20_route_map.png", "Screenshot 6.4 - Route Planner: stops chosen on the map, optimal tour and "
        "shortest path (the algorithms are covered in the DAA report).", max_h=CONTENT_H * .36)
    mob = [Image(str(SHOTS / f), width=CONTENT_W / 4.6, height=CONTENT_W / 4.6 * 844 / 390)
           for f in ["17_mobile_dashboard.png", "18_mobile_predict.png", "19_mobile_menu.png"]]
    t = Table([mob, [Paragraph(x, S["caption"]) for x in ["Dashboard", "Prediction result", "Navigation menu"]]])
    t.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER")]))
    story.append(KeepTogether([t, Paragraph("Screenshot 6.5 - Mobile views (390 × 844).", S["caption"])]))

    # ---------------------------------------------------------------- 7
    H1("7. Testing, Automation and Deployment")
    H2("7.1 Unit tests")
    P("<font face='Mono'>tests/test_algorithms.py</font> uses Python's built-in <font face='Mono'>unittest</font> "
      "framework: 11 tests in 4 <font face='Mono'>TestCase</font> classes, all passing. Each algorithm is "
      "checked against an independent reference implementation.")
    code("tests/test_algorithms.py", "test_hand_worked_example", 10, "Listing 7.1 - A unittest test case.")
    H2("7.2 Other checks")
    table([["Check", "How", "Result"],
           ["No listing in both train and test", "set intersection of listing ids", "0 overlap"],
           ["Feature leakage", "rebuild proximity_index with and without price", "none"],
           ["Lite model fidelity", "numpy evaluator vs LightGBM on 300 rows", "max difference 0.0"],
           ["Pages and API", "HTTP requests locally and on Vercel", "all HTTP 200"],
           ["UI interactions", "Playwright scripts (capture_screenshots.py)", "working"]],
          col_w=[4.6 * cm, 6.6 * cm, CONTENT_W - 11.2 * cm])
    P("The screenshots in this report are captured automatically. <font face='Mono'>capture_screenshots.py</font> "
      "drives a real Chrome browser with Playwright: it opens each page, clicks the layer buttons, fills the "
      "predictor form and saves the images, so they can be regenerated after any change.")
    H2("7.3 Deployment")
    P("The code is on GitHub and the app runs on Vercel's serverless Python runtime. "
      "<font face='Mono'>requirements.txt</font> lists only Flask, numpy, pandas and markdown, which keeps "
      "the bundle under Vercel's size limit. <font face='Mono'>requirements-ml.txt</font> has the full "
      "training stack. When the ML libraries are missing, <font face='Mono'>Predictor</font> switches to the "
      "numpy model automatically (Chapter 5).")

    # ---------------------------------------------------------------- 8
    H1("8. Python Concepts Used")
    table([["Concept", "Where it is used"],
           ["Functions, default arguments, return of tuples", "clean() returns (df, log); plan_routes(points, start=0, k=3)"],
           ["Nested functions and closures", "step() inside clean(); connect() inside build_graph()"],
           ["Lambdas", "loss function in ensemble_weights(); sort keys in tsp_nearest_neighbour()"],
           ["Classes, __init__, methods, state", "Predictor, LiteLGBM, ReportDoc (inherits BaseDocTemplate)"],
           ["Inheritance and method overriding", "ReportDoc overrides afterFlowable() for the table of contents"],
           ["Exceptions", "try/except ImportError (lite mode); ValueError/KeyError in API handlers"],
           ["Modules, packages, __name__ guard", "every src/*.py module; shared config.py"],
           ["Comprehensions and generators", "dict and list comprehensions throughout; any(...) negative-cycle check"],
           ["Standard library", "pathlib, json, heapq, itertools, math, time, random, subprocess, unittest"],
           ["File I/O", "CSV with pandas, JSON reports, joblib/npz models, PNG figures, PDF"],
           ["Data structures", "dicts as graphs, sets for visited nodes, heaps, bitmask integers"],
           ["Vectorisation", "pandas groupby/transform, NumPy haversine and argsort"],
           ["Decorators", "Flask @app.route and @app.context_processor"],
           ["Testing", "unittest.TestCase, assertAlmostEqual, randomised tests"]],
          col_w=[5.8 * cm, CONTENT_W - 5.8 * cm])

    # ---------------------------------------------------------------- 9
    H1("9. Conclusion")
    P("Altitude shows how far a single language can take a project, from raw CSV to a live web product. pandas "
      "handled the cleaning, matplotlib and seaborn the analysis, and scikit-learn with three gradient-boosting "
      "libraries the modelling. The result explains 85.7% of the variation in log price on unseen listings. "
      "Object-oriented design keeps the serving code clean and lets it run with or without the heavy libraries. "
      "Flask exposes it all through six pages and a JSON API, and unittest and Playwright check that it works.")
    H2("Limitations and future work")
    bullets(["Photos, floor area and amenities are not in the data and probably explain most of the remaining error.",
             "The data is one snapshot, with no seasonality.",
             "Possible next steps: type hints and mypy, pytest with coverage, Docker packaging, and a FastAPI version of the API."])
    H2("References")
    for r in ["Python Software Foundation. Python 3 documentation, https://docs.python.org/3/",
              "McKinney, W. (2022). <i>Python for Data Analysis</i>, 3rd ed. O'Reilly.",
              "Pedregosa, F. et al. (2011). Scikit-learn: Machine learning in Python. <i>JMLR</i>, 12, 2825-2830.",
              "Ke, G. et al. (2017). LightGBM: A highly efficient gradient boosting decision tree. <i>NeurIPS</i> 30.",
              "Lundberg, S. M. and Lee, S.-I. (2017). A unified approach to interpreting model predictions. <i>NeurIPS</i> 30.",
              "Gyódi, K. and Nawaro, Ł. (2021). Determinants of Airbnb prices in European cities. <i>Tourism Management</i>, 86.",
              "Flask documentation, https://flask.palletsprojects.com"]:
        story.append(Paragraph(r, S["bullet"], bulletText="•"))


if __name__ == "__main__":
    build()
    save("Altitude_Python_Report.pdf")
