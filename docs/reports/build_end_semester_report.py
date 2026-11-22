"""Build the end-semester B.Tech project report (DOCX) from repository results.

Run:  python docs/reports/build_end_semester_report.py
Output: docs/reports/BTP_End_Semester_Report.docx
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

ROOT = Path(__file__).resolve().parents[2]
RES = ROOT / "results"
PLOTS = RES / "plots"
MID_IMG = ROOT / "docs" / "reports" / "mid_sem_figures"   # figures extracted from the mid-sem report
OUT = ROOT / "docs" / "reports" / "BTP_End_Semester_Report.docx"

doc = Document()
sec = doc.sections[0]
sec.page_width, sec.page_height = Cm(21), Cm(29.7)
sec.left_margin = sec.right_margin = Cm(2.5)
sec.top_margin = sec.bottom_margin = Cm(2.5)

st = doc.styles["Normal"]
st.font.name = "Times New Roman"
st.font.size = Pt(12)
st.element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
st.paragraph_format.line_spacing = 1.3
st.paragraph_format.space_after = Pt(6)
for name, size in [("Heading 1", 18), ("Heading 2", 14), ("Heading 3", 12)]:
    h = doc.styles[name]
    h.font.name = "Times New Roman"
    h.font.size = Pt(size)
    h.font.bold = True
    h.font.color.rgb = None
    h.element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")

FIG = [0]
TAB = [0]


def P(text, bold=False, italic=False, align=None, size=None, after=None):
    p = doc.add_paragraph()
    r = p.add_run(text)
    r.bold, r.italic = bold, italic
    if size:
        r.font.size = Pt(size)
    if align == "c":
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    elif align == "j":
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    if after is not None:
        p.paragraph_format.space_after = Pt(after)
    return p


def J(text):
    return P(text, align="j")


def H(text, lvl=1):
    return doc.add_heading(text, level=lvl)


def B(items, numbered=False):
    for it in items:
        doc.add_paragraph(it, style="List Number" if numbered else "List Bullet")


def EQ(text, num):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(f"{text}        ({num})")
    r.italic = True


def PB():
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)


def FIGURE(path, caption, width=14.5):
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(path)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run().add_picture(str(path), width=Cm(width))
    FIG[0] += 1
    c = P(f"Figure {FIG[0]}. {caption}", italic=True, align="c", size=10.5)
    return FIG[0]


def shade(cell, color="D9E2F3"):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), color)
    tcPr.append(shd)


def TABLE(df, caption, fs=9, widths=None):
    TAB[0] += 1
    P(f"Table {TAB[0]}. {caption}", bold=True, align="c", size=10.5, after=3)
    t = doc.add_table(rows=1, cols=len(df.columns))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, c in enumerate(df.columns):
        cell = t.rows[0].cells[i]
        cell.text = ""
        run = cell.paragraphs[0].add_run(str(c))
        run.bold = True
        run.font.size = Pt(fs)
        shade(cell)
    for _, row in df.iterrows():
        cells = t.add_row().cells
        for i, v in enumerate(row):
            cells[i].text = ""
            run = cells[i].paragraphs[0].add_run(str(v))
            run.font.size = Pt(fs)
    for row in t.rows:
        for c in row.cells:
            c.paragraphs[0].paragraph_format.space_after = Pt(0)
            c.paragraphs[0].paragraph_format.line_spacing = 1.0
    if widths:
        for row in t.rows:
            for i, w in enumerate(widths):
                row.cells[i].width = Cm(w)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)
    return TAB[0]


def pfmt(p):
    if p == "" or pd.isna(p):
        return ""
    p = float(p)
    if p == 0 or p < 1e-300:
        return "<1e-300"
    return f"{p:.2e}" if p < 1e-3 else f"{p:.4f}"


def toc_field():
    p = doc.add_paragraph()
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
    t.text = "Right-click here and choose 'Update Field' (or press F9) to build the table of contents."
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
eta = pd.read_csv(RES / "staged_combustion_eta_squared.csv")
reg = pd.read_csv(RES / "staged_combustion_regression_summary.csv")

# two extra figures for the statistics chapter
rng = np.random.default_rng(0)
fig, ax = plt.subplots(1, 2, figsize=(11, 4))
red = cmp_.NOx_reduction_pct.values
ax[0].hist(red, bins=40, color="#4472c4", edgecolor="white")
bs = [rng.choice(red, len(red)).mean() for _ in range(5000)]
lo, hi = np.percentile(bs, [2.5, 97.5])
ax[0].axvline(red.mean(), color="k", ls="--", label=f"mean = {red.mean():.1f}%")
ax[0].axvspan(lo, hi, color="orange", alpha=0.5, label=f"95% bootstrap CI [{lo:.1f}, {hi:.1f}]")
ax[0].axvline(0, color="r")
ax[0].set_xlabel("NOx reduction by staging (%)")
ax[0].set_ylabel("Number of matched operating points")
ax[0].set_title("(a) Staging benefit, 469 matched cases")
ax[0].legend(fontsize=8)
sub = stat[stat.Test.str.startswith("Type-II ANOVA") & (stat.Phase == "Main 605-case")].copy()
sub["factor"] = sub.Test.str.extract(r"\((.*)\)")
pv = sub.pivot(index="Quantity", columns="factor", values="Effect")
pr = pv.apply(lambda col: col.str.extract(r"=([0-9.]+)")[0].astype(float))
pr = pr[["NH3_frac", "Phi_1", "Tau_ms"]].loc[["T_final_K", "NOx_ppm", "H2_slip", "Delta_T_K", "Delta_NOx_ppm"]]
x = np.arange(len(pr))
for k, (col, c) in enumerate(zip(pr.columns, ["#4472c4", "#ed7d31", "#70ad47"])):
    ax[1].bar(x + (k - 1) * 0.27, pr[col], 0.27, label=col, color=c)
ax[1].set_xticks(x)
ax[1].set_xticklabels(pr.index, rotation=25, fontsize=8)
ax[1].set_ylabel("Partial R$^2$ (Type-II ANOVA)")
ax[1].set_title("(b) Variance share of each factor")
ax[1].legend(fontsize=8)
plt.tight_layout()
STAT_FIG1 = PLOTS / "stat_staging_benefit_and_variance_share.png"
plt.savefig(STAT_FIG1, dpi=200)
plt.close()

# ================================================================ TITLE PAGE
for _ in range(2):
    P("")
P("NUMERICAL INVESTIGATION OF TWO-STAGE NH\u2083/H\u2082 STAGED COMBUSTION", bold=True, align="c", size=20)
P("From Idealised Perfectly Stirred Reactors to Gas-Turbine Operating Regimes: Staging Benefit, Reaction-Pathway Analysis, Reactor-Architecture Physics and Statistical Significance", align="c", size=13)
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
H("Abstract", 1)
mean_red = cmp_.NOx_reduction_pct.mean()
J("Ammonia\u2013hydrogen (NH\u2083/H\u2082) blends are attractive carbon-free fuels, but their use in gas-turbine-type combustors "
  "is constrained by low reactivity, unburnt fuel and, above all, fuel-bound nitrogen oxide (NO\u2093) formation. Rich\u2013lean "
  "air staging is the standard remedy. The mid-semester work built a two-stage ideal-gas perfectly stirred reactor (PSR) "
  "model in Cantera with the Tamaoki et al. (2024) mechanism and mapped 605 operating points (586 converged) over NH\u2083 "
  "fraction, primary equivalence ratio \u03c6\u2081 and residence time at a fixed overall \u03c6 = 0.9. That study left four "
  "limitations: no single-stage baseline, no kinetic explanation of the non-monotonic (U-shaped) NO\u2093 response, "
  "idealised reactor architecture (equal residence times, instantaneous secondary mixing) and idealised conditions "
  "(1 atm, 300 K, adiabatic).")
J(f"This report removes each limitation in four phases and then tests every conclusion statistically. "
  f"(1) A matched single-stage baseline over 469 comparable operating points shows that staging reduces NO\u2093 by "
  f"{mean_red:.1f}% on average (95% bootstrap CI {lo:.1f}\u2013{hi:.1f}%, up to 90.4%); staging wins in 93.6% of cases "
  "(sign test p < 10\u207b\u2079\u2070), the exception being pure H\u2082 where there is no fuel nitrogen to suppress. "
  "(2) Rate-of-production and reaction-pathway analysis shows the U-curve is the exact superposition of a monotonic "
  "fall of Stage-1 NO\u2093 (4400 \u2192 29 ppm; thermal NO shutdown and NH\u2082/NH + NO de-NO\u2093 steps) and a monotonic "
  "rise of Stage-2 NO\u2093 generation (\u2212191 \u2192 +3586 ppm; carry-over of NH\u2082 from 5 to 86 ppm and unburnt NH\u2083 "
  "from 22 to 8560 ppm oxidised via HNO + OH and NH + O\u2082). "
  "(3) Decoupling residence times shows that a *longer*, not shorter, rich residence time lowers NH\u2082 carry-over "
  "(\u03c6\u2081 = 2.0: 282 \u2192 157 ppm for \u03c4\u2081 = 10 \u2192 50 ms) and NO\u2093; replacing instantaneous secondary mixing with five "
  "progressive dilution stages cuts right-branch NO\u2093 from 3693 to 433 ppm (\u221288.3%). "
  "(4) At gas-turbine conditions, pressure moves the low-NO\u2093 valley from \u03c6\u2081 = 1.3 (1 atm) to 1.1 (\u226510 atm) and raises the "
  "NO\u2082/NO\u2093 ratio about 6.6-fold (1 \u2192 30 atm), air preheat raises NO\u2093 by about 6 ppm per kelvin of inlet temperature, and "
  "liner cooling (U = 3000 W m\u207b\u00b2 K\u207b\u00b9) lowers NO\u2093 by 386 ppm on average (paired p = 2\u00d710\u207b\u2076). "
  "Statistical testing (ANOVA, non-parametric paired tests, bootstrap confidence intervals, effect sizes) confirms that "
  "the staging benefit, the U-shape, the mixing benefit and the thermal effects are significant, while it also shows "
  "that the net pressure effect is not significant when pooled over \u03c6\u2081 because it changes sign between branches.")
J("The work gives a quantified, mechanistically explained and statistically supported design map for NH\u2083/H\u2082 staged "
  "combustors and a reproducible open code base. All results are zero-dimensional and mechanism-dependent; they are "
  "design guidance, not predictions of a specific burner.")
PB()

# ================================================================ TOC etc.
H("Table of Contents", 1)
toc_field()
PB()
H("List of Abbreviations and Symbols", 1)
TABLE(pd.DataFrame([
    ["PSR", "Perfectly stirred reactor"],
    ["\u03c6, \u03c6\u2081", "Overall and primary-stage equivalence ratio"],
    ["x_NH3", "NH\u2083 mole fraction in the fuel (H\u2082 = 1 \u2212 x_NH3)"],
    ["\u03c4\u2081, \u03c4\u2082", "Residence time of primary and secondary stage"],
    ["N", "Number of progressive secondary-air dilution stages"],
    ["NO\u2093", "NO + NO\u2082 (ppm, mole basis)"],
    ["ROP", "Rate of production"],
    ["\u03b7\u00b2, partial R\u00b2", "Main-effect and Type-II variance fractions"],
    ["CI", "Confidence interval"],
    ["U, A", "Wall heat-transfer coefficient and area"],
], columns=["Symbol", "Meaning"]), "Abbreviations and symbols.", fs=10, widths=[3.5, 11])
PB()

# ================================================================ CH 1
H("Chapter 1: Introduction", 1)
H("1.1 Motivation", 2)
J("Ammonia carries no carbon and can be stored and transported more easily than hydrogen, which makes NH\u2083/H\u2082 blends "
  "promising for power generation and industrial heat [3]. Its combustion is, however, difficult: laminar burning "
  "velocity and flame stability are low, and because the fuel contains nitrogen, NO\u2093 formation is controlled by fuel-bound "
  "nitrogen chemistry in addition to the thermal (Zeldovich) route [4, 5]. Hydrogen addition restores reactivity but "
  "raises flame temperature and radical pools.")
J("Rich\u2013lean staging separates the problem in two. A rich primary zone limits free oxygen so that fuel nitrogen is "
  "directed towards N\u2082 through NH\u2082/NH + NO reactions (the thermal de-NO\u2093 chemistry [6, 7]); the remaining air then burns "
  "out the products in a lean secondary zone. Whether this helps, and how much, depends on how the NH\u2093 and H\u2082 "
  "intermediates leaving the rich zone meet the secondary oxygen.")
H("1.2 Summary of the mid-semester study and its limitations", 2)
J("The mid-semester report built the two-stage PSR model and swept x_NH3 (0\u20131, 11 levels), \u03c6\u2081 (1.0\u20132.0, 11 levels) and "
  "\u03c4 (20\u2013100 ms, 5 levels) at \u03c6 = 0.9, 300 K, 1 atm: 605 cases, 586 converged. Final temperature was governed by "
  "fuel composition (\u03b7\u00b2 = 0.981); NO\u2093 depended on both NH\u2083 fraction and \u03c6\u2081 (\u03b7\u00b2 = 0.186, 0.254) and was "
  "non-monotonic; \u0394T of Stage 2 was governed by \u03c6\u2081 (\u03b7\u00b2 = 0.993). The study ended with four stated limitations:")
B(["No single-stage baseline, so the benefit of staging was not quantified.",
   "No rate-of-production or pathway analysis, so the cause of the U-shaped NO\u2093 response was inferred, not shown.",
   "Equal residence times and instantaneous secondary mixing.",
   "Adiabatic operation at 1 atm and 300 K, far from gas-turbine conditions."])
H("1.3 Objectives of the end-semester work", 2)
B(["Quantify the benefit of staging against an identical-condition single-stage PSR (Phase 1).",
   "Identify, from elementary reaction fluxes, the chemical origin of the U-shaped NO\u2093 curve (Phase 2).",
   "Decouple \u03c4\u2081 \u2260 \u03c4\u2082 and replace instantaneous secondary mixing with finite-rate progressive dilution (Phase 3).",
   "Extend to elevated pressure, compressor-discharge preheat and wall heat loss (Phase 4).",
   "Establish the statistical significance and uncertainty of every headline result.",
   "Deliver a reproducible, version-controlled code base with documented outputs."], numbered=True)
H("1.4 Research questions", 2)
B(["By how much, and under which conditions, does staging reduce NO\u2093 relative to single-stage combustion?",
   "Which elementary reactions produce the left branch, the valley and the right branch of the NO\u2093 U-curve?",
   "Does a short rich-zone residence time reduce unburnt intermediate carry-over?",
   "Does finite-rate secondary mixing change the NO\u2093 response?",
   "How do pressure, preheat and liner cooling alter the optimum \u03c6\u2081?",
   "Which of these effects are statistically significant, and how large are they?"], numbered=True)
PB()

# ================================================================ CH 2
H("Chapter 2: Literature Survey", 1)
H("2.1 Ammonia oxidation kinetics", 2)
J("Tamaoki et al. developed a 33-species, 228-reaction ammonia mechanism from the Zhang\u2013Otomo model and showed that "
  "NH\u2082 branching reactions, notably NH\u2082 + HO\u2082 and NH\u2082 + NH\u2082, strongly affect ammonia consumption and hydrogen "
  "generation at intermediate temperatures [1]. Review papers describe ammonia as a fuel with narrow flammability, low "
  "burning velocity and high NO\u2093 potential, with hydrogen blending and staged combustion as the principal mitigation "
  "routes [3, 4].")
H("2.2 Nitrogen chemistry and de-NO\u2093", 2)
J("Nitrogen oxide chemistry in combustion has been reviewed by Miller and Bowman [5] and, for ammonia-relevant systems, "
  "by Glarborg et al. [4]. The key competition is between oxidation of NH\u2093/HNO to NO (NH + O\u2082, HNO + OH) and reduction "
  "of NO by NH\u2082 and NH to N\u2082 or N\u2082O/NNH (NH\u2082 + NO, NH + NO), the basis of thermal de-NO\u2093 [6, 7]. These are the "
  "reactions interrogated in the rate-of-production analysis here.")
H("2.3 Reactor-network modelling with Cantera", 2)
J("Cantera provides ideal-gas thermodynamics, kinetics and reactor-network objects [2]. PSR networks are a standard "
  "low-cost way to explore staging and mixing effects before CFD, with the caveat that they omit spatial structure.")
H("2.4 Gap addressed", 2)
J("Mechanisms and flame studies describe the chemistry but do not provide, for a staged NH\u2083/H\u2082 reactor, "
  "(i) a quantitative baseline-controlled staging benefit, (ii) a flux-level explanation of the NO\u2093 U-curve, (iii) "
  "the role of independent stage residence times and finite secondary mixing, and (iv) the shift of these results under "
  "gas-turbine pressure, preheat and heat loss. This report addresses these four points and attaches statistical "
  "support to each.")
PB()

# ================================================================ CH 3
H("Chapter 3: Problem Formulation and Governing Relations", 1)
H("3.1 Fuel composition and air allocation", 2)
J("The fuel is an NH\u2083/H\u2082 mixture with x_H\u2082 = 1 \u2212 x_NH3. For one mole of fuel the stoichiometric O\u2082 demand is "
  "0.75 x_NH3 + 0.50 x_H\u2082, giving A_stoic = 4.76 \u00d7 that value in air moles. The primary and total air and the "
  "secondary-air fraction follow from the equivalence ratios:")
EQ("A\u2081 = A_stoic / \u03c6\u2081", 1)
EQ("A_total = A_stoic / \u03c6", 2)
EQ("A\u2082 / A_total = 1 \u2212 \u03c6/\u03c6\u2081", 3)
J("With \u03c6 = 0.9 the secondary stage receives 10% of the air at \u03c6\u2081 = 1.0 and 55% at \u03c6\u2081 = 2.0.")
FIGURE(MID_IMG / "image1.png", "Air redistribution between stages as a function of \u03c6\u2081 at \u03c6 = 0.9.", 11)
H("3.2 Perfectly stirred reactor model", 2)
J("Each stage is a constant-pressure, adiabatic (unless stated) PSR with species and energy balances")
EQ("d(m Y_k)/dt = \u1e41 (Y_k,in \u2212 Y_k) + V \u03c9\u0307_k W_k", 4)
EQ("\u1e41 = m / \u03c4", 5)
J("The reactor is integrated in time until temperature and composition change by less than 10\u207b\u2078 (relative), which is "
  "more robust than a steady-state Newton solve for stiff NH\u2083 chemistry. The primary outlet is passed unchanged to the "
  "secondary stage, where the secondary air is added.")
FIGURE(MID_IMG / "image2.png", "Two-stage PSR representation used throughout the study.", 12)
H("3.3 Decoupled residence times (Phase 3)", 2)
J("The two stages receive independent residence times \u03c4\u2081 and \u03c4\u2082 (\u1e41\u2081 = m\u2081/\u03c4\u2081, \u1e41\u2082 = m\u2082/\u03c4\u2082). The total "
  "residence time is \u03c4\u2081 + \u03c4\u2082 and the ratio \u03c4\u2081/\u03c4\u2082 is a sizing variable.")
H("3.4 Finite-rate secondary mixing (Phase 3)", 2)
J("Instantaneous mixing is replaced by a progressive dilution sequence. The secondary air is divided into N equal "
  "parcels \u0394n = n_air,2/N and the secondary residence time into N sub-intervals \u03c4_sub = \u03c4\u2082/N. In sub-stage k the "
  "product of sub-stage k \u2212 1 is mixed with one parcel and reacted before entering sub-stage k + 1. N = 1 recovers "
  "instantaneous mixing; N = 3 and 5 approximate an air-injection plug-flow reactor with increasing resolution.")
H("3.5 Gas-turbine conditions (Phase 4)", 2)
J("Operating pressure P, inlet (compressor-discharge) temperature T_in and wall heat loss are added. Wall heat loss "
  "enters the energy equation of each reactor as")
EQ("Q\u0307_wall = U A (T \u2212 T_wall)", 6)
J("with U in W m\u207b\u00b2 K\u207b\u00b9 and A = 0.25 m\u00b2.")
H("3.6 Kinetic diagnostics", 2)
J("For each stage the net rate of progress of every reaction is evaluated at the reactor state. The contribution of a "
  "reaction to NO is its net rate multiplied by the net stoichiometric coefficient of NO (kmol m\u207b\u00b3 s\u207b\u00b9). Summing these "
  "over reactions gives the net NO production rate, and the largest positive and negative terms define the "
  "production and consumption pathways. Nitrogen-flux graphs are generated with Cantera\u2019s reaction-path diagrams.")
H("3.7 Metrics", 2)
EQ("NO\u2093 = NO + NO\u2082", 7)
EQ("Staging benefit (%) = 100 (NO\u2093,single \u2212 NO\u2093,staged) / NO\u2093,single", 8)
EQ("\u0394T = T\u2082 \u2212 T\u2081,   \u0394NO\u2093 = NO\u2093,\u2082 \u2212 NO\u2093,\u2081", 9)
H("3.8 Statistical framework", 2)
J("The simulations are deterministic, so there is no sampling noise in the usual sense. Significance is therefore "
  "assessed over the sampled operating conditions: a result is significant if the effect is too large and consistent "
  "across conditions to be explained by chance variation of the response with the other factors. Four tools are used:")
B(["Type-II ANOVA (partial F-tests with dummy-coded factors) for factorial grids; effect size is the partial R\u00b2.",
   "Paired tests for baseline-controlled comparisons: paired t-test, Wilcoxon signed-rank test, binomial sign test, "
   "with Cohen\u2019s d_z as effect size (staged vs single stage; N = 1 vs 3 vs 5; adiabatic vs cooled; 1 vs 30 atm).",
   "Rank-trend tests: Spearman correlation per \u03c6\u2081 level, tested across levels by a one-sample t-test; Friedman test for "
   "repeated measures across N.",
   "Non-parametric bootstrap (10 000 resamples, fixed seed) for 95% confidence intervals [8]."])
J("Because the Wilcoxon test is rank-based [9] it does not require normality of the NO\u2093 differences, which are "
  "right-skewed. Where p-values underflow double precision they are reported as < 10\u207b\u00b3\u2070\u2070. "
  "With deterministic data, n is the number of operating conditions, so large n inflates significance; effect sizes and "
  "confidence intervals are therefore reported alongside p-values.")
PB()

# ================================================================ CH 4
H("Chapter 4: Numerical Methodology", 1)
H("4.1 Software, mechanism and code organisation", 2)
J("Simulations use Cantera 3.0 and the Tamaoki et al. (2024) NH\u2083 mechanism (33 species, 228 reactions) shipped in the "
  "repository as mechanisms/TamaokiNH3.yaml [1, 2]. The mid-semester report could not analyse the mechanism file; it is now "
  "included, which is what made the baseline and ROP phases possible.")
TABLE(pd.DataFrame([
    ["double_stage/staged_combustion.py", "Two-stage core: equal \u03c4, decoupled \u03c4, finite mixing, gas-turbine conditions"],
    ["single_stage/single_stage_baseline.py", "Phase 1 single-stage baseline and matched comparison"],
    ["double_stage/rate_of_production_analysis.py", "Phase 2 ROP and reaction-path diagrams"],
    ["double_stage/decoupled_mixing_analysis.py", "Phase 3 \u03c4\u2081/\u03c4\u2082 grid and finite-mixing comparison"],
    ["double_stage/gas_turbine_regimes_analysis.py", "Phase 4 pressure, preheat, heat-loss sweeps"],
    ["double_stage/statistical_significance_analysis.py", "Statistical tests and bootstrap CIs for all phases"],
    ["docs/reports/build_end_semester_report.py", "Regenerates this report from the result CSV files"],
], columns=["Module", "Purpose"]), "Code modules.", fs=9, widths=[7, 8.5])
H("4.2 Computational campaigns", 2)
TABLE(pd.DataFrame([
    ["Main study", "x_NH3 0\u20131 (11), \u03c6\u2081 1.0\u20132.0 (11), \u03c4 20\u2013100 ms (5)", "300 K, 1 atm", "605 (586 conv.)"],
    ["Phase 1 baseline", "x_NH3 (11), \u03c4 20\u2013200 ms (8)", "300 K, 1 atm", "88 single-stage; 469 matched"],
    ["Phase 2 ROP", "x_NH3 = 0.5, \u03c4 = 60 ms, \u03c6\u2081 1.0\u20132.0 (11)", "300 K, 1 atm", "11 (both stages)"],
    ["Phase 3a \u03c4\u2081/\u03c4\u2082", "x_NH3 = 0.5, \u03c6\u2081 \u2208 {1.2,1.4,1.6,1.8,2.0}, \u03c4\u2081 10\u201350, \u03c4\u2082 20\u2013100 ms", "300 K, 1 atm", "125"],
    ["Phase 3b mixing", "x_NH3 = 0.5, \u03c6\u2081 1.0\u20132.0 (11), N = 1, 3, 5; \u03c4\u2081 = 30, \u03c4\u2082 = 60 ms", "300 K, 1 atm", "33"],
    ["Phase 4a pressure", "x_NH3 = 0.5, \u03c6\u2081 (11), P = 1, 5, 10, 20, 30 atm; \u03c4\u2081 = 40, \u03c4\u2082 = 60 ms", "300 K", "55"],
    ["Phase 4b preheat", "\u03c6\u2081 (7), T_in = 300, 450, 600, 750 K", "10 atm", "28"],
    ["Phase 4c heat loss", "\u03c6\u2081 (7), U = 0, 500, 1500, 3000 W m\u207b\u00b2 K\u207b\u00b9", "15 atm, 650 K", "28"],
], columns=["Campaign", "Parameter space", "Fixed conditions", "Cases"]), "Simulation campaigns; all at \u03c6 = 0.9 overall. All Phase 1\u20134 cases converged except where noted.", fs=8.5, widths=[2.6, 7.2, 2.7, 2.9])
H("4.3 Verification", 2)
J("The overall equivalence ratio is preserved to 1.1 \u00d7 10\u207b\u00b9\u2076 (absolute) in converged cases. Phase 3 and 4 sweeps "
  "converged in all 125 + 33 + 55 + 28 + 28 cases. Case-to-case consistency was checked by recovering the main-study values "
  "(e.g. \u03c4\u2081 = \u03c4\u2082 slices and N = 1 reproduce the instantaneous-mixing results) and the decoupled/finite-mixing "
  "tests show consistent trends across \u03c6\u2081.")
H("4.4 Limitations of the numerical approach", 2)
B(["Zero-dimensional ideal mixing within each reactor (finite-rate mixing is approximated by a reactor sequence).",
   "A single mechanism is used; no mechanism-uncertainty study was done.",
   "Deterministic output: confidence intervals describe variability across operating conditions, not measurement noise.",
   "19 main-study cases did not converge and are excluded; Phase 1 comparisons therefore use 469 matched pairs."])
PB()

# ================================================================ CH 5
H("Chapter 5: Results and Discussion", 1)
H("5.1 Recap of the 605-case parametric study", 2)
J("The principal findings of the mid-semester campaign are reproduced here as the reference against which the new "
  "phases are measured. Final temperature ranges from 1908 to 2349 K and falls from 2335 K (pure H\u2082) to 1930 K (pure NH\u2083); "
  "final NO\u2093 ranges from 891 to 6772 ppm, is non-monotonic in x_NH3 and \u03c6\u2081, and H\u2082 slip falls from 8787 to 1011 ppm "
  "with NH\u2083 fraction.")
FIGURE(MID_IMG / "image3.png", "Main effect of NH\u2083 fraction on final temperature (mean over converged cases).", 11)
FIGURE(MID_IMG / "image6.png", "Mean final NO\u2093 versus \u03c6\u2081: the U-shaped response investigated in Phase 2.", 11)
FIGURE(MID_IMG / "image10.png", "Final NO\u2093 map over NH\u2083 fraction and \u03c6\u2081 at \u03c4 = 60 ms.", 11)
eta_tab = pd.DataFrame([
    ["T_final", "98.1%", "0.6%", "0.4%"], ["NO\u2093", "18.6%", "25.4%", "2.8%"],
    ["H\u2082 slip", "90.7%", "3.1%", "2.9%"], ["\u0394T (stage 2)", "0.3%", "99.3%", "0.0%"],
    ["\u0394NO\u2093 (stage 2)", "33.2%", "48.0%", "0.2%"]], columns=["Response", "NH\u2083 fraction \u03b7\u00b2", "\u03c6\u2081 \u03b7\u00b2", "\u03c4 \u03b7\u00b2"])
TABLE(eta_tab, "Main-effect variance fractions from the 605-case study (mid-semester).", widths=[4, 3.5, 3.5, 3.5])

# ------------------------------------------------------------ Phase 1
H("5.2 Phase 1: Single-stage baseline and quantified staging benefit", 2)
J("A single PSR with identical fuel blends, \u03c6 = 0.9, inlet state, and with total residence time equal to \u03c4\u2081 + \u03c4\u2082 "
  "of the staged configuration was simulated for 11 blends and 8 residence times (88 cases) and matched to 469 converged "
  "staged cases. For these 469 points the mean NO\u2093 reduction is "
  f"{cmp_.NOx_reduction_pct.mean():.1f}% and the median reduction is {cmp_.NOx_reduction_pct.median():.1f}%; staging gives "
  f"lower NO\u2093 in {(cmp_.NOx_reduction_pct > 0).mean() * 100:.1f}% of cases. The maximum reduction is {cmp_.NOx_reduction_pct.max():.1f}% "
  "(x_NH3 = 0.20, \u03c6\u2081 = 2.0, \u03c4 = 20 ms: 10 158 \u2192 973 ppm).")
g = cmp_.groupby("NH3_frac").agg(single=("NOx_single_ppm", "mean"), staged=("NOx_ppm", "mean"),
                                 red=("NOx_reduction_pct", "mean"), mx=("NOx_reduction_pct", "max"),
                                 mn=("NOx_reduction_pct", "min"), n=("NOx_ppm", "size")).reset_index()
t1 = pd.DataFrame({"x_NH3": g.NH3_frac.round(1), "n": g.n, "Single-stage NO\u2093 (ppm)": g.single.round(0).astype(int),
                   "Staged NO\u2093 (ppm)": g.staged.round(0).astype(int), "Mean reduction (%)": g.red.round(1),
                   "Best (%)": g.mx.round(1), "Worst (%)": g.mn.round(1)})
TABLE(t1, "Single-stage vs staged NO\u2093 by fuel blend (means over matched \u03c6\u2081, \u03c4).", widths=[1.8, 1.4, 3, 2.6, 2.6, 2, 2])
FIGURE(PLOTS / "baseline_nox_comparison.png", "Staged versus single-stage NO\u2093 across fuel blends.", 14)
FIGURE(PLOTS / "staging_benefit_heatmap.png", "Staging benefit map: NO\u2093 reduction over x_NH3 and \u03c6\u2081.", 14)
J("The benefit is strongly blend dependent. Pure H\u2082 is the only fuel for which staging is a net penalty "
  "(down to \u221268.4%): there is no fuel nitrogen to divert to N\u2082, so the extra high-temperature residence time simply adds "
  "thermal NO. For x_NH3 \u2265 0.10 the mean reduction is 60.1% (95% CI 57.6\u201362.5%). At high \u03c6\u2081 and NH\u2083-rich blends staging can also "
  "lose (x_NH3 = 0.8, \u03c6\u2081 = 2.0: \u221247.6%) because of the right-branch surge explained in Section 5.3. Thus staging is "
  "effective only inside a window of \u03c6\u2081 that shifts with fuel composition.")
FIGURE(PLOTS / "baseline_tradeoff_scatter.png", "NO\u2093 versus unburnt-fuel slip trade-off for staged and single-stage cases.", 12)

# ------------------------------------------------------------ Phase 2
H("5.3 Phase 2: Rate-of-production and reaction-pathway analysis", 2)
J("For x_NH3 = 0.5 and \u03c4 = 60 ms the full net-rate-of-progress vector was extracted for both stages at all 11 \u03c6\u2081 "
  "values, and NO production was decomposed by reaction. Table 6 gives the stage-resolved NO\u2093 and the intermediates "
  "leaving Stage 1.")
t2 = rop[["Phi_1", "T_stage1_K", "O2_stage1_pct", "NOx_stage1_ppm", "Delta_NOx_ppm", "NOx_stage2_ppm",
          "NH3_stage1_ppm", "NH2_stage1_ppm", "NH_stage1_ppm"]].copy()
t2.columns = ["\u03c6\u2081", "T\u2081 (K)", "O\u2082 Stage 1 (%)", "NO\u2093 Stage 1 (ppm)", "\u0394NO\u2093 Stage 2 (ppm)",
              "NO\u2093 final (ppm)", "NH\u2083 out of S1 (ppm)", "NH\u2082 out of S1 (ppm)", "NH out of S1 (ppm)"]
for c in t2.columns[1:]:
    t2[c] = t2[c].round(1 if c not in ("O\u2082 Stage 1 (%)",) else 2)
TABLE(t2, "Stage-resolved NO\u2093 and intermediates (x_NH3 = 0.5, \u03c4 = 60 ms).", fs=8)
FIGURE(PLOTS / "rop_u_curve_pathway_mechanism.png",
       "Decomposition of the U-curve: Stage-1 NO\u2093 (monotonic fall), Stage-2 NO\u2093 generation (monotonic rise) and amine carry-over.", 15)
J("The U-curve is therefore not a single phenomenon. Stage-1 NO\u2093 falls monotonically from 4400 to 29 ppm as oxygen is "
  "removed and temperature drops (2168 \u2192 1720 K), shutting down thermal and prompt NO. Stage-2 NO\u2093 generation rises "
  "monotonically from \u2212191 to +3586 ppm as the NH\u2082 leaving Stage 1 grows from 5.2 to 85.7 ppm and unburnt NH\u2083 from 22 to "
  "about 8560 ppm (Table 6). The sum of a falling and a rising monotonic term has a "
  "minimum, here at \u03c6\u2081 \u2248 1.3 (986 ppm).")
# Top NO reactions per regime
def top_rx(phi, stage, k=4):
    d = ropr[(ropr.Phi_1.round(2) == phi) & (ropr.Stage == stage)].copy()
    pos = d.nlargest(k, "NO_contribution_kmol_m3_s")[["Equation", "NO_contribution_kmol_m3_s"]]
    neg = d.nsmallest(k, "NO_contribution_kmol_m3_s")[["Equation", "NO_contribution_kmol_m3_s"]]
    return pos, neg
rows = []
for phi, stage in [(1.0, "Stage 1"), (1.3, "Stage 1"), (1.3, "Stage 2"), (2.0, "Stage 2")]:
    pos, neg = top_rx(phi, stage)
    for _, r in pos.iterrows():
        rows.append([phi, stage, "NO source", r.Equation, f"{r.NO_contribution_kmol_m3_s:+.2e}"])
    for _, r in neg.iterrows():
        rows.append([phi, stage, "NO sink", r.Equation, f"{r.NO_contribution_kmol_m3_s:+.2e}"])
TABLE(pd.DataFrame(rows, columns=["\u03c6\u2081", "Stage", "Role", "Reaction", "NO rate (kmol m\u207b\u00b3 s\u207b\u00b9)"]),
      "Dominant NO-producing and NO-consuming reactions in selected regimes (from rop_no_reactions_by_phi1.csv).", fs=8,
      widths=[1.2, 1.7, 2, 6.5, 3.5])
FIGURE(PLOTS / "rop_top_no_reactions_stage1_vs_stage2.png", "Dominant elementary NO source and sink reactions in each stage across the three regimes.", 15)
J("Three regimes follow from the fluxes:")
B(["Left branch (\u03c6\u2081 = 1.0\u20131.2): a hot, oxygen-containing Stage 1 forms NO directly (HNO + OH \u21c4 H\u2082O + NO, "
   "NH + O\u2082 \u21c4 NO + OH, plus Zeldovich steps) and Stage 2 only adds a little.",
   "Valley (\u03c6\u2081 \u2248 1.2\u20131.4): Stage 1 is oxygen-lean enough that NH\u2082 + NO \u21c4 N\u2082 + H\u2082O and NH + NO \u21c4 N\u2082 + OH "
   "(thermal de-NO\u2093) consume NO, while the amine carry-over into Stage 2 is still moderate (23 ppm NH\u2082 at \u03c6\u2081 = 1.3).",
   "Right branch (\u03c6\u2081 \u2265 1.6): Stage 1 is oxygen-starved, so NH\u2083 and NH\u2082 leave unburnt; the large secondary air "
   "flow (45\u201355% of the air) oxidises them through HNO + OH \u21c4 H\u2082O + NO (about 14\u00d7 the \u03c6\u2081 = 1.0 rate) and "
   "NH + O\u2082 \u21c4 NO + OH (more than 5000\u00d7 higher)."])
J("The nitrogen-flux graphs below show the same picture graphically: at \u03c6\u2081 = 1.0 the NO node dominates the nitrogen "
  "outflow of Stage 1, while at \u03c6\u2081 = 1.8 the Stage-2 graph is dominated by the NH\u2093 \u2192 HNO/NO arrows.")
FIGURE(PLOTS / "reaction_path_phi1_1p0_stage1.png", "Nitrogen reaction-path diagram, Stage 1, \u03c6\u2081 = 1.0 (x_NH3 = 0.5, \u03c4 = 60 ms).", 13)
FIGURE(PLOTS / "reaction_path_phi1_1p8_stage2.png", "Nitrogen reaction-path diagram, Stage 2, \u03c6\u2081 = 1.8.", 13)

# ------------------------------------------------------------ Phase 3
H("5.4 Phase 3: Reactor architecture and mixing physics", 2)
H("5.4.1 Decoupled residence times", 3)
J("The grid \u03c4\u2081 \u2208 {10,\u202620,\u202630,\u202640,\u202650} ms \u00d7 \u03c4\u2082 \u2208 {20,\u202640,\u202660,\u202680,\u2026100} ms was run at five values of \u03c6\u2081 (x_NH3 = 0.5, 125 cases, all converged).")
a = dec.pivot_table(index="Phi_1", columns="Tau_1_ms", values="NOx_final_ppm", aggfunc="mean").round(0).astype(int)
a.columns = [f"\u03c4\u2081 = {int(c)} ms" for c in a.columns]
a.insert(0, "\u03c6\u2081", a.index)
TABLE(a.reset_index(drop=True), "Final NO\u2093 (ppm) versus \u03c4\u2081, averaged over \u03c4\u2082.", widths=[1.5, 2.4, 2.4, 2.4, 2.4, 2.4])
b = dec.pivot_table(index="Phi_1", columns="Tau_1_ms", values="NH2_primary_ppm", aggfunc="mean").round(1)
b.columns = [f"\u03c4\u2081 = {int(c)} ms" for c in b.columns]
b.insert(0, "\u03c6\u2081", b.index)
TABLE(b.reset_index(drop=True), "NH\u2082 leaving the primary reactor (ppm) versus \u03c4\u2081, averaged over \u03c4\u2082.", widths=[1.5, 2.4, 2.4, 2.4, 2.4, 2.4])
FIGURE(PLOTS / "decoupled_tau_2d_contour.png", "Final NO\u2093 over (\u03c4\u2081, \u03c4\u2082) at \u03c6\u2081 = 1.2, 1.4, 1.6, 2.0.", 15)
FIGURE(PLOTS / "decoupled_tau_ratio_tradeoff.png", "Effect of the sizing ratio \u03c4\u2081/\u03c4\u2082 on NO\u2093 and fuel slip.", 13)
J("A short rich residence time does not mitigate carry-over: the opposite holds. Increasing \u03c4\u2081 from 10 to 50 ms lowers "
  "primary NH\u2082 at \u03c6\u2081 = 2.0 from 282 to 157 ppm and at \u03c6\u2081 = 1.2 from 48 to 19 ppm, because a longer rich residence time lets "
  "the amine pool relax towards its equilibrium and consume NO. Final NO\u2093 falls correspondingly (\u03c6\u2081 = 2.0: 4105 \u2192 3726 ppm; "
  "\u03c6\u2081 = 1.2: 1808 \u2192 1201 ppm). The secondary residence time acts in a different way: a longer \u03c4\u2082 reduces right-branch "
  "NO\u2093 (\u03c6\u2081 = 2.0: 4438 \u2192 3490 ppm, \u03c4\u2082 = 20 \u2192 100 ms) and NH\u2083 slip, but slightly increases NO\u2093 near the valley "
  "(\u03c6\u2081 = 1.2: 1367 \u2192 1484 ppm) because more time is available for thermal NO. The overall minimum of the grid is "
  "1124 ppm at \u03c6\u2081 = 1.2, \u03c4\u2081 = 50 ms, \u03c4\u2082 = 20 ms, i.e. a long rich zone and a short lean zone. This is a sizing "
  "recommendation that equal-\u03c4 modelling could not produce.")
H("5.4.2 Finite-rate secondary mixing", 3)
J("Final NO\u2093 for instantaneous mixing (N = 1) and progressive dilution (N = 3, 5) at x_NH3 = 0.5, \u03c4\u2081 = 30 ms, \u03c4\u2082 = 60 ms:")
pv_ = fm.pivot(index="Phi_1", columns="N_mixing_stages", values="NOx_final_ppm")
t3 = pd.DataFrame({"\u03c6\u2081": pv_.index.round(1), "N = 1": pv_[1].round(0).astype(int), "N = 3": pv_[3].round(0).astype(int),
                   "N = 5": pv_[5].round(0).astype(int), "Reduction N = 5 vs 1 (%)": ((pv_[5] / pv_[1] - 1) * 100).round(1)})
TABLE(t3, "Effect of progressive secondary dilution on final NO\u2093 (ppm).", widths=[1.8, 2.5, 2.5, 2.5, 4.5])
FIGURE(PLOTS / "finite_mixing_nox_comparison.png", "NO\u2093 U-curve for N = 1, 3, 5 secondary dilution stages.", 13)
FIGURE(PLOTS / "finite_mixing_temperature_trajectories.png", "Temperature trajectory through the progressive mixing stages.", 13)
J("Finite-rate mixing flattens the U-curve. At \u03c6\u2081 = 2.0 final NO\u2093 falls from 3693 ppm (instantaneous) to 640 ppm (N = 3) "
  "and 433 ppm (N = 5), \u221288.3%; at the left branch the gain is small (\u22128.8% at \u03c6\u2081 = 1.0). Physically, adding air in "
  "small parcels keeps the intermediate stages sub-stoichiometric and hot, so NH\u2082 + NO and NH + NO keep consuming "
  "NO instead of the NH\u2093 being oxidised abruptly. Intermediate stages pass through \u03c6 \u2248 1 (T_peak \u2248 2180 K), "
  "but the short sub-stage time (12 ms at N = 5) limits thermal NO. The practical implication is that the "
  "right-branch penalty of Phase 2 is partly an artefact of assuming instantaneous mixing, and that a "
  "real combustor with progressive air injection can run at deeper staging than instantaneous-mixing models allow. "
  "This finding is a model result; it depends on the sub-stage equal-split assumption and has not been validated "
  "against experiment.")

# ------------------------------------------------------------ Phase 4
H("5.5 Phase 4: Gas-turbine operating regimes", 2)
H("5.5.1 Elevated pressure", 3)
pp = ps.pivot(index="Phi_1", columns="P_atm", values="NOx_ppm")
t4 = pd.DataFrame({"\u03c6\u2081": pp.index.round(1)})
for c in pp.columns:
    t4[f"{int(c)} atm"] = pp[c].round(0).astype(int).values
TABLE(t4, "Final NO\u2093 (ppm) versus pressure (x_NH3 = 0.5, 300 K, \u03c4\u2081 = 40 ms, \u03c4\u2082 = 60 ms).", widths=[1.8, 2.5, 2.5, 2.5, 2.5, 2.5])
FIGURE(PLOTS / "pressure_effect_nox_u_curve.png", "NO\u2093 U-curve at 1\u201330 atm.", 13)
FIGURE(PLOTS / "pressure_no2_fraction_shift.png", "NO\u2082/NO\u2093 ratio versus pressure.", 11)
J("Pressure suppresses the left branch strongly (\u03c6\u2081 = 1.0: 4548 \u2192 1753 ppm, \u221261.5%, from 1 to 30 atm) and the "
  "extreme right branch (\u03c6\u2081 = 2.0: 3652 \u2192 2129 ppm, \u221241.7%), but increases NO\u2093 in the valley and "
  "mid-right region (\u03c6\u2081 = 1.3: 1072 \u2192 1604 ppm). As a result the minimum shifts from \u03c6\u2081 = 1.3 (1 atm) through 1.2 (5 atm) to "
  "1.1 (10\u201330 atm), and the lowest NO\u2093 stays within 1023\u20131281 ppm. The NO\u2082/NO\u2093 ratio rises from "
  f"{ps[ps.P_atm == 1.0].NO2_ratio.mean() * 100:.3f}% to {ps[ps.P_atm == 30.0].NO2_ratio.mean() * 100:.3f}% (mean over \u03c6\u2081), consistent with faster "
  "H + O\u2082 + M \u21c4 HO\u2082 + M recombination and NO + HO\u2082 \u21c4 NO\u2082 + OH. This mechanistic explanation is inferred from the "
  "kinetics; it was not separately confirmed by a pressure-resolved ROP analysis.")
H("5.5.2 Compressor-discharge preheat", 3)
pw = pre.pivot(index="Phi_1", columns="T_in_K", values="NOx_ppm")
t5 = pd.DataFrame({"\u03c6\u2081": pw.index.round(1)})
for c in pw.columns:
    t5[f"{int(c)} K"] = pw[c].round(0).astype(int).values
mt = pre.groupby("T_in_K").agg(Nx=("NOx_ppm", "mean"), Tf=("T_final_K", "mean"))
t5.loc[len(t5)] = ["mean NO\u2093"] + [int(round(v)) for v in mt.Nx]
t5.loc[len(t5)] = ["mean T_final (K)"] + [int(round(v)) for v in mt.Tf]
TABLE(t5, "Final NO\u2093 (ppm) versus inlet temperature at 10 atm.", widths=[3, 2.4, 2.4, 2.4, 2.4])
FIGURE(PLOTS / "preheat_flame_temperature_and_nox.png", "Final temperature and NO\u2093 versus inlet temperature.", 13)
J("Flame temperature rises by 0.66 K per kelvin of preheat (100 K per 150 K) and mean NO\u2093 by about 6.1 ppm per kelvin "
  "(1957 \u2192 4699 ppm over 300 \u2192 750 K), the Arrhenius sensitivity of the Zeldovich and N\u2082O routes. "
  "At 750 K the best staged NO\u2093 is still 4546 ppm at \u03c6\u2081 = 1.2: preheat shifts the whole curve upward, so "
  "gas-turbine pressure ratio forces additional NO\u2093 control.")
H("5.5.3 Combustor liner cooling", 3)
hh = hl.pivot(index="Phi_1", columns="U_wall_W_m2K", values="NOx_ppm")
t6 = pd.DataFrame({"\u03c6\u2081": hh.index.round(1)})
for c in hh.columns:
    t6[f"U = {int(c)}"] = hh[c].round(0).astype(int).values
t6["\u0394 (U = 3000)"] = (hh[3000.0] - hh[0.0]).round(0).astype(int).values
mt = hl.groupby("U_wall_W_m2K").agg(Tf=("T_final_K", "mean"), sl=("NH3_slip_ppm", "mean"))
TABLE(t6, "Final NO\u2093 (ppm) versus wall heat-transfer coefficient (15 atm, 650 K).", widths=[1.8, 2.3, 2.3, 2.3, 2.3, 2.7])
FIGURE(PLOTS / "wall_heat_loss_mitigation.png", "NO\u2093 reduction by liner heat loss.", 13)
J(f"Heat loss at U = 3000 W m\u207b\u00b2 K\u207b\u00b9 lowers the mean final temperature by {mt.Tf.iloc[0] - mt.Tf.iloc[-1]:.0f} K "
  f"({mt.Tf.iloc[0]:.0f} \u2192 {mt.Tf.iloc[-1]:.0f} K) and NO\u2093 by 286\u2013431 ppm depending on \u03c6\u2081 (mean 386 ppm). Mean NH\u2083 slip stays "
  f"below {mt.sl.max():.2f} ppm, so within this model cooling does not threaten burnout. Real liner cooling also affects "
  "flame stability and CO-like burnout in ways a PSR cannot represent.")

# ------------------------------------------------------------ Statistics
H("5.6 Statistical significance of the results", 2)
J("All tests are produced by double_stage/statistical_significance_analysis.py and stored in "
  "results/statistical_significance_summary.csv (43 tests). Table 14 gives the main-study ANOVA, Table 15 the baseline-controlled "
  "and architecture tests, Table 16 the Phase 4 tests.")
s1 = stat[(stat.Phase == "Main 605-case") & stat.Test.str.startswith("Type-II")].copy()
s1["Factor"] = s1.Test.str.extract(r"\((.*)\)")
s1["partial R\u00b2"] = s1.Effect.str.extract(r"=([0-9.]+)")[0]
s1 = s1[["Quantity", "Factor", "Statistic", "partial R\u00b2", "p_value"]]
s1.columns = ["Response", "Factor", "F", "partial R\u00b2", "p"]
s1["p"] = s1.p.map(pfmt)
TABLE(s1, "Type-II ANOVA of the 586 converged main-study cases (df = 10 or 4 numerator, 561 denominator).", fs=8.5, widths=[3.2, 2.6, 2.2, 2.4, 2.6])
FIGURE(STAT_FIG1, "(a) Distribution and 95% bootstrap CI of the staging benefit; (b) partial R\u00b2 of each factor.", 15.5)
J("For T_final, H\u2082 slip, \u0394T and NO\u2093 the factor that dominated the \u03b7\u00b2 analysis is also overwhelmingly significant "
  "(p \u2264 10\u207b\u00b3\u00b3), and the \u03c4 effect on NO\u2093 (partial R\u00b2 = 0.029) is small but significant (p = 5 \u00d7 10\u207b\u2076). "
  "The \u03c4 effect on \u0394NO\u2093 (p = 0.095) and, at the 1% level, on \u0394T (p = 0.035) is not significant, which supports the "
  "mid-semester statement that residence time mainly matters for the absolute state, not the stage-wise change. "
  "Within each fuel/\u03c6\u2081 cell, NO\u2093 decreases with \u03c4 (mean Spearman \u03c1 = \u22120.43, t-test p = 1.8 \u00d7 10\u207b\u2077).")
s2 = stat[stat.Phase.isin(["Phase 1", "Phase 2", "Phase 3"])].copy()
s2 = s2[["Phase", "Test", "Quantity", "N", "Statistic", "p_value", "Effect", "CI95"]]
s2["p_value"] = s2.p_value.map(pfmt)
s2.columns = ["Phase", "Test", "Quantity", "N", "Stat.", "p", "Effect size", "95% CI"]
TABLE(s2, "Statistical tests for Phases 1\u20133.", fs=7, widths=[1.2, 3.6, 2, 0.9, 1.4, 1.6, 3.2, 2.2])
s3 = stat[stat.Phase == "Phase 4"].copy()
s3 = s3[["Test", "Quantity", "N", "Statistic", "p_value", "Effect", "CI95"]]
s3["p_value"] = s3.p_value.map(pfmt)
s3.columns = ["Test", "Quantity", "N", "Stat.", "p", "Effect size", "95% CI"]
TABLE(s3, "Statistical tests for Phase 4.", fs=7.5, widths=[4.2, 1.8, 0.8, 1.4, 1.5, 3.6, 2.2])
J("Interpretation by phase:")
B([f"Phase 1: staging reduces NO\u2093 by {cmp_.NOx_reduction_pct.mean():.1f}% on average (95% bootstrap CI {lo:.1f}\u2013{hi:.1f}%); the paired "
   "difference is 4167 ppm (CI 3921\u20134409 ppm, Cohen\u2019s d_z = 1.56, a very large effect); the Wilcoxon p = 5 \u00d7 10\u207b\u2077\u2076 and the "
   "sign test (439 of 469 wins) p = 3 \u00d7 10\u207b\u2079\u2074. The benefit is significant and not driven by a few outliers. The exceptions "
   "(30 cases) are concentrated in pure H\u2082 and extreme right-branch conditions.",
   "Phase 2: the monotonic Stage-1 NO\u2093 decline and the monotonic Stage-2 rise are both perfectly rank-correlated with \u03c6\u2081 "
   "(\u03c1 = \u22121 and +1, n = 11, exact permutation p = 2/11! = 5 \u00d7 10\u207b\u2078), and the curvature of the "
   "total is significantly positive (quadratic coefficient t = 5.19, p = 8 \u00d7 10\u207b\u2074), i.e. the U-shape is statistically real.",
   "Phase 3: both finite-mixing levels reduce NO\u2093 significantly versus instantaneous mixing (N = 3: mean 1145 ppm, p = 0.003; "
   "N = 5: 1287 ppm, p = 0.002; Wilcoxon p = 0.001 for all pairs), and N = 5 is significantly better than N = 3 "
   "(143 ppm, d_z = 2.95, p = 2 \u00d7 10\u207b\u2076; Friedman p = 1.7 \u00d7 10\u207b\u2075). For decoupled residence times \u03c6\u2081 explains 94.7% "
   "of NO\u2093 variance, \u03c4\u2081 2.0% (p = 9 \u00d7 10\u207b\u00b9\u2075) and \u03c4\u2082 1.0% (p = 1 \u00d7 10\u207b\u2078): both residence times matter "
   "significantly but are secondary to \u03c6\u2081. NH\u2083 slip depends on \u03c4\u2082 (partial R\u00b2 = 0.14, p = 3 \u00d7 10\u207b\u00b9\u2078) but not "
   "on \u03c4\u2081 (p = 0.30).",
   "Phase 4: preheat and liner cooling are monotone at every \u03c6\u2081 (\u03c1 = +1 and \u22121; exact sign test p = 0.0156 with 7 levels, the minimum attainable); the adiabatic vs U = 3000 paired "
   "difference is 386 ppm (CI 344\u2013422 ppm, p = 2 \u00d7 10\u207b\u2076) and T_final is linear in T_in (slope 0.663 K/K, R\u00b2 = 1.000). "
   "In contrast the pooled pressure effect is not significant (paired 1 vs 30 atm: mean 440 ppm, CI \u221291 to 1069 ppm, p = 0.19; "
   "mean per-\u03c6\u2081 \u03c1 = \u22120.10, p = 0.69). This is not evidence that pressure is unimportant: it reflects the sign change "
   "of the effect between branches (strongly negative at \u03c6\u2081 = 1.0 and 2.0, positive in the valley), so the pooled test "
   "averages opposing effects. Pressure must therefore be treated as interacting with \u03c6\u2081, not as a main effect."])
J("Caveats: (i) the model is deterministic, so p-values describe consistency across the sampled operating "
  "conditions and not experimental repeatability; (ii) with n = 11 per curve, only large effects are detectable; "
  "(iii) no multiple-testing correction was applied to the 43 tests; under a Bonferroni threshold of 0.05/43 \u2248 1.2 \u00d7 10\u207b\u00b3 the Phase 3 parametric paired t-tests (p = 0.003, 0.002) would not survive, whereas the Wilcoxon tests (p = 0.00098) and the Friedman test (p = 1.7 \u00d7 10\u207b\u2075) do, so the finite-mixing benefit is robust but its pairwise p-values are marginal because only 11 \u03c6\u2081 levels are available; (iv) the single mechanism was not varied, so "
  "mechanism uncertainty is not part of any interval.")

# ------------------------------------------------------------ integrated discussion
H("5.7 Integrated discussion", 2)
J("The four phases form one argument. Staging works (Phase 1) because the rich zone converts fuel nitrogen towards N\u2082 "
  "(Phase 2 valley chemistry); it fails when the rich zone is too rich because the unburnt NH\u2093 is converted to NO by the "
  "secondary air (Phase 2 right branch). The failure mode is controllable by architecture: a longer rich residence time "
  "reduces carry-over and progressive air injection avoids the abrupt oxidation (Phase 3), recovering 88% of the "
  "right-branch penalty. Real gas-turbine conditions (Phase 4) change the optimum rather than remove the benefit: pressure "
  "moves the best \u03c6\u2081 towards 1.1, preheat raises NO\u2093 across the board, and cooling gives a modest, statistically clear "
  "reduction. Taken together, a design window of \u03c6\u2081 \u2248 1.1\u20131.4 with progressive secondary mixing, long rich residence "
  "time and liner cooling is where the model predicts the lowest NO\u2093 at acceptable burnout.")
PB()

# ================================================================ CH 6
H("Chapter 6: Conclusions and Future Work", 1)
H("6.1 Principal findings", 2)
B([f"Phase 1: staging reduces NO\u2093 by {cmp_.NOx_reduction_pct.mean():.1f}% on average over 469 matched cases (95% CI {lo:.1f}\u2013{hi:.1f}%, max 90.4%); it "
   "wins in 93.6% of cases and loses only for pure H\u2082 and extreme right-branch NH\u2083-rich conditions.",
   "Phase 2: the NO\u2093 U-curve is the sum of a monotonic decline of Stage-1 NO\u2093 and a monotonic rise of Stage-2 NO\u2093 generation. The valley "
   "is controlled by NH\u2082/NH + NO de-NO\u2093 steps; the right branch by carry-over of NH\u2082 (5 \u2192 86 ppm) and NH\u2083 oxidised through "
   "HNO + OH and NH + O\u2082.",
   "Phase 3: longer rich residence time reduces carry-over and NO\u2093; progressive five-stage dilution reduces \u03c6\u2081 = 2.0 NO\u2093 by 88.3% "
   "(3693 \u2192 433 ppm).",
   "Phase 4: pressure moves the optimum \u03c6\u2081 from 1.3 to 1.1 and increases NO\u2082/NO\u2093; preheat raises NO\u2093 about 6.1 ppm/K; liner cooling "
   "lowers NO\u2093 by about 386 ppm.",
   "Statistics: all of the above except the pooled pressure effect are significant, with large effect sizes; the pooled pressure effect "
   "is not significant because of branch-dependent sign changes."], numbered=True)
H("6.2 Contribution", 2)
J("The work converts a descriptive parametric map into a baseline-controlled, mechanistically explained and statistically "
  "tested design study, and provides code and data that reproduce every figure and table (see Appendix A).")
H("6.3 Limitations", 2)
B(["Zero-dimensional PSR network: spatial mixing structure, flame stabilisation and turbulence\u2013chemistry interaction are absent.",
   "One mechanism (Tamaoki 2024) and no experimental validation of the new phases.",
   "Fixed fuel blend (x_NH3 = 0.5) in Phases 3\u20134; the fuel dependence of those results is not established.",
   "Pressure mechanism explanations are inferred and not confirmed by a pressure-resolved ROP analysis.",
   "Wall heat loss is a simple UA(T \u2212 T_wall) model, with no radiation."])
H("6.4 Future work", 2)
B(["Compare at least two further NH\u2083 mechanisms to estimate kinetic uncertainty in NO\u2093, N\u2082O and slip.",
   "Validate the staged and finite-mixing predictions against jet-stirred reactor, flow reactor or gas-turbine-combustor data.",
   "Repeat Phases 3\u20134 for other blends and run pressure-resolved ROP analysis.",
   "Add N\u2082O reporting and a global-warming-potential-weighted emission metric.",
   "Replace the equal-split dilution by a mixing-time-resolved model (PaSR/PFR with tunable mixing time) and move to CFD-informed reactor networks.",
   "Use the database for surrogate models with cross-validation and out-of-distribution checks.",
   "Run the 19 non-converged main-study cases with tighter tolerances and continuation."], numbered=True)
PB()

# ================================================================ REFERENCES
H("References", 1)
refs = [
    "K. Tamaoki, Y. Murakami, K. Kanayama, T. Tezuka, M. Izumi, and H. Nakamura, \u201cRoles of NH\u2082 reactions in ammonia oxidation at intermediate temperatures: Experiments and chemical kinetic modeling,\u201d Combustion and Flame, vol. 259, Art. no. 113177, 2024, doi: 10.1016/j.combustflame.2023.113177.",
    "D. G. Goodwin, H. K. Moffat, R. L. Speth, I. Schoegl, and B. W. Weber, \u201cCantera: An object-oriented software toolkit for chemical kinetics, thermodynamics, and transport processes,\u201d 2021, doi: 10.5281/zenodo.4527812.",
    "H. Kobayashi, A. Hayakawa, K. D. K. A. Somarathne, and E. C. Okafor, \u201cScience and technology of ammonia combustion,\u201d Proceedings of the Combustion Institute, vol. 37, pp. 109\u2013133, 2019.",
    "P. Glarborg, J. A. Miller, B. Ruscic, and S. J. Klippenstein, \u201cModeling nitrogen chemistry in combustion,\u201d Progress in Energy and Combustion Science, vol. 67, pp. 31\u201368, 2018.",
    "J. A. Miller and C. T. Bowman, \u201cMechanism and modeling of nitrogen chemistry in combustion,\u201d Progress in Energy and Combustion Science, vol. 15, pp. 287\u2013338, 1989.",
    "P. Glarborg, K. Dam-Johansen, J. A. Miller, R. J. Kee, and M. E. Coltrin, \u201cModeling the thermal DeNOx process in flow reactors. Surface effects and nitrous oxide formation,\u201d International Journal of Chemical Kinetics, vol. 26, pp. 421\u2013436, 1994.",
    "S. Song, R. K. Hanson, C. T. Bowman, and D. M. Golden, \u201cShock tube determination of the overall rate of NH\u2082 + NO \u2192 products in the thermal DeNOx process,\u201d International Journal of Chemical Kinetics, vol. 33, pp. 715\u2013721, 2001.",
    "B. Efron, \u201cBootstrap methods: Another look at the jackknife,\u201d The Annals of Statistics, vol. 7, no. 1, pp. 1\u201326, 1979.",
    "F. Wilcoxon, \u201cIndividual comparisons by ranking methods,\u201d Biometrics Bulletin, vol. 1, no. 6, pp. 80\u201383, 1945.",
    "H. Nakamura, S. Hasegawa, and T. Tezuka, \u201cKinetic modeling of ammonia/air weak flames in a micro flow reactor with a controlled temperature profile,\u201d Combustion and Flame, vol. 185, pp. 16\u201327, 2017.",
]
for i, r in enumerate(refs, 1):
    p = doc.add_paragraph(f"[{i}] {r}")
    p.paragraph_format.left_indent = Cm(1)
    p.paragraph_format.first_line_indent = Cm(-1)
PB()

# ================================================================ APPENDIX
H("Appendix A: Reproducing the Results", 1)
J("From the repository root with the Cantera environment active:")
for cmd in ["python -m single_stage.single_stage_baseline", "python -m double_stage.rate_of_production_analysis",
            "python -m double_stage.decoupled_mixing_analysis", "python -m double_stage.gas_turbine_regimes_analysis",
            "python -m double_stage.statistical_significance_analysis", "python docs/reports/build_end_semester_report.py"]:
    p = doc.add_paragraph()
    r = p.add_run(cmd)
    r.font.name = "Courier New"
    r.font.size = Pt(10)
J("The statistics script and the report builder read only the committed CSV files in results/, so they run in seconds "
  "and do not require re-running Cantera.")

page_number_footer()
doc.save(OUT)
print("saved", OUT, "figures:", FIG[0], "tables:", TAB[0])
