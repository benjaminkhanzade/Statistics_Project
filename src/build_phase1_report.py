#!/usr/bin/env python3
"""Build the English Phase 1 PDF from the reproducible analysis outputs."""
import json
import math
import re
import shutil
from pathlib import Path
import xml.etree.ElementTree as ET

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Flowable, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "phase1"
RESULT = OUT / "phase1_results.json"
PDF = OUT / "report_phase1.pdf"
data = json.loads(RESULT.read_text(encoding="utf-8"))
stats = data["summary_statistics"]
link = data["linkage"]

ACC = colors.HexColor("#176B87")
INK = colors.HexColor("#1F2937")
MUTED = colors.HexColor("#64748B")
PALE = colors.HexColor("#EEF5F8")
GRID = colors.HexColor("#DCE5EB")
title = ParagraphStyle("title", fontName="Helvetica-Bold", fontSize=22, leading=28, textColor=INK, spaceAfter=8)
subtitle = ParagraphStyle("subtitle", fontName="Helvetica", fontSize=11, leading=16, textColor=MUTED, spaceAfter=8)
h1 = ParagraphStyle("h1", fontName="Helvetica-Bold", fontSize=14, leading=19, textColor=ACC, spaceBefore=8, spaceAfter=5)
body = ParagraphStyle("body", fontName="Helvetica", fontSize=9, leading=14, textColor=INK, spaceAfter=6)
small = ParagraphStyle("small", fontName="Helvetica", fontSize=8, leading=12, textColor=MUTED)


def fmt(value, digits=2):
    if value is None:
        return "—"
    if isinstance(value, (int, float)) and float(value).is_integer():
        return f"{int(value):,}"
    return f"{value:,.{digits}f}"


def table(headers, rows, widths):
    t = Table([headers, *rows], colWidths=widths, repeatRows=1, hAlign="LEFT")
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), ACC), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 7.8), ("LEADING", (0, 0), (-1, -1), 11),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("GRID", (0, 0), (-1, -1), .35, GRID), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PALE]),
    ]))
    return t


def footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(GRID)
    canvas.line(20 * mm, 13 * mm, A4[0] - 20 * mm, 13 * mm)
    canvas.setFillColor(MUTED)
    canvas.setFont("Helvetica", 8)
    canvas.drawString(20 * mm, 8 * mm, "Phase 1 descriptive report | NACC UDS + MRI")
    canvas.drawRightString(A4[0] - 20 * mm, 8 * mm, str(doc.page))
    canvas.restoreState()


class SVGFigure(Flowable):
    """Draw the project's primitive-only SVG charts as scalable PDF vectors."""
    def __init__(self, path, max_width=170 * mm, max_height=125 * mm):
        super().__init__()
        self.path = Path(path)
        self.root = ET.parse(self.path).getroot()
        self.vb = [float(x) for x in self.root.attrib.get("viewBox", "0 0 900 520").split()]
        self.scale = min(max_width / self.vb[2], max_height / self.vb[3])
        self.width, self.height = self.vb[2] * self.scale, self.vb[3] * self.scale

    def wrap(self, available_width, available_height):
        return min(self.width, available_width), self.height

    @staticmethod
    def color(value, default=None):
        if not value or value == "none":
            return default
        if value.startswith("#") and len(value) == 7:
            return colors.HexColor(value)
        named = {"white": colors.white, "black": colors.black}
        return named.get(value, default)

    def draw(self):
        c = self.canv
        c.saveState()
        c.translate(0, self.height)
        c.scale(self.scale, -self.scale)
        c.setFillColor(colors.white)
        c.rect(0, 0, self.vb[2], self.vb[3], stroke=0, fill=1)
        for el in self.root:
            tag = el.tag.rsplit("}", 1)[-1]
            a = el.attrib
            if tag == "rect":
                x, y = float(a.get("x", 0)), float(a.get("y", 0))
                try:
                    w, h = float(a["width"]), float(a["height"])
                except (KeyError, ValueError):
                    continue
                fill = self.color(a.get("fill"))
                stroke = self.color(a.get("stroke"))
                if fill: c.setFillColor(fill)
                if stroke: c.setStrokeColor(stroke)
                c.setLineWidth(float(a.get("stroke-width", 1)))
                c.rect(x, y, w, h, stroke=int(stroke is not None), fill=int(fill is not None))
            elif tag == "line":
                stroke = self.color(a.get("stroke"), colors.black)
                c.setStrokeColor(stroke)
                c.setLineWidth(float(a.get("stroke-width", 1)))
                c.line(float(a["x1"]), float(a["y1"]), float(a["x2"]), float(a["y2"]))
            elif tag == "circle":
                fill = self.color(a.get("fill"))
                stroke = self.color(a.get("stroke"))
                if fill: c.setFillColor(fill)
                if stroke: c.setStrokeColor(stroke)
                if a.get("fill-opacity") and hasattr(c, "setFillAlpha"):
                    c.setFillAlpha(float(a["fill-opacity"]))
                c.circle(float(a["cx"]), float(a["cy"]), float(a["r"]),
                         stroke=int(stroke is not None), fill=int(fill is not None))
                if hasattr(c, "setFillAlpha"): c.setFillAlpha(1)
            elif tag == "text":
                txt = el.text or ""
                if not txt.strip(): continue
                x, y = float(a.get("x", 0)), float(a.get("y", 0))
                transform = a.get("transform", "")
                tr = re.search(r"translate\(([\d.+-]+)[, ]+([\d.+-]+)\)", transform)
                rot = re.search(r"rotate\(([\d.+-]+)", transform)
                if tr:
                    x, y = float(tr.group(1)), float(tr.group(2))
                c.saveState()
                c.translate(x, y)
                if rot:
                    c.rotate(-float(rot.group(1)))
                c.scale(1, -1)
                fill = self.color(a.get("fill"), INK)
                c.setFillColor(fill)
                size = float(a.get("font-size", 12))
                bold = a.get("font-weight", "") in ("700", "bold")
                c.setFont("Helvetica-Bold" if bold else "Helvetica", size)
                anchor = a.get("text-anchor", "start")
                if anchor == "middle": c.drawCentredString(0, 0, txt)
                elif anchor == "end": c.drawRightString(0, 0, txt)
                else: c.drawString(0, 0, txt)
                c.restoreState()
        c.restoreState()


story = [
    Spacer(1, 10 * mm),
    Paragraph("Phase 1: MoCA and Entorhinal MRI Measures", title),
    Paragraph("NACC UDS + structural MRI | Analytic sample: age 65 and older", subtitle),
    Paragraph("Statistical question", h1),
    Paragraph("Among adults aged 65 or older, what descriptive linear relationships are observed between MoCA score (MOCATOTS) and entorhinal cortical volume and thickness? Age (NACCAGE) and years of education (EDUC) are planned adjustment variables for the later modeling phase.", body),
    table(["Sample step", "Participants / records"], [
        ["UDS rows / unique participants", f"{link['UDS_rows']:,} / {link['unique_UDS_NACCID']:,}"],
        ["MRI rows / unique participants", f"{link['MRI_rows']:,} / {link['unique_MRI_NACCID']:,}"],
        ["IDs linked across both files", f"{link['common_participants']:,}"],
        ["Age 65+ analytic sample", f"{link['analytic_participants_age_65_plus']:,}"],
        ["Complete cases across core variables", f"{link['participants_with_both_MRI_and_UDS_valid_main_variables']:,}"],
    ], [105 * mm, 58 * mm]),
    Paragraph("Unit of analysis and selection rule", h1),
    Paragraph("The unit is one participant identified by NACCID. Each supplied file contains one row per ID, with no duplicate IDs; that available row is retained. Participants are then restricted to NACCAGE ≥ 65. Visit identifiers/dates and MRI scan dates are absent, so the record cannot be verified as a true baseline and the timing of UDS and MRI cannot be established.", body),
    Paragraph("Descriptive statistics", h1),
]

keys = [
    ("NACCAGE", "Age (years)"),
    ("EDUC_years", "Education (years)"),
    ("MOCATOTS_valid_0_30", "MOCATOTS"),
    ("ENTORHINAL_BILATERAL_GVOL_mm3", "Bilateral volume (mm³)"),
    ("ENTORHINAL_BILATERAL_AVGTH_mm", "Bilateral thickness (mm)"),
]
desc = [[label, fmt(stats[key]["n"], 0), fmt(stats[key]["mean"]), fmt(stats[key]["median"]),
         fmt(stats[key]["sd"]), fmt(stats[key]["iqr"]), fmt(stats[key]["skewness"])]
        for key, label in keys]
story += [table(["Variable", "n", "Mean", "Median", "SD", "IQR", "Skewness"], desc,
                [47 * mm, 14 * mm, 23 * mm, 22 * mm, 20 * mm, 19 * mm, 18 * mm]), Spacer(1, 4 * mm),
          Paragraph("MOCATOTS is concentrated toward the upper end of its valid range, reflected by negative skewness. EDUC=99 is treated as unknown, and out-of-range MOCATOTS values are invalid. Nonpositive entorhinal volumes are not accepted as valid measurements. The UDS filename indicates imputed/processed data, but its method and original missingness mask were not supplied.", body),
          PageBreak(), Paragraph("Missingness and data quality", h1)]
miss = [[r["variable"], fmt(r["n_valid"], 0), fmt(r["n_unavailable"], 0), f"{r['percent_unavailable']:.2f}%"]
        for r in data["missingness"]]
story += [table(["Variable", "Valid n", "Missing/invalid n", "Percent"], miss,
                [72 * mm, 28 * mm, 38 * mm, 25 * mm]),
          Paragraph("Phase 1 figures", h1),
          table(["Figure", "File"], [
              ["MOCATOTS distribution", "figures/phase1/02_moca_distribution.svg"],
              ["MoCA vs. bilateral entorhinal volume with linear trend", "figures/phase1/08_moca_entorhinal_volume_scatter.svg"],
              ["MoCA boxplot by cognitive status", "figures/phase1/06_moca_by_status.svg"],
              ["Pearson correlation heatmap", "figures/phase1/10_correlation_heatmap.svg"],
          ], [88 * mm, 75 * mm]), Paragraph("Interpretation and next step", h1),
          Paragraph("The plotted trend and heatmap correlations are raw, descriptive associations. They do not control for age or education and do not establish causation. In the modeling phase, fit separate multiple linear regression models for entorhinal volume and thickness: MOCATOTS ~ entorhinal measure + NACCAGE + EDUC. Check assumptions, residuals, missingness, MRI quality, and UDS–MRI timing before interpreting adjusted estimates. The available NACC clinical/research subset is not a probability sample of the general population.", body),
          Paragraph("Analysis code: src/phase1_analysis.py | Tables and machine-readable results: reports/phase1/ | Figures: figures/phase1/", small)]

# Add every generated Phase 1 figure as vector artwork in an illustrated appendix.
captions = {
    "01_age_distribution.svg": "Age distribution in the age-65+ analytic sample.",
    "02_moca_distribution.svg": "Distribution of valid MOCATOTS scores (0–30).",
    "03_entorhinal_distribution.svg": "Distribution of bilateral mean entorhinal cortical thickness.",
    "04_cognitive_status.svg": "Participant counts by UDS cognitive-status category.",
    "05_sex_distribution.svg": "Participant counts by recorded sex category.",
    "06_moca_by_status.svg": "MOCATOTS distribution by NACCUDSD cognitive-status category.",
    "07_thickness_by_status.svg": "Bilateral entorhinal thickness by NACCUDSD category.",
    "08_moca_entorhinal_volume_scatter.svg": "MoCA versus bilateral entorhinal volume with an unadjusted linear trend.",
    "09_moca_entorhinal_thickness_scatter.svg": "MoCA versus bilateral entorhinal thickness with an unadjusted linear trend.",
    "10_correlation_heatmap.svg": "Pairwise Pearson correlations among the main continuous variables.",
    "11_linkage.svg": "Counts of UDS-only, MRI-only, and linked participant records.",
}
figures = []
for filename, caption_text in captions.items():
    path = ROOT / "figures" / "phase1" / filename
    if path.exists():
        fig = SVGFigure(path)
        figures.append((fig, caption_text))

if figures:
    story.append(PageBreak())
    story.append(Paragraph("Figures and supplementary charts", h1))
    page_items = []
    used_height = 22 * mm
    for fig, caption_text in figures:
        block_height = fig.height + 13 * mm
        if page_items and used_height + block_height > 245 * mm:
            story.extend(page_items)
            story.append(PageBreak())
            page_items = []
            used_height = 0
        page_items.extend([fig, Paragraph(caption_text, small), Spacer(1, 5 * mm)])
        used_height += block_height
    if page_items:
        story.extend(page_items)

doc = SimpleDocTemplate(str(PDF), pagesize=A4, rightMargin=20 * mm, leftMargin=20 * mm,
                        topMargin=20 * mm, bottomMargin=19 * mm,
                        title="Phase 1: NACC Older Adults, MoCA, and Entorhinal MRI", author="Reproducible descriptive analysis")
doc.build(story, onFirstPage=footer, onLaterPages=footer)
shutil.copyfile(PDF, ROOT / "reports" / "phase1.pdf")
print(f"Created {PDF} and reports/phase1.pdf")
