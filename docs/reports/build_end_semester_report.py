"""Build a concise, high-signal end-semester B.Tech project report (DOCX).

Follows IIT Delhi BTP formatting conventions (Times New Roman 12 pt, justified body
text, centered equations with right-justified equation numbers, italicized variables,
Introduction and Conclusion subsections per chapter, List of Figures, List of Tables,
ordered IEEE references, and dynamic Figure/Table/Equation numbering) while eliminating
redundant tables, overlapping figures, and repetitive narrative.

Run:    python docs/reports/build_end_semester_report.py
Output: docs/reports/BTP_End_Semester_Report.docx
"""
from __future__ import annotations

import re
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.image as mpimg
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_TAB_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

ROOT = Path(__file__).resolve().parents[2]
RES = ROOT / "results"
PLOTS = RES / "plots"
MID_IMG = ROOT / "docs" / "reports" / "mid_sem_figures"
OUT = ROOT / "docs" / "reports" / "BTP_End_Semester_Report.docx"

doc = Document()
sec = doc.sections[0]
sec.page_width, sec.page_height = Cm(21.0), Cm(29.7)
sec.left_margin = sec.right_margin = Cm(2.5)
sec.top_margin = sec.bottom_margin = Cm(2.5)
TEXT_WIDTH_CM = 16.0

st = doc.styles["Normal"]
st.font.name = "Times New Roman"
st.font.size = Pt(12)
st.element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
st.paragraph_format.line_spacing = 1.25
st.paragraph_format.space_after = Pt(5)
st.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

for name, size in [("Heading 1", 16), ("Heading 2", 13), ("Heading 3", 12)]:
    h = doc.styles[name]
    h.font.name = "Times New Roman"
    h.font.size = Pt(size)
    h.font.bold = True
    h.font.color.rgb = RGBColor(0x1B, 0x36, 0x5D) if name == "Heading 1" else RGBColor(0, 0, 0)
    h.element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
    h.paragraph_format.space_before = Pt(9 if name == "Heading 1" else 7)
    h.paragraph_format.space_after = Pt(3)
    h.paragraph_format.keep_with_next = True

FIG_ENTRIES: list[tuple[int, str]] = []
TAB_ENTRIES: list[tuple[int, str]] = []
TOC_ENTRIES: list[tuple[int, str]] = []
EQ_COUNT = [0]

TOKEN_RE = re.compile(r"(</?(?:i|b|sub|sup|code)>)")


def _add_runs(p, text: str, base_bold=False, base_italic=False, size=None):
    """Parse nested inline tags <i>, <b>, <sub>, <sup>, <code> into python-docx runs."""
    counts = {"b": 0, "i": 0, "sub": 0, "sup": 0, "code": 0}
    for part in TOKEN_RE.split(text):
        if not part:
            continue
        if part.startswith("<") and part.endswith(">"):
            closing = part.startswith("</")
            tag = part[2:-1] if closing else part[1:-1]
            counts[tag] = max(0, counts[tag] + (-1 if closing else 1))
            continue
        r = p.add_run(part)
        r.bold = base_bold or (counts["b"] > 0)
        r.italic = base_italic or (counts["i"] > 0)
        if counts["sub"] > 0:
            r.font.subscript = True
        if counts["sup"] > 0:
            r.font.superscript = True
        if counts["code"] > 0:
            r.font.name = "Courier New"
            r.font.size = Pt(10 if not size else size - 1)
        elif size:
            r.font.size = Pt(size)


def P(text: str, bold=False, italic=False, align=None, size=None, after=None):
    p = doc.add_paragraph()
    _add_runs(p, text, base_bold=bold, base_italic=italic, size=size)
    if align == "c":
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    elif align == "j":
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    elif align == "l":
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    if after is not None:
        p.paragraph_format.space_after = Pt(after)
    return p


def J(text: str):
    return P(text, align="j")


def H(text: str, lvl: int = 1, record_toc: bool = True):
    h = doc.add_heading(text, level=lvl)
    if record_toc and lvl in (1, 2):
        TOC_ENTRIES.append((lvl, text))
    return h


def B(items: list[str], numbered: bool = False):
    for it in items:
        p = doc.add_paragraph(style="List Number" if numbered else "List Bullet")
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p.paragraph_format.space_after = Pt(3)
        _add_runs(p, it)


def EQ(text: str) -> str:
    """Centered equation with right-justified equation number (n) on the same line."""
    EQ_COUNT[0] += 1
    num = EQ_COUNT[0]
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p.paragraph_format.tab_stops.add_tab_stop(Cm(TEXT_WIDTH_CM / 2.0), WD_TAB_ALIGNMENT.CENTER)
    p.paragraph_format.tab_stops.add_tab_stop(Cm(TEXT_WIDTH_CM), WD_TAB_ALIGNMENT.RIGHT)
    p.paragraph_format.space_before = Pt(3)
    p.paragraph_format.space_after = Pt(5)
    p.add_run("\t")
    _add_runs(p, text)
    r_num = p.add_run(f"\t({num})")
    r_num.italic = False
    return f"({num})"


def PB():
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)


def FIGURE(path, caption: str, width: float = 14.0) -> int:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(path)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.keep_with_next = True
    p.add_run().add_picture(str(path), width=Cm(width))
    num = len(FIG_ENTRIES) + 1
    FIG_ENTRIES.append((num, caption))
    cp = doc.add_paragraph()
    cp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    cp.paragraph_format.space_after = Pt(6)
    _add_runs(cp, f"Figure {num}. {caption}", base_italic=True, size=10.5)
    return num


def shade(cell, color="D9E2F3"):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), color)
    tcPr.append(shd)


def TABLE(df: pd.DataFrame, caption: str, fs: float = 9.0, widths: list[float] | None = None) -> int:
    num = len(TAB_ENTRIES) + 1
    TAB_ENTRIES.append((num, caption))
    tp = doc.add_paragraph()
    tp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    tp.paragraph_format.space_before = Pt(5)
    tp.paragraph_format.space_after = Pt(3)
    tp.paragraph_format.keep_with_next = True
    _add_runs(tp, f"Table {num}. {caption}", base_bold=True, size=10.5)

    t = doc.add_table(rows=1, cols=len(df.columns))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, c in enumerate(df.columns):
        cell = t.rows[0].cells[i]
        cell.text = ""
        _add_runs(cell.paragraphs[0], str(c), base_bold=True, size=fs)
        cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        shade(cell)
    for _, row in df.iterrows():
        cells = t.add_row().cells
        for i, v in enumerate(row):
            cells[i].text = ""
            _add_runs(cells[i].paragraphs[0], str(v), size=fs)
            cells[i].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.LEFT if i == 0 else WD_ALIGN_PARAGRAPH.CENTER
    for row in t.rows:
        for c in row.cells:
            c.paragraphs[0].paragraph_format.space_after = Pt(1)
            c.paragraphs[0].paragraph_format.space_before = Pt(1)
            c.paragraphs[0].paragraph_format.line_spacing = 1.05
    if widths:
        for row in t.rows:
            for i, w in enumerate(widths):
                row.cells[i].width = Cm(w)
    sp = doc.add_paragraph()
    sp.paragraph_format.space_after = Pt(3)
    return num


def pfmt(p) -> str:
    if p == "" or pd.isna(p):
        return ""
    p = float(p)
    if p == 0 or p < 1e-300:
        return "<1e-300"
    return f"{p:.2e}" if p < 1e-3 else f"{p:.4f}"


def insert_paragraph_before(anchor_p, text: str, left_cm: float = 0.0, bold: bool = False, size: float = 11.0):
    np_ = anchor_p.insert_paragraph_before()
    np_.alignment = WD_ALIGN_PARAGRAPH.LEFT
    np_.paragraph_format.left_indent = Cm(left_cm)
    np_.paragraph_format.space_after = Pt(2)
    np_.paragraph_format.line_spacing = 1.15
    _add_runs(np_, text, base_bold=bold, size=size)
    return np_


def toc_field(anchor_p):
    p = anchor_p.insert_paragraph_before()
    p.paragraph_format.space_after = Pt(4)
    run = p.add_run()
    for kind, txt in [("begin", None), (None, 'TOC \\o "1-2" \\h \\z \\u'), ("separate", None)]:
        if kind:
            el = OxmlElement("w:fldChar")
            el.set(qn("w:fldCharType"), kind)
        else:
            el = OxmlElement("w:instrText")
            el.set(qn("xml:space"), "preserve")
            el.text = txt
        run._r.append(el)
    t = OxmlElement("w:t")
    t.text = "[Word TOC Field \u2014 Press F9 / Update Field in Microsoft Word for exact page numbers]"
    run._r.append(t)
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    run._r.append(end)


def page_number_footer():
    f = sec.footer.paragraphs[0]
    f.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = f.add_run()
    for kind, txt in [("begin", None), (None, "PAGE"), ("end", None)]:
        if kind:
            el = OxmlElement("w:fldChar")
            el.set(qn("w:fldCharType"), kind)
        else:
            el = OxmlElement("w:instrText")
            el.set(qn("xml:space"), "preserve")
            el.text = txt
        run._r.append(el)


# =============================================================== DATA & COMPOSITE FIGURES
cmp_ = pd.read_csv(RES / "staged_vs_single_stage_comparison.csv")
cmp_ = cmp_[cmp_.Status == "Converged"].dropna(subset=["NOx_ppm", "NOx_single_ppm"])
rop = pd.read_csv(RES / "rop_analysis_summary.csv")
dec = pd.read_csv(RES / "decoupled_residence_time_results.csv")
fm = pd.read_csv(RES / "finite_mixing_comparison_results.csv")
ps = pd.read_csv(RES / "pressure_sweep_results.csv")
pre = pd.read_csv(RES / "preheat_sweep_results.csv")
hl = pd.read_csv(RES / "heat_loss_sweep_results.csv")
stat = pd.read_csv(RES / "statistical_significance_summary.csv")

# Statistics summary figure
rng = np.random.default_rng(0)
fig, ax = plt.subplots(1, 2, figsize=(11, 4))
red = cmp_.NOx_reduction_pct.values
ax[0].hist(red, bins=40, color="#4472c4", edgecolor="white")
bs = [rng.choice(red, len(red)).mean() for _ in range(5000)]
lo, hi = np.percentile(bs, [2.5, 97.5])
ax[0].axvline(red.mean(), color="k", ls="--", label=f"mean = {red.mean():.1f}%")
ax[0].axvspan(lo, hi, color="orange", alpha=0.5, label=f"95% CI [{lo:.1f}, {hi:.1f}]")
ax[0].axvline(0, color="r")
ax[0].set_xlabel(r"$\mathrm{NO}_x$ reduction by staging (%)")
ax[0].set_ylabel("Matched cases")
ax[0].set_title("(a) Staging benefit (469 matched pairs)")
ax[0].legend(fontsize=8)

sub = stat[stat.Test.str.startswith("Type-II ANOVA") & (stat.Phase == "Main 605-case")].copy()
sub["factor"] = sub.Test.str.extract(r"\((.*)\)")
pv = sub.pivot(index="Quantity", columns="factor", values="Effect")
pr = pv.apply(lambda col: col.str.extract(r"=([0-9.]+)")[0].astype(float))
pr = pr[["NH3_frac", "Phi_1", "Tau_ms"]].loc[["T_final_K", "NOx_ppm", "H2_slip", "Delta_T_K", "Delta_NOx_ppm"]]
x = np.arange(len(pr))
for k, (col, c, lab) in enumerate(zip(pr.columns, ["#4472c4", "#ed7d31", "#70ad47"],
                                      [r"$x_{\mathrm{NH_3}}$", r"$\phi_1$", r"$\tau$"])):
    ax[1].bar(x + (k - 1) * 0.27, pr[col], 0.27, label=lab, color=c)
ax[1].set_xticks(x)
ax[1].set_xticklabels([r"$T_{\mathrm{final}}$", r"$\mathrm{NO}_x$", r"$\mathrm{H_2}$ slip",
                       r"$\Delta T$", r"$\Delta \mathrm{NO}_x$"], rotation=20, fontsize=9)
ax[1].set_ylabel("Partial $R^2$ (Type-II ANOVA)")
ax[1].set_title("(b) Main-study variance share")
ax[1].legend(fontsize=8)
plt.tight_layout()
STAT_FIG1 = PLOTS / "stat_staging_benefit_and_variance_share.png"
plt.savefig(STAT_FIG1, dpi=200)
plt.close()

# Side-by-side 1x3 composite of key nitrogen reaction-path diagrams
rp_fig, rp_axes = plt.subplots(1, 3, figsize=(15, 6), dpi=220)
for ax_i, fname, title in [
    (rp_axes[0], "reaction_path_phi1_1p0_stage1.png", r"(a) Stage 1, $\phi_1 = 1.0$ (Left Branch)"),
    (rp_axes[1], "reaction_path_phi1_1p8_stage1.png", r"(b) Stage 1, $\phi_1 = 1.8$ (Rich Zone)"),
    (rp_axes[2], "reaction_path_phi1_1p8_stage2.png", r"(c) Stage 2, $\phi_1 = 1.8$ (Re-Oxidation)"),
]:
    ax_i.imshow(mpimg.imread(PLOTS / fname))
    ax_i.set_title(title, fontsize=11, fontweight="bold")
    ax_i.axis("off")
plt.tight_layout()
RP_COMP = PLOTS / "reaction_path_composite_3regimes.png"
plt.savefig(RP_COMP, dpi=220)
plt.close()

# ================================================================ TITLE PAGE
for _ in range(2):
    P("")
P("NUMERICAL INVESTIGATION OF TWO-STAGE NH<sub>3</sub>/H<sub>2</sub> STAGED COMBUSTION", bold=True, align="c", size=19)
P("Baseline Quantification, Reaction-Pathway Analysis, Reactor-Architecture Physics, Gas-Turbine Regimes, and Statistical Significance", align="c", size=12.5)
P("")
P("B.Tech Project Report \u2013 End Semester", bold=True, align="c", size=14)
P("")
P("Submitted by", align="c")
P("Arnav Garg (2023ES10187)", bold=True, align="c", size=14)
P("Department of Energy Engineering", align="c")
P("Indian Institute of Technology Delhi", bold=True, align="c")
P("")
P("Project Supervisor: Prof. Sujeet Yadav", align="c")
P("November 2026", align="c")
PB()

# ================================================================ ABSTRACT (~210 words)
H("Abstract", 1, record_toc=False)
mean_red = cmp_.NOx_reduction_pct.mean()
J(f"Rich\u2013lean air staging is investigated for carbon-free NH<sub>3</sub>/H<sub>2</sub> combustion using zero-dimensional perfectly "
  f"stirred reactor (PSR) networks in Cantera with the Tamaoki et al. (2024) mechanism at fixed overall equivalence ratio "
  f"<i>\u03c6</i> = 0.9. Extending a 605-case mid-semester parametric sweep (586 converged), this work closes four key gaps across "
  f"four phases and tests every finding statistically. First, against an identical single-stage PSR baseline (469 matched "
  f"pairs), staging reduces NO<sub>x</sub> by {mean_red:.1f}% on average (95% CI [{lo:.1f}, {hi:.1f}]%, peak 90.4%, sign test "
  f"<i>p</i> = 2.81 \u00d7 10<sup>\u221294</sup>), penalising only pure H<sub>2</sub>. Second, rate-of-production (ROP) analysis proves that the "
  f"U-shaped NO<sub>x</sub> curve against primary equivalence ratio (<i>\u03c6</i><sub>1</sub> = 1.0\u20132.0) is the superposition of falling Stage-1 "
  f"NO<sub>x</sub> (4400 \u2192 29 ppm) and rising Stage-2 oxidation (\u2212191 \u2192 +3586 ppm) of carried-over NH<sub>2</sub> and NH<sub>3</sub> via "
  f"HNO + OH \u21c4 H<sub>2</sub>O + NO, separated by a thermal de-NO<sub>x</sub> valley at <i>\u03c6</i><sub>1</sub> \u2248 1.3. Third, decoupling residence "
  f"times shows longer primary residence (<i>\u03c4</i><sub>1</sub> = 50 ms) reduces amine carry-over and NO<sub>x</sub>, while five-stage progressive "
  f"secondary dilution cuts right-branch NO<sub>x</sub> at <i>\u03c6</i><sub>1</sub> = 2.0 by 88.3% (3693 \u2192 433 ppm, Friedman <i>p</i> = 1.67 \u00d7 10<sup>\u22125</sup>). "
  f"Fourth, pressure (1\u201330 atm) shifts the optimal valley to <i>\u03c6</i><sub>1</sub> = 1.1 and collapses curve variance by 73.7% (Levene "
  f"<i>p</i> = 0.0125), compressor preheat (300\u2013750 K) raises NO<sub>x</sub> by 6.1 ppm K<sup>\u22121</sup>, and liner cooling (<i>U</i> = 3000 W m<sup>\u22122</sup> K<sup>\u22121</sup>) "
  f"recovers a 386 ppm reduction (<i>p</i> = 2.04 \u00d7 10<sup>\u22126</sup>).")
PB()

# ================================================================ FRONT MATTER ANCHORS
H("Table of Contents", 1, record_toc=False)
toc_anchor = doc.add_paragraph("")
PB()

H("List of Figures", 1, record_toc=False)
lof_anchor = doc.add_paragraph("")
PB()

H("List of Tables", 1, record_toc=False)
lot_anchor = doc.add_paragraph("")
PB()

H("Nomenclature and Abbreviations", 1, record_toc=False)
TABLE(pd.DataFrame([
    ["PSR / RQL", "Perfectly stirred reactor / Rich\u2013quench\u2013lean staging"],
    ["ROP / ANOVA / CI", "Rate of production / Analysis of variance / 95% bootstrap confidence interval"],
    ["CFD / PaSR", "Computational fluid dynamics / Partially stirred reactor"],
    ["<i>\u03c6</i>, <i>\u03c6</i><sub>1</sub>", "Overall equivalence ratio (0.9) and primary-stage equivalence ratio (1.0\u20132.0)"],
    ["<i>x</i><sub>NH3</sub>, <i>x</i><sub>H2</sub>", "Inlet fuel mole fractions of NH<sub>3</sub> and H<sub>2</sub> (1 \u2212 <i>x</i><sub>NH3</sub>)"],
    ["<i>\u03c4</i><sub>1</sub>, <i>\u03c4</i><sub>2</sub>, <i>N</i>", "Primary and secondary residence times (ms); number of dilution stages (1, 3, 5)"],
    ["NO<sub>x</sub>", "Sum of NO + NO<sub>2</sub> mole fractions (ppm)"],
    ["<i>P</i>, <i>T</i><sub>in</sub>, <i>T</i><sub>final</sub>", "Pressure (atm), inlet preheat temperature (K), and Stage-2 outlet temperature (K)"],
    ["<i>U</i>, <i>A</i>", "Liner heat-transfer coefficient (W m<sup>\u22122</sup> K<sup>\u22121</sup>) and wall area (0.25 m<sup>2</sup>)"],
    ["<i>\u03b7</i><sup>2</sup>, partial <i>R</i><sup>2</sup>, <i>d</i><sub>z</sub>", "Variance fractions and Cohen\u2019s paired effect size"],
], columns=["Symbol / Acronym", "Meaning"]), "Nomenclature, symbols, and acronyms.", fs=9.5, widths=[4.5, 11.5])
PB()

# ================================================================ CHAPTER 1
H("Chapter 1: Introduction", 1)
H("1.1 Introduction", 2)
J("This chapter introduces the challenges of ammonia\u2013hydrogen (NH<sub>3</sub>/H<sub>2</sub>) combustion, summarises the mid-semester "
  "parametric baseline and its four limitations, and states the objectives of this end-semester investigation.")

H("1.2 Motivation and Mid-Semester Context", 2)
J("Ammonia offers carbon-free hydrogen storage and transport, but its direct combustion suffers from low reactivity and "
  "high fuel-bound nitrogen oxide (NO<sub>x</sub> = NO + NO<sub>2</sub>) emissions [1, 2]. Blending H<sub>2</sub> boosts flame speed, while rich\u2013quench\u2013lean "
  "(RQL) air staging reduces fuel-N conversion to NO by burning rich first before lean burnout [3\u20135].")
J("The mid-semester study solved a two-stage perfectly stirred reactor (PSR) network in Cantera [6] using the Tamaoki "
  "et al. (2024) mechanism [7] across 605 cases (586 converged) in NH<sub>3</sub> fraction (<i>x</i><sub>NH3</sub> = 0\u20131), primary equivalence "
  "ratio (<i>\u03c6</i><sub>1</sub> = 1.0\u20132.0), and residence time (<i>\u03c4</i> = 20\u2013100 ms) at overall <i>\u03c6</i> = 0.9, 300 K, 1 atm. While fuel blend "
  "governed final temperature (<i>\u03b7</i><sup>2</sup> = 0.981) and NO<sub>x</sub> followed a non-monotonic U-curve against <i>\u03c6</i><sub>1</sub>, four "
  "limitations prevented practical design conclusions: (i) no single-stage baseline to quantify the staging gain, (ii) no "
  "elementary rate-of-production (ROP) explanation of the U-curve, (iii) equal stage residence times and instantaneous "
  "secondary mixing, and (iv) ambient adiabatic conditions (1 atm, 300 K, no heat loss).")

H("1.3 Objectives", 2)
B(["<b>Phase 1 (Baseline):</b> Benchmark two-stage combustion against an identical-condition single-stage PSR across all blends.",
   "<b>Phase 2 (Kinetics):</b> Isolate the elementary NO reactions and nitrogen pathways producing the U-shaped NO<sub>x</sub> curve.",
   "<b>Phase 3 (Architecture & Mixing):</b> Decouple stage residence times (<i>\u03c4</i><sub>1</sub> \u2260 <i>\u03c4</i><sub>2</sub>) and model progressive <i>N</i>-stage secondary air dilution.",
   "<b>Phase 4 (Gas-Turbine Regimes):</b> Evaluate elevated pressure (1\u201330 atm), air preheat (300\u2013750 K), and liner cooling (<i>U</i> \u2264 3000 W m<sup>\u22122</sup> K<sup>\u22121</sup>).",
   "<b>Statistical Verification:</b> Establish significance, effect sizes, and bootstrap confidence intervals (CIs) for all results."], numbered=True)

H("1.4 Conclusion", 2)
J("Closing these four gaps converts the earlier parametric map into a baseline-controlled, mechanistically grounded design "
  "framework. Chapter 2 reviews the ammonia kinetics and reactor modelling literature underpinning this work.")
PB()

# ================================================================ CHAPTER 2
H("Chapter 2: Literature Survey", 1)
H("2.1 Introduction", 2)
J("This chapter reviews ammonia oxidation kinetics (Section 2.2), nitrogen formation and thermal de-NO<sub>x</sub> pathways "
  "(Section 2.3), and PSR network approximations for gas-turbine realism (Section 2.4).")

H("2.2 Ammonia Oxidation Kinetics", 2)
J("Ammonia oxidation initiates via H-abstraction (NH<sub>3</sub> + OH/H/O \u21c4 NH<sub>2</sub> + H<sub>2</sub>O/H<sub>2</sub>/OH), progressing far more slowly than "
  "H<sub>2</sub> or hydrocarbons [1, 8]. Hydrogen blending supplies O/OH/H radicals that accelerate NH<sub>3</sub> consumption [2]. Tamaoki "
  "et al. [7] developed a 33-species, 228-reaction mechanism showing that NH<sub>2</sub> branching (NH<sub>2</sub> + HO<sub>2</sub>, NH<sub>2</sub> + NH<sub>2</sub>, "
  "and NH<sub>2</sub> + NO) governs intermediate-temperature reactivity and H<sub>2</sub> generation; that validated mechanism is adopted here.")

H("2.3 Fuel-Bound Nitrogen Chemistry and Thermal DeNOx", 2)
J("Miller and Bowman [3] established that fuel-N oxidation proceeds through NH<sub>2</sub> \u2192 NH \u2192 HNO/N \u2192 NO. Under moderately rich "
  "conditions, however, amine radicals reduce NO back to N<sub>2</sub> via thermal de-NO<sub>x</sub> steps (NH<sub>2</sub> + NO \u21c4 H<sub>2</sub>O + N<sub>2</sub> / NNH + OH "
  "and NH + NO \u21c4 N<sub>2</sub> + OH / H + N<sub>2</sub>O) [4, 5]. Competing oxidation (HNO + OH, NH + O<sub>2</sub>) versus de-NO<sub>x</sub> reduction "
  "determines whether staging suppresses or regenerates NO<sub>x</sub>.")

H("2.4 Reactor-Network Modelling and Gap Addressed", 2)
J("Cantera PSR networks [6] efficiently capture staged chemical kinetics before costly computational fluid dynamics (CFD), "
  "but conventional 0-D models omit unequal primary/secondary sizing, finite secondary dilution rates, and high-pressure "
  "heat-loss effects [1, 2]. Prior literature lacks a single-stage-controlled, ROP-verified, and statistically tested study "
  "quantifying how these architectural and engine variables interact.")

H("2.5 Conclusion", 2)
J("The literature identifies amine-radical branching as the lever controlling staged NO<sub>x</sub>. Chapter 3 formulates the PSR "
  "models, diagnostics, and statistical tests used to evaluate it.")
PB()

# ================================================================ CHAPTER 3
H("Chapter 3: Problem Formulation and Numerical Methodology", 1)
H("3.1 Introduction", 2)
J("This chapter formulates the stoichiometry and reactor networks (Sections 3.2\u20133.4), ROP diagnostics (Section 3.5), "
  "simulation campaigns (Section 3.6), and statistical tests (Section 3.7).")

H("3.2 Fuel Composition and Air Allocation", 2)
J("The binary fuel molar composition is <i>x</i><sub>NH3</sub> \u2208 [0, 1] and:")
eq_fuel = EQ("<i>x</i><sub>H2</sub> = 1 \u2212 <i>x</i><sub>NH3</sub>")
J(f"From {eq_fuel}, stoichiometric O<sub>2</sub> demand is 0.75<i>x</i><sub>NH3</sub> + 0.50<i>x</i><sub>H2</sub> per mole of fuel. With standard air "
  "(O<sub>2</sub>:N<sub>2</sub> = 1:3.76) and fixed overall <i>\u03c6</i> = 0.9, primary air <i>A</i><sub>1</sub> and secondary air fraction <i>A</i><sub>2</sub>/<i>A</i><sub>total</sub> follow from:")
eq_a1 = EQ("<i>A</i><sub>stoic</sub> = 4.76(0.75<i>x</i><sub>NH3</sub> + 0.50<i>x</i><sub>H2</sub>),   <i>A</i><sub>1</sub> = <i>A</i><sub>stoic</sub> / <i>\u03c6</i><sub>1</sub>,   <i>A</i><sub>total</sub> = <i>A</i><sub>stoic</sub> / <i>\u03c6</i>")
eq_a2 = EQ("<i>A</i><sub>2</sub> / <i>A</i><sub>total</sub> = 1 \u2212 <i>\u03c6</i> / <i>\u03c6</i><sub>1</sub>")
J(f"Per {eq_a1}\u2013{eq_a2}, sweeping <i>\u03c6</i><sub>1</sub> from 1.0 to 2.0 shifts secondary air from 10% to 55% of total air.")

H("3.3 PSR Network and Phase 1/3 Extensions", 2)
J("Each constant-pressure PSR (nominal volume <i>V</i> = 1.0 m<sup>3</sup>) solves transient species conservation until relative "
  "changes in temperature and composition fall below 10<sup>\u22128</sup> (5 to 100 nominal residence times):")
eq_psr = EQ("d(<i>mY</i><sub>k</sub>)/d<i>t</i> = <i>\u1e41</i>(<i>Y</i><sub>k,in</sub> \u2212 <i>Y</i><sub>k</sub>) + <i>V\u03c9\u0307</i><sub>k</sub><i>W</i><sub>k</sub>,   <i>\u1e41</i> = <i>m</i> / <i>\u03c4</i>")
J(f"where {eq_psr} sets mass flow rate via residence time <i>\u03c4</i>. Figure {{FIG_NET}} shows the two-stage baseline layout; three "
  "extensions remove prior idealisations: (i) a <b>single-stage baseline</b> at <i>\u03c6</i> = 0.9 matched at both <i>\u03c4</i> and 2<i>\u03c4</i> "
  "(Phase 1), (ii) <b>decoupled residence times</b> <i>\u03c4</i><sub>1</sub> \u2208 [10, 50] ms and <i>\u03c4</i><sub>2</sub> \u2208 [20, 100] ms (Phase 3a), and "
  "(iii) <b>progressive dilution</b> splitting secondary air equally across <i>N</i> \u2208 {1, 3, 5} sub-stages of duration <i>\u03c4</i><sub>2</sub>/<i>N</i> (Phase 3b).")
fig_net = FIGURE(MID_IMG / "image2.png", "Two-stage perfectly stirred reactor (PSR) network configuration.", 11.5)

H("3.4 Gas-Turbine Regimes and Wall Heat Loss (Phase 4)", 2)
J("Phase 4 varies pressure <i>P</i> (1\u201330 atm), inlet air preheat <i>T</i><sub>in</sub> (300\u2013750 K), and liner wall heat loss using Cantera\u2019s "
  "<code>Wall</code> model (area <i>A</i> = 0.25 m<sup>2</sup>, wall temperature <i>T</i><sub>wall</sub> = <i>T</i><sub>in</sub>):")
eq_wall = EQ("<i>Q\u0307</i><sub>wall</sub> = <i>UA</i>(<i>T</i> \u2212 <i>T</i><sub>wall</sub>)")

H("3.5 Kinetic Diagnostics and Performance Metrics", 2)
J(f"At <i>x</i><sub>NH3</sub> = 0.50, <i>\u03c4</i> = 60 ms, elementary NO production contributions of all NO-participating reactions are evaluated via {eq_wall.replace('5','6')} "
  "— wait, let's reference dynamically!")
# fix equation ref cleanly:
doc.paragraphs[-1]._element.getparent().remove(doc.paragraphs[-1]._element)
J("At <i>x</i><sub>NH3</sub> = 0.50 and <i>\u03c4</i> = 60 ms, elementary NO production contributions are evaluated across all NO-participating reactions:")
eq_rop = EQ("<i>C</i><sub>NO,<i>i</i></sub> = (<i>\u03bd</i>\u2033<sub>NO,<i>i</i></sub> \u2212 <i>\u03bd</i>\u2032<sub>NO,<i>i</i></sub>) <i>q</i><sub>net,<i>i</i></sub>   [kmol m<sup>\u22123</sup> s<sup>\u22121</sup>]")
J(f"Element-\u2018N\u2019 <code>ReactionPathDiagram</code> networks are rendered with normalised flux scaling (<code>scale = -1</code>, 2% threshold) "
  f"via Graphviz. Emissions and staging benefit are quantified via {eq_rop} and:")
eq_met = EQ("NO<sub>x</sub> = NO + NO<sub>2</sub>,   <i>\u0394</i>NO<sub>x</sub> = NO<sub>x,2</sub> \u2212 NO<sub>x,1</sub>")
eq_ben = EQ("Staging benefit (%) = 100 (NO<sub>x,single</sub> \u2212 NO<sub>x,staged</sub>) / NO<sub>x,single</sub>")

H("3.6 Computational Campaigns and Verification", 2)
J("Table {{TAB_CAMP}} summarises the eight Cantera 3.0 simulation campaigns using <code>mechanisms/TamaokiNH3.yaml</code> [6, 7]. "
  "Equivalence ratio is preserved to 1.11 \u00d7 10<sup>\u221216</sup>, all Phase 1\u20134 grids achieved 100% convergence, and <i>\u03c4</i><sub>1</sub> = <i>\u03c4</i><sub>2</sub> / <i>N</i> = 1 "
  "slices match the baseline two-stage solver.")
tab_camp = TABLE(pd.DataFrame([
    ["Main 605-case", "<i>x</i><sub>NH3</sub> 0\u20131 (11), <i>\u03c6</i><sub>1</sub> 1.0\u20132.0 (11), <i>\u03c4</i> 20\u2013100 ms (5)", "300 K, 1 atm, <i>U</i> = 0", "605 (586 conv.)"],
    ["Phase 1 Baseline", "<i>x</i><sub>NH3</sub> 0\u20131 (11), <i>\u03c4</i> 20\u2013200 ms (8)", "300 K, 1 atm, <i>\u03c6</i> = 0.9", "88 single; 469 matched"],
    ["Phase 2 ROP", "<i>\u03c6</i><sub>1</sub> 1.0\u20132.0 (11), Stage 1 & Stage 2", "<i>x</i><sub>NH3</sub> = 0.5, <i>\u03c4</i> = 60 ms", "11 (1,606 rxn rows)"],
    ["Phase 3a Decoupled <i>\u03c4</i>", "<i>\u03c6</i><sub>1</sub> \u2208 {1.2,1.4,1.6,1.8,2.0}, <i>\u03c4</i><sub>1</sub> 10\u201350, <i>\u03c4</i><sub>2</sub> 20\u2013100 ms", "<i>x</i><sub>NH3</sub> = 0.5, 300 K, 1 atm", "125 (100% conv.)"],
    ["Phase 3b Mixing", "<i>\u03c6</i><sub>1</sub> 1.0\u20132.0 (11), <i>N</i> \u2208 {1, 3, 5}", "<i>\u03c4</i><sub>1</sub> = 30, <i>\u03c4</i><sub>2</sub> = 60 ms", "33 (100% conv.)"],
    ["Phase 4a Pressure", "<i>\u03c6</i><sub>1</sub> 1.0\u20132.0 (11), <i>P</i> \u2208 {1, 5, 10, 20, 30} atm", "<i>x</i><sub>NH3</sub> = 0.5, <i>T</i><sub>in</sub> = 300 K", "55 (100% conv.)"],
    ["Phase 4b Preheat", "<i>\u03c6</i><sub>1</sub> (7 levels), <i>T</i><sub>in</sub> \u2208 {300, 450, 600, 750} K", "<i>x</i><sub>NH3</sub> = 0.5, 10 atm", "28 (100% conv.)"],
    ["Phase 4c Heat Loss", "<i>\u03c6</i><sub>1</sub> (7 levels), <i>U</i> \u2208 {0, 500, 1500, 3000} W m<sup>\u22122</sup> K<sup>\u22121</sup>", "15 atm, 650 K", "28 (100% conv.)"],
], columns=["Campaign", "Varied Parameters", "Fixed Conditions", "Cases"]), "Computational campaigns (all at overall <i>\u03c6</i> = 0.9).", fs=8.5, widths=[2.7, 6.4, 3.6, 3.3])

H("3.7 Statistical Significance Framework", 2)
J("Because PSR runs are deterministic, significance is evaluated across sampled operating conditions using Type-II ANOVA "
  "partial <i>F</i>-tests (partial <i>R</i><sup>2</sup>), paired <i>t</i>-tests (Cohen\u2019s <i>d</i><sub>z</sub>), non-parametric Wilcoxon signed-rank [9], "
  "binomial sign, Friedman, and Levene variance-collapse tests, plus 10,000-resample 95% bootstrap CIs [10]. All tests "
  "live in <code>double_stage/statistical_significance_analysis.py</code>; 0-D mixing and single-mechanism assumptions apply.")

H("3.8 Conclusion", 2)
J("Chapter 3 defined the simulation grids, extensions, and inference tools. Chapter 4 applies them to Phases 1 and 2.")
PB()

# ================================================================ CHAPTER 4
H("Chapter 4: Baseline Quantification and Chemical Kinetic Pathway Analysis", 1)
H("4.1 Introduction", 2)
J("This chapter presents Phases 1 and 2: quantifying staging gains against a single-stage baseline (Section 4.3) and "
  "identifying the elementary reactions and nitrogen pathways behind the NO<sub>x</sub> U-curve (Sections 4.4\u20134.5).")

H("4.2 Mid-Semester 605-Case Reference", 2)
J("Across the 586 converged mid-semester cases, final temperature drops monotonically from 2335 K (pure H<sub>2</sub>) to 1930 K "
  "(pure NH<sub>3</sub>), governed almost exclusively by <i>x</i><sub>NH3</sub> (<i>\u03b7</i><sup>2</sup> = 0.981). Final NO<sub>x</sub> spans 891\u20136772 ppm and "
  "forms a non-monotonic U-shaped valley over <i>x</i><sub>NH3</sub> and <i>\u03c6</i><sub>1</sub> (Figure {{FIG_MNMAP}}), with high emissions both near "
  "<i>\u03c6</i><sub>1</sub> = 1.0 (H<sub>2</sub>-rich blends) and near <i>\u03c6</i><sub>1</sub> = 2.0 (NH<sub>3</sub> > 70%).")
fig_mnmap = FIGURE(MID_IMG / "image10.png", "Mid-semester reference map: final NO<sub>x</sub> (ppm) over NH<sub>3</sub> fraction and <i>\u03c6</i><sub>1</sub> at <i>\u03c4</i> = 60 ms.", 11.0)

H("4.3 Single-Stage Baseline Comparison (Phase 1)", 2)
J("Across 469 matched operating pairs linking the 88 single-stage lean cases to the two-stage dataset (Table {{TAB_B1}}, "
  "Figures {{FIG_B1}}\u2013{{FIG_B2}}), staging reduces NO<sub>x</sub> by 55.1% on average (median 64.9%), beating single-stage combustion "
  "in 439 of 469 cases (93.6%).")
g = cmp_.groupby("NH3_frac").agg(single=("NOx_single_ppm", "mean"), staged=("NOx_ppm", "mean"),
                                 red=("NOx_reduction_pct", "mean"), mx=("NOx_reduction_pct", "max"),
                                 mn=("NOx_reduction_pct", "min")).reset_index()
# Compact 6 representative blend rows
sel = g[g.NH3_frac.round(1).isin([0.0, 0.2, 0.3, 0.5, 0.8, 1.0])]
t1 = pd.DataFrame({
    "<i>x</i><sub>NH3</sub>": sel.NH3_frac.round(1),
    "Single-stage NO<sub>x</sub> (ppm)": sel.single.round(0).astype(int),
    "Staged NO<sub>x</sub> (ppm)": sel.staged.round(0).astype(int),
    "Mean cut (%)": sel.red.round(1),
    "Range min..max (%)": [f"{a:.1f}..{b:.1f}" for a, b in zip(sel.mn, sel.mx)],
})
tab_b1 = TABLE(t1, "Single-stage vs. staged NO<sub>x</sub> across representative fuel blends (means over matched <i>\u03c6</i><sub>1</sub> and <i>\u03c4</i>).",
               widths=[2.0, 3.4, 3.2, 2.8, 4.6])
fig_b1 = FIGURE(PLOTS / "baseline_nox_comparison.png", "Two-stage vs. matched single-stage NO<sub>x</sub> across fuel blends at <i>\u03c4</i> = 60 ms.", 13.5)
fig_b2 = FIGURE(PLOTS / "staging_benefit_heatmap.png", "Staging benefit contour map (% NO<sub>x</sub> reduction vs. single-stage baseline) at <i>\u03c4</i> = 60 ms.", 13.5)
J(f"Single-stage NO<sub>x</sub> peaks above 8300 ppm at <i>x</i><sub>NH3</sub> = 0.20\u20130.30 because abundant H<sub>2</sub>-derived O/OH radicals rapidly "
  f"oxidise fuel nitrogen; staging drops emissions to 973\u20131014 ppm (up to 90.4% cut). Pure H<sub>2</sub> (<i>x</i><sub>NH3</sub> = 0.0) incurs a "
  f"net penalty (down to \u221268.4%) because extra residence time generates thermal NO without fuel-N to suppress. Across all "
  f"ammonia blends (<i>x</i><sub>NH3</sub> \u2265 0.10), staging averages a 60.1% cut, though NH<sub>3</sub>-rich mixtures at extreme <i>\u03c6</i><sub>1</sub> = 2.0 "
  f"enter a right-branch penalty corner (Figure {{FIG_B2}}, \u221247.6% at <i>x</i><sub>NH3</sub> = 0.80) while maintaining comparable fuel slip.")

H("4.4 Rate-of-Production Origin of the U-Curve (Phase 2)", 2)
J("Stage-resolved ROP diagnostics at <i>x</i><sub>NH3</sub> = 0.50, <i>\u03c4</i> = 60 ms resolve the exact mechanism behind the U-curve "
  "(Figures {{FIG_ROP1}} and {{FIG_ROP2}}).")
fig_rop1 = FIGURE(PLOTS / "rop_u_curve_pathway_mechanism.png",
                  "Kinetic decomposition of the U-curve: (a) Stage-1 vs. final temperature and NO<sub>x</sub>, (b) amine carry-over from Stage 1, and (c) dominant Stage-2 NO rates.", 15.2)
fig_rop2 = FIGURE(PLOTS / "rop_top_no_reactions_stage1_vs_stage2.png", "Top elementary NO source (blue) and sink (red) reactions in Stage 1 and Stage 2 at <i>\u03c6</i><sub>1</sub> = 1.0, 1.3, and 1.8.", 14.8)
J(f"Figure {{FIG_ROP1}}(a) proves the U-curve is the sum of two monotonic processes: Stage-1 NO<sub>x</sub> drops monotonically from "
  f"4400 ppm (<i>\u03c6</i><sub>1</sub> = 1.0, 2168 K) to 29 ppm (<i>\u03c6</i><sub>1</sub> = 2.0, 1720 K), while Stage-2 NO<sub>x</sub> generation climbs monotonically "
  f"from \u2212191 to +3586 ppm. Simultaneously, Figure {{FIG_ROP1}}(b) shows Stage-1 outlet carry-over surging: NH<sub>2</sub> rises 16.4\u00d7 "
  f"(5.2 \u2192 85.7 ppm) and unburnt NH<sub>3</sub> rises nearly 400\u00d7 (21.9 \u2192 8558 ppm). Figure {{FIG_ROP2}} and Figure {{FIG_ROP1}}(c) "
  f"define three regimes:")
B(["<b>Left Branch (<i>\u03c6</i><sub>1</sub> = 1.0\u20131.2):</b> Hot, oxygen-containing Stage 1 forms 4400 ppm NO via N + OH \u21c4 H + NO and "
   "HNO + OH \u21c4 H<sub>2</sub>O + NO; Stage 2 yields net de-NO<sub>x</sub> (\u2212191 ppm).",
   "<b>DeNOx Valley (<i>\u03c6</i><sub>1</sub> \u2248 1.3):</b> Moderate oxygen depletion lowers Stage-1 NO<sub>x</sub> to 437 ppm via NH + NO \u21c4 H + N<sub>2</sub>O, "
   "N + NO \u21c4 N<sub>2</sub> + O, and NH<sub>2</sub> + NO \u21c4 H<sub>2</sub>O + N<sub>2</sub> / NNH + OH, while modest NH<sub>2</sub> carry-over (23.3 ppm) limits total NO<sub>x</sub> to 986 ppm.",
   "<b>Right Branch (<i>\u03c6</i><sub>1</sub> \u2265 1.6):</b> Oxygen starvation cuts Stage-1 NO<sub>x</sub> below 110 ppm, but 45\u201355% secondary air in Stage 2 "
   "oxidises carried-over NH<sub>3</sub>/NH<sub>2</sub> via HNO + OH \u21c4 H<sub>2</sub>O + NO (+4.01 \u00d7 10<sup>\u22124</sup> kmol m<sup>\u22123</sup> s<sup>\u22121</sup> at <i>\u03c6</i><sub>1</sub> = 2.0, "
   "24\u00d7 its <i>\u03c6</i><sub>1</sub> = 1.0 rate) and NH + O<sub>2</sub> \u21c4 NO + OH (>9500\u00d7), overwhelming Stage-2 de-NO<sub>x</sub> and regenerating +3586 ppm NO<sub>x</sub>."])

H("4.5 Nitrogen Reaction-Pathway Topology", 2)
fig_rp = FIGURE(RP_COMP, "Normalised element-\u2018N\u2019 reaction-path diagrams: (a) Stage 1 left branch (<i>\u03c6</i><sub>1</sub> = 1.0), (b) Stage 1 right branch (<i>\u03c6</i><sub>1</sub> = 1.8), and (c) Stage 2 re-oxidation (<i>\u03c6</i><sub>1</sub> = 1.8).", 15.5)
J(f"Figure {{FIG_RP}} confirms the flux shift visually: in Stage 1 at <i>\u03c6</i><sub>1</sub> = 1.0 (a), oxidation routes HNO \u2192 NO (0.235) "
  f"and N \u2192 NO (0.197) dominate; at <i>\u03c6</i><sub>1</sub> = 1.8 (b), oxygen starvation redirects amines into N\u2013N coupling "
  f"(N<sub>2</sub>H<sub>2</sub> \u2192 N<sub>2</sub>H<sub>3</sub> / NNH \u2192 N<sub>2</sub>); yet upon entering Stage 2 (c), carried-over NH<sub>3</sub>/NH<sub>2</sub> routes through "
  f"NH<sub>2</sub>/NH \u2192 HNO into the dominant HNO \u2192 NO arrow (0.548) and NO\u2013HONO\u2013NO<sub>2</sub> cycling.")

H("4.6 Conclusion", 2)
J("Staging cuts NO<sub>x</sub> by 60.1% across NH<sub>3</sub> blends, failing only when rich primary carry-over oxidises via HNO + OH in Stage 2. "
  "Chapter 5 tests architectural and gas-turbine strategies to suppress this carry-over.")
PB()

# ================================================================ CHAPTER 5
H("Chapter 5: Reactor Architecture, Mixing Physics, and Gas-Turbine Regimes", 1)
H("5.1 Introduction", 2)
J("This chapter removes idealised reactor and ambient assumptions across Phase 3 (decoupled residence times, Section 5.2; "
  "finite-rate secondary mixing, Section 5.3) and Phase 4 (pressure, preheat, and wall cooling, Sections 5.4\u20135.6).")

H("5.2 Decoupled Stage Residence Times", 2)
J("Sweeping <i>\u03c4</i><sub>1</sub> \u2208 [10, 50] ms \u00d7 <i>\u03c4</i><sub>2</sub> \u2208 [20, 100] ms across five <i>\u03c6</i><sub>1</sub> values (<i>x</i><sub>NH3</sub> = 0.50, 125 cases) "
  "refutes the assumption that a shorter rich zone helps (Figures {{FIG_D1}}\u2013{{FIG_D2}}).")
fig_d1 = FIGURE(PLOTS / "decoupled_tau_2d_contour.png", "Final NO<sub>x</sub> (ppm) contours over (<i>\u03c4</i><sub>1</sub>, <i>\u03c4</i><sub>2</sub>) at four <i>\u03c6</i><sub>1</sub> values (dashed line: <i>\u03c4</i><sub>1</sub> = <i>\u03c4</i><sub>2</sub>).", 14.5)
fig_d2 = FIGURE(PLOTS / "decoupled_tau_ratio_tradeoff.png", "Effect of stage residence-time ratio <i>\u03c4</i><sub>1</sub>/<i>\u03c4</i><sub>2</sub> on final NO<sub>x</sub> and fuel slip.", 13.0)
J(f"Shortening <i>\u03c4</i><sub>1</sub> to 10 ms freezes Stage 1 far from equilibrium, raising NH<sub>2</sub> carry-over to 281.6 ppm and NO<sub>x</sub> to "
  f"4105 ppm at <i>\u03c6</i><sub>1</sub> = 2.0 (Figure {{FIG_D1}}). Extending <i>\u03c4</i><sub>1</sub> to 50 ms lets rich amine chemistry relax toward N<sub>2</sub>, "
  f"halving NH<sub>2</sub> carry-over (157.2 ppm at <i>\u03c6</i><sub>1</sub> = 2.0) and lowering NO<sub>x</sub> across all <i>\u03c6</i><sub>1</sub>. Meanwhile, longer <i>\u03c4</i><sub>2</sub> lowers "
  f"right-branch NO<sub>x</sub> (4438 \u2192 3490 ppm) and slip but slightly elevates thermal NO in the valley (1367 \u2192 1484 ppm at <i>\u03c6</i><sub>1</sub> = 1.2). "
  f"The grid optimum (1124 ppm) therefore occurs at asymmetric sizing: <i>\u03c4</i><sub>1</sub> = 50 ms, <i>\u03c4</i><sub>2</sub> = 20 ms, <i>\u03c6</i><sub>1</sub> = 1.2 (Figure {{FIG_D2}}).")

H("5.3 Finite-Rate Progressive Secondary Dilution", 2)
J("Splitting secondary air equally across <i>N</i> = 3 or <i>N</i> = 5 progressive sub-stages (<i>x</i><sub>NH3</sub> = 0.50, <i>\u03c4</i><sub>1</sub> = 30 ms, "
  "<i>\u03c4</i><sub>2</sub> = 60 ms) dramatically flattens the right branch (Figures {{FIG_FM1}}\u2013{{FIG_FM2}}, Table {{TAB_P34}}).")
fig_fm1 = FIGURE(PLOTS / "finite_mixing_nox_comparison.png", "Flattening of the NO<sub>x</sub> U-curve by 3-stage and 5-stage progressive secondary dilution.", 13.0)
fig_fm2 = FIGURE(PLOTS / "finite_mixing_temperature_trajectories.png", "Sub-stage temperature trajectory across progressive dilution stages (<i>N</i> = 5 vs. <i>N</i> = 1).", 13.0)
J(f"At <i>\u03c6</i><sub>1</sub> = 2.0, final NO<sub>x</sub> drops from 3693 ppm (instantaneous, <i>N</i> = 1) to 640 ppm (<i>N</i> = 3) and 433 ppm (<i>N</i> = 5, \u221288.3%; "
  f"Figure {{FIG_FM1}}). Parcel-wise addition maintains hot, sub-stoichiometric intermediate zones where NH<sub>2</sub> + NO de-NO<sub>x</sub> stays "
  f"active, while short sub-stage residence times (12 ms at <i>N</i> = 5) cross the ~2180 K stoichiometric peak too briefly for thermal "
  f"NO rebuild (Figure {{FIG_FM2}}). Thus the severe right-branch penalty of 0-D models is largely an artefact of instantaneous mixing.")

H("5.4 Elevated Pressure, Air Preheat, and Wall Cooling (Phase 4)", 2)
J("Phase 4 evaluates gas-turbine pressure (1\u201330 atm), compressor-discharge preheat (300\u2013750 K at 10 atm), and liner wall "
  "heat loss (<i>U</i> = 0\u20133000 W m<sup>\u22122</sup> K<sup>\u22121</sup> at 15 atm, 650 K) for <i>x</i><sub>NH3</sub> = 0.50, <i>\u03c4</i><sub>1</sub> = 40 ms, <i>\u03c4</i><sub>2</sub> = 60 ms "
  "(Figures {{FIG_P1}}\u2013{{FIG_HL}}, Table {{TAB_P34}}).")
fig_p1 = FIGURE(PLOTS / "pressure_effect_nox_u_curve.png", "Shift and variance collapse of the NO<sub>x</sub> U-curve from <i>P</i> = 1 to 30 atm.", 13.0)
fig_ph = FIGURE(PLOTS / "preheat_flame_temperature_and_nox.png", "Increase in flame temperature and NO<sub>x</sub> with compressor-discharge preheat (300\u2013750 K, 10 atm).", 13.0)
fig_hl = FIGURE(PLOTS / "wall_heat_loss_mitigation.png", "NO<sub>x</sub> and temperature reduction from combustor liner wall cooling (15 atm, 650 K).", 13.5)
J(f"Three operational shifts govern realistic engine operation:")
B([f"<b>Pressure (Figure {{FIG_P1}}):</b> Raising <i>P</i> from 1 to 30 atm cuts near-stoichiometric NO<sub>x</sub> at <i>\u03c6</i><sub>1</sub> = 1.0 by 61.5% "
   f"(4548 \u2192 1753 ppm) and right-branch NO<sub>x</sub> at <i>\u03c6</i><sub>1</sub> = 2.0 by 41.7% (3652 \u2192 2129 ppm) while raising valley NO<sub>x</sub> "
   f"(1072 \u2192 1604 ppm at <i>\u03c6</i><sub>1</sub> = 1.3). This shifts the optimal primary ratio left from <i>\u03c6</i><sub>1</sub> = 1.3 (1 atm) to 1.1 (10\u201330 atm) "
   f"and raises NO<sub>2</sub>/NO<sub>x</sub> 6.6-fold (0.032% \u2192 0.209%, inferred from H + O<sub>2</sub> + M \u21c4 HO<sub>2</sub> + M recombination).",
   f"<b>Air Preheat (Figure {{FIG_PH}}):</b> Mean final temperature rises linearly by 0.663 K K<sup>\u22121</sup> (2119 \u2192 2418 K), escalating "
   f"mean NO<sub>x</sub> from 1957 to 4699 ppm (~6.1 ppm K<sup>\u22121</sup>) via thermal Zeldovich kinetics while keeping the minimum at <i>\u03c6</i><sub>1</sub> = 1.2\u20131.3.",
   f"<b>Liner Cooling (Figure {{FIG_HL}}):</b> At <i>U</i> = 3000 W m<sup>\u22122</sup> K<sup>\u22121</sup>, wall heat loss cools exhaust gases by 34.9 K "
   f"(2357 \u2192 2322 K) and cuts NO<sub>x</sub> by 286\u2013431 ppm (mean 386.1 ppm) without increasing NH<sub>3</sub> slip (< 0.07 ppm)."])

tab_p34 = TABLE(pd.DataFrame([
    ["Phase 3a Decoupled <i>\u03c4</i>", "<i>\u03c4</i><sub>1</sub> = 50, <i>\u03c4</i><sub>2</sub> = 20 ms, <i>\u03c6</i><sub>1</sub> = 1.2", "1124 ppm minimum NO<sub>x</sub>; <i>\u03c4</i><sub>1</sub> = 50 ms cuts NH<sub>2</sub> carry-over ~44%"],
    ["Phase 3b Progressive Mixing", "<i>N</i> = 5 vs. 1 at <i>\u03c6</i><sub>1</sub> = 2.0", "3693 \u2192 433 ppm (\u221288.3%), eliminates right-branch surge"],
    ["Phase 4a Pressure", "<i>P</i> = 1 \u2192 30 atm", "Optimum shifts <i>\u03c6</i><sub>1</sub> = 1.3 \u2192 1.1; NO<sub>x</sub> SD drops 73.7%"],
    ["Phase 4b Preheat", "<i>T</i><sub>in</sub> = 300 \u2192 750 K (10 atm)", "Mean NO<sub>x</sub>: 1957 \u2192 4699 ppm (+6.1 ppm K<sup>\u22121</sup>)"],
    ["Phase 4c Liner Cooling", "<i>U</i> = 3000 W m<sup>\u22122</sup> K<sup>\u22121</sup> (15 atm, 650 K)", "\u2212386.1 ppm mean NO<sub>x</sub> cut (\u221234.9 K); NH<sub>3</sub> slip < 0.07 ppm"],
], columns=["Study", "Condition / Sweep", "Key Quantitative Finding"]), "Summary of Phase 3 architectural and Phase 4 gas-turbine findings (<i>x</i><sub>NH3</sub> = 0.50).", fs=8.8, widths=[3.8, 4.6, 7.6])
J(f"Table {{TAB_P34}} consolidates these Phase 3\u20134 sensitivities into direct architectural and thermal trade-offs.")

H("5.5 Conclusion", 2)
J("Longer rich residence times, progressive air dilution, high pressure, and liner cooling work synergistically to expand the "
  "low-NO<sub>x</sub> operating envelope. Chapter 6 verifies these effects statistically and synthesises the final design window.")
PB()

# ================================================================ CHAPTER 6
H("Chapter 6: Statistical Significance Analysis and Integrated Design Synthesis", 1)
H("6.1 Introduction", 2)
J("This chapter tests every headline claim from Chapters 4\u20135 for statistical consistency across the sampled parameter grids "
  "(Sections 6.2\u20136.3), states inferential caveats (Section 6.4), and synthesises an integrated combustor design window (Section 6.5).")

H("6.2 Factorial Variance Decomposition and Hypothesis Tests", 2)
fig_stat = FIGURE(STAT_FIG1, "(a) Staging NO<sub>x</sub> reduction distribution and 95% bootstrap CI (469 matched cases); (b) Type-II ANOVA partial <i>R</i><sup>2</sup> on the 586 converged main-study cases.", 15.0)
J("Figure {{FIG_STAT}}(b) confirms that <i>x</i><sub>NH3</sub> dominates <i>T</i><sub>final</sub> (partial <i>R</i><sup>2</sup> = 0.981, <i>p</i> < 10<sup>\u2212300</sup>) and H<sub>2</sub> slip "
  "(0.906, <i>p</i> < 10<sup>\u2212300</sup>), <i>\u03c6</i><sub>1</sub> dominates Stage-2 <i>\u0394T</i> (0.994, <i>p</i> < 10<sup>\u2212300</sup>), and residence time <i>\u03c4</i> significantly reduces "
  "within-cell NO<sub>x</sub> (mean Spearman <i>\u03c1</i> = \u22120.433, <i>p</i> = 1.79 \u00d7 10<sup>\u22127</sup>) while leaving <i>\u0394</i>NO<sub>x</sub> unchanged (<i>p</i> = 0.095). "
  "Table {{TAB_STAT}} compiles the primary inferential tests across Phases 1\u20134 (full 47-test archive in "
  "<code>results/statistical_significance_summary.csv</code>).")

# Build concise 14-row master statistical summary table directly from statistical_significance_summary.csv
keep_tests = [
    ("Main 605-case", "One-sample t on within-cell Spearman rho(tau, NOx)", "NOx_ppm"),
    ("Phase 1", "Paired t-test (single - staged)", "NOx_ppm"),
    ("Phase 1", "Wilcoxon signed-rank (single vs staged)", "NOx_ppm"),
    ("Phase 1", "Two-sided binomial sign test (staging wins)", "NOx_reduction_pct>0"),
    ("Phase 1", "Bootstrap CI of mean % reduction", "NOx_reduction_pct"),
    ("Phase 2", "Spearman trend vs phi1 (exact p for |rho|=1)", "Stage-1 NOx"),
    ("Phase 2", "Quadratic coefficient t-test (U-shape)", "NOx_final vs phi1 (N=1)"),
    ("Phase 3", "Friedman test across N=1,3,5", "NOx_final_ppm"),
    ("Phase 3", "Paired t / Wilcoxon: N=3 vs N=5", "NOx_final_ppm"),
    ("Phase 3", "Type-II ANOVA F-test (Tau_1_ms)", "NOx_final_ppm"),
    ("Phase 3", "Type-II ANOVA F-test (Tau_2_ms)", "NH3_slip_ppm"),
    ("Phase 4", "Paired t-test 1 atm vs 30 atm", "NOx_ppm"),
    ("Phase 4", "Levene variance test 1 atm vs 30 atm", "NOx_ppm"),
    ("Phase 4", "Spearman rho(P_atm, NOx), valley 1.2<=phi1<=1.4", "NOx_ppm"),
    ("Phase 4", "Spearman rho(P_atm, NOx), right branch phi1>=1.7", "NOx_ppm"),
    ("Phase 4", "Spearman rho(P_atm, NO2/NOx)", "NO2_ratio"),
    ("Phase 4", "Exact sign test, same monotone direction at every phi1 (preheat)", "NOx_ppm"),
    ("Phase 4", "Paired t-test adiabatic vs U=3000", "NOx_ppm"),
]
sel_rows = []
for ph, tst, q in keep_tests:
    r = stat[(stat.Phase == ph) & (stat.Test == tst) & (stat.Quantity == q)].iloc[0]
    sel_rows.append([ph, tst, int(r.N), "" if pd.isna(r.Statistic) else r.Statistic, pfmt(r.p_value),
                     "" if pd.isna(r.Effect) else r.Effect, "" if pd.isna(r.CI95) else r.CI95])
tab_stat = TABLE(pd.DataFrame(sel_rows, columns=["Phase", "Test", "<i>N</i>", "Stat.", "<i>p</i>-value", "Effect Size", "95% CI"]),
                 "Headline statistical significance tests across all phases (excerpt from 47-test archive).",
                 fs=7.3, widths=[1.6, 4.3, 0.8, 1.3, 1.5, 4.0, 2.5])

J(f"Table {{TAB_STAT}} and Figure {{FIG_STAT}}(a) verify four points: (i) staging delivers a very large, grid-wide benefit "
  f"(Cohen\u2019s <i>d</i><sub>z</sub> = 1.56, <i>p</i> = 1.26 \u00d7 10<sup>\u2212127</sup>); (ii) the U-curve curvature is statistically significant "
  f"(<i>p</i> = 8.31 \u00d7 10<sup>\u22124</sup>); (iii) progressive dilution cuts NO<sub>x</sub> significantly across <i>N</i> (Friedman <i>p</i> = 1.67 \u00d7 10<sup>\u22125</sup>); "
  f"and (iv) pooled pressure tests appear non-significant (<i>p</i> = 0.188) only because pressure reverses sign between the valley "
  f"(<i>\u03c1</i> = +0.666, <i>p</i> = 0.0068) and right branch (<i>\u03c1</i> = \u22120.766, <i>p</i> = 8.12 \u00d7 10<sup>\u22125</sup>) while collapsing spread by 73.7% (Levene <i>p</i> = 0.0125).")

H("6.3 Statistical Caveats", 2)
J("Because simulations are deterministic, <i>p</i>-values measure grid consistency rather than experimental noise. Curve tests "
  "have modest sample size (<i>n</i> = 7\u201311); under Bonferroni correction across 47 tests (<i>\u03b1</i> = 1.06 \u00d7 10<sup>\u22123</sup>), "
  "pairwise parametric <i>t</i>-tests for <i>N</i> = 1 vs. 3/5 (<i>p</i> = 0.0028/0.0018) are marginal while their Wilcoxon (<i>p</i> = 9.77 \u00d7 10<sup>\u22124</sup>) "
  "and Friedman (<i>p</i> = 1.67 \u00d7 10<sup>\u22125</sup>) tests remain significant. Mechanism uncertainty is not included in CIs.")

H("6.4 Integrated Combustor Design Window", 2)
J("Combining all phases defines a coherent low-NO<sub>x</sub> NH<sub>3</sub>/H<sub>2</sub> design strategy: target primary equivalence ratio "
  "<i>\u03c6</i><sub>1</sub> \u2248 1.1\u20131.3 (shifting toward 1.1 at 10\u201330 atm), provide sufficient primary residence time (<i>\u03c4</i><sub>1</sub> \u2248 40\u201350 ms) to "
  "relax amine radicals, stage secondary air progressively (<i>N</i> \u2265 3\u20135) to prevent HNO + OH oxidation surges, and use liner "
  "cooling to mitigate preheat-induced thermal NO.")

H("6.5 Conclusion", 2)
J("Statistical inference confirms the robustness of staging, kinetic deconstruction, progressive mixing, and cooling while "
  "isolating the sign-reversing pressure interaction. Chapter 7 summarises project conclusions and future research.")
PB()

# ================================================================ CHAPTER 7
H("Chapter 7: Conclusions", 1)
H("7.1 Summary", 2)
B(["<b>Phase 1:</b> Two-stage RQL combustion cuts NO<sub>x</sub> by 55.1% across 469 matched cases (60.1% for NH<sub>3</sub> blends, up to 90.4%, "
   "<i>p</i> = 2.81 \u00d7 10<sup>\u221294</sup>), failing only for pure H<sub>2</sub> or extreme right-branch NH<sub>3</sub>-rich conditions.",
   "<b>Phase 2:</b> The NO<sub>x</sub> U-curve arises from falling Stage-1 thermal NO (4400 \u2192 29 ppm) and rising Stage-2 oxidation "
   "(\u2212191 \u2192 +3586 ppm) of carried-over NH<sub>2</sub>/NH<sub>3</sub> via HNO + OH \u21c4 H<sub>2</sub>O + NO, separated by a de-NO<sub>x</sub> valley at <i>\u03c6</i><sub>1</sub> \u2248 1.3.",
   "<b>Phase 3:</b> Longer rich residence (<i>\u03c4</i><sub>1</sub> = 50 ms) suppresses NH<sub>2</sub> carry-over, and 5-stage progressive secondary dilution "
   "eliminates the right-branch NO<sub>x</sub> surge (\u221288.3%, Friedman <i>p</i> = 1.67 \u00d7 10<sup>\u22125</sup>).",
   "<b>Phase 4:</b> Pressure (30 atm) shifts optimal <i>\u03c6</i><sub>1</sub> to 1.1 and collapses curve variance by 73.7% (<i>p</i> = 0.0125); air preheat "
   "adds 6.1 ppm K<sup>\u22121</sup>; and liner cooling (<i>U</i> = 3000 W m<sup>\u22122</sup> K<sup>\u22121</sup>) cuts NO<sub>x</sub> by 386 ppm (<i>p</i> = 2.04 \u00d7 10<sup>\u22126</sup>) with complete burnout."], numbered=True)

H("7.2 Future Work", 2)
B(["Compare multiple NH<sub>3</sub>/H<sub>2</sub> kinetic mechanisms to bound kinetic parameter uncertainty.",
   "Validate staged and progressive-dilution predictions against experimental jet-stirred and gas-turbine combustor rigs.",
   "Extend Phases 3\u20134 across the full 0\u2013100% NH<sub>3</sub> blend spectrum, add pressure-resolved ROP, and track N<sub>2</sub>O global-warming impact.",
   "Replace discrete equal-split dilution with mixing-time-resolved PaSR or CFD-informed chemical reactor networks."], numbered=True)
PB()

# ================================================================ REFERENCES
H("References", 1)
refs = [
    "H. Kobayashi, A. Hayakawa, K. D. K. A. Somarathne, and E. C. Okafor, \u201cScience and technology of ammonia combustion,\u201d <i>Proceedings of the Combustion Institute</i>, vol. 37, no. 1, pp. 109\u2013133, 2019.",
    "P. Glarborg, J. A. Miller, B. Ruscic, and S. J. Klippenstein, \u201cModeling nitrogen chemistry in combustion,\u201d <i>Progress in Energy and Combustion Science</i>, vol. 67, pp. 31\u201368, 2018.",
    "J. A. Miller and C. T. Bowman, \u201cMechanism and modeling of nitrogen chemistry in combustion,\u201d <i>Progress in Energy and Combustion Science</i>, vol. 15, no. 4, pp. 287\u2013338, 1989.",
    "P. Glarborg, K. Dam-Johansen, J. A. Miller, R. J. Kee, and M. E. Coltrin, \u201cModeling the thermal DeNOx process in flow reactors. Surface effects and nitrous oxide formation,\u201d <i>International Journal of Chemical Kinetics</i>, vol. 26, no. 4, pp. 421\u2013436, 1994.",
    "S. Song, R. K. Hanson, C. T. Bowman, and D. M. Golden, \u201cShock tube determination of the overall rate of NH<sub>2</sub> + NO \u2192 products in the thermal DeNOx process,\u201d <i>International Journal of Chemical Kinetics</i>, vol. 33, no. 11, pp. 715\u2013721, 2001.",
    "D. G. Goodwin, H. K. Moffat, R. L. Speth, I. Schoegl, and B. W. Weber, \u201cCantera: An object-oriented software toolkit for chemical kinetics, thermodynamics, and transport processes,\u201d Zenodo, 2021, doi: 10.5281/zenodo.4527812.",
    "K. Tamaoki, Y. Murakami, K. Kanayama, T. Tezuka, M. Izumi, and H. Nakamura, \u201cRoles of NH<sub>2</sub> reactions in ammonia oxidation at intermediate temperatures: Experiments and chemical kinetic modeling,\u201d <i>Combustion and Flame</i>, vol. 259, Art. no. 113177, 2024, doi: 10.1016/j.combustflame.2023.113177.",
    "H. Nakamura, S. Hasegawa, and T. Tezuka, \u201cKinetic modeling of ammonia/air weak flames in a micro flow reactor with a controlled temperature profile,\u201d <i>Combustion and Flame</i>, vol. 185, pp. 16\u201327, 2017.",
    "F. Wilcoxon, \u201cIndividual comparisons by ranking methods,\u201d <i>Biometrics Bulletin</i>, vol. 1, no. 6, pp. 80\u201383, 1945.",
    "B. Efron, \u201cBootstrap methods: Another look at the jackknife,\u201d <i>The Annals of Statistics</i>, vol. 7, no. 1, pp. 1\u201326, 1979.",
]
for i, ref in enumerate(refs, 1):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p.paragraph_format.left_indent = Cm(1.0)
    p.paragraph_format.first_line_indent = Cm(-1.0)
    _add_runs(p, f"[{i}] {ref}", size=11)

# ================================================================ RESOLVE PLACEHOLDERS & FRONT MATTER
repl = {
    "{FIG_NET}": str(fig_net), "{FIG_MNMAP}": str(fig_mnmap),
    "{FIG_B1}": str(fig_b1), "{FIG_B2}": str(fig_b2),
    "{FIG_ROP1}": str(fig_rop1), "{FIG_ROP2}": str(fig_rop2), "{FIG_RP}": str(fig_rp),
    "{FIG_D1}": str(fig_d1), "{FIG_D2}": str(fig_d2),
    "{FIG_FM1}": str(fig_fm1), "{FIG_FM2}": str(fig_fm2),
    "{FIG_P1}": str(fig_p1), "{FIG_PH}": str(fig_ph), "{FIG_HL}": str(fig_hl), "{FIG_STAT}": str(fig_stat),
    "{TAB_CAMP}": str(tab_camp), "{TAB_B1}": str(tab_b1), "{TAB_P34}": str(tab_p34), "{TAB_STAT}": str(tab_stat),
}
for p in doc.paragraphs:
    for r in p.runs:
        for k, v in repl.items():
            kk = "{" + k + "}"
            if kk in r.text:
                r.text = r.text.replace(kk, v)
            if k in r.text:
                r.text = r.text.replace(k, v)

toc_field(toc_anchor)
for lvl, title in TOC_ENTRIES:
    insert_paragraph_before(toc_anchor, title, left_cm=0.0 if lvl == 1 else 0.7, bold=(lvl == 1), size=11 if lvl == 1 else 10.5)
toc_anchor._element.getparent().remove(toc_anchor._element)

for num, cap in FIG_ENTRIES:
    insert_paragraph_before(lof_anchor, f"<b>Figure {num}.</b> {cap}", left_cm=0.0, size=10.5)
lof_anchor._element.getparent().remove(lof_anchor._element)

for num, cap in TAB_ENTRIES:
    insert_paragraph_before(lot_anchor, f"<b>Table {num}.</b> {cap}", left_cm=0.0, size=10.5)
lot_anchor._element.getparent().remove(lot_anchor._element)

page_number_footer()
doc.save(OUT)
print(f"Saved {OUT}: {len(FIG_ENTRIES)} figures, {len(TAB_ENTRIES)} tables, {EQ_COUNT[0]} equations")
