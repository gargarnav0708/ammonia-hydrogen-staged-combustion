"""Build the end-semester B.Tech project report (DOCX) from repository results.

Follows IIT Delhi BTP formatting conventions (Times New Roman 12 pt, justified body
text, centered equations with right-justified equation numbers, italicized variables,
Introduction and Conclusion subsections per chapter, List of Figures, List of Tables,
ordered IEEE references, and dynamic Figure/Table/Equation numbering).

Run:    python docs/reports/build_end_semester_report.py
Output: docs/reports/BTP_End_Semester_Report.docx
"""
from __future__ import annotations

import re
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
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
st.paragraph_format.line_spacing = 1.3
st.paragraph_format.space_after = Pt(6)
st.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

for name, size in [("Heading 1", 16), ("Heading 2", 13.5), ("Heading 3", 12)]:
    h = doc.styles[name]
    h.font.name = "Times New Roman"
    h.font.size = Pt(size)
    h.font.bold = True
    h.font.color.rgb = RGBColor(0x1B, 0x36, 0x5D) if name == "Heading 1" else RGBColor(0, 0, 0)
    h.element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
    h.paragraph_format.space_before = Pt(10 if name == "Heading 1" else 8)
    h.paragraph_format.space_after = Pt(4)
    h.paragraph_format.keep_with_next = True

FIG_ENTRIES: list[tuple[int, str]] = []
TAB_ENTRIES: list[tuple[int, str]] = []
TOC_ENTRIES: list[tuple[int, str]] = []
EQ_COUNT = [0]

TOKEN_RE = re.compile(r"(</?(?:i|b|sub|sup|code)>)")


def _add_runs(p, text: str, base_bold=False, base_italic=False, size=None):
    """Parse nested inline tags <i>, <b>, <sub>, <sup>, <code> into python-docx runs."""
    state = {"b": base_bold, "i": base_italic, "sub": False, "sup": False, "code": False}
    counts = {k: 0 for k in state}
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
        _add_runs(p, it)


def EQ(text: str) -> str:
    """Centered equation with right-justified equation number (n) on the same line."""
    EQ_COUNT[0] += 1
    num = EQ_COUNT[0]
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p.paragraph_format.tab_stops.add_tab_stop(Cm(TEXT_WIDTH_CM / 2.0), WD_TAB_ALIGNMENT.CENTER)
    p.paragraph_format.tab_stops.add_tab_stop(Cm(TEXT_WIDTH_CM), WD_TAB_ALIGNMENT.RIGHT)
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after = Pt(6)
    p.add_run("\t")
    _add_runs(p, text)
    r_num = p.add_run(f"\t({num})")
    r_num.italic = False
    return f"({num})"


def PB():
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)


def FIGURE(path, caption: str, width: float = 14.5) -> int:
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
    cp.paragraph_format.space_after = Pt(8)
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
    tp.paragraph_format.space_before = Pt(6)
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
    sp.paragraph_format.space_after = Pt(4)
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


# =============================================================== DATA
main = pd.read_csv(RES / "staged_combustion_results.csv")
mc = main[main.Status == "Converged"].copy()
cmp_ = pd.read_csv(RES / "staged_vs_single_stage_comparison.csv")
cmp_ = cmp_[cmp_.Status == "Converged"].dropna(subset=["NOx_ppm", "NOx_single_ppm"])
rop = pd.read_csv(RES / "rop_analysis_summary.csv")
ropr = pd.read_csv(RES / "rop_no_reactions_by_phi1.csv")
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
ax[0].axvspan(lo, hi, color="orange", alpha=0.5, label=f"95% bootstrap CI [{lo:.1f}, {hi:.1f}]")
ax[0].axvline(0, color="r")
ax[0].set_xlabel(r"$\mathrm{NO}_x$ reduction by staging (%)")
ax[0].set_ylabel("Number of matched operating points")
ax[0].set_title("(a) Staging benefit across 469 matched cases")
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
ax[1].set_title("(b) Main-study variance share by factor")
ax[1].legend(fontsize=8)
plt.tight_layout()
STAT_FIG1 = PLOTS / "stat_staging_benefit_and_variance_share.png"
plt.savefig(STAT_FIG1, dpi=200)
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

# ================================================================ ABSTRACT
H("Abstract", 1, record_toc=False)
mean_red = cmp_.NOx_reduction_pct.mean()
J("Ammonia\u2013hydrogen (NH<sub>3</sub>/H<sub>2</sub>) blends are promising carbon-free fuels for stationary power and industrial heat, "
  "but practical deployment in gas-turbine combustors is constrained by low ammonia reactivity, residual fuel slip, and "
  "elevated fuel-bound nitrogen oxide (NO<sub>x</sub>) emissions. Rich\u2013lean air staging is the primary architectural strategy "
  "to resolve this trade-off. In the mid-semester study, a two-stage ideal-gas perfectly stirred reactor (PSR) network "
  "was constructed in Cantera using the 33-species, 228-reaction Tamaoki et al. (2024) mechanism and swept across 605 "
  "operating points (586 converged) in NH<sub>3</sub> mole fraction (<i>x</i><sub>NH3</sub> = 0.0\u20131.0), primary equivalence ratio "
  "(<i>\u03c6</i><sub>1</sub> = 1.0\u20132.0), and residence time (<i>\u03c4</i> = 20\u2013100 ms) at fixed overall equivalence ratio <i>\u03c6</i> = 0.9, "
  "300 K, and 1 atm. That baseline work left four open gaps: no single-stage baseline comparison, no elementary chemical "
  "kinetic explanation of the non-monotonic U-shaped NO<sub>x</sub> curve, idealised reactor assumptions (equal stage "
  "residence times and instantaneous secondary air mixing), and ambient adiabatic boundary conditions.")
J(f"This end-semester report closes all four gaps across four structured engineering phases and establishes formal "
  f"statistical significance for every conclusion. First, an identical-condition single-stage PSR baseline over 469 "
  f"matched operating points proves that staging lowers NO<sub>x</sub> by {mean_red:.1f}% on average (95% bootstrap confidence "
  f"interval [CI]: {lo:.1f}\u2013{hi:.1f}%, up to 90.4%), outperforming single-stage combustion in 93.6% of cases (binomial sign "
  "test <i>p</i> = 2.81 \u00d7 10<sup>\u221294</sup>); staging penalises only pure H<sub>2</sub> where no fuel nitrogen is present to suppress. "
  "Second, elementary rate-of-production (ROP) and nitrogen-flux pathway analyses demonstrate that the U-shaped NO<sub>x</sub> "
  "response is the exact superposition of a monotonic Stage-1 NO<sub>x</sub> decline (4400 \u2192 29 ppm, Spearman <i>\u03c1</i> = \u22121.0, "
  "exact <i>p</i> = 5.01 \u00d7 10<sup>\u22128</sup>) driven by oxygen depletion and thermal de-NO<sub>x</sub> (NH<sub>2</sub>/NH + NO), and a monotonic "
  "Stage-2 NO<sub>x</sub> surge (\u2212191 \u2192 +3586 ppm, <i>\u03c1</i> = +1.0) fuelled by Stage-1 carry-over of NH<sub>2</sub> (5.2 \u2192 85.7 ppm) and "
  "unburnt NH<sub>3</sub> (21.9 \u2192 8558 ppm) that oxidise in Stage 2 predominantly via HNO + OH \u21c4 H<sub>2</sub>O + NO (24\u00d7 higher at "
  "<i>\u03c6</i><sub>1</sub> = 2.0 than at <i>\u03c6</i><sub>1</sub> = 1.0) and NH + O<sub>2</sub> \u21c4 NO + OH. Third, decoupling stage residence times "
  "(<i>\u03c4</i><sub>1</sub> \u2260 <i>\u03c4</i><sub>2</sub>) shows that a longer, rather than shorter, rich primary residence time reduces NH<sub>2</sub> "
  "carry-over (from 282 to 157 ppm at <i>\u03c6</i><sub>1</sub> = 2.0 across <i>\u03c4</i><sub>1</sub> = 10 \u2192 50 ms) and lowers final NO<sub>x</sub>; replacing "
  "instantaneous secondary mixing (<i>N</i> = 1) with five progressive dilution stages (<i>N</i> = 5) cuts right-branch NO<sub>x</sub> at "
  "<i>\u03c6</i><sub>1</sub> = 2.0 from 3693 to 433 ppm (\u221288.3%, Friedman <i>p</i> = 1.67 \u00d7 10<sup>\u22125</sup>) by sustaining in-situ thermal "
  "de-NO<sub>x</sub> before lean burnout. Fourth, under realistic gas-turbine regimes, elevating pressure from 1 to 30 atm shifts "
  "the low-NO<sub>x</sub> valley from <i>\u03c6</i><sub>1</sub> = 1.3 to 1.1, collapses U-curve variance by 73.7% (Levene <i>p</i> = 0.0125), and "
  "increases the NO<sub>2</sub>/NO<sub>x</sub> ratio 6.6-fold (<i>\u03c1</i> = 0.988, <i>p</i> = 3.14 \u00d7 10<sup>\u221244</sup>); compressor-discharge preheat "
  "(300 \u2192 750 K) raises mean NO<sub>x</sub> linearly by 6.1 ppm K<sup>\u22121</sup>; and liner wall cooling (<i>U</i> = 3000 W m<sup>\u22122</sup> K<sup>\u22121</sup>) cuts "
  "NO<sub>x</sub> by 386 ppm on average (paired <i>p</i> = 2.04 \u00d7 10<sup>\u22126</sup>) while maintaining complete burnout (NH<sub>3</sub> slip < 0.07 ppm). "
  "All simulations are zero-dimensional and mechanism-specific, offering quantitative architectural guidance rather than "
  "burner-resolved CFD predictions.")
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
    ["PSR", "Perfectly stirred reactor"],
    ["RQL", "Rich\u2013quench\u2013lean combustion architecture"],
    ["ROP", "Rate of production"],
    ["ANOVA", "Analysis of variance"],
    ["CI", "Confidence interval (95% non-parametric bootstrap)"],
    ["CFD", "Computational fluid dynamics"],
    ["PFR / PaSR", "Plug-flow reactor / Partially stirred reactor"],
    ["<i>\u03c6</i>, <i>\u03c6</i><sub>1</sub>", "Overall equivalence ratio (fixed at 0.9) and primary-stage equivalence ratio (1.0\u20132.0)"],
    ["<i>x</i><sub>NH3</sub>, <i>x</i><sub>H2</sub>", "Inlet fuel mole fractions of NH<sub>3</sub> and H<sub>2</sub> (<i>x</i><sub>H2</sub> = 1 \u2212 <i>x</i><sub>NH3</sub>)"],
    ["<i>\u03c4</i>, <i>\u03c4</i><sub>1</sub>, <i>\u03c4</i><sub>2</sub>", "Nominal, primary-stage, and secondary-stage reactor residence times (ms)"],
    ["<i>N</i>", "Number of progressive secondary-air dilution stages (1, 3, or 5)"],
    ["NO<sub>x</sub>", "Sum of nitric oxide and nitrogen dioxide mole fractions, NO + NO<sub>2</sub> (ppm)"],
    ["<i>T</i><sub>in</sub>, <i>T</i><sub>1</sub>, <i>T</i><sub>final</sub>", "Inlet, Stage-1 outlet, and Stage-2 outlet temperatures (K)"],
    ["<i>P</i>", "Combustor operating pressure (atm)"],
    ["<i>U</i>, <i>A</i>", "Liner wall heat-transfer coefficient (W m<sup>\u22122</sup> K<sup>\u22121</sup>) and surface area (m<sup>2</sup>)"],
    ["<i>\u03b7</i><sup>2</sup>, partial <i>R</i><sup>2</sup>", "One-way main-effect variance fraction and Type-II ANOVA variance share"],
    ["<i>d</i><sub>z</sub>", "Cohen\u2019s paired standardised effect size"],
], columns=["Symbol / Acronym", "Meaning"]), "Nomenclature, symbols, and acronyms used throughout the report.", fs=9.5, widths=[4.2, 11.8])
PB()

# ================================================================ CHAPTER 1
H("Chapter 1: Introduction", 1)
H("1.1 Introduction", 2)
J("This chapter establishes the engineering motivation for staged ammonia\u2013hydrogen (NH<sub>3</sub>/H<sub>2</sub>) combustion, summarises "
  "the foundation and limitations of the mid-semester study, defines the end-semester research objectives and questions, "
  "and outlines the structure of the remainder of the thesis.")

H("1.2 Motivation and Mid-Semester Foundation", 2)
J("Ammonia is a leading carbon-free chemical hydrogen carrier and zero-carbon gas-turbine fuel because it liquefies at "
  "moderate pressure and leverages global agricultural transport infrastructure [1]. However, practical ammonia combustion "
  "faces two coupled kinetic hurdles: (i) low chemical reactivity, narrow flammability limits, and slow flame propagation "
  "relative to hydrocarbons, and (ii) fuel-bound nitrogen chemistry that converts NH<sub>3</sub> directly into nitrogen oxides "
  "(NO<sub>x</sub> = NO + NO<sub>2</sub>) even at moderate flame temperatures [1, 2]. Blending H<sub>2</sub> into NH<sub>3</sub> accelerates radical pool "
  "growth and stabilises oxidation, while rich\u2013quench\u2013lean (RQL) air staging suppresses NO<sub>x</sub> by reacting the fuel first in "
  "an oxygen-lean primary zone before burning out residuals in a lean secondary zone [3\u20135].")
J("The mid-semester study constructed a two-stage ideal-gas perfectly stirred reactor (PSR) network in Cantera [6] using the "
  "Tamaoki et al. (2024) NH<sub>3</sub>/H<sub>2</sub> kinetic mechanism [7] and evaluated a 605-point factorial grid over fuel composition "
  "(<i>x</i><sub>NH3</sub> = 0.0\u20131.0), primary equivalence ratio (<i>\u03c6</i><sub>1</sub> = 1.0\u20132.0), and shared residence time (<i>\u03c4</i> = 20\u2013100 ms) at "
  "overall <i>\u03c6</i> = 0.9, 300 K, and 1 atm (586 converged points). While that map showed that fuel blend governs final "
  "temperature (<i>\u03b7</i><sup>2</sup> = 0.981), <i>\u03c6</i><sub>1</sub> governs Stage-2 temperature rise (<i>\u03b7</i><sup>2</sup> = 0.993), and NO<sub>x</sub> forms a "
  "strongly non-monotonic U-shaped curve against <i>\u03c6</i><sub>1</sub>, four critical limitations prevented architectural conclusions:")
B(["No single-stage baseline existed on the same operating grid, leaving the quantitative NO<sub>x</sub> benefit of staging unproven.",
   "No elementary rate-of-production (ROP) or reaction-pathway flux analysis was performed, leaving the mechanism behind the "
   "non-monotonic U-shaped NO<sub>x</sub> curve inferred rather than demonstrated.",
   "Equal stage residence times (<i>\u03c4</i><sub>1</sub> = <i>\u03c4</i><sub>2</sub>) and instantaneous secondary air mixing omitted real combustor mixing physics.",
   "Ambient, adiabatic boundary conditions (1 atm, 300 K, <i>U</i> = 0) excluded gas-turbine pressure, preheat, and wall cooling effects."])

H("1.3 Objectives of the End-Semester Study", 2)
B(["<b>Phase 1 \u2014 Baseline Quantification:</b> Simulate an identical-condition single-stage lean PSR baseline across all fuel "
   "blends and residence times and quantify the NO<sub>x</sub> reduction and fuel-slip trade-offs of staging.",
   "<b>Phase 2 \u2014 Kinetic Deconstruction:</b> Perform reaction-by-reaction ROP and nitrogen-flux pathway analysis across "
   "<i>\u03c6</i><sub>1</sub> = 1.0\u20132.0 to isolate the exact reactions creating the left branch, valley minimum, and right branch.",
   "<b>Phase 3 \u2014 Reactor Architecture and Mixing Physics:</b> Decouple primary and secondary residence times (<i>\u03c4</i><sub>1</sub> \u2260 <i>\u03c4</i><sub>2</sub>) "
   "and replace instantaneous mixing with progressive <i>N</i>-stage finite-rate secondary air dilution.",
   "<b>Phase 4 \u2014 Gas-Turbine Operating Regimes:</b> Extend the staged network to elevated pressure (1\u201330 atm), compressor-discharge "
   "preheat (300\u2013750 K), and non-adiabatic combustor liner wall heat loss (<i>U</i> = 0\u20133000 W m<sup>\u22122</sup> K<sup>\u22121</sup>).",
   "<b>Statistical Verification:</b> Apply formal hypothesis tests, effect sizes, and bootstrap confidence intervals (CIs) "
   "across all phases to test consistency and interaction structure.",
   "<b>Reproducibility:</b> Consolidate all Python simulation modules, datasets, figures, and this report builder into a "
   "version-controlled repository."], numbered=True)

H("1.4 Research Questions", 2)
B(["By how much, and across which fuel blends and staging windows, does two-stage combustion outperform single-stage combustion?",
   "Which elementary reactions and inter-stage nitrogen radical carry-over species produce the U-shaped NO<sub>x</sub> curve?",
   "Does shortening rich primary residence time <i>\u03c4</i><sub>1</sub> suppress intermediate carry-over, or does a longer rich zone help?",
   "How strongly does finite-rate progressive secondary air dilution mitigate the right-branch NO<sub>x</sub> penalty?",
   "How do gas-turbine pressure, inlet air preheat, and liner cooling shift the minimum-NO<sub>x</sub> <i>\u03c6</i><sub>1</sub> operating point?",
   "Which observed effects remain statistically significant across operating regimes, and where do opposing interactions mask main effects?"], numbered=True)

H("1.5 Organisation of the Report", 2)
J("Chapter 2 reviews the ammonia combustion kinetics and nitrogen-chemistry literature that motivate the mechanism and "
  "diagnostics. Chapter 3 formulates the governing equations, architectural extensions, ROP diagnostics, simulation campaigns, "
  "and statistical methods. Chapter 4 presents the Phase 1 single-stage baseline comparison and Phase 2 kinetic ROP/pathway "
  "analysis. Chapter 5 investigates Phase 3 residence-time decoupling and finite-rate mixing alongside Phase 4 gas-turbine "
  "pressure, preheat, and wall heat-loss regimes. Chapter 6 establishes formal statistical significance across all phases and "
  "synthesises an integrated combustor design window. Chapter 7 summarises the conclusions and future research directions.")

H("1.6 Conclusion", 2)
J("The end-semester investigation transforms the mid-semester parametric grid into a complete combustion engineering study "
  "by introducing an explicit baseline, elementary kinetic proof, realistic reactor mixing physics, gas-turbine conditions, "
  "and rigorous statistical verification. Chapter 2 now places these modelling choices in the context of existing NH<sub>3</sub>/H<sub>2</sub> "
  "combustion literature.")
PB()

# ================================================================ CHAPTER 2
H("Chapter 2: Literature Survey", 1)
H("2.1 Introduction", 2)
J("This chapter reviews prior experimental and chemical-kinetic studies of ammonia oxidation, fuel-bound NO<sub>x</sub> chemistry, "
  "and PSR network modelling. Section 2.2 covers ammonia oxidation branching, Section 2.3 summarises NO formation and thermal "
  "de-NO<sub>x</sub> reduction pathways, Section 2.4 reviews zero-dimensional reactor-network modelling for combustor realism, and "
  "Section 2.5 defines the specific modelling gap resolved by this project.")

H("2.2 Ammonia Oxidation Kinetics", 2)
J("Comprehensive reviews by Kobayashi et al. [1] and Glarborg et al. [2] establish that ammonia oxidation proceeds primarily "
  "through hydrogen abstraction (NH<sub>3</sub> + OH/H/O \u21c4 NH<sub>2</sub> + H<sub>2</sub>O/H<sub>2</sub>/OH) rather than unimolecular bond scission. "
  "Because NH<sub>3</sub> reaction rates are substantially slower than those of H<sub>2</sub> or CH<sub>4</sub>, pure ammonia flames exhibit low laminar "
  "burning velocities and high ignition temperatures [1, 8]. Blending H<sub>2</sub> supplies reactive H, O, and OH radicals that accelerate "
  "NH<sub>3</sub> initiation and expand lean blow-off margins.")
J("Tamaoki et al. [7] investigated NH<sub>3</sub> oxidation across fuel-lean to fuel-rich conditions in flow reactors and constructed "
  "a 33-species, 228-reaction mechanism refined from earlier Zhang and Otomo models. They demonstrated that model-to-model "
  "discrepancies originate largely from NH<sub>2</sub> radical branching at intermediate temperatures\u2014specifically competition between "
  "chain-carrying NH<sub>2</sub> + HO<sub>2</sub> steps, radical-recombination NH<sub>2</sub> + NH<sub>2</sub> hydrogen-forming steps, and NO-reducing channels. "
  "Their validated mechanism (<code>TamaokiNH3.yaml</code>) is used directly in this work.")

H("2.3 Fuel-Bound Nitrogen Chemistry and Thermal DeNOx", 2)
J("Miller and Bowman [3] showed that when fuel contains chemically bound nitrogen, NO<sub>x</sub> formation is dominated by fast "
  "fuel-N radical pathways (NH<sub>2</sub> \u2192 NH \u2192 HNO/N \u2192 NO) rather than solely by high-temperature Zeldovich N<sub>2</sub> fixation. "
  "Crucially, under moderately fuel-rich conditions, amine radicals also selectively reduce NO back to molecular N<sub>2</sub> via "
  "the thermal de-NO<sub>x</sub> reactions NH<sub>2</sub> + NO \u21c4 H<sub>2</sub>O + N<sub>2</sub>, NH<sub>2</sub> + NO \u21c4 NNH + OH, and NH + NO \u21c4 N<sub>2</sub> + OH / H + N<sub>2</sub>O [4, 5]. "
  "As documented by Glarborg et al. [4] and shock-tube measurements by Song et al. [5], the balance between NO oxidation "
  "(HNO + OH, NH + O<sub>2</sub>, N + O<sub>2</sub>) and NO reduction depends strongly on temperature, O<sub>2</sub> availability, and radical residence time.")

H("2.4 Reactor-Network Modelling and Combustor Realism", 2)
J("Cantera provides a validated thermodynamic and chemical-kinetic framework for zero-dimensional PSR networks [6]. While "
  "two-stage PSR models capture rich\u2013lean chemical staging at a fraction of the cost of multidimensional computational fluid "
  "dynamics (CFD), standard idealised models omit three physical features present in practical gas turbines: unequal primary "
  "and secondary residence times, finite-rate turbulent dilution of secondary air (approximated in chemical reactor networks "
  "by progressive multi-stage injection or plug-flow mixing), and elevated pressure, compressor-discharge preheat, and wall "
  "heat transfer [1, 2].")

H("2.5 Research Gap Addressed", 2)
J("Existing literature establishes NH<sub>3</sub>/H<sub>2</sub> mechanism chemistry and qualitative RQL principles, but lacks an integrated, "
  "reproducible study linking (i) baseline-controlled staging benefits across full fuel-blend maps, (ii) elementary ROP proof "
  "of the NO<sub>x</sub> U-curve and inter-stage amine carry-over, (iii) architectural decoupling of stage residence times and "
  "progressive secondary air dilution, (iv) gas-turbine pressure/preheat/wall-cooling shifts, and (v) formal statistical "
  "significance across every phase.")

H("2.6 Conclusion", 2)
J("The reviewed kinetics highlight a clear mechanistic competition between HNO/NH oxidation and NH<sub>2</sub>/NH thermal de-NO<sub>x</sub>. "
  "Chapter 3 translates these physical principles into exact Cantera PSR network formulations, diagnostic equations, and "
  "statistical tests.")
PB()

# ================================================================ CHAPTER 3
H("Chapter 3: Problem Formulation and Numerical Methodology", 1)
H("3.1 Introduction", 2)
J("This chapter presents the mathematical formulation and computational methodology used across all phases of the project. "
  "Section 3.2 defines fuel stoichiometry and stage-wise air splitting; Section 3.3 formulates the baseline two-stage PSR, "
  "decoupled residence times, and progressive dilution networks; Section 3.4 incorporates gas-turbine pressure, preheat, and "
  "liner heat loss; Section 3.5 defines ROP and nitrogen-flux diagnostics; Section 3.6 summarises all simulation campaigns "
  "and solver verification; Section 3.7 defines the statistical significance tests; and Section 3.8 notes modelling limitations.")

H("3.2 Fuel Composition and Air Allocation", 2)
J("The fuel blend is defined on a molar basis by ammonia mole fraction <i>x</i><sub>NH3</sub> \u2208 [0, 1] and hydrogen mole fraction:")
eq_fuel = EQ("<i>x</i><sub>H2</sub> = 1 \u2212 <i>x</i><sub>NH3</sub>")
J(f"Per mole of binary fuel using {eq_fuel}, complete oxidation to N<sub>2</sub> and H<sub>2</sub>O requires "
  "<i>O</i><sub>2,stoic</sub> = 0.75<i>x</i><sub>NH3</sub> + 0.50<i>x</i><sub>H2</sub> moles of O<sub>2</sub>. Using standard dry air "
  "(O<sub>2</sub>:N<sub>2</sub> = 1:3.76), the stoichiometric, primary, total, and secondary air moles follow "
  "from the fixed overall equivalence ratio (<i>\u03c6</i> = 0.9) and primary equivalence ratio (<i>\u03c6</i><sub>1</sub> \u2208 [1.0, 2.0]):")
eq_a1 = EQ("<i>A</i><sub>stoic</sub> = 4.76(0.75<i>x</i><sub>NH3</sub> + 0.50<i>x</i><sub>H2</sub>),   <i>A</i><sub>1</sub> = <i>A</i><sub>stoic</sub> / <i>\u03c6</i><sub>1</sub>,   <i>A</i><sub>total</sub> = <i>A</i><sub>stoic</sub> / <i>\u03c6</i>")
eq_a2 = EQ("<i>A</i><sub>2</sub> / <i>A</i><sub>total</sub> = 1 \u2212 <i>\u03c6</i> / <i>\u03c6</i><sub>1</sub>")
J(f"As defined in {eq_a1}\u2013{eq_a2}, increasing <i>\u03c6</i><sub>1</sub> from 1.0 to 2.0 at fixed <i>\u03c6</i> = 0.9 monotonically shifts the secondary air fraction "
  f"from 10% to 55% of total combustor air. This air redistribution is plotted in Figure {{FIG_AIR}}.")
fig_air = FIGURE(MID_IMG / "image1.png", "Air redistribution between primary and secondary stages as a function of primary equivalence ratio <i>\u03c6</i><sub>1</sub> at fixed overall <i>\u03c6</i> = 0.9.", 11.0)

H("3.3 Two-Stage PSR Network and Architectural Extensions", 2)
J("Each PSR stage is solved as a constant-pressure, spatially uniform control volume of nominal volume <i>V</i> = 1.0 m<sup>3</sup> "
  "governed by the transient species mass conservation equation and mass flow relation:")
eq_psr = EQ("d(<i>mY</i><sub>k</sub>)/d<i>t</i> = <i>\u1e41</i>(<i>Y</i><sub>k,in</sub> \u2212 <i>Y</i><sub>k</sub>) + <i>V\u03c9\u0307</i><sub>k</sub><i>W</i><sub>k</sub>,   <i>\u1e41</i> = <i>m</i> / <i>\u03c4</i>")
J(f"where <i>m</i> is reactor gas mass, <i>Y</i><sub>k</sub> is species mass fraction, <i>\u1e41</i> is mass flow rate controlled via {eq_psr}, <i>\u03c9\u0307</i><sub>k</sub> is molar "
  "production rate, and <i>W</i><sub>k</sub> is molar mass. Rather than relying on steady-state Newton iteration, each PSR is integrated "
  "transiently from an equilibrated (Stage 1) or mixed (Stage 2) state until relative changes in temperature and all species "
  "fall below 10<sup>\u22128</sup> after at least 5 nominal residence times (capped at 100<i>\u03c4</i>). Stage 1 products pass unaltered to Stage 2, "
  "where secondary air is injected (Figure {{FIG_NET}}).")
fig_net = FIGURE(MID_IMG / "image2.png", "Schematic of the two-stage perfectly stirred reactor network showing inter-stage species transfer.", 12.0)
J("Three architectural variants were built on this core:")
B(["<b>Phase 1 Single-Stage Baseline:</b> Fuel and total air (<i>\u03c6</i> = 0.9) react directly in one PSR evaluated both at matched "
   "single-stage residence time <i>\u03c4</i> (20\u2013100 ms) and matched total combustor residence time <i>\u03c4</i><sub>equiv</sub> = 2<i>\u03c4</i> (40\u2013200 ms).",
   "<b>Phase 3a Decoupled Residence Times:</b> Stage 1 and Stage 2 receive independent residence times <i>\u03c4</i><sub>1</sub> \u2208 [10, 50] ms "
   "and <i>\u03c4</i><sub>2</sub> \u2208 [20, 100] ms (total <i>\u03c4</i><sub>total</sub> = <i>\u03c4</i><sub>1</sub> + <i>\u03c4</i><sub>2</sub>, ratio <i>\u03c4</i><sub>1</sub>/<i>\u03c4</i><sub>2</sub>).",
   "<b>Phase 3b Progressive Finite-Rate Dilution:</b> Instead of instantaneous addition (<i>N</i> = 1), secondary air <i>A</i><sub>2</sub> is split "
   "equally into <i>N</i> \u2208 {1, 3, 5} parcels \u0394<i>A</i> = <i>A</i><sub>2</sub>/<i>N</i>, each entering a sub-stage PSR of residence time "
   "<i>\u03c4</i><sub>sub</sub> = <i>\u03c4</i><sub>2</sub>/<i>N</i> to approximate sequential secondary air jet mixing."])

H("3.4 Gas-Turbine Regimes and Wall Heat Loss", 2)
J("Phase 4 generalises the two-stage network to arbitrary operating pressure <i>P</i> (1\u201330 atm), compressor-discharge inlet "
  "temperature <i>T</i><sub>in</sub> (300\u2013750 K), and convective/effusion liner wall heat loss using Cantera\u2019s <code>Wall</code> object on each reactor:")
eq_wall = EQ("<i>Q\u0307</i><sub>wall</sub> = <i>UA</i>(<i>T</i> \u2212 <i>T</i><sub>wall</sub>)")
J(f"where heat transfer obeys {eq_wall} with <i>U</i> \u2208 [0, 3000] W m<sup>\u22122</sup> K<sup>\u22121</sup>, wall surface area <i>A</i> = 0.25 m<sup>2</sup>, and wall temperature fixed at <i>T</i><sub>wall</sub> = <i>T</i><sub>in</sub>.")

H("3.5 Rate-of-Production and Pathway Diagnostics", 2)
J("At each converged stage state (<i>x</i><sub>NH3</sub> = 0.50, <i>\u03c4</i> = 60 ms, <i>\u03c6</i><sub>1</sub> = 1.0\u20132.0), Cantera evaluates the net rate of progress "
  "<i>q</i><sub>net,<i>i</i></sub> for every elementary reaction <i>i</i>. The NO production contribution of reaction <i>i</i> is computed as:")
eq_rop = EQ("<i>C</i><sub>NO,<i>i</i></sub> = (<i>\u03bd</i>\u2033<sub>NO,<i>i</i></sub> \u2212 <i>\u03bd</i>\u2032<sub>NO,<i>i</i></sub>) <i>q</i><sub>net,<i>i</i></sub>   [kmol m<sup>\u22123</sup> s<sup>\u22121</sup>]")
J(f"Recording all NO-participating reactions via {eq_rop} avoids filtering biases and yields exact NO source/sink rankings. "
  "In addition, element-\u2018N\u2019 <code>ReactionPathDiagram</code> graphs are generated with normalised flux scaling (<code>scale = -1</code>, threshold = 2% "
  "of peak stage nitrogen flux) and rendered with Graphviz <code>dot</code> so both rich primary pyrolysis and lean burnout fluxes are resolved.")
J("The principal performance and emission metrics reported across chapters are defined by (7)\u2013(8):")
eq_met = EQ("NO<sub>x</sub> = NO + NO<sub>2</sub>,   <i>\u0394T</i> = <i>T</i><sub>2</sub> \u2212 <i>T</i><sub>1</sub>,   <i>\u0394</i>NO<sub>x</sub> = NO<sub>x,2</sub> \u2212 NO<sub>x,1</sub>")
eq_ben = EQ("Staging benefit (%) = 100 (NO<sub>x,single</sub> \u2212 NO<sub>x,staged</sub>) / NO<sub>x,single</sub>")

H("3.6 Computational Campaigns and Verification", 2)
J("All simulations run in Python with Cantera 3.0 and <code>mechanisms/TamaokiNH3.yaml</code> (33 species, 228 reactions) [6, 7]. "
  "Table {{TAB_MOD}} lists the repository software modules, and Table {{TAB_CAMP}} summarises the eight computational campaigns.")
tab_mod = TABLE(pd.DataFrame([
    ["<code>double_stage/staged_combustion.py</code>", "Core two-stage PSR, decoupled <i>\u03c4</i>, finite dilution (<i>N</i> stages), and gas-turbine regimes"],
    ["<code>single_stage/single_stage_baseline.py</code>", "Phase 1 single-stage PSR baseline sweep and matched comparison datasets/plots"],
    ["<code>double_stage/rate_of_production_analysis.py</code>", "Phase 2 elementary NO ROP extraction and normalised N-pathway Graphviz diagrams"],
    ["<code>double_stage/decoupled_mixing_analysis.py</code>", "Phase 3 decoupled (<i>\u03c4</i><sub>1</sub>, <i>\u03c4</i><sub>2</sub>) 2D grid and <i>N</i>-stage finite-mixing engine"],
    ["<code>double_stage/gas_turbine_regimes_analysis.py</code>", "Phase 4 elevated pressure, preheat, and wall heat-loss sweeps"],
    ["<code>double_stage/statistical_significance_analysis.py</code>", "47-test statistical inference suite (ANOVA, paired tests, bootstrap CIs)"],
    ["<code>docs/reports/build_end_semester_report.py</code>", "Automated end-semester report generator reading directly from committed CSVs"],
], columns=["Module", "Responsibility"]), "Repository software modules created and maintained in the study.", fs=8.8, widths=[6.8, 9.2])

tab_camp = TABLE(pd.DataFrame([
    ["Main 605-case", "<i>x</i><sub>NH3</sub> 0\u20131 (11), <i>\u03c6</i><sub>1</sub> 1.0\u20132.0 (11), <i>\u03c4</i> 20\u2013100 ms (5)", "300 K, 1 atm, <i>U</i> = 0", "605 (586 converged)"],
    ["Phase 1 Baseline", "<i>x</i><sub>NH3</sub> 0\u20131 (11), <i>\u03c4</i> 20\u2013200 ms (8)", "300 K, 1 atm, <i>\u03c6</i> = 0.9", "88 single; 469 matched"],
    ["Phase 2 ROP", "<i>\u03c6</i><sub>1</sub> 1.0\u20132.0 (11), Stage 1 & Stage 2", "<i>x</i><sub>NH3</sub> = 0.5, <i>\u03c4</i> = 60 ms", "11 (1606 rxn rows)"],
    ["Phase 3a Decoupled <i>\u03c4</i>", "<i>\u03c6</i><sub>1</sub> \u2208 {1.2,1.4,1.6,1.8,2.0}, <i>\u03c4</i><sub>1</sub> 10\u201350, <i>\u03c4</i><sub>2</sub> 20\u2013100 ms", "<i>x</i><sub>NH3</sub> = 0.5, 300 K, 1 atm", "125 (100% converged)"],
    ["Phase 3b Mixing", "<i>\u03c6</i><sub>1</sub> 1.0\u20132.0 (11), <i>N</i> \u2208 {1, 3, 5}", "<i>\u03c4</i><sub>1</sub> = 30, <i>\u03c4</i><sub>2</sub> = 60 ms", "33 (100% converged)"],
    ["Phase 4a Pressure", "<i>\u03c6</i><sub>1</sub> 1.0\u20132.0 (11), <i>P</i> \u2208 {1, 5, 10, 20, 30} atm", "<i>x</i><sub>NH3</sub> = 0.5, <i>T</i><sub>in</sub> = 300 K", "55 (100% converged)"],
    ["Phase 4b Preheat", "<i>\u03c6</i><sub>1</sub> (7 levels), <i>T</i><sub>in</sub> \u2208 {300, 450, 600, 750} K", "<i>x</i><sub>NH3</sub> = 0.5, 10 atm", "28 (100% converged)"],
    ["Phase 4c Heat Loss", "<i>\u03c6</i><sub>1</sub> (7 levels), <i>U</i> \u2208 {0, 500, 1500, 3000} W m<sup>\u22122</sup> K<sup>\u22121</sup>", "15 atm, 650 K", "28 (100% converged)"],
], columns=["Campaign", "Varied Parameters", "Fixed Conditions", "Cases"]), "Summary of computational simulation campaigns (all at overall <i>\u03c6</i> = 0.9).", fs=8.5, widths=[2.7, 6.4, 3.6, 3.3])
J(f"Overall equivalence ratio across converged main-study cases is preserved to a maximum absolute error of 1.11 \u00d7 10<sup>\u221216</sup>. "
  f"As shown in Table {tab_camp}, every Phase 1\u20134 extension converged 100%, and <i>\u03c4</i><sub>1</sub> = <i>\u03c4</i><sub>2</sub> and <i>N</i> = 1 slices recover the "
  "instantaneous baseline formulation exactly.")

H("3.7 Statistical Significance Framework", 2)
J("Because Cantera PSR integrations are deterministic, statistical significance here tests whether an observed effect is too "
  "large and systematic across the sampled operating grid to arise from random fluctuation across other operating factors. "
  "Four complementary inferential methods are used in <code>double_stage/statistical_significance_analysis.py</code>:")
B(["<b>Type-II ANOVA Partial <i>F</i>-Tests:</b> Ordinary least-squares regression with categorical factor dummies isolates the "
   "unique partial <i>R</i><sup>2</sup> contribution and <i>F</i>-statistic of each factor on factorial grids.",
   "<b>Paired Parametric and Non-Parametric Tests:</b> Matched-condition comparisons (single-stage vs. staged, <i>N</i> = 1 vs. 3 vs. 5, "
   "adiabatic vs. cooled, 1 vs. 30 atm) use paired <i>t</i>-tests, Cohen\u2019s <i>d</i><sub>z</sub>, rank-based Wilcoxon signed-rank tests [9] "
   "(robust to right-skewed NO<sub>x</sub> differences), and two-sided binomial sign tests.",
   "<b>Monotonic Rank and Variance-Collapse Tests:</b> Per-<i>\u03c6</i><sub>1</sub> Spearman rank correlations <i>\u03c1</i> (exact permutation "
   "<i>p</i> = 2/<i>n</i>! when |<i>\u03c1</i>| = 1, or exact sign test across levels), Friedman repeated-measures tests across <i>N</i>, "
   "and Levene\u2019s test for spread collapse under high pressure.",
   "<b>Non-Parametric Bootstrap CIs:</b> 10 000 resamples (fixed seed = 42) yield 95% percentile CIs [10]."])

H("3.8 Limitations of the Modelling Framework", 2)
B(["Zero-dimensional PSRs neglect spatial temperature gradients, flame front propagation, and turbulence\u2013chemistry interactions.",
   "Only one kinetic mechanism (Tamaoki et al., 2024) was used; kinetic parameter uncertainty was not propagated.",
   "Phases 2\u20134 focus on the equimolar 50% NH<sub>3</sub> / 50% H<sub>2</sub> blend; blend sensitivity of Phases 3\u20134 remains future work.",
   "Nineteen main-study cases (3.1%) did not converge within 100<i>\u03c4</i> and are excluded, leaving 469 matched Phase 1 pairs."])

H("3.9 Conclusion", 2)
J("Chapter 3 established the governing conservation relations, reactor extensions for Phases 1\u20134, complete ROP/pathway "
  "diagnostics, and statistical testing protocol. Chapter 4 applies this framework to quantify the staging advantage against "
  "a single-stage baseline and resolve the chemical origin of the NO<sub>x</sub> U-curve.")
PB()

# ================================================================ CHAPTER 4
H("Chapter 4: Baseline Quantification and Chemical Kinetic Pathway Analysis", 1)
H("4.1 Introduction", 2)
J("This chapter presents the first two major end-semester contributions: quantifying the exact NO<sub>x</sub> reduction benefit of "
  "air staging relative to an identical-condition single-stage combustor (Phase 1), and resolving the elementary chemical "
  "reactions and nitrogen-flux pathways responsible for the non-monotonic U-shaped NO<sub>x</sub> profile (Phase 2). Section 4.2 "
  "recaps the mid-semester reference trends, Section 4.3 analyses the Phase 1 baseline comparison, Section 4.4 decomposes "
  "the Stage-1 and Stage-2 ROP rates, Section 4.5 examines the Graphviz nitrogen pathway diagrams, and Section 4.6 concludes.")

H("4.2 Mid-Semester 605-Case Parametric Reference", 2)
J("Across the 586 converged mid-semester cases, final temperature spans 1908.5\u20132349.0 K and falls monotonically by 404.4 K "
  "(2334.7 \u2192 1930.4 K) as fuel shifts from pure H<sub>2</sub> to pure NH<sub>3</sub> (Figure {{FIG_MTEMP}}). Final NO<sub>x</sub> spans 891.4\u20136771.5 ppm "
  "(mean 2569.7 ppm) and exhibits a distinct U-shaped minimum near <i>\u03c6</i><sub>1</sub> = 1.2\u20131.3 (mean 1676.6 ppm at <i>\u03c6</i><sub>1</sub> = 1.2 vs. "
  "3772.8 ppm at <i>\u03c6</i><sub>1</sub> = 1.0 and 3390.3 ppm at <i>\u03c6</i><sub>1</sub> = 2.0, Figure {{FIG_MU}}). As Table {{TAB_ETA}} summarises, main-effect "
  "<i>\u03b7</i><sup>2</sup> shows that fuel composition controls <i>T</i><sub>final</sub> (98.1%) and H<sub>2</sub> slip (90.7%), <i>\u03c6</i><sub>1</sub> controls Stage-2 <i>\u0394T</i> (99.3%), "
  "and both parameters jointly govern final NO<sub>x</sub> (Figure {{FIG_MNMAP}}).")
fig_mtemp = FIGURE(MID_IMG / "image3.png", "Mid-semester reference: final PSR temperature versus NH<sub>3</sub> mole fraction at <i>\u03c4</i> = 60 ms.", 11.0)
fig_mu = FIGURE(MID_IMG / "image6.png", "Mid-semester reference: mean final NO<sub>x</sub> versus primary equivalence ratio <i>\u03c6</i><sub>1</sub> showing the U-shaped response.", 11.0)
fig_mnmap = FIGURE(MID_IMG / "image10.png", "Mid-semester reference: 2D final NO<sub>x</sub> contour map over NH<sub>3</sub> fraction and <i>\u03c6</i><sub>1</sub> at <i>\u03c4</i> = 60 ms.", 11.0)
tab_eta = TABLE(pd.DataFrame([
    ["<i>T</i><sub>final</sub> (K)", "98.1%", "0.6%", "0.4%"],
    ["NO<sub>x</sub> (ppm)", "18.6%", "25.4%", "2.8%"],
    ["NH<sub>3</sub> slip (ppm)", "31.3%", "14.7%", "3.9%"],
    ["H<sub>2</sub> slip (ppm)", "90.7%", "3.1%", "2.9%"],
    ["<i>\u0394T</i> (K)", "0.3%", "99.3%", "0.0%"],
    ["<i>\u0394</i>NO<sub>x</sub> (ppm)", "33.2%", "48.0%", "0.2%"],
], columns=["Response", "<i>x</i><sub>NH3</sub> <i>\u03b7</i><sup>2</sup>", "<i>\u03c6</i><sub>1</sub> <i>\u03b7</i><sup>2</sup>", "<i>\u03c4</i> <i>\u03b7</i><sup>2</sup>"]),
    "Mid-semester main-effect variance fractions (<i>\u03b7</i><sup>2</sup>) over 586 converged cases.", widths=[4.0, 4.0, 4.0, 4.0])

H("4.3 Single-Stage Baseline and Quantified Staging Benefit (Phase 1)", 2)
J("To isolate the benefit of two-stage combustion, 88 single-stage lean PSR cases (<i>\u03c6</i> = 0.9) were simulated across all 11 "
  "fuel blends and 8 residence times (matching both stage <i>\u03c4</i> and total combustor residence time 2<i>\u03c4</i>). Merging against the "
  "converged two-stage dataset yields 469 matched pairs (Table {{TAB_B1}}).")
g = cmp_.groupby("NH3_frac").agg(single=("NOx_single_ppm", "mean"), staged=("NOx_ppm", "mean"),
                                 red=("NOx_reduction_pct", "mean"), mx=("NOx_reduction_pct", "max"),
                                 mn=("NOx_reduction_pct", "min"), n=("NOx_ppm", "size")).reset_index()
t1 = pd.DataFrame({
    "<i>x</i><sub>NH3</sub>": g.NH3_frac.round(1),
    "Pairs (<i>n</i>)": g.n,
    "Single-stage NO<sub>x</sub> (ppm)": g.single.round(0).astype(int),
    "Staged NO<sub>x</sub> (ppm)": g.staged.round(0).astype(int),
    "Mean cut (%)": g.red.round(1),
    "Best (%)": g.mx.round(1),
    "Worst (%)": g.mn.round(1),
})
tab_b1 = TABLE(t1, "Single-stage vs. two-stage NO<sub>x</sub> emissions by fuel blend (averaged over matched <i>\u03c6</i><sub>1</sub> and <i>\u03c4</i>).",
               widths=[1.8, 1.5, 3.1, 2.7, 2.3, 2.2, 2.2])
fig_b1 = FIGURE(PLOTS / "baseline_nox_comparison.png", "Final NO<sub>x</sub> emissions: two-stage staged combustion versus matched single-stage baselines across NH<sub>3</sub> fuel fraction at <i>\u03c4</i> = 60 ms.", 14.0)
fig_b2 = FIGURE(PLOTS / "staging_benefit_heatmap.png", "Two-stage combustion advantage contour map (% NO<sub>x</sub> reduction vs. single-stage baseline) over <i>x</i><sub>NH3</sub> and <i>\u03c6</i><sub>1</sub> at <i>\u03c4</i> = 60 ms.", 14.0)
J(f"Across all 469 matched comparisons, two-stage combustion lowers NO<sub>x</sub> by an average of {cmp_.NOx_reduction_pct.mean():.1f}% "
  f"(median {cmp_.NOx_reduction_pct.median():.1f}%), beating single-stage combustion in {(cmp_.NOx_reduction_pct > 0).sum()} of 469 cases (93.6%). "
  f"As shown in Figure {{FIG_B1}} and Table {{TAB_B1}}, single-stage lean combustion of NH<sub>3</sub>/H<sub>2</sub> peaks above 8300 ppm NO<sub>x</sub> "
  f"at <i>x</i><sub>NH3</sub> = 0.20\u20130.30 because abundant H<sub>2</sub>-derived O/OH radicals rapidly oxidise fuel nitrogen; staging at "
  f"<i>\u03c6</i><sub>1</sub> = 1.6\u20132.0 slashes emissions to ~973\u20131014 ppm (up to 90.4% reduction). Excluding pure H<sub>2</sub> (where no fuel-N exists "
  f"so extra staging residence time generates thermal NO, causing a \u221268.4% penalty at <i>\u03c6</i><sub>1</sub> = 1.0), ammonia-containing blends "
  f"(<i>x</i><sub>NH3</sub> \u2265 0.10) average a 60.1% NO<sub>x</sub> cut. Figure {{FIG_B2}} maps the operational staging window: deep rich staging "
  f"(<i>\u03c6</i><sub>1</sub> \u2248 2.0) remains advantageous for H<sub>2</sub>-rich blends, whereas at high ammonia shares (<i>x</i><sub>NH3</sub> \u2265 0.70) over-rich "
  f"staging enters a penalty corner (\u221247.6% at <i>x</i><sub>NH3</sub> = 0.80, <i>\u03c6</i><sub>1</sub> = 2.0). Figure {{FIG_B3}} confirms that staging "
  f"achieves this NO<sub>x</sub> reduction while simultaneously maintaining lower total unburnt fuel slip than single-stage operation.")
fig_b3 = FIGURE(PLOTS / "baseline_tradeoff_scatter.png", "Pareto trade-off comparison between final NO<sub>x</sub> and unburnt fuel slip (NH<sub>3</sub> + H<sub>2</sub>) for staged and single-stage simulations.", 12.5)

H("4.4 Elementary Rate-of-Production Analysis of the U-Curve (Phase 2)", 2)
J("To uncover why staging exhibits a U-shaped NO<sub>x</sub> profile against <i>\u03c6</i><sub>1</sub> and why NH<sub>3</sub>-rich right-branch cases lose to "
  "single-stage combustion, detailed stage-resolved species and ROP diagnostics were extracted across <i>\u03c6</i><sub>1</sub> = 1.0\u20132.0 at "
  "<i>x</i><sub>NH3</sub> = 0.50 and <i>\u03c4</i> = 60 ms (Table {{TAB_ROP}} and Figure {{FIG_ROP1}}).")
t2 = rop[["Phi_1", "T_stage1_K", "O2_stage1_pct", "NOx_stage1_ppm", "Delta_NOx_ppm", "NOx_stage2_ppm",
          "NH3_stage1_ppm", "NH2_stage1_ppm", "NH_stage1_ppm"]].copy()
t2.columns = ["<i>\u03c6</i><sub>1</sub>", "<i>T</i><sub>1</sub> (K)", "O<sub>2</sub> S1 (%)", "NO<sub>x</sub> S1 (ppm)", "<i>\u0394</i>NO<sub>x</sub> S2 (ppm)",
              "NO<sub>x</sub> final (ppm)", "NH<sub>3</sub> out S1 (ppm)", "NH<sub>2</sub> out S1 (ppm)", "NH out S1 (ppm)"]
for c in t2.columns[1:]:
    t2[c] = t2[c].round(2 if "O<sub>2</sub>" in c else 1)
tab_rop = TABLE(t2, "Stage-resolved temperature, NO<sub>x</sub>, and primary-outlet amine intermediates (<i>x</i><sub>NH3</sub> = 0.50, <i>\u03c4</i> = 60 ms).", fs=8.0)
fig_rop1 = FIGURE(PLOTS / "rop_u_curve_pathway_mechanism.png",
                  "Elementary kinetic decomposition of the NO<sub>x</sub> U-curve: (a) Stage-1 vs. final temperature and NO<sub>x</sub>, (b) amine radical carry-over from Stage 1, and (c) dominant Stage-2 NO elementary reaction rates.", 15.5)
J(f"Table {{TAB_ROP}} and Figure {{FIG_ROP1}}(a) show that the U-shaped final NO<sub>x</sub> curve is the algebraic sum of two opposite "
  f"monotonic trends: Stage-1 NO<sub>x</sub> drops monotonically from 4399.7 ppm (<i>\u03c6</i><sub>1</sub> = 1.0) to 29.2 ppm (<i>\u03c6</i><sub>1</sub> = 2.0) as primary "
  f"temperature falls from 2167.9 K to 1720.2 K, whereas Stage-2 NO<sub>x</sub> generation (<i>\u0394</i>NO<sub>x</sub>) climbs monotonically from "
  f"\u2212190.7 ppm (net destruction) to +3585.8 ppm. Simultaneously, Figure {{FIG_ROP1}}(b) shows Stage-1 outlet carry-over surging: "
  f"NH<sub>2</sub> increases 16.4\u00d7 (5.2 \u2192 85.7 ppm), NH increases 8.3\u00d7 (0.9 \u2192 7.6 ppm), and unburnt NH<sub>3</sub> climbs nearly 400\u00d7 "
  f"(21.9 \u2192 8558.2 ppm). Figure {{FIG_ROP1}}(c) resolves the Stage-2 kinetic competition: while NH<sub>2</sub> + NO \u21c4 H<sub>2</sub>O + N<sub>2</sub> "
  f"and NH<sub>2</sub> + NO \u21c4 NNH + OH destroy NO at rates up to \u22121.36 \u00d7 10<sup>\u22125</sup> and \u22122.28 \u00d7 10<sup>\u22125</sup> kmol m<sup>\u22123</sup> s<sup>\u22121</sup>, "
  f"oxidative branching via HNO + OH \u21c4 H<sub>2</sub>O + NO overwhelms them by more than an order of magnitude (+4.01 \u00d7 10<sup>\u22124</sup> "
  f"kmol m<sup>\u22123</sup> s<sup>\u22121</sup> at <i>\u03c6</i><sub>1</sub> = 2.0, 24\u00d7 its rate at <i>\u03c6</i><sub>1</sub> = 1.0), alongside NH + O<sub>2</sub> \u21c4 NO + OH (>9500\u00d7 higher than at <i>\u03c6</i><sub>1</sub> = 1.0).")

def _top_rx(phi, stage, k=3):
    d = ropr[(ropr.Phi_1.round(2) == phi) & (ropr.Stage == stage)]
    return d.nlargest(k, "NO_contribution_kmol_m3_s"), d.nsmallest(k, "NO_contribution_kmol_m3_s")

rx_rows = []
for phi, stg in [(1.0, "Stage 1"), (1.3, "Stage 1"), (1.3, "Stage 2"), (1.8, "Stage 2"), (2.0, "Stage 2")]:
    pos, neg = _top_rx(phi, stg, k=3)
    for _, r in pos.iterrows():
        rx_rows.append([phi, stg, "NO source", r.Equation, f"{r.NO_contribution_kmol_m3_s:+.2e}"])
    for _, r in neg.iterrows():
        rx_rows.append([phi, stg, "NO sink", r.Equation, f"{r.NO_contribution_kmol_m3_s:+.2e}"])
tab_rxn = TABLE(pd.DataFrame(rx_rows, columns=["<i>\u03c6</i><sub>1</sub>", "Stage", "Role", "Elementary Reaction", "NO Rate (kmol m<sup>\u22123</sup> s<sup>\u22121</sup>)"]),
                "Top NO-producing and NO-consuming elementary reactions across regimes (from complete NO ROP dataset).", fs=8.0,
                widths=[1.3, 1.8, 2.0, 6.9, 4.0])
fig_rop2 = FIGURE(PLOTS / "rop_top_no_reactions_stage1_vs_stage2.png", "Top elementary NO source (blue) and sink (red) reactions in Stage 1 and Stage 2 across the left branch (<i>\u03c6</i><sub>1</sub> = 1.0), valley (1.3), and right branch (1.8).", 15.0)
J(f"Table {{TAB_RXN}} and Figure {{FIG_ROP2}} establish three distinct chemical regimes across <i>\u03c6</i><sub>1</sub>:")
B(["<b>Left Branch (<i>\u03c6</i><sub>1</sub> = 1.0\u20131.2):</b> Near-stoichiometric primary conditions preserve high temperature (2168 K) and "
   "available oxygen, generating 4400 ppm NO<sub>x</sub> inside Stage 1 via N + OH \u21c4 H + NO, HNO + OH \u21c4 H<sub>2</sub>O + NO, and "
   "H + HNO \u21c4 H<sub>2</sub> + NO. Adding 10% secondary air in Stage 2 lowers temperature by 61 K and yields net de-NO<sub>x</sub> (\u2212191 ppm).",
   "<b>DeNOx Valley Minimum (<i>\u03c6</i><sub>1</sub> \u2248 1.2\u20131.4):</b> Moderate richness drops Stage-1 NO<sub>x</sub> by an order of magnitude "
   "(437 ppm at <i>\u03c6</i><sub>1</sub> = 1.3) as NH + NO \u21c4 H + N<sub>2</sub>O, N + NO \u21c4 N<sub>2</sub> + O, and NH<sub>2</sub> + NO \u21c4 NNH + OH / H<sub>2</sub>O + N<sub>2</sub> "
   "convert NO towards N<sub>2</sub>, while amine carry-over remains modest (23.3 ppm NH<sub>2</sub>), limiting final NO<sub>x</sub> to 986.4 ppm.",
   "<b>Right Branch (<i>\u03c6</i><sub>1</sub> \u2265 1.6):</b> Severe oxygen starvation reduces Stage-1 NO<sub>x</sub> below 110 ppm, but leaves large "
   "unburnt NH<sub>3</sub> and NH<sub>2</sub> inventories. Introducing 45\u201355% secondary air in Stage 2 drives vigorous oxidative branching "
   "through HNO + OH \u21c4 H<sub>2</sub>O + NO (+2.34 \u00d7 10<sup>\u22124</sup> at <i>\u03c6</i><sub>1</sub> = 1.8) alongside rapid NO\u2013HONO\u2013NO<sub>2</sub> radical cycling "
   "(H + NO<sub>2</sub> \u21c4 NO + OH vs. NO + OH (+M)), regenerating +2483 to +3586 ppm NO<sub>x</sub>."])

H("4.5 Nitrogen Reaction-Pathway Diagrams", 2)
J("Normalised element-\u2018N\u2019 reaction-pathway graphs (Figure {{FIG_RP1}} through Figure {{FIG_RP4}}) directly visualise how "
  "nitrogen flux topology reorganises across staging regimes.")
fig_rp1 = FIGURE(PLOTS / "reaction_path_phi1_1p0_stage1.png", "Normalised nitrogen reaction-path diagram in Stage 1 at <i>\u03c6</i><sub>1</sub> = 1.0 (left branch; peak flux scale = 0.012 kmol m<sup>\u22123</sup> s<sup>\u22121</sup>).", 10.5)
fig_rp2 = FIGURE(PLOTS / "reaction_path_phi1_1p3_stage1.png", "Normalised nitrogen reaction-path diagram in Stage 1 at <i>\u03c6</i><sub>1</sub> = 1.3 (valley; scale = 0.024 kmol m<sup>\u22123</sup> s<sup>\u22121</sup>).", 8.8)
fig_rp3 = FIGURE(PLOTS / "reaction_path_phi1_1p8_stage1.png", "Normalised nitrogen reaction-path diagram in Stage 1 at <i>\u03c6</i><sub>1</sub> = 1.8 (right branch Stage 1; scale = 0.037 kmol m<sup>\u22123</sup> s<sup>\u22121</sup>).", 9.5)
fig_rp4 = FIGURE(PLOTS / "reaction_path_phi1_1p8_stage2.png", "Normalised nitrogen reaction-path diagram in Stage 2 at <i>\u03c6</i><sub>1</sub> = 1.8 (right branch Stage 2; scale = 4.5 \u00d7 10<sup>\u22124</sup> kmol m<sup>\u22123</sup> s<sup>\u22121</sup>).", 9.2)
J("Comparing Figure {{FIG_RP1}} (<i>\u03c6</i><sub>1</sub> = 1.0), Figure {{FIG_RP2}} (<i>\u03c6</i><sub>1</sub> = 1.3), and Figure {{FIG_RP3}} (<i>\u03c6</i><sub>1</sub> = 1.8) "
  "in Stage 1 reveals a decisive shift in nitrogen routing: at <i>\u03c6</i><sub>1</sub> = 1.0, NO forms through parallel HNO \u2192 NO (0.235) "
  "and N \u2192 NO (0.197) fluxes and cycles through HONO and N<sub>2</sub>O; at <i>\u03c6</i><sub>1</sub> = 1.3, NO reduction to N<sub>2</sub> via "
  "NO \u2192 N<sub>2</sub> (0.136), NO \u2192 N<sub>2</sub>O \u2192 N<sub>2</sub> (0.108), and NNH \u2192 N<sub>2</sub> (0.186) dominates; and at <i>\u03c6</i><sub>1</sub> = 1.8, "
  "oxygen starvation activates bimolecular N\u2013N coupling (NH<sub>2</sub>/NH \u2192 N<sub>2</sub>H<sub>2</sub> \u2192 N<sub>2</sub>H<sub>3</sub> and NNH \u2192 N<sub>2</sub>, "
  "plus NH<sub>2</sub> \u2192 N<sub>2</sub> at 0.091). In Stage 2 at <i>\u03c6</i><sub>1</sub> = 1.8 (Figure {{FIG_RP4}}), however, the carried-over "
  "NH<sub>3</sub> \u2192 NH<sub>2</sub> stream branches strongly through NH<sub>2</sub> \u2192 HNO (0.306) and NH \u2192 HNO (0.234) into the dominant "
  "HNO \u2192 NO arrow (0.548) accompanied by fast NO \u2192 HONO \u2192 NO<sub>2</sub> \u2192 NO cycling (0.381/0.378/0.379), confirming "
  "the Stage-2 oxidation surge visually.")

H("4.6 Conclusion", 2)
J("Phase 1 proved that rich\u2013lean staging cuts NO<sub>x</sub> by 55.1% overall (60.1% across NH<sub>3</sub>-containing blends, up to 90.4%), "
  "and Phase 2 demonstrated through complete ROP and N-flux analysis that the right-branch failure stems from Stage-1 "
  "amine carry-over oxidised via HNO + OH in Stage 2. Chapter 5 examines whether decoupling stage residence times and "
  "softening secondary air mixing can eliminate this carry-over penalty and evaluates performance under gas-turbine conditions.")
PB()

# ================================================================ CHAPTER 5
H("Chapter 5: Reactor Architecture, Mixing Physics, and Gas-Turbine Regimes", 1)
H("5.1 Introduction", 2)
J("Having established the chemical cause of the right-branch NO<sub>x</sub> surge in Chapter 4, this chapter removes the remaining "
  "idealised reactor and boundary assumptions across Phases 3 and 4. Section 5.2 investigates decoupled primary and secondary "
  "residence times (<i>\u03c4</i><sub>1</sub> \u2260 <i>\u03c4</i><sub>2</sub>), Section 5.3 models finite-rate progressive secondary dilution, Sections 5.4\u20135.6 examine "
  "gas-turbine pressure, air preheat, and wall heat loss, and Section 5.7 synthesises the architectural conclusions.")

H("5.2 Decoupled Stage Residence Times", 2)
J("A 125-case 2D sweep was executed across <i>\u03c4</i><sub>1</sub> \u2208 [10, 50] ms and <i>\u03c4</i><sub>2</sub> \u2208 [20, 100] ms at five primary equivalence "
  "ratios (<i>\u03c6</i><sub>1</sub> = 1.2, 1.4, 1.6, 1.8, 2.0) for <i>x</i><sub>NH3</sub> = 0.50 (100% converged; Tables {{TAB_D1}} and {{TAB_D2}}).")
a = dec.pivot_table(index="Phi_1", columns="Tau_1_ms", values="NOx_final_ppm", aggfunc="mean").round(0).astype(int)
a.columns = [f"<i>\u03c4</i><sub>1</sub> = {int(c)} ms" for c in a.columns]
a.insert(0, "<i>\u03c6</i><sub>1</sub>", a.index)
tab_d1 = TABLE(a.reset_index(drop=True), "Final NO<sub>x</sub> (ppm) versus primary residence time <i>\u03c4</i><sub>1</sub>, averaged across <i>\u03c4</i><sub>2</sub> = 20\u2013100 ms.",
               widths=[1.6, 2.8, 2.8, 2.8, 2.8, 2.8])

b = dec.pivot_table(index="Phi_1", columns="Tau_1_ms", values="NH2_primary_ppm", aggfunc="mean").round(1)
b.columns = [f"<i>\u03c4</i><sub>1</sub> = {int(c)} ms" for c in b.columns]
b.insert(0, "<i>\u03c6</i><sub>1</sub>", b.index)
tab_d2 = TABLE(b.reset_index(drop=True), "Primary-outlet NH<sub>2</sub> carry-over (ppm) versus <i>\u03c4</i><sub>1</sub>, averaged across <i>\u03c4</i><sub>2</sub>.",
               widths=[1.6, 2.8, 2.8, 2.8, 2.8, 2.8])
fig_d1 = FIGURE(PLOTS / "decoupled_tau_2d_contour.png", "2D contour maps of final NO<sub>x</sub> over (<i>\u03c4</i><sub>1</sub>, <i>\u03c4</i><sub>2</sub>) at four <i>\u03c6</i><sub>1</sub> levels (dashed red line denotes equal <i>\u03c4</i><sub>1</sub> = <i>\u03c4</i><sub>2</sub>).", 15.0)
fig_d2 = FIGURE(PLOTS / "decoupled_tau_ratio_tradeoff.png", "Impact of stage residence-time ratio (<i>\u03c4</i><sub>1</sub>/<i>\u03c4</i><sub>2</sub>) on final NO<sub>x</sub> emissions and residual fuel slip.", 13.5)
J(f"Contrary to the hypothesis that shortening a rich primary zone limits radical build-up, Tables {{TAB_D1}}\u2013{{TAB_D2}} and "
  f"Figures {{FIG_D1}}\u2013{{FIG_D2}} show the exact opposite: a shorter <i>\u03c4</i><sub>1</sub> freezes Stage 1 far from equilibrium, maximizing "
  f"NH<sub>2</sub> carry-over (281.6 ppm at <i>\u03c4</i><sub>1</sub> = 10 ms, <i>\u03c6</i><sub>1</sub> = 2.0) and driving NO<sub>x</sub> to 4105 ppm. Extending <i>\u03c4</i><sub>1</sub> to 50 ms "
  f"lets rich amine chemistry relax toward N<sub>2</sub>, cutting NH<sub>2</sub> carry-over to 157.2 ppm and dropping NO<sub>x</sub> by 379\u2013607 ppm across "
  f"all <i>\u03c6</i><sub>1</sub>. Meanwhile, <i>\u03c4</i><sub>2</sub> exerts opposing effects across regimes: longer <i>\u03c4</i><sub>2</sub> (20 \u2192 100 ms) lowers right-branch "
  f"NO<sub>x</sub> (4438 \u2192 3490 ppm at <i>\u03c6</i><sub>1</sub> = 2.0) and suppresses NH<sub>3</sub> slip below 0.1 ppm, but slightly increases valley NO<sub>x</sub> "
  f"(1367 \u2192 1484 ppm at <i>\u03c6</i><sub>1</sub> = 1.2) via extended thermal NO formation. Consequently, the global minimum on the grid "
  f"(1124.0 ppm) occurs at asymmetric sizing: long rich zone (<i>\u03c4</i><sub>1</sub> = 50 ms) and compact lean burnout (<i>\u03c4</i><sub>2</sub> = 20 ms) at <i>\u03c6</i><sub>1</sub> = 1.2.")

H("5.3 Finite-Rate Progressive Secondary Dilution", 2)
J("To replace instantaneous Stage-2 air addition (<i>N</i> = 1), progressive equal-parcel dilution sequences with <i>N</i> = 3 and <i>N</i> = 5 "
  "stages were simulated across <i>\u03c6</i><sub>1</sub> = 1.0\u20132.0 at <i>x</i><sub>NH3</sub> = 0.50, <i>\u03c4</i><sub>1</sub> = 30 ms, and <i>\u03c4</i><sub>2</sub> = 60 ms (Table {{TAB_FM}}).")
pv_ = fm.pivot(index="Phi_1", columns="N_mixing_stages", values="NOx_final_ppm")
t3 = pd.DataFrame({
    "<i>\u03c6</i><sub>1</sub>": pv_.index.round(1),
    "<i>N</i> = 1 (Instantaneous)": pv_[1].round(0).astype(int),
    "<i>N</i> = 3": pv_[3].round(0).astype(int),
    "<i>N</i> = 5": pv_[5].round(0).astype(int),
    "Cut <i>N</i> = 5 vs. 1 (%)": ((pv_[5] / pv_[1] - 1) * 100).round(1),
})
tab_fm = TABLE(t3, "Effect of progressive secondary air dilution stages (<i>N</i> = 1, 3, 5) on final NO<sub>x</sub> (ppm).",
               widths=[1.8, 3.6, 2.4, 2.4, 3.8])
fig_fm1 = FIGURE(PLOTS / "finite_mixing_nox_comparison.png", "Flattening of the NO<sub>x</sub> U-curve by progressive 3-stage and 5-stage finite-rate secondary air dilution.", 13.5)
fig_fm2 = FIGURE(PLOTS / "finite_mixing_temperature_trajectories.png", "Progressive sub-stage temperature trajectories across intermediate dilution stages (<i>N</i> = 5 vs. <i>N</i> = 1).", 13.5)
J("Progressive dilution dramatically flattens the NO<sub>x</sub> U-curve (Figure {{FIG_fm1}} and Table {{TAB_FM}}). At <i>\u03c6</i><sub>1</sub> = 2.0, final "
  "NO<sub>x</sub> collapses from 3693 ppm (<i>N</i> = 1) to 640 ppm (<i>N</i> = 3) and 433 ppm (<i>N</i> = 5)\u2014an 88.3% cut\u2014eliminating the "
  "right-branch penalty altogether. Figure {{FIG_fm2}} clarifies why: parcel-wise air injection walks the mixture gradually "
  "through sub-rich intermediate zones where thermal de-NO<sub>x</sub> (NH<sub>2</sub> + NO) remains active, while each short sub-stage "
  "(<i>\u03c4</i><sub>sub</sub> = 12 ms at <i>N</i> = 5) traverses peak stoichiometric temperatures (~2180 K) too rapidly for thermal NO to rebuild. "
  "Although dependent on equal parcel splitting and unvalidated experimentally, this finding shows that the severe right-branch "
  "penalty of 0-D models is partly an artefact of instantaneous mixing.")

H("5.4 Elevated Combustor Pressure Regimes", 2)
J("Phase 4a evaluated combustor pressure from 1 to 30 atm at <i>x</i><sub>NH3</sub> = 0.50, <i>T</i><sub>in</sub> = 300 K, <i>\u03c4</i><sub>1</sub> = 40 ms, and <i>\u03c4</i><sub>2</sub> = 60 ms "
  "(Table {{TAB_PR}} and Figures {{FIG_P1}}\u2013{{FIG_P2}}).")
pp = ps.pivot(index="Phi_1", columns="P_atm", values="NOx_ppm")
t4 = pd.DataFrame({"<i>\u03c6</i><sub>1</sub>": pp.index.round(1)})
for c in pp.columns:
    t4[f"{int(c)} atm"] = pp[c].round(0).astype(int).values
tab_pr = TABLE(t4, "Final NO<sub>x</sub> (ppm) across primary equivalence ratio and pressure (1\u201330 atm).", widths=[1.8, 2.8, 2.8, 2.8, 2.8, 2.8])
fig_p1 = FIGURE(PLOTS / "pressure_effect_nox_u_curve.png", "Shift and flattening of the staged NO<sub>x</sub> U-curve across pressures <i>P</i> = 1\u201330 atm.", 13.5)
fig_p2 = FIGURE(PLOTS / "pressure_no2_fraction_shift.png", "Increase in exhaust NO<sub>2</sub>/NO<sub>x</sub> partitioning with pressure.", 12.0)
J(f"Pressure reshapes the U-curve asymmetrically (Table {{TAB_PR}}, Figure {{FIG_P1}}): it suppresses near-stoichiometric "
  f"NO<sub>x</sub> at <i>\u03c6</i><sub>1</sub> = 1.0 by 61.5% (4548 \u2192 1753 ppm) and right-branch NO<sub>x</sub> at <i>\u03c6</i><sub>1</sub> = 2.0 by 41.7% (3652 \u2192 2129 ppm), "
  f"while elevating valley NO<sub>x</sub> at <i>\u03c6</i><sub>1</sub> = 1.3 (1072 \u2192 1604 ppm). Consequently, the optimum primary staging ratio shifts left "
  f"from <i>\u03c6</i><sub>1</sub> = 1.3 (1 atm) to 1.2 (5 atm) and 1.1 (10\u201330 atm), and U-curve variance collapses by 73.7%. Concurrently, "
  f"Figure {{FIG_P2}} shows the mean NO<sub>2</sub>/NO<sub>x</sub> ratio rising 6.6-fold ({ps[ps.P_atm==1].NO2_ratio.mean()*100:.3f}% \u2192 "
  f"{ps[ps.P_atm==30].NO2_ratio.mean()*100:.3f}%), consistent with pressure-accelerated three-body H + O<sub>2</sub> + M \u21c4 HO<sub>2</sub> + M "
  f"recombination driving NO + HO<sub>2</sub> \u21c4 NO<sub>2</sub> + OH (inferred kinetically rather than proven by a separate high-pressure ROP run).")

H("5.5 Compressor-Discharge Air Preheat", 2)
J("At <i>P</i> = 10 atm, increasing inlet temperature from 300 K to 750 K models realistic compressor-discharge preheating "
  "(Table {{TAB_PH}} and Figure {{FIG_PH}}).")
pw = pre.pivot(index="Phi_1", columns="T_in_K", values="NOx_ppm")
t5 = pd.DataFrame({"<i>\u03c6</i><sub>1</sub>": pw.index.round(1)})
for c in pw.columns:
    t5[f"{int(c)} K"] = pw[c].round(0).astype(int).values
mt = pre.groupby("T_in_K").agg(Nx=("NOx_ppm", "mean"), Tf=("T_final_K", "mean"))
t5.loc[len(t5)] = ["Mean NO<sub>x</sub> (ppm)"] + [int(round(v)) for v in mt.Nx]
t5.loc[len(t5)] = ["Mean <i>T</i><sub>final</sub> (K)"] + [int(round(v)) for v in mt.Tf]
tab_ph = TABLE(t5, "Final NO<sub>x</sub> (ppm) and mean final temperature versus compressor-discharge preheat at <i>P</i> = 10 atm.", widths=[3.6, 3.0, 3.0, 3.0, 3.0])
fig_ph = FIGURE(PLOTS / "preheat_flame_temperature_and_nox.png", "Escalation of final flame temperature and NO<sub>x</sub> across inlet air preheat (300\u2013750 K) at 10 atm.", 13.5)
J("Every 150 K of air preheat elevates mean final temperature linearly by ~100 K (2119 \u2192 2418 K, slope 0.663 K K<sup>\u22121</sup>), "
  "driving mean NO<sub>x</sub> upward from 1957 to 4699 ppm (~6.1 ppm K<sup>\u22121</sup>) via thermal Zeldovich kinetics (Table {{TAB_PH}}, Figure {{FIG_PH}}). "
  "Even so, staging near <i>\u03c6</i><sub>1</sub> = 1.2\u20131.3 retains the flat valley minimum across all preheat levels.")

H("5.6 Non-Adiabatic Liner Wall Heat Loss", 2)
J("Under severe gas-turbine conditions (<i>P</i> = 15 atm, <i>T</i><sub>in</sub> = 650 K), convective liner cooling with <i>U</i> \u2208 [0, 3000] W m<sup>\u22122</sup> K<sup>\u22121</sup> "
  "was evaluated across seven <i>\u03c6</i><sub>1</sub> levels (Table {{TAB_HL}} and Figure {{FIG_HL}}).")
hh = hl.pivot(index="Phi_1", columns="U_wall_W_m2K", values="NOx_ppm")
t6 = pd.DataFrame({"<i>\u03c6</i><sub>1</sub>": hh.index.round(1)})
for c in hh.columns:
    t6[f"<i>U</i> = {int(c)}"] = hh[c].round(0).astype(int).values
t6["<i>\u0394</i> (<i>U</i> = 3000)"] = (hh[3000.0] - hh[0.0]).round(0).astype(int).values
mt_hl = hl.groupby("U_wall_W_m2K").agg(Tf=("T_final_K", "mean"), sl=("NH3_slip_ppm", "mean"))
tab_hl = TABLE(t6, "Final NO<sub>x</sub> (ppm) versus wall heat-transfer coefficient <i>U</i> (W m<sup>\u22122</sup> K<sup>\u22121</sup>) at <i>P</i> = 15 atm, <i>T</i><sub>in</sub> = 650 K.",
               widths=[1.8, 2.5, 2.5, 2.5, 2.5, 3.0])
fig_hl = FIGURE(PLOTS / "wall_heat_loss_mitigation.png", "Effect of combustor liner heat loss on (a) final NO<sub>x</sub> and (b) final temperature at 15 atm and 650 K.", 14.0)
J(f"At <i>U</i> = 3000 W m<sup>\u22122</sup> K<sup>\u22121</sup>, liner cooling reduces mean final flame temperature by {mt_hl.Tf.iloc[0] - mt_hl.Tf.iloc[-1]:.1f} K "
  f"({mt_hl.Tf.iloc[0]:.0f} \u2192 {mt_hl.Tf.iloc[-1]:.0f} K) and lowers NO<sub>x</sub> consistently by 286\u2013431 ppm across all <i>\u03c6</i><sub>1</sub> (mean 386.1 ppm, "
  f"Table {{TAB_HL}} and Figure {{FIG_HL}}), while mean NH<sub>3</sub> slip remains negligible (< {mt_hl.sl.max():.3f} ppm). Thus passive "
  f"liner cooling helps counteract preheat-driven thermal NO<sub>x</sub> without jeopardising burnout in the PSR limit.")

H("5.7 Conclusion", 2)
J("Phase 3 demonstrated that long rich residence times and progressive secondary air dilution can eliminate the right-branch "
  "NO<sub>x</sub> surge (\u221288.3%), while Phase 4 showed that high pressure shifts the optimal primary ratio to <i>\u03c6</i><sub>1</sub> = 1.1\u20131.2, preheat "
  "raises baseline NO<sub>x</sub>, and wall cooling restores ~386 ppm mitigation. Chapter 6 tests all results statistically and synthesises "
  "an integrated design window.")
PB()

# ================================================================ CHAPTER 6
H("Chapter 6: Statistical Significance Analysis and Integrated Design Synthesis", 1)
H("6.1 Introduction", 2)
J("Because combustion simulations across parametric grids can exhibit large visual swings driven by isolated extremes or "
  "opposing interactions, Chapter 6 rigorously tests every claim from Chapters 4 and 5. Section 6.2 reports Type-II ANOVA "
  "variance shares on the 586-point factorial study, Section 6.3 presents all hypothesis tests and bootstrap CIs across Phases 1\u20134, "
  "Section 6.4 states statistical caveats, Section 6.5 integrates all phases into a unified operating window, and Section 6.6 concludes.")

H("6.2 Factorial Sensitivity and Variance Decomposition", 2)
J("Type-II ANOVA partial <i>F</i>-tests on the 586 converged main-study cases (Table {{TAB_S1}}, Figure {{FIG_STAT}}(b)) separate "
  "main-factor contributions cleanly without confounding factor imbalance from the 19 non-converged points.")
s1 = stat[(stat.Phase == "Main 605-case") & stat.Test.str.startswith("Type-II")].copy()
s1["Factor"] = s1.Test.str.extract(r"\((.*)\)")
s1["Partial <i>R</i><sup>2</sup>"] = s1.Effect.str.extract(r"=([0-9.]+)")[0]
s1 = s1[["Quantity", "Factor", "Statistic", "Partial <i>R</i><sup>2</sup>", "p_value"]]
s1.columns = ["Response", "Factor", "<i>F</i>", "Partial <i>R</i><sup>2</sup>", "<i>p</i>-value"]
s1["<i>p</i>-value"] = s1["<i>p</i>-value"].map(pfmt)
tab_s1 = TABLE(s1, "Type-II ANOVA of the 586 converged main-study cases (numerator df = 10 for <i>x</i><sub>NH3</sub>/<i>\u03c6</i><sub>1</sub>, 4 for <i>\u03c4</i>; denominator df = 561).",
               fs=8.5, widths=[3.2, 2.8, 2.4, 2.6, 2.8])
fig_stat = FIGURE(STAT_FIG1, "(a) Histogram and 95% bootstrap CI of the staging NO<sub>x</sub> reduction across 469 matched pairs; (b) Type-II ANOVA partial <i>R</i><sup>2</sup> variance shares across main-study responses.", 15.5)
J("Fuel composition overwhelmingly drives <i>T</i><sub>final</sub> (partial <i>R</i><sup>2</sup> = 0.981, <i>p</i> < 10<sup>\u2212300</sup>) and H<sub>2</sub> slip (0.906, <i>p</i> < 10<sup>\u2212300</sup>), "
  "whereas <i>\u03c6</i><sub>1</sub> explains 99.4% of Stage-2 <i>\u0394T</i> (<i>p</i> < 10<sup>\u2212300</sup>; Table {{TAB_S1}}). Residence time <i>\u03c4</i> significantly reduces "
  "NO<sub>x</sub> within matched (<i>x</i><sub>NH3</sub>, <i>\u03c6</i><sub>1</sub>) cells (mean Spearman <i>\u03c1</i> = \u22120.433, 95% CI [\u22120.580, \u22120.277], <i>t</i> = \u22125.56, <i>p</i> = 1.79 \u00d7 10<sup>\u22127</sup>), "
  "yet has no significant effect on Stage-2 <i>\u0394</i>NO<sub>x</sub> (<i>p</i> = 0.095) and only marginal impact on <i>\u0394T</i> (<i>p</i> = 0.035).")

H("6.3 Significance Testing Across Phases 1\u20134", 2)
J("Tables {{TAB_S2}} and {{TAB_S3}} collect all 47 statistical tests archived in <code>results/statistical_significance_summary.csv</code>.")
s2 = stat[stat.Phase.isin(["Phase 1", "Phase 2", "Phase 3"])].copy()
s2 = s2[["Phase", "Test", "Quantity", "N", "Statistic", "p_value", "Effect", "CI95"]]
s2["p_value"] = s2["p_value"].map(pfmt)
s2.columns = ["Phase", "Test", "Quantity", "<i>N</i>", "Stat.", "<i>p</i>-value", "Effect Size", "95% CI"]
tab_s2 = TABLE(s2, "Hypothesis tests, effect sizes, and 95% bootstrap confidence intervals for Phases 1\u20133.",
               fs=7.2, widths=[1.2, 3.8, 1.9, 0.8, 1.3, 1.6, 3.2, 2.2])

s3 = stat[stat.Phase == "Phase 4"].copy()
s3 = s3[["Test", "Quantity", "N", "Statistic", "p_value", "Effect", "CI95"]]
s3["p_value"] = s3["p_value"].map(pfmt)
s3.columns = ["Test", "Quantity", "<i>N</i>", "Stat.", "<i>p</i>-value", "Effect Size", "95% CI"]
tab_s3 = TABLE(s3, "Statistical significance and interaction tests for Phase 4 gas-turbine regimes.",
               fs=7.5, widths=[4.5, 1.8, 0.8, 1.3, 1.5, 3.8, 2.3])
J("Key inferential conclusions from Tables {{TAB_S2}} and {{TAB_S3}} and Figure {{FIG_STAT}}(a) are:")
B(["<b>Phase 1 (Staging Benefit):</b> The 4167.0 ppm paired mean reduction (95% CI [3920.7, 4409.0] ppm) has a very large "
   "effect size (<i>d</i><sub>z</sub> = 1.56, paired <i>t</i> = 33.79, <i>p</i> = 1.26 \u00d7 10<sup>\u2212127</sup>). Non-parametric Wilcoxon (<i>p</i> = 5.28 \u00d7 10<sup>\u221276</sup>) "
   "and binomial sign tests (439/469 wins, <i>p</i> = 2.81 \u00d7 10<sup>\u221294</sup>) confirm the benefit is grid-wide, not outlier-driven.",
   "<b>Phase 2 (U-Curve Origin):</b> Both the monotonic Stage-1 NO<sub>x</sub> decline (<i>\u03c1</i> = \u22121.0) and monotonic Stage-2 NO<sub>x</sub> and NH<sub>2</sub> "
   "rises (<i>\u03c1</i> = +1.0) reach the exact permutation floor (<i>p</i> = 2/11! = 5.01 \u00d7 10<sup>\u22128</sup>), and total NO<sub>x</sub> possesses positive "
   "quadratic curvature (<i>t</i> = 5.19, <i>p</i> = 8.31 \u00d7 10<sup>\u22124</sup>), proving statistical reality of the U-shape.",
   "<b>Phase 3 (Architecture & Mixing):</b> On decoupled residence times, <i>\u03c6</i><sub>1</sub> dominates NO<sub>x</sub> variance (partial <i>R</i><sup>2</sup> = 0.947), "
   "while <i>\u03c4</i><sub>1</sub> (0.020, <i>p</i> = 9.01 \u00d7 10<sup>\u221215</sup>) and <i>\u03c4</i><sub>2</sub> (0.010, <i>p</i> = 1.26 \u00d7 10<sup>\u22128</sup>) exert genuine secondary control; "
   "NH<sub>3</sub> slip depends on <i>\u03c4</i><sub>2</sub> (0.139, <i>p</i> = 3.32 \u00d7 10<sup>\u221218</sup>) rather than <i>\u03c4</i><sub>1</sub> (<i>p</i> = 0.301). Progressive mixing "
   "produces a significant difference across <i>N</i> = 1, 3, 5 (Friedman <i>p</i> = 1.67 \u00d7 10<sup>\u22125</sup>), with <i>N</i> = 5 outperforming <i>N</i> = 3 "
   "at every <i>\u03c6</i><sub>1</sub> (mean 142.5 ppm, <i>d</i><sub>z</sub> = 2.95, <i>p</i> = 1.94 \u00d7 10<sup>\u22126</sup>).",
   "<b>Phase 4 (Gas-Turbine Regimes):</b> Preheat (+6.1 ppm K<sup>\u22121</sup>) and liner cooling (\u2212386.1 ppm mean cut, 95% CI [343.8, 421.9] ppm, "
   "<i>p</i> = 2.04 \u00d7 10<sup>\u22126</sup>) act monotonically at all 7 <i>\u03c6</i><sub>1</sub> levels (exact sign test <i>p</i> = 0.0156). Crucially, pooled pressure "
   "tests are non-significant (paired 1 vs. 30 atm <i>p</i> = 0.188; pooled <i>\u03c1</i> = \u22120.10, <i>p</i> = 0.690) solely because pressure reverses "
   "sign between branches: it significantly <i>increases</i> NO<sub>x</sub> in the valley (<i>\u03c1</i> = +0.666, <i>p</i> = 0.0068), <i>decreases</i> it on the right "
   "branch (<i>\u03c1</i> = \u22120.766, <i>p</i> = 8.12 \u00d7 10<sup>\u22125</sup>), collapses curve SD by 73.7% (Levene <i>p</i> = 0.0125), and monotonically drives "
   "NO<sub>2</sub>/NO<sub>x</sub> upward (<i>\u03c1</i> = 0.988, <i>p</i> = 3.14 \u00d7 10<sup>\u221244</sup>). Pressure must therefore be modelled via its <i>P</i> \u00d7 <i>\u03c6</i><sub>1</sub> interaction."])

H("6.4 Statistical Caveats and Multiple-Testing Considerations", 2)
J("Four limitations govern interpretation of Tables {{TAB_S1}}\u2013{{TAB_S3}}: (i) deterministic grid outputs carry no physical measurement "
  "noise, so <i>p</i>-values measure consistency across operating conditions and large factorial <i>n</i> inflates significance; "
  "(ii) curve comparisons have <i>n</i> = 7\u201311, restricting power to large effects; (iii) under a conservative Bonferroni threshold "
  "<i>\u03b1</i> = 0.05/47 \u2248 1.06 \u00d7 10<sup>\u22123</sup>, the Phase 3 parametric paired <i>t</i>-tests comparing <i>N</i> = 1 vs. 3 (<i>p</i> = 0.0028) and <i>N</i> = 1 vs. 5 "
  "(<i>p</i> = 0.0018) would not survive, whereas the non-parametric Wilcoxon (<i>p</i> = 9.77 \u00d7 10<sup>\u22124</sup>) and Friedman (<i>p</i> = 1.67 \u00d7 10<sup>\u22125</sup>) "
  "tests do survive; and (iv) mechanism uncertainty is unquantified.")

H("6.5 Integrated Combustor Design Window", 2)
J("Synthesising Phases 1\u20134 yields a coherent design strategy for low-NO<sub>x</sub> NH<sub>3</sub>/H<sub>2</sub> staged combustors: operate the primary "
  "stage inside <i>\u03c6</i><sub>1</sub> \u2248 1.1\u20131.4 (shifting toward 1.1 at 10\u201330 atm), provide generous rich-zone residence time (<i>\u03c4</i><sub>1</sub> \u2248 40\u201350 ms) "
  "so amine radicals relax toward N<sub>2</sub> rather than carrying over, stage secondary air injection progressively (<i>N</i> \u2265 3\u20135) to "
  "prevent HNO + OH oxidation surges, and employ combustor liner cooling to offset compressor-discharge preheat penalties.")

H("6.6 Conclusion", 2)
J("Statistical testing confirms the robustness of staging, kinetic U-curve decomposition, progressive secondary dilution, "
  "and thermal mitigation while exposing the sign-reversing interaction of pressure across equivalence ratios. Chapter 7 "
  "summarises overall project contributions and future research priorities.")
PB()

# ================================================================ CHAPTER 7
H("Chapter 7: Conclusions", 1)
H("7.1 Summary", 2)
B(["<b>Phase 1 (Baseline Benefit):</b> Across 469 matched cases, two-stage RQL combustion reduces NO<sub>x</sub> by an average of 55.1% "
   "(95% CI [52.2, 57.9]%, up to 90.4%, sign test <i>p</i> = 2.81 \u00d7 10<sup>\u221294</sup>), with gains of 60.1% across all NH<sub>3</sub>-containing blends.",
   "<b>Phase 2 (Kinetic Mechanism):</b> The NO<sub>x</sub> U-curve is the superposition of falling Stage-1 thermal/prompt NO (4400 \u2192 29 ppm) "
   "and rising Stage-2 oxidation (\u2212191 \u2192 +3586 ppm) of unburnt NH<sub>2</sub> (5.2 \u2192 85.7 ppm) and NH<sub>3</sub> (21.9 \u2192 8558 ppm) via "
   "HNO + OH \u21c4 H<sub>2</sub>O + NO (24\u00d7 surge at <i>\u03c6</i><sub>1</sub> = 2.0), framed around a thermal de-NO<sub>x</sub> valley at <i>\u03c6</i><sub>1</sub> \u2248 1.3.",
   "<b>Phase 3 (Reactor Architecture):</b> Longer rich residence times (<i>\u03c4</i><sub>1</sub> = 50 ms) lower NH<sub>2</sub> carry-over and NO<sub>x</sub>; progressive "
   "5-stage secondary air dilution slashes right-branch NO<sub>x</sub> at <i>\u03c6</i><sub>1</sub> = 2.0 by 88.3% (3693 \u2192 433 ppm, Friedman <i>p</i> = 1.67 \u00d7 10<sup>\u22125</sup>).",
   "<b>Phase 4 (Gas-Turbine Regimes):</b> Pressure shifts the minimum-NO<sub>x</sub> valley from <i>\u03c6</i><sub>1</sub> = 1.3 to 1.1, collapses curve spread "
   "by 73.7% (Levene <i>p</i> = 0.0125), and raises NO<sub>2</sub>/NO<sub>x</sub> 6.6-fold; preheat escalates NO<sub>x</sub> by 6.1 ppm K<sup>\u22121</sup>; liner cooling "
   "(<i>U</i> = 3000 W m<sup>\u22122</sup> K<sup>\u22121</sup>) recovers a 386.1 ppm NO<sub>x</sub> reduction (<i>p</i> = 2.04 \u00d7 10<sup>\u22126</sup>) with near-zero NH<sub>3</sub> slip (< 0.07 ppm)."], numbered=True)

H("7.2 Future Work", 2)
B(["Benchmark predictions across multiple published NH<sub>3</sub>/H<sub>2</sub> mechanisms (e.g., Glarborg, Okafor, Stagni) to quantify kinetic uncertainty.",
   "Validate staged, decoupled, and progressive-dilution predictions against experimental jet-stirred reactor, flow-reactor, and gas-turbine datasets.",
   "Extend Phases 3\u20134 across the full 0\u2013100% NH<sub>3</sub> blend spectrum and perform pressure-resolved ROP analysis at 10\u201330 atm.",
   "Track N<sub>2</sub>O explicitly alongside NO<sub>x</sub> using greenhouse-warming-potential-weighted emission metrics.",
   "Replace discrete equal-split dilution by mixing-time-resolved partially stirred reactor (PaSR) or CFD-informed chemical reactor networks."], numbered=True)
PB()

# ================================================================ REFERENCES (Strictly ordered [1]..[10], IEEE style)
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
PB()

# ================================================================ APPENDIX
H("Appendix A: Repository Architecture and Reproducibility", 1)
J("All results in this report can be reproduced sequentially from the repository root with the Cantera environment active:")
for cmd in [
    "python -m single_stage.single_stage_baseline",
    "python -m double_stage.rate_of_production_analysis",
    "python -m double_stage.decoupled_mixing_analysis",
    "python -m double_stage.gas_turbine_regimes_analysis",
    "python -m double_stage.statistical_significance_analysis",
    "python docs/reports/build_end_semester_report.py",
]:
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p.paragraph_format.left_indent = Cm(0.8)
    p.paragraph_format.space_after = Pt(2)
    r = p.add_run(cmd)
    r.font.name = "Courier New"
    r.font.size = Pt(10)
J("The statistical significance script and report builder operate directly on the committed CSV datasets under "
  "<code>results/</code> and regenerate both <code>results/statistical_significance_summary.csv</code> and this DOCX report in seconds.")

# ================================================================ RESOLVE PLACEHOLDERS & FRONT MATTER
repl = {
    "{FIG_AIR}": str(fig_air), "{FIG_NET}": str(fig_net),
    "{FIG_MTEMP}": str(fig_mtemp), "{FIG_MU}": str(fig_mu), "{FIG_MNMAP}": str(fig_mnmap),
    "{FIG_B1}": str(fig_b1), "{FIG_B2}": str(fig_b2), "{FIG_B3}": str(fig_b3),
    "{FIG_ROP1}": str(fig_rop1), "{FIG_ROP2}": str(fig_rop2),
    "{FIG_RP1}": str(fig_rp1), "{FIG_RP2}": str(fig_rp2), "{FIG_RP3}": str(fig_rp3), "{FIG_RP4}": str(fig_rp4),
    "{FIG_D1}": str(fig_d1), "{FIG_D2}": str(fig_d2),
    "{FIG_fm1}": str(fig_fm1), "{FIG_fm2}": str(fig_fm2),
    "{FIG_P1}": str(fig_p1), "{FIG_P2}": str(fig_p2),
    "{FIG_PH}": str(fig_ph), "{FIG_HL}": str(fig_hl), "{FIG_STAT}": str(fig_stat),
    "{TAB_MOD}": str(tab_mod), "{TAB_CAMP}": str(tab_camp), "{TAB_ETA}": str(tab_eta),
    "{TAB_B1}": str(tab_b1), "{TAB_ROP}": str(tab_rop), "{TAB_RXN}": str(tab_rxn),
    "{TAB_D1}": str(tab_d1), "{TAB_D2}": str(tab_d2), "{TAB_FM}": str(tab_fm),
    "{TAB_PR}": str(tab_pr), "{TAB_PH}": str(tab_ph), "{TAB_HL}": str(tab_hl),
    "{TAB_S1}": str(tab_s1), "{TAB_S2}": str(tab_s2), "{TAB_S3}": str(tab_s3),
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
