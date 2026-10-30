"""Shared layout, styles and helpers for the Altitude PDF reports.

report_python.py and report_daa.py import this module and append flowables to
`story`. Inputs: models/*.json, reports/*.json, static/figures, reports/figures
and reports/screenshots (run capture_screenshots.py and report_figures.py first).
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


DOC = {"title": "Altitude", "header": "Altitude", "subject": "Project Report"}


class ReportDoc(BaseDocTemplate):
    def __init__(self, path):
        super().__init__(path, pagesize=A4, leftMargin=MARGIN, rightMargin=MARGIN, topMargin=MARGIN,
                         bottomMargin=MARGIN, title=DOC["title"], author="Altitude project")
        frame = Frame(MARGIN, MARGIN, CONTENT_W, H - 2 * MARGIN, id="f")
        self.addPageTemplates([PageTemplate("cover", [frame], onPage=lambda c, d: None),
                               PageTemplate("normal", [frame], onPage=self.decorate)])

    def decorate(self, c, doc):
        c.saveState()
        c.setStrokeColor(LINE); c.setLineWidth(.6)
        c.line(MARGIN, H - MARGIN + 14, W - MARGIN, H - MARGIN + 14)
        c.line(MARGIN, MARGIN - 16, W - MARGIN, MARGIN - 16)
        c.setFont("Body", 8.5); c.setFillColor(GREY)
        c.drawString(MARGIN, H - MARGIN + 19, DOC["header"])
        c.drawRightString(W - MARGIN, H - MARGIN + 19, DOC["subject"])
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




def pair(files, captions, fig_caption, max_h):
    """Two screenshots side by side with their own captions."""
    half = (CONTENT_W - .6 * cm) / 2
    ims = []
    for f in files:
        with PILImage.open(SHOTS / f) as im:
            w, h = im.size
        sc = min(half / w, max_h / h)
        ims.append(Image(str(SHOTS / f), width=w * sc, height=h * sc))
    t = Table([ims, [Paragraph(x, S["caption"]) for x in captions]], colWidths=[half + .3 * cm] * 2)
    t.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER"), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.append(KeepTogether([t, Paragraph(fig_caption, S["caption"])]))


def code(path, name, max_lines=40, caption=None):
    """Excerpt of a function or class from the project source, ending at the next top-level definition."""
    lines = (ROOT / path).read_text(encoding="utf-8").splitlines()
    i = next(k for k, ln in enumerate(lines) if ln.lstrip().startswith((f"def {name}(", f"class {name}")))
    indent = len(lines[i]) - len(lines[i].lstrip())
    j = i + 1
    while j < len(lines) and (not lines[j].strip() or len(lines[j]) - len(lines[j].lstrip()) > indent):
        j += 1
    block = [ln[indent:] for ln in lines[i:j]]
    while block and not block[-1].strip():
        block.pop()
    if len(block) > max_lines:
        block = block[:max_lines] + ["    ..."]
    parts = [Preformatted("\n".join(block), S["code"])]
    if caption:
        parts.append(Paragraph(caption, S["caption"]))
    story.append(KeepTogether(parts) if len(block) < 45 else parts[0])


def cover(kicker, title, subtitle, rows, shot="01_dashboard_top.png"):
    story.append(Spacer(1, 3 * cm))
    story.append(Paragraph(kicker, ParagraphStyle("k", fontName="Body-Bold", fontSize=11, textColor=BRAND,
                                                  spaceAfter=10)))
    story.append(Paragraph(title, ParagraphStyle("t", fontName="Body-Bold", fontSize=30, leading=36, textColor=INK,
                                                 spaceAfter=14)))
    story.append(Paragraph(subtitle, ParagraphStyle("st", fontName="Body", fontSize=13.5, leading=18,
                                                    textColor=GREY, spaceAfter=24)))
    img(SHOTS / shot, None, max_h=8.5 * cm)
    story.append(Spacer(1, .8 * cm))
    table(rows + [["Live application", "https://airbnb-price-predictor-ivory.vercel.app"],
                  ["Source code", "https://github.com/lovishv1718/airbnb-price-predictor"],
                  ["Date", f"{date.today():%d %B %Y}"]],
          col_w=[4 * cm, CONTENT_W - 4 * cm], header=False, zebra=False)
    story.append(NextPageTemplate("normal"))
    story.append(PageBreak())
    story.append(Paragraph("Table of Contents", ParagraphStyle("tochead", parent=S["h1"])))
    toc = TableOfContents()
    toc.levelStyles = [S["toc1"], S["toc2"]]
    story.append(toc)
    story.append(PageBreak())


def chapter(t):
    """First chapter after the table of contents starts at the top of its page."""
    story.append(Paragraph(t, S["h1"]))


def save(filename):
    out = REPORTS_DIR / filename
    doc = ReportDoc(str(out))
    doc.multiBuild(story)
    print("Saved", out, "pages:", doc.page)
