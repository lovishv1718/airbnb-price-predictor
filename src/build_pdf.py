"""Build the full project report as a PDF (reports/PriceScope_Project_Report.pdf).

Inputs: models/*.json, reports/*.json, static/figures, reports/figures and
reports/screenshots (run capture_screenshots.py and report_figures.py first).
"""
import json
from datetime import date

import pandas as pd
from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (CondPageBreak, Image, KeepTogether, PageBreak, Paragraph, Preformatted, Spacer, Table,
                                TableStyle)
from reportlab.platypus.doctemplate import BaseDocTemplate, Frame, NextPageTemplate, PageTemplate
from reportlab.platypus.tableofcontents import TableOfContents

from config import FIG_DIR, MODELS_DIR, PROCESSED_CSV, REPORTS_DIR, ROOT, TARGET

FONTS = "C:/Windows/Fonts/"
pdfmetrics.registerFont(TTFont("Body", FONTS + "calibri.ttf"))
pdfmetrics.registerFont(TTFont("Body-Bold", FONTS + "calibrib.ttf"))
pdfmetrics.registerFont(TTFont("Body-Italic", FONTS + "calibrii.ttf"))
pdfmetrics.registerFont(TTFont("Mono", FONTS + "consola.ttf"))
pdfmetrics.registerFontFamily("Body", normal="Body", bold="Body-Bold", italic="Body-Italic", boldItalic="Body-Bold")

BRAND = colors.HexColor("#E31C5F")
INK = colors.HexColor("#111827")
GREY = colors.HexColor("#6B7280")
LINE = colors.HexColor("#E5E7EB")
SOFT = colors.HexColor("#F9FAFB")

W, H = A4
MARGIN = 2.1 * cm
CONTENT_W = W - 2 * MARGIN
CONTENT_H = H - 2 * MARGIN - 1.2 * cm

S = {
    "body": ParagraphStyle("body", fontName="Body", fontSize=11, leading=15.5, alignment=TA_JUSTIFY,
                           textColor=INK, spaceAfter=7),
    "h1": ParagraphStyle("h1", fontName="Body-Bold", fontSize=22, leading=27, textColor=BRAND, spaceBefore=14,
                         spaceAfter=12),
    "h2": ParagraphStyle("h2", fontName="Body-Bold", fontSize=15, leading=19, textColor=INK, spaceBefore=12,
                         spaceAfter=6),
    "h3": ParagraphStyle("h3", fontName="Body-Bold", fontSize=12.5, leading=16, textColor=INK, spaceBefore=8,
                         spaceAfter=4),
    "bullet": ParagraphStyle("bullet", fontName="Body", fontSize=11, leading=15, leftIndent=14, bulletIndent=3,
                             textColor=INK, spaceAfter=3, bulletFontName="Body"),
    "caption": ParagraphStyle("caption", fontName="Body-Italic", fontSize=9.5, leading=12, textColor=GREY,
                              alignment=TA_CENTER, spaceBefore=3, spaceAfter=10),
    "cell": ParagraphStyle("cell", fontName="Body", fontSize=9.5, leading=12, textColor=INK),
    "cellb": ParagraphStyle("cellb", fontName="Body-Bold", fontSize=9.5, leading=12, textColor=INK),
    "code": ParagraphStyle("code", fontName="Mono", fontSize=7.8, leading=9.8, textColor=INK, backColor=SOFT,
                           borderColor=LINE, borderWidth=.5, borderPadding=6, spaceBefore=4, spaceAfter=10),
    "callout": ParagraphStyle("callout", fontName="Body", fontSize=10.5, leading=14.5, textColor=INK,
                              backColor=colors.HexColor("#FFF1F3"), borderColor=colors.HexColor("#FECDD3"),
                              borderWidth=.6, borderPadding=8, spaceBefore=6, spaceAfter=12),
    "toc1": ParagraphStyle("toc1", fontName="Body", fontSize=12, leading=21, leftIndent=0),
    "toc2": ParagraphStyle("toc2", fontName="Body", fontSize=10.5, leading=14.5, leftIndent=16, textColor=GREY),
}


class ReportDoc(BaseDocTemplate):
    def __init__(self, path):
        super().__init__(path, pagesize=A4, leftMargin=MARGIN, rightMargin=MARGIN, topMargin=MARGIN,
                         bottomMargin=MARGIN, title="PriceScope: Airbnb Price Prediction - Project Report",
                         author="PriceScope project")
        frame = Frame(MARGIN, MARGIN, CONTENT_W, H - 2 * MARGIN, id="f")
        self.addPageTemplates([PageTemplate("cover", [frame], onPage=lambda c, d: None),
                               PageTemplate("normal", [frame], onPage=self.decorate)])

    def decorate(self, c, doc):
        c.saveState()
        c.setStrokeColor(LINE); c.setLineWidth(.6)
        c.line(MARGIN, H - MARGIN + 14, W - MARGIN, H - MARGIN + 14)
        c.line(MARGIN, MARGIN - 16, W - MARGIN, MARGIN - 16)
        c.setFont("Body", 8.5); c.setFillColor(GREY)
        c.drawString(MARGIN, H - MARGIN + 19, "PriceScope - Airbnb Price Prediction Across 10 European Cities")
        c.drawRightString(W - MARGIN, H - MARGIN + 19, "Project Report")
        c.drawString(MARGIN, MARGIN - 28, f"{date.today():%B %Y}")
        c.drawRightString(W - MARGIN, MARGIN - 28, f"Page {doc.page}")
        c.restoreState()

    def afterFlowable(self, f):
        if isinstance(f, Paragraph) and f.style.name in ("h1", "h2"):
            level = 0 if f.style.name == "h1" else 1
            key = f"h{id(f)}"
            self.canv.bookmarkPage(key)
            self.canv.addOutlineEntry(f.getPlainText(), key, level=level)
            if level == 0:
                self.notify("TOCEntry", (level, f.getPlainText(), self.page, key))


# ------------------------------------------------------------------ helpers
story = []
P = lambda t, s="body": story.append(Paragraph(t, S[s]))
H1 = lambda t: (story.append(CondPageBreak(CONTENT_H * .25)), story.append(Spacer(1, 6)),
               story.append(Paragraph(t, S["h1"])))
H2 = lambda t, need=5.5 * cm: (story.append(CondPageBreak(need)), P(t, "h2"))
H3 = lambda t: (story.append(CondPageBreak(4 * cm)), P(t, "h3"))


def bullets(items):
    for it in items:
        story.append(Paragraph(it, S["bullet"], bulletText="•"))
    story.append(Spacer(1, 4))


def img(path, caption=None, max_h=None, width=CONTENT_W):
    with PILImage.open(path) as im:
        w, h = im.size
    max_h = max_h or CONTENT_H * .34
    dw = width
    dh = dw * h / w
    if dh > max_h:
        dh, dw = max_h, max_h * w / h
    parts = [Image(str(path), width=dw, height=dh)]
    if caption:
        parts.append(Paragraph(caption, S["caption"]))
    story.append(KeepTogether(parts))


def table(rows, col_w=None, header=True, font=9.5, zebra=True):
    data = [[Paragraph(str(c), S["cellb" if (header and i == 0) else "cell"]) for c in r] for i, r in enumerate(rows)]
    t = Table(data, colWidths=col_w, repeatRows=1 if header else 0, hAlign="LEFT")
    st = [("GRID", (0, 0), (-1, -1), .4, LINE), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
          ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
          ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5)]
    if header:
        st.append(("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F3F4F6")))
    if zebra:
        for i in range(2, len(rows), 2):
            st.append(("BACKGROUND", (0, i), (-1, i), SOFT))
    t.setStyle(TableStyle(st))
    story.append(t)
    story.append(Spacer(1, 10))


eur = lambda v: f"€{v:,.0f}"
pct = lambda v: f"{v:.1f}%"


# ------------------------------------------------------------------ data
M = json.loads((MODELS_DIR / "metrics.json").read_text())
EDA = json.loads((MODELS_DIR / "eda.json").read_text())
LOG = json.loads((REPORTS_DIR / "cleaning_log.json").read_text())
ERR = json.loads((REPORTS_DIR / "error_analysis.json").read_text())
DF = pd.read_csv(PROCESSED_CSV)
BEST = M["results"][M["best_model"]]
SHOTS = REPORTS_DIR / "screenshots"
RFIG = REPORTS_DIR / "figures"
K = EDA["kpis"]


def build():
    # ---------------------------------------------------------------- cover
    story.append(Spacer(1, 3.2 * cm))
    story.append(Paragraph("PROJECT REPORT", ParagraphStyle("k", fontName="Body-Bold", fontSize=11, textColor=BRAND,
                                                            spaceAfter=10)))
    story.append(Paragraph("Airbnb Price Prediction Across 10 European Cities",
                           ParagraphStyle("t", fontName="Body-Bold", fontSize=32, leading=38, textColor=INK,
                                          spaceAfter=16)))
    story.append(Paragraph("Data cleaning, exploratory analysis, machine-learning modelling and deployment of "
                           "<b>PriceScope</b>, an interactive price-intelligence web application",
                           ParagraphStyle("st", fontName="Body", fontSize=14, leading=19, textColor=GREY,
                                          spaceAfter=28)))
    img(SHOTS / "01_dashboard_top.png", None, max_h=8.5 * cm)
    story.append(Spacer(1, 1 * cm))
    cover = [["Dataset", f"{LOG['raw_rows']:,} listings, 10 cities, 29 columns"],
             ["Best model", "Weighted ensemble of CatBoost, XGBoost and LightGBM"],
             ["Hold-out accuracy", f"R² {BEST['r2_log']:.3f} (log price), median error {pct(BEST['median_ape_pct'])}"],
             ["Live application", "https://airbnb-price-predictor-ivory.vercel.app"],
             ["Source code", "https://github.com/lovishv1718/airbnb-price-predictor"],
             ["Date", f"{date.today():%d %B %Y}"]]
    table(cover, col_w=[4 * cm, CONTENT_W - 4 * cm], header=False, zebra=False)
    story.append(NextPageTemplate("normal"))
    story.append(PageBreak())

    # ---------------------------------------------------------------- toc
    story.append(Paragraph("Table of Contents", ParagraphStyle("tochead", parent=S["h1"])))
    toc = TableOfContents()
    toc.levelStyles = [S["toc1"], S["toc2"]]
    story.append(toc)
    story.append(PageBreak())

    # ---------------------------------------------------------------- 1 summary
    story.append(Paragraph("1. Executive Summary", S["h1"]))
    P("This project builds a complete, reproducible machine-learning system that estimates the price of an "
      "Airbnb listing in ten European cities from its location, its characteristics, its host and reviews, "
      f"and the economic profile of its city. Starting from <b>{LOG['raw_rows']:,} listings</b> in Amsterdam, "
      "Athens, Barcelona, Berlin, Budapest, Lisbon, London, Paris, Rome and Vienna, the data was validated and "
      f"cleaned to <b>{LOG['clean_rows']:,} rows</b>, analysed, and used to train and compare six models. The "
      "best model is served through PriceScope, a public web application with interactive maps.")
    table([["Metric", "Value", "Meaning"],
           ["R² (log price)", f"{BEST['r2_log']:.3f}", "Share of variation in log price explained"],
           ["Median absolute error", pct(BEST["median_ape_pct"]), "Half of all predictions are closer than this"],
           ["Within ±30%", pct(BEST["within_30pct"]), "Share of predictions within 30% of the real price"],
           ["MAE", eur(BEST["mae_eur"]), f"Mean absolute error (median price is {eur(K['median_price'])})"],
           ["Baseline (city median)", f"R² {M['results']['City median (baseline)']['r2_log']:.3f}",
            "Quoting the city's median price"]],
          col_w=[4.2 * cm, 2.8 * cm, CONTENT_W - 7 * cm])
    P("All scores come from listings the model never saw. The split is grouped by listing, so the weekday and "
      "weekend copies of the same apartment are never on both sides. A naive random split would report "
      f"R² {M['random_split_reference']['r2_log']:.3f}, inflated by those duplicates.", "callout")
    bullets(["<b>Main finding:</b> location (centrality, attractions, restaurants, metro access) drives price "
             "most, followed by city, room type and capacity. Host reputation and reviews matter little.",
             "<b>Deliverables:</b> reproducible pipeline, six compared models, the PriceScope web app (dashboard, "
             "map explorer, price predictor, route planner, model page), public deployment on Vercel, and source "
             "code on GitHub.",
             "<b>Algorithms component:</b> a Route Planner that runs Dijkstra, Bellman-Ford and two Travelling "
             "Salesman algorithms (Held-Karp exact, nearest neighbour + 2-opt) over chosen listings, all written "
             "from scratch with tests and an empirical complexity analysis (Chapter 11)."])

    # ---------------------------------------------------------------- 2 intro
    H1("2. Introduction")
    P("Most Airbnb hosts are individuals without revenue-management tools, and they set prices by looking at a "
      "few nearby listings and guessing. A data-driven estimate gives hosts a starting point, helps guests judge "
      "whether a price is fair, and helps analysts see how tourism demand is spread across a city. European "
      "capitals make a demanding test, because the model must learn both <i>between-city</i> differences "
      "(Amsterdam versus Athens) and <i>within-city</i> differences (the historic centre versus the suburbs).")
    H2("2.1 Objectives")
    bullets(["Validate and clean the dataset, documenting every change.",
             "Explore how price varies with location, listing features and city economics.",
             "Train and compare regression models under a leakage-free evaluation protocol.",
             "Explain predictions globally and for each individual listing.",
             "Deliver the model in a professional, publicly deployed web application with maps."])
    H2("2.2 Related work")
    P("The dataset comes from Gyódi and Nawaro (2021), who found that distance to the centre and the attraction "
      "and restaurant indices are among the strongest determinants of price. Hedonic-pricing studies (Rosen, "
      "1974) model log price as a sum of characteristic effects, which explains why the log transform works "
      "well. Gradient-boosted trees (XGBoost, LightGBM, CatBoost) usually beat linear models on tabular pricing "
      "data because they capture non-linear effects and interactions, and SHAP values (Lundberg and Lee, 2017) "
      "are the standard way to explain them. A common pitfall in published Airbnb models is leakage through "
      "repeated listings. This project avoids it with grouped splits.")

    # ---------------------------------------------------------------- 3 data
    H1("3. Dataset")
    P(f"The input file has {LOG['raw_rows']:,} rows and {LOG['raw_cols']} columns. Each row is one listing on a "
      "weekday or a weekend. The target, <font face='Mono'>price_total</font>, is the total price in euros of a "
      "2-night stay for 2 people, as defined by the source dataset.")
    table([["Group", "Columns"],
           ["Target", "price_total"],
           ["Listing", "room_type, is_shared_room, is_private_room, max_guests, num_bedrooms"],
           ["Host and reviews", "is_superhost, is_multi_listing, is_business_listing, cleanliness_score (0-10), "
                                "guest_satisfaction_score (0-100)"],
           ["Location", "latitude, longitude (rounded to 0.01°), distance_city_center, distance_metro, "
                        "attraction_index_norm, restaurant_index_norm, proximity_index"],
           ["Administrative", "city, district, state, country_name"],
           ["City economics", "Crime_Index, Safety_Index, Monthly_Average_Net_salary, Taxi_price_per_Km, "
                              "Monthly_Basic_Utilities"],
           ["Time", "day_type (weekday or weekend)"]],
          col_w=[3.4 * cm, CONTENT_W - 3.4 * cm])
    cnt = DF.groupby("city").agg(n=(TARGET, "size"), med=(TARGET, "median"),
                                 sal=("Monthly_Average_Net_salary", "first"), saf=("Safety_Index", "first"))
    rows = [["City", "Country", "Listings", "Median price", "Net salary", "Safety index"]]
    for c, r in cnt.sort_values("n", ascending=False).iterrows():
        rows.append([c, DF.loc[DF.city == c, "country_name"].iloc[0], f"{int(r.n):,}", eur(r.med), eur(r.sal), f"{r.saf:.1f}"])
    table(rows)

    # ---------------------------------------------------------------- 4 cleaning
    H1("4. Data Cleaning and Validation")
    P("The file had no missing values, but a systematic validation (<font face='Mono'>src/clean.py</font>, "
      "logged to <font face='Mono'>reports/cleaning_log.json</font>) still found several problems.")
    rows = [["Step", "Removed", "Detail"]]
    for s in LOG["steps"]:
        rows.append([s["step"], s["removed"], s["note"] or "-"])
    table(rows, col_w=[4.6 * cm, 1.8 * cm, CONTENT_W - 6.4 * cm])
    bullets(["<b>Geocoding error:</b> 4,580 Rome listings were labelled <i>Holy See (Vatican City State)</i> and "
             "were relabelled <i>Italy</i>.",
             "<b>Outliers:</b> a per-city 3 × IQR fence on log price removed only 33 rows (0.06%), including a "
             "€43,955 entry error. Genuine luxury listings were kept.",
             "<b>proximity_index leakage check:</b> it is rebuilt from the four location columns with R² 0.9994, "
             "and adding price as an input does not improve the fit. It is a valid feature."])
    P(f"<b>Key finding:</b> {LOG['listings_in_both_day_types']:,} listings appear twice, once on a weekday and "
      "once on a weekend, at almost the same price. Each row was given a <font face='Mono'>listing_id</font>, "
      "and every train/test split is grouped by it.", "callout")

    # ---------------------------------------------------------------- 5 EDA
    H1("5. Exploratory Data Analysis")
    P(f"The cleaned data has a median price of {eur(K['median_price'])} and a mean of {eur(K['mean_price'])}. "
      f"{K['superhost_pct']}% of listings belong to Superhosts, and weekend stays carry a median premium of "
      f"+{K['weekend_premium_pct']}%.")
    img(FIG_DIR / "01_price_distribution.png", "Figure 5.1 - Raw and log-transformed price.", max_h=CONTENT_H * .26)
    P("Price is strongly right-skewed. On a log scale it is close to normal, so all models predict "
      "log(1 + price), and errors are measured in relative terms.")
    img(FIG_DIR / "03_city_roomtype.png", "Figure 5.2 - Median price by city and room type.", max_h=CONTENT_H * .3)
    c = EDA["cities"]
    P(f"Amsterdam ({eur(c[0]['median_price'])}) and Paris ({eur(c[1]['median_price'])}) are the most expensive "
      f"markets, and Athens ({eur(c[-1]['median_price'])}) the cheapest. An entire home costs roughly 1.5 to 2.5 "
      "times as much as a private room in the same city, and the gap varies by city. That is an interaction "
      "tree models capture naturally.")
    img(FIG_DIR / "05_location_effects.png", "Figure 5.3 - Log price against centre distance, attraction and restaurant indices.",
        max_h=CONTENT_H * .26)
    P("Price falls steeply within the first 1 to 2 km of the centre, then flattens, and it rises with the "
      "attraction and restaurant indices. Location is the strongest signal in the data.")
    img(FIG_DIR / "08_host_quality.png", "Figure 5.4 - Superhost versus regular host, and price by satisfaction band.",
        max_h=CONTENT_H * .26)
    P("Superhost status and satisfaction scores come with only small price differences. Guests pay mainly "
      "for location and space; reviews probably affect occupancy more than price.")

    # ---------------------------------------------------------------- 6 cities
    H1("6. City Comparison")
    rows = [["City", "Listings", "Median", "Weekend", "Entire home", "≤1 km vs >4 km", "Model R²", "Med. error"]]
    for cd in EDA["cities"]:
        d = DF[DF.city == cd["city"]]
        near = d[d.distance_city_center <= 1][TARGET].median()
        far = d[d.distance_city_center > 4][TARGET].median()
        pc = M["per_city"][cd["city"]]
        rows.append([cd["city"], f"{cd['listings']:,}", eur(cd["median_price"]),
                     f"{(cd['weekend_median'] / cd['weekday_median'] - 1) * 100:+.1f}%", pct(cd["entire_home_pct"]),
                     f"{near / far:.1f}×" if far == far else "-", f"{pc['r2_log']:.3f}", pct(pc["median_ape_pct"])])
    table(rows, font=9)
    P("The centre premium (median price within 1 km of the centre divided by the median beyond 4 km) shows how "
      "concentrated each market is. Model accuracy is highest in Lisbon, Vienna and Rome. Paris has the lowest "
      "R², because prices there vary widely even at similar locations, probably due to building quality and "
      "views, which the data does not record.")
    img(RFIG / "city_Paris.png", "Figure 6.1 - Paris: listing prices on the map and the centre premium by room type.",
        max_h=CONTENT_H * .27)

    # ---------------------------------------------------------------- 7 method
    H1("7. Feature Engineering and Methodology")
    H2("7.1 Features")
    P("The models use 25 features: the original listing, location and city columns plus six engineered ones. "
      "district, state and country_name were dropped as redundant with city and the coordinates.")
    table([["Engineered feature", "Formula", "Rationale"],
           ["is_weekend", "day_type == weekend", "Binary stay type"],
           ["guests_per_bedroom", "max_guests / max(bedrooms, 1)", "How crowded the unit is"],
           ["log_dist_center / metro", "log(1 + distance)", "Steep effect near the centre, flat further out"],
           ["attr_x_rest", "attraction × restaurant / 100", "High only when a location has both"],
           ["quality_score", "0.4 × cleanliness × 10 + 0.6 × satisfaction", "Combined review quality (0-100)"]],
          col_w=[4 * cm, 5.4 * cm, CONTENT_W - 9.4 * cm])
    P("Spatial neighbour price features (out-of-fold k-nearest-neighbour target encoding) were also tested. "
      "They did not improve hold-out accuracy and were removed.")
    H2("7.2 Evaluation protocol")
    bullets([f"<b>Target:</b> log(1 + price), converted back to euros for the euro metrics.",
             f"<b>Hold-out test set:</b> {M['split']['test_rows']:,} rows (20% of listings), grouped by listing_id "
             "and never used for tuning.",
             "<b>Validation:</b> a further grouped 15% of training listings, used for early stopping and "
             "ensemble weights.",
             f"<b>Production model:</b> refit on all {LOG['clean_rows']:,} rows with the tuned number of boosting rounds."])
    H2("7.3 Models")
    table([["Model", "Configuration"],
           ["City median", "Baseline: median training price of the listing's city"],
           ["Ridge regression", "One-hot encoding, standardised features, alpha 1.0"],
           ["Random Forest", "300 trees, max_features 0.5, min_samples_leaf 2"],
           ["LightGBM", f"63 leaves, lr 0.02, subsampling, {M['best_iterations']['LightGBM']} rounds (early stopping)"],
           ["XGBoost", f"depth 8, lr 0.02, native categoricals, {M['best_iterations']['XGBoost']} rounds"],
           ["CatBoost", f"depth 8, lr 0.04, native categoricals, {M['best_iterations']['CatBoost']} rounds"],
           ["Weighted ensemble", "Non-negative weights minimising validation MSE: " +
            ", ".join(f"{k} {v * 100:.0f}%" for k, v in M["weights"].items())]],
          col_w=[3.6 * cm, CONTENT_W - 3.6 * cm])

    # ---------------------------------------------------------------- 8 results
    H1("8. Results")
    rows = [["Model", "R² log", "R² €", "MAE €", "MAPE", "Med. APE", "±20%", "±30%"]]
    for n, r in M["results"].items():
        rows.append([("<b>%s</b>" % n) if n == M["best_model"] else n, f"{r['r2_log']:.4f}", f"{r['r2_eur']:.3f}",
                     f"{r['mae_eur']:.1f}", pct(r["mape_pct"]), pct(r["median_ape_pct"]),
                     pct(r["within_20pct"]), pct(r["within_30pct"])])
    table(rows, col_w=[4.4 * cm] + [(CONTENT_W - 4.4 * cm) / 7] * 7)
    img(RFIG / "model_compare.png", "Figure 8.1 - R² and median error for every model on the hold-out set.",
        max_h=CONTENT_H * .28)
    P("Every learned model is far better than the city-median baseline. Ridge already reaches R² 0.81 because "
      "many effects are close to linear on a log scale. The tree ensembles add about 4-5 points by capturing "
      "non-linear distance effects and interactions. The three boosting libraries score almost identically, "
      "which suggests the model is close to the limit of what these features can explain, and the ensemble is "
      "slightly better on every metric.")
    P("<b>Why is R² in euros lower (0.65)?</b> Squared euro error is dominated by a handful of very expensive "
      "listings. On the log scale, which reflects relative accuracy, the model explains 86% of the variation. "
      "The 17% median error is the best summary of a typical prediction.", "callout")
    img(FIG_DIR / "10_actual_vs_pred.png", "Figure 8.2 - Predicted against actual price, and the log residuals.",
        max_h=CONTENT_H * .3)

    # ---------------------------------------------------------------- 9 errors + explain
    H1("9. Error Analysis and Explainability")
    w = ERR["within"]
    img(RFIG / "err_cdf.png", "Figure 9.1 - Cumulative share of predictions by absolute % error (LightGBM, hold-out).",
        max_h=CONTENT_H * .25)
    P(f"{w['10']}% of predictions are within ±10% of the real price, {w['20']}% within ±20% and {w['30']}% "
      f"within ±30%. The model is most accurate in the middle of the price range. It slightly over-predicts the "
      "cheapest listings and under-predicts the most expensive ones, because the features that would justify an "
      "extreme price (interior, view, size) are not in the data. Entire homes are predicted best "
      f"({pct(ERR['by_room']['Entire home/apt'])} median error), then private rooms "
      f"({pct(ERR['by_room']['Private room'])}).")
    img(RFIG / "err_price_band.png", "Figure 9.2 - Error and bias by price quintile.", max_h=CONTENT_H * .25)
    img(FIG_DIR / "12_shap_summary.png", "Figure 9.3 - SHAP summary: impact of each feature on log price.",
        max_h=CONTENT_H * .4)
    imp = list(M["feature_importance"].items())
    P(f"The leading features, {imp[0][0]} and {imp[1][0]}, together account for "
      f"{(imp[0][1] + imp[1][1]) * 100:.0f}% of LightGBM's split gain, and both measure how central and lively a "
      "location is. High values push the price up strongly, as do entire homes and more guests and bedrooms. "
      "Long distances to the centre and the metro lower it. In the app, these contributions are grouped into "
      "nine readable price drivers for every prediction.")

    # ---------------------------------------------------------------- 10 app
    story.append(PageBreak())
    H1("10. The PriceScope Web Application")
    P("PriceScope is a Flask application with a responsive interface: a sidebar for navigation, card layouts, "
      "Plotly charts and Leaflet maps with OpenStreetMap tiles. It has six pages and a REST API. The Route Planner page is covered in Chapter 11.")
    H2("10.1 Market dashboard")
    img(SHOTS / "01_dashboard_top.png", "Screenshot 10.1 - Dashboard: KPI cards, Europe price map and median price by city.",
        max_h=CONTENT_H * .4)
    P("Six KPI cards summarise the market. A map of Europe shows one bubble per city, sized by listings and "
      "coloured by median price, and clicking a bubble opens that city in the explorer. Further down are charts "
      "of room-type premiums, the centre premium, the price distribution and capacity, and a city scorecard.")
    H2("10.2 Map explorer", need=CONTENT_H * .45)
    half = (CONTENT_W - .6 * cm) / 2

    def pair(files, captions, fig_caption, max_h):
        ims = []
        for f in files:
            with PILImage.open(SHOTS / f) as im:
                w, h = im.size
            sc = min(half / w, max_h / h)
            ims.append(Image(str(SHOTS / f), width=w * sc, height=h * sc))
        t = Table([ims, [Paragraph(x, S["caption"]) for x in captions]], colWidths=[half + .3 * cm] * 2)
        t.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER"), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
        story.append(KeepTogether([t, Paragraph(fig_caption, S["caption"])]))

    pair(["03_explorer_paris_points.png", "04_explorer_paris_heatmap.png"], ["Listings layer", "Price heatmap layer"],
         "Screenshot 10.2 - Map Explorer, Paris.", CONTENT_H * .3)
    P("Every listing in the chosen city is drawn on the map, coloured from blue (cheapest 20%) to red (most "
      "expensive 20%). The price heatmap highlights expensive districts, and a density layer shows where supply "
      "is concentrated. Filters for room type, day type, maximum price, guests and Superhost status update the "
      "map and the summary card instantly.")
    img(SHOTS / "06_explorer_london_filtered.png", "Screenshot 10.3 - London filtered to entire homes owned by Superhosts.",
        max_h=CONTENT_H * .38)
    H2("10.3 Price predictor", need=CONTENT_H * .8)
    img(SHOTS / "09_predict_paris_full.png", "Screenshot 10.4 - Full prediction for a central Paris apartment.",
        max_h=CONTENT_H * .78)
    P("The user picks a city, clicks or drags the pin to the listing's location and describes it. Metro "
      "distance and the attraction, restaurant and proximity indices are derived from the 25 nearest real "
      "listings. Distance to the centre is computed from a city centre estimated from the data. The result "
      "shows the 2-night and per-night price, an 80% prediction interval, comparisons with the city and "
      "neighbourhood medians, the price drivers, each model's prediction and nearby comparable listings.")
    pair(["10_predict_amsterdam_family.png", "11_predict_athens_private.png"],
         ["Amsterdam: 6-guest family home, weekend", "Athens: private room for 2"],
         "Screenshot 10.5 - Two contrasting prediction scenarios.", CONTENT_H * .6)
    H2("10.4 Model performance and mobile views", need=CONTENT_H * .45)
    img(SHOTS / "13_model_top.png", "Screenshot 10.6 - Model Performance page: KPIs, leaderboard and feature importance.",
        max_h=CONTENT_H * .38)
    mob = [Image(str(SHOTS / f), width=CONTENT_W / 4.6, height=CONTENT_W / 4.6 * 844 / 390)
           for f in ["17_mobile_dashboard.png", "18_mobile_predict.png", "19_mobile_menu.png"]]
    t = Table([mob, [Paragraph(x, S["caption"]) for x in ["Dashboard", "Prediction result", "Navigation menu"]]])
    t.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER")]))
    story.append(KeepTogether([t, Paragraph("Screenshot 10.7 - Mobile views (390 × 844).", S["caption"])]))

    # ---------------------------------------------------------------- 11 route planner (DAA)
    H1("11. Route Planner: Design and Analysis of Algorithms")
    P("The Route Planner turns the listings into a graph problem. A traveller picks the Airbnbs they want to "
      "visit; the app finds the shortest path between two of them and the shortest round trip that visits all "
      "of them. Every algorithm is implemented from scratch in plain Python in "
      "<font face='Mono'>src/algorithms.py</font>, using only <font face='Mono'>heapq</font> from the standard "
      "library, and served through <font face='Mono'>POST /api/route</font>.")
    H2("11.1 Problem formulation")
    bullets(["<b>Vertices V:</b> the n selected listings (2 to 20), one of them marked as the start.",
             "<b>Edges E:</b> each listing is joined to its k nearest listings (k = 1 to 6, default 3). The edge "
             "weight is the great-circle (haversine) distance in km. The graph is undirected, so |E| ≤ k·n.",
             "<b>Connectivity:</b> a k-nearest-neighbour graph can split into clusters. Depth-first search finds "
             "the components, and the closest pair of listings between components is joined until one remains.",
             "<b>Shortest path:</b> from the start to every listing, solved by Dijkstra and by Bellman-Ford.",
             "<b>Travelling Salesman (TSP):</b> a minimum-length closed tour from the start through every "
             "listing. It runs on the all-pairs shortest-path matrix, so each leg of the tour follows a real "
             "path in the graph."])
    H2("11.2 Algorithms and complexity")
    table([["Algorithm", "Technique", "Time", "Space"],
           ["k-NN graph + DFS", "sort neighbours, then join components", "O(V² log V)", "O(V + E)"],
           ["Dijkstra", "greedy, binary min-heap, lazy deletion", "O((V + E) log V)", "O(V + E)"],
           ["Bellman-Ford", "dynamic programming over edge relaxations", "O(V · E)", "O(V)"],
           ["All-pairs Dijkstra", "Dijkstra from every vertex", "O(V (V + E) log V)", "O(V²)"],
           ["Held-Karp TSP", "dynamic programming over subsets (bitmasks)", "O(n² · 2ⁿ)", "O(n · 2ⁿ)"],
           ["Nearest neighbour + 2-opt", "greedy construction + local search", "O(n²) per pass", "O(n)"],
           ["Brute-force TSP (tests only)", "try every permutation", "O(n!)", "O(n)"]],
          col_w=[4.2 * cm, 6.4 * cm, 3.3 * cm, CONTENT_W - 13.9 * cm])
    pseudo = [
        ("Dijkstra(G, s)",
         "dist[v] = INF for all v;  dist[s] = 0;  heap = [(0, s)]\n"
         "while heap not empty:\n"
         "    (d, u) = pop_min(heap)\n"
         "    if u settled: continue          # stale entry\n"
         "    settle u\n"
         "    for (v, w) in adj[u]:\n"
         "        if d + w < dist[v]:\n"
         "            dist[v] = d + w;  prev[v] = u;  push(heap, (dist[v], v))"),
        ("Bellman-Ford(G, s)",
         "dist[v] = INF for all v;  dist[s] = 0\n"
         "repeat V-1 times:\n"
         "    changed = false\n"
         "    for each directed edge (u, v, w):\n"
         "        if dist[u] + w < dist[v]: dist[v] = dist[u] + w;  prev[v] = u;  changed = true\n"
         "    if not changed: break           # early exit\n"
         "negative_cycle = any(dist[u] + w < dist[v] for (u, v, w))"),
        ("Held-Karp(D, start)",
         "C[{j}][j] = D[start][j]\n"
         "C[S + {k}][k] = min over j in S of  C[S][j] + D[j][k]     (k not in S, S + {k} = union)\n"
         "tour length = min over j of  C[all][j] + D[j][start]\n"
         "the tour is rebuilt from the stored parent of each state"),
        ("2-opt(tour, D)",
         "repeat until no improvement:\n"
         "    for every pair of edges (a,b), (c,d) in the tour:\n"
         "        if D[a][c] + D[b][d] < D[a][b] + D[c][d]:\n"
         "            reverse the segment b..c       # removes a crossing"),
    ]
    for title, code in pseudo:
        story.append(KeepTogether([Paragraph(title, S["h3"]), Preformatted(code, S["code"])]))
    P("Dijkstra is correct only for non-negative weights, which holds for distances. Bellman-Ford is slower "
      "but also handles negative weights and reports negative cycles; it is included to compare the two "
      "approaches and as an independent check, since both must return identical distances. The TSP is NP-hard: "
      f"Held-Karp gives the guaranteed optimum but needs exponential time, so the app uses it up to "
      f"{12} stops. Nearest neighbour + 2-opt is polynomial and very fast, but it can get stuck in a local "
      "optimum.")

    H2("11.3 Worked example: nine Paris landmarks")
    RX = json.loads((REPORTS_DIR / "route_example.json").read_text(encoding="utf-8"))
    P("The example uses the Paris listing closest to each of nine landmarks, starts at the Eiffel Tower and "
      f"finds the shortest path to Bastille. With k = {RX['k']}, the graph has {RX['n']} vertices and "
      f"{RX['graph']['num_edges']} edges.")
    img(SHOTS / "20_route_map.png", "Screenshot 11.1 - Route Planner: exact TSP tour (red), Dijkstra path to "
        "Bastille (blue) and numbered stops.", max_h=CONTENT_H * .42)
    names = RX["landmarks"]
    rows = [["Stop", "Near", "Price", "Dijkstra km", "Bellman-Ford km", "Shortest path"]]
    parent = {v: p for p, v in RX["dijkstra"]["tree"]}
    for i, nm in enumerate(names):
        path, v = [i], i
        while v in parent:
            v = parent[v]; path.insert(0, v)
        rows.append([i + 1, nm, eur(RX["prices"][i]), f"{RX['dijkstra']['all_distances'][i]:.3f}",
                     f"{RX['bellman_ford']['all_distances'][i]:.3f}", " → ".join(str(p + 1) for p in path)])
    table(rows, font=9)
    d, b, x, h = RX["dijkstra"], RX["bellman_ford"], RX["tsp_exact"], RX["tsp_heuristic"]
    table([["Algorithm", "Result", "Route", "Work done"],
           ["Dijkstra", f"{d['distance']:.2f} km to stop {RX['target'] + 1}", " → ".join(str(p + 1) for p in d["path"]),
            f"{d['relaxations']} relaxations, {d['heap_pushes']} heap pushes"],
           ["Bellman-Ford", f"{b['distance']:.2f} km to stop {RX['target'] + 1}", " → ".join(str(p + 1) for p in b["path"]),
            f"{b['passes']} of {b['max_passes']} passes, {b['relaxations']} relaxations, no negative cycle"],
           ["Held-Karp", f"{x['km']:.2f} km round trip", " → ".join(str(p + 1) for p in x["tour"]),
            f"{x['subsets']} subsets, {x['states']:,} DP transitions"],
           ["NN + 2-opt", f"{h['km']:.2f} km round trip", " → ".join(str(p + 1) for p in h["tour"]),
            f"greedy {h['greedy_km']:.2f} km, then {h['two_opt_swaps']} 2-opt swap(s)"]],
          col_w=[2.6 * cm, 3.4 * cm, 5.4 * cm, CONTENT_W - 11.4 * cm], font=9)
    P(f"Both shortest-path algorithms return identical distances to every stop. The shortest route from the "
      f"Eiffel Tower to Bastille goes through the Louvre listing ({d['distance']:.2f} km), because the two have no "
      f"direct edge. Bellman-Ford needed only {b['passes']} of its {b['max_passes']} allowed passes. The optimal "
      f"round trip is {x['km']:.2f} km and follows the landmarks in a ring. The greedy tour alone was "
      f"{h['greedy_km']:.2f} km ({(h['greedy_km'] / x['km'] - 1) * 100:.0f}% longer); one 2-opt swap removed its "
      "crossing and reached the optimum.")
    img(SHOTS / "22_route_algorithms.png", "Screenshot 11.2 - Result cards for the four algorithms, with complexity, "
        "operation counts and run times.", max_h=CONTENT_H * .4)

    H2("11.4 Empirical analysis", need=CONTENT_H * .4)
    BM = json.loads((REPORTS_DIR / "algo_benchmark.json").read_text())
    sp, ts = BM["shortest_path"], BM["tsp"]
    img(RFIG / "algo_benchmark.png", "Figure 11.1 - Measured run times (log scale) and the 2-opt optimality gap on "
        "random Paris-sized instances.", max_h=CONTENT_H * .28)
    rows = [["Stops V", "Edges E", "Dijkstra ms", "Bellman-Ford ms", "Ratio"]]
    for i, n in enumerate(sp["n"]):
        rows.append([n, sp["edges"][i], f"{sp['dijkstra'][i]:.3f}", f"{sp['bellman_ford'][i]:.3f}",
                     f"{sp['bellman_ford'][i] / sp['dijkstra'][i]:.1f}×"])
    table(rows, font=9)
    growth = [ts["held_karp"][i + 1] / ts["held_karp"][i] for i in range(len(ts["n"]) - 1) if ts["n"][i] >= 8]
    P(f"<b>Shortest paths.</b> Dijkstra grows roughly linearly here, because E ≈ 2V in a k = 3 graph. "
      f"Bellman-Ford is {sp['bellman_ford'][-1] / sp['dijkstra'][-1]:.0f}× slower at {sp['n'][-1]} stops. Thanks "
      "to the early exit it needs far fewer than V − 1 passes on these geometric graphs, so it stays well below "
      "its O(V·E) worst case, but it still re-scans every edge on each pass.")
    rows = [["Stops n"] + [str(n) for n in ts["n"]],
            ["Held-Karp ms"] + [f"{v:.2f}" for v in ts["held_karp"]],
            ["NN + 2-opt ms"] + [f"{v:.2f}" for v in ts["heuristic"]],
            ["Mean gap %"] + [f"{v:.2f}" for v in ts["gap_mean"]],
            ["Optimal in %"] + [f"{v:.0f}" for v in ts["optimal_pct"]]]
    table(rows, font=8.5)
    P(f"<b>Travelling Salesman.</b> Held-Karp's time multiplies by about {sum(growth) / len(growth):.1f}× for each "
      f"extra stop, close to the factor of about 2 predicted by O(n² · 2ⁿ), and reaches "
      f"{ts['held_karp'][-1]:.0f} ms at {ts['n'][-1]} stops. At that rate, 20 stops would take minutes, which is "
      f"why the app switches to the heuristic above 12. Nearest neighbour + 2-opt stays below 0.1 ms. Across 25 "
      "random instances per size, it found the exact optimum 68-100% of the time, with a mean gap below 2%. "
      f"Its worst case was {max(ts['gap_max']):.0f}% longer than optimal, which shows why an exact method is "
      "still worth having when it is affordable.")
    H2("11.5 Correctness testing")
    P("<font face='Mono'>tests/test_algorithms.py</font> has 11 unit tests, all passing "
      "(<font face='Mono'>python -m unittest discover tests</font>):")
    bullets(["Dijkstra and Bellman-Ford match an independent Floyd-Warshall implementation on 30 random graphs, "
             "from every source.",
             "A hand-worked 4-node example where the shortest path (A-C-B-D, length 4) is not the direct edge.",
             "Bellman-Ford handles negative edges correctly and detects a negative cycle.",
             "Held-Karp equals the O(n!) brute-force optimum for 3 to 8 stops.",
             "2-opt never beats the exact optimum, and every tour visits each stop exactly once.",
             "Expanded tours use only real graph edges; the generated graphs are connected and symmetric.",
             "The API rejects fewer than 2 or more than 20 stops, out-of-range indices and malformed input."])

    # ---------------------------------------------------------------- 12 architecture
    H1("12. Architecture, API and Deployment")
    story.append(Preformatted(
        "Cleaned_data.csv\n"
        "  -> src/clean.py        dedupe, fix labels, checks, outlier fence, listing_id\n"
        "  -> src/eda.py          figures + dashboard data\n"
        "  -> src/train.py        grouped split, 5 models + ensemble, metrics, SHAP\n"
        "  -> src/export_lite.py  LightGBM -> numpy arrays, city centres\n"
        "  -> app.py + src/predictor.py   PriceScope (local: ensemble | Vercel: lite LightGBM)", S["code"]))
    table([["Endpoint", "Description"],
           ["GET /api/health", "Service status, serving model and its R²"],
           ["GET /api/listings/&lt;city&gt;", "All listings of a city in compact form (used by the map)"],
           ["POST /api/predict", "Price, interval, drivers, location profile and comparables. Needs city, "
                                 "latitude and longitude; other fields have defaults"],
           ["POST /api/route", "Graph, Dijkstra, Bellman-Ford, Held-Karp and 2-opt results for 2-20 points "
                               "(Chapter 11)"]],
          col_w=[4.4 * cm, CONTENT_W - 4.4 * cm])
    P("<b>Deployment.</b> The source code is on GitHub (lovishv1718/airbnb-price-predictor) and the app runs on "
      "Vercel at <b>https://airbnb-price-predictor-ivory.vercel.app</b>. XGBoost, CatBoost and SHAP together "
      "exceed Vercel's bundle limit of about 250 MB, so the public site serves the trained LightGBM model "
      "exported to numpy arrays (R² 0.854 against 0.857 for the ensemble). Its predictions matched LightGBM "
      "exactly on 300 test listings, at about 10 ms each. Locally, the app serves the full ensemble.")
    table([["Test", "Result"],
           ["No listing in both train and test", "Passed (0 overlap)"],
           ["proximity_index leakage", "None (R² 0.9994 with or without price)"],
           ["Lite model against LightGBM", "Maximum difference 0.0"],
           ["All pages and API, locally and on Vercel", "HTTP 200, no console errors"],
           ["Map, filter and prediction interactions (Playwright)", "Working (screenshots in Chapter 10)"],
           ["Mobile layout (390 px)", "Stacks correctly, menu works"],
           ["Route Planner algorithms (11 unit tests)", "All pass (Section 11.5)"]],
          col_w=[8 * cm, CONTENT_W - 8 * cm])

    # ---------------------------------------------------------------- 13 limits + conclusion
    H1("13. Limitations and Future Work")
    bullets(["<b>Missing price drivers:</b> photos, floor area, amenities, interior and views are not in the data "
             "and probably explain most of the remaining 14% of variance.",
             "<b>Coarse coordinates:</b> latitude and longitude are rounded to about 1 km, so fine location detail "
             "comes from the distance and index columns.",
             "<b>Snapshot data:</b> there is no seasonality or booking calendar, so prices should be re-validated "
             "before live use.",
             "<b>Straight-line routes:</b> the Route Planner uses great-circle distances between listings, not "
             "street-network distances. Real walking or driving distances would need a road graph such as "
             "OpenStreetMap's.",
             "<b>Future work:</b> street-network routing for the Route Planner, text and photo features, quantile models for listing-specific intervals, Optuna "
             "tuning with grouped cross-validation, data from several snapshots over time, an occupancy model for "
             "revenue-optimal pricing, and ONNX export of the full ensemble."])
    H1("14. Conclusion")
    P("The project delivered an end-to-end system for Airbnb price prediction across ten European cities. "
      "Validating the supposedly clean data found duplicates, a geocoding error affecting 4,580 Rome listings, "
      f"extreme price errors and {LOG['listings_in_both_day_types']:,} listings duplicated across weekday and "
      "weekend rows. That last "
      "finding shaped an evaluation protocol that measures performance on genuinely new listings.")
    P(f"Location turned out to be the decisive factor in price. A weighted ensemble of CatBoost, XGBoost and "
      f"LightGBM explains {BEST['r2_log'] * 100:.1f}% of the variation in log price on unseen listings, with a "
      f"typical error of {pct(BEST['median_ape_pct'])}. PriceScope makes this usable: drop a pin, describe the "
      "listing, and get a price with an uncertainty range, an explanation and real comparable listings. The "
      "Route Planner adds a Design and Analysis of Algorithms component: Dijkstra, Bellman-Ford, Held-Karp and "
      "2-opt, implemented from scratch, verified by unit tests and compared empirically against their "
      "theoretical complexity. The system is publicly deployed and fully reproducible from the GitHub "
      "repository.")
    H2("References")
    for r in [
        "Gyódi, K. and Nawaro, Ł. (2021). Determinants of Airbnb prices in European cities: A spatial "
        "econometrics approach. <i>Tourism Management</i>, 86, 104319.",
        "Lundberg, S. M. and Lee, S.-I. (2017). A unified approach to interpreting model predictions. <i>NeurIPS</i> 30.",
        "Ke, G. et al. (2017). LightGBM: A highly efficient gradient boosting decision tree. <i>NeurIPS</i> 30.",
        "Chen, T. and Guestrin, C. (2016). XGBoost: A scalable tree boosting system. <i>KDD '16</i>, 785-794.",
        "Prokhorenkova, L. et al. (2018). CatBoost: unbiased boosting with categorical features. <i>NeurIPS</i> 31.",
        "Rosen, S. (1974). Hedonic prices and implicit markets. <i>Journal of Political Economy</i>, 82(1), 34-55.",
        "Dijkstra, E. W. (1959). A note on two problems in connexion with graphs. <i>Numerische Mathematik</i>, 1, 269-271.",
        "Bellman, R. (1958). On a routing problem. <i>Quarterly of Applied Mathematics</i>, 16(1), 87-90.",
        "Held, M. and Karp, R. M. (1962). A dynamic programming approach to sequencing problems. <i>Journal of "
        "the SIAM</i>, 10(1), 196-210.",
        "Croes, G. A. (1958). A method for solving traveling-salesman problems. <i>Operations Research</i>, 6(6), 791-812.",
        "Cormen, T. H., Leiserson, C. E., Rivest, R. L. and Stein, C. (2022). <i>Introduction to Algorithms</i>, "
        "4th ed. MIT Press.",
    ]:
        story.append(Paragraph(r, S["bullet"], bulletText="•"))


def main():
    build()
    out = REPORTS_DIR / "PriceScope_Project_Report.pdf"
    doc = ReportDoc(str(out))
    doc.multiBuild(story)
    print("Saved", out, "pages:", doc.page)


if __name__ == "__main__":
    main()
