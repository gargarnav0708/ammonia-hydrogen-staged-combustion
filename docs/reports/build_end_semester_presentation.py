"""Build the end-semester B.Tech project presentation (PPTX) matching the mid-term style.

Matches the Canva mid-semester deck:
- 16:9 widescreen (13.333 x 7.5 in)
- Dark slate-navy background (#2D384F)
- Top-left icy-blue textured header banner (#CBD8DE) with dark navy bold title
- Clean white typography directly on the dark background (no colored boxes/cards)
- Original title & thank-you diagonal paper background and IIT Delhi logo

Run:    python docs/reports/build_end_semester_presentation.py
Output: docs/reports/BTP_End_Semester_Presentation.pptx
"""
from __future__ import annotations

from pathlib import Path
from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

ROOT = Path(__file__).resolve().parents[2]
PLOTS = ROOT / "results" / "plots"
MID_IMG = ROOT / "docs" / "reports" / "mid_sem_figures"
THEME = ROOT / "docs" / "reports" / "pres_theme"
OUT = ROOT / "docs" / "reports" / "BTP_End_Semester_Presentation.pptx"

NAVY = RGBColor(0x2D, 0x38, 0x4F)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
MUTED = RGBColor(0xD8, 0xE2, 0xEA)
ICE = RGBColor(0xC6, 0xD4, 0xDC)
FONT = "Calibri"

# Crop a clean textured icy-blue strip from title_bg.png for the top-left header banner
HEADER_BANNER = THEME / "header_banner.png"
if not HEADER_BANNER.exists():
    im = Image.open(THEME / "title_bg.png")
    crop = im.crop((820, 60, 1550, 220))
    crop.save(HEADER_BANNER)

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)
BLANK = prs.slide_layouts[6]


def set_bg(slide, color=NAVY):
    fill = slide.background.fill
    fill.solid()
    fill.fore_color.rgb = color


def add_header(slide, title: str, slide_no: int):
    set_bg(slide, NAVY)
    # Top-left icy-blue textured banner (matching mid-term slides 2-17)
    slide.shapes.add_picture(str(HEADER_BANNER), Inches(0), Inches(0), width=Inches(8.55), height=Inches(1.42))
    tb = slide.shapes.add_textbox(Inches(0.5), Inches(0.14), Inches(7.9), Inches(1.15))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    r = p.add_run()
    r.text = title
    r.font.name = FONT
    r.font.size = Pt(31 if len(title) < 38 else 26)
    r.font.bold = True
    r.font.color.rgb = NAVY

    # Subtle bottom-right slide number
    nb = slide.shapes.add_textbox(Inches(12.3), Inches(6.95), Inches(0.7), Inches(0.35))
    np_ = nb.text_frame.paragraphs[0]
    np_.alignment = PP_ALIGN.RIGHT
    nr = np_.add_run()
    nr.text = str(slide_no)
    nr.font.name = FONT
    nr.font.size = Pt(14)
    nr.font.color.rgb = MUTED


def add_bullets(slide, x, y, w, h, heading: str | None, items: list[tuple[str, str]],
                fs: int = 16, h_fs: int = 19, space: int = 8):
    """Add clean white text directly on the dark background (no boxes)."""
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    first = True
    if heading:
        p = tf.paragraphs[0]
        first = False
        p.space_after = Pt(space)
        r = p.add_run()
        r.text = heading
        r.font.name = FONT
        r.font.size = Pt(h_fs)
        r.font.bold = True
        r.font.color.rgb = WHITE
    for lead, body in items:
        p = tf.paragraphs[0] if first else tf.add_paragraph()
        first = False
        p.space_after = Pt(space)
        p.line_spacing = 1.15
        if lead:
            rl = p.add_run()
            rl.text = f"\u2022 {lead} "
            rl.font.name = FONT
            rl.font.size = Pt(fs)
            rl.font.bold = True
            rl.font.color.rgb = WHITE
        rb = p.add_run()
        rb.text = body if lead else f"\u2022 {body}"
        rb.font.name = FONT
        rb.font.size = Pt(fs)
        rb.font.color.rgb = WHITE
    return tb


def add_note(slide, x, y, w, h, text: str, fs: int = 15, bold: bool = False, align=PP_ALIGN.LEFT):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.alignment = align
    r = p.add_run()
    r.text = text
    r.font.name = FONT
    r.font.size = Pt(fs)
    r.font.bold = bold
    r.font.color.rgb = WHITE
    return tb


def add_pic(slide, path: Path, x, y, max_w: float, max_h: float):
    """Insert image preserving aspect ratio inside (max_w, max_h) inches."""
    im = Image.open(path)
    iw, ih = im.size
    scale = min(max_w / iw, max_h / ih)
    w, h = iw * scale, ih * scale
    dx = x + (max_w - w) / 2.0
    dy = y + (max_h - h) / 2.0
    slide.shapes.add_picture(str(path), Inches(dx), Inches(dy), width=Inches(w), height=Inches(h))


# ================================================================ SLIDE 1: TITLE
s1 = prs.slides.add_slide(BLANK)
set_bg(s1, NAVY)
s1.shapes.add_picture(str(THEME / "title_bg.png"), Inches(0), Inches(0), width=Inches(13.333), height=Inches(7.5))
s1.shapes.add_picture(str(THEME / "iitd_logo.png"), Inches(0.25), Inches(1.42), width=Inches(0.75), height=Inches(0.75))

tb = s1.shapes.add_textbox(Inches(1.08), Inches(1.45), Inches(3.2), Inches(0.75))
tf = tb.text_frame
tf.word_wrap = True
p = tf.paragraphs[0]
r = p.add_run()
r.text = "INDIAN INSTITUTE OF\nTECHNOLOGY, DELHI"
r.font.name = FONT
r.font.size = Pt(15)
r.font.bold = True
r.font.color.rgb = WHITE

tb = s1.shapes.add_textbox(Inches(1.75), Inches(3.15), Inches(11.1), Inches(2.1))
tf = tb.text_frame
tf.word_wrap = True
p = tf.paragraphs[0]
p.alignment = PP_ALIGN.RIGHT
r = p.add_run()
r.text = "NUMERICAL INVESTIGATION OF\nTWO-STAGE NH\u2083/H\u2082 COMBUSTION"
r.font.name = FONT
r.font.size = Pt(38)
r.font.bold = True
r.font.color.rgb = NAVY

p2 = tf.add_paragraph()
p2.alignment = PP_ALIGN.RIGHT
p2.space_before = Pt(8)
r2 = p2.add_run()
r2.text = "End-Semester B.Tech Project Presentation"
r2.font.name = FONT
r2.font.size = Pt(20)
r2.font.bold = True
r2.font.color.rgb = NAVY

tb = s1.shapes.add_textbox(Inches(6.2), Inches(5.95), Inches(6.0), Inches(1.0))
tf = tb.text_frame
tf.word_wrap = True
p = tf.paragraphs[0]
p.alignment = PP_ALIGN.LEFT
r = p.add_run()
r.text = "Presented by: Arnav Garg (2023ES10187)\nSupervision of: Prof. Sujeet Yadav"
r.font.name = FONT
r.font.size = Pt(18)
r.font.bold = True
r.font.color.rgb = NAVY


# ================================================================ SLIDE 2: MID-TERM RECAP 1
s2 = prs.slides.add_slide(BLANK)
add_header(s2, "Mid-Semester Recap: Model & Grid", 2)
add_pic(s2, MID_IMG / "image2.png", 0.5, 1.75, 7.0, 3.6)

# Minimal white-outline equation box (like mid-sem slide 5)
eq_box = s2.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(1.2), Inches(5.55), Inches(5.6), Inches(1.1))
eq_box.fill.background()
eq_box.line.color.rgb = WHITE
eq_box.line.width = Pt(1.5)
eq_tf = eq_box.text_frame
eq_tf.vertical_anchor = MSO_ANCHOR.MIDDLE
p = eq_tf.paragraphs[0]
p.alignment = PP_ALIGN.CENTER
r = p.add_run()
r.text = "A\u2082 / A_total = 1 \u2212 \u03c6 / \u03c6\u2081   (\u03c6 = 0.9 fixed)"
r.font.name = FONT
r.font.size = Pt(22)
r.font.bold = True
r.font.color.rgb = WHITE

add_bullets(s2, 7.8, 1.75, 5.0, 5.1, "TWO-STAGE PSR SETUP", [
    ("Mechanism:", "Cantera 3.0 with TamaokiNH3.yaml (33 species, 228 reactions)."),
    ("605-Case Grid:", "x_NH3 = 0\u20131 (11), \u03c6\u2081 = 1.0\u20132.0 (11), \u03c4 = 20\u2013100 ms (5) at 300 K, 1 atm (586 converged)."),
    ("Air Split:", "Increasing \u03c6\u2081 from 1.0 to 2.0 shifts secondary air from 10% to 55%."),
    ("Thermal Control:", "Fuel blend dominates T_final (\u03b7\u00b2 = 98.1%); \u03c6\u2081 dominates Stage-2 \u0394T (\u03b7\u00b2 = 99.3%)."),
], fs=16, space=12)


# ================================================================ SLIDE 3: MID-TERM RECAP 2 + GAPS
s3 = prs.slides.add_slide(BLANK)
add_header(s3, "Mid-Term Findings & Gaps Addressed", 3)
add_pic(s3, MID_IMG / "image10.png", 0.5, 1.7, 6.7, 5.1)
add_bullets(s3, 7.5, 1.7, 5.4, 5.2, "POST-MID-SEMESTER ROADMAP", [
    ("Mid-Term Observation:", "NOx shows a non-monotonic U-curve over \u03c6\u2081, with a low-NOx valley around \u03c6\u2081 = 1.2\u20131.5."),
    ("Phase 1 (Baseline):", "Added identical single-stage PSR runs to quantify exact staging NOx reduction."),
    ("Phase 2 (Kinetics):", "Ran elementary ROP & N-pathway analysis to explain the U-curve."),
    ("Phase 3 (Architecture):", "Decoupled \u03c4\u2081 \u2260 \u03c4\u2082 and replaced instant mixing with N-stage progressive dilution."),
    ("Phase 4 & Stats:", "Added pressure (1\u201330 atm), preheat (300\u2013750 K), wall cooling, and 47 statistical tests."),
], fs=15, space=10)


# ================================================================ SLIDE 4: PHASE 1 BASELINE
s4 = prs.slides.add_slide(BLANK)
add_header(s4, "Phase 1: Single-Stage Baseline Comparison", 4)
add_pic(s4, PLOTS / "baseline_nox_comparison.png", 0.45, 1.65, 7.6, 5.2)
add_bullets(s4, 8.25, 1.75, 4.7, 5.1, "QUANTIFIED STAGING GAIN", [
    ("Matched Grid:", "88 single-stage lean PSR cases (\u03c6 = 0.9, matched \u03c4 and 2\u03c4) \u2192 469 paired comparisons."),
    ("Mean NOx Cut:", "55.1% average reduction (95% CI [52.2, 57.9]%, median 64.9%)."),
    ("Peak Benefit:", "Up to 90.4% cut at x_NH3 = 0.20, \u03c6\u2081 = 2.0 (10,158 \u2192 973 ppm)."),
    ("Pure H2 Exception:", "Penalty down to \u221268.4% at x_NH3 = 0 (no fuel-N; extra \u03c4 adds thermal NO)."),
], fs=16, space=12)


# ================================================================ SLIDE 5: PHASE 1 ADVANTAGE MAP
s5 = prs.slides.add_slide(BLANK)
add_header(s5, "Phase 1: Operational Staging Window", 5)
add_pic(s5, PLOTS / "staging_benefit_heatmap.png", 0.45, 1.65, 7.6, 5.2)
add_bullets(s5, 8.25, 1.8, 4.7, 5.0, "WHERE STAGING WINS", [
    ("93.6% Win Rate:", "Staging outperforms single-stage in 439 of 469 cases (sign test p = 2.81 \u00d7 10\u207b\u2079\u2074)."),
    ("NH3 Blends:", "For x_NH3 \u2265 0.10, mean NOx reduction is 60.1%."),
    ("Safe Corridor:", "Moderate primary staging (\u03c6\u2081 = 1.1\u20131.4) stays in the 40\u201370% reduction zone across blends."),
    ("Penalty Corner:", "Over-rich primary at high NH3 (x_NH3 \u2265 0.80, \u03c6\u2081 = 2.0) loses by up to \u221247.6%."),
], fs=16, space=12)


# ================================================================ SLIDE 6: PHASE 2 ROP U-CURVE
s6 = prs.slides.add_slide(BLANK)
add_header(s6, "Phase 2: Kinetic Origin of the NOx U-Curve", 6)
add_pic(s6, PLOTS / "rop_u_curve_pathway_mechanism.png", 0.45, 1.58, 12.4, 3.85)
add_bullets(s6, 0.55, 5.5, 12.2, 1.7, None, [
    ("Superposition:", "Stage-1 NOx drops monotonically (4766 \u2192 51 ppm) while Stage-2 \u0394NOx rises monotonically (\u2212557 \u2192 +3564 ppm)."),
    ("Amine Carry-Over:", "From \u03c6\u2081 = 1.0 \u2192 2.0, Stage-1 outlet NH2 rises 26.2\u00d7 (5.7 \u2192 148.4 ppm) and unburnt NH3 rises ~625\u00d7 (23.7 \u2192 14,813 ppm)."),
    ("Stage-2 Oxidation Surge:", "Secondary air oxidises carried-over intermediates via HNO + OH \u21c4 H2O + NO (24\u00d7 higher at \u03c6\u2081 = 2.0 than 1.0)."),
], fs=14, space=4)


# ================================================================ SLIDE 7: PHASE 2 ELEMENTARY REACTIONS
s7 = prs.slides.add_slide(BLANK)
add_header(s7, "Phase 2: Elementary NO Source & Sink Reactions", 7)
add_pic(s7, PLOTS / "rop_top_no_reactions_stage1_vs_stage2.png", 0.4, 1.6, 7.9, 5.45)
add_bullets(s7, 8.45, 1.65, 4.65, 2.75, "THREE CHEMICAL REGIMES", [
    ("Left Branch (\u03c6\u2081 = 1.0):", "Hot O-rich Stage 1 forms NO via N + OH and HNO + OH; Stage 2 slightly reduces NO."),
    ("DeNOx Valley (\u03c6\u2081 = 1.3):", "NH + NO / N + NO / NH2 + NO convert fuel-N to N2; valley minimum at 986 ppm."),
    ("Right Branch (\u03c6\u2081 = 1.8):", "Stage 1 is O2-starved (88 ppm NOx), but Stage 2 HNO + OH (+2.3 \u00d7 10\u207b\u2074) regenerates NO."),
], fs=13.5, h_fs=16, space=6)

tbl_shape = s7.shapes.add_table(4, 4, Inches(8.45), Inches(4.55), Inches(4.65), Inches(2.2))
tbl = tbl_shape.table
col_w = [0.65, 1.35, 1.35, 1.30]
for i, w in enumerate(col_w):
    tbl.columns[i].width = Inches(w)
rows_s7 = [
    ["\u03c6\u2081", "S1 Net NO\n(kmol/m\u00b3s)", "S2 Net NO\n(kmol/m\u00b3s)", "NOx S1 \u2192 S2\n(ppm)"],
    ["1.0", "+4.46e\u22124", "\u22122.04e\u22125", "4766 \u2192 4209"],
    ["1.3", "+5.67e\u22125", "+5.17e\u22125", "573 \u2192 986"],
    ["1.8", "+9.94e\u22126", "+2.43e\u22124", "88 \u2192 2537"],
]
for r_i, r_vals in enumerate(rows_s7):
    for c_i, val in enumerate(r_vals):
        cell = tbl.cell(r_i, c_i)
        cell.vertical_anchor = MSO_ANCHOR.MIDDLE
        cell.fill.solid()
        cell.fill.fore_color.rgb = ICE if r_i == 0 else NAVY
        p = cell.text_frame.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        run = p.add_run()
        run.text = val
        run.font.name = FONT
        run.font.size = Pt(10.5 if r_i == 0 else 11.5)
        run.font.bold = (r_i == 0 or c_i == 0)
        run.font.color.rgb = NAVY if r_i == 0 else WHITE


# ================================================================ SLIDE 8: PHASE 2 NITROGEN PATHWAY DIAGRAMS
s8 = prs.slides.add_slide(BLANK)
add_header(s8, "Phase 2: Nitrogen Reaction-Pathway Topology", 8)
add_pic(s8, PLOTS / "reaction_path_composite_3regimes.png", 0.4, 1.58, 12.5, 4.15)
add_bullets(s8, 0.55, 5.75, 12.2, 1.45, None, [
    ("Left Branch Stage 1 (a):", "Parallel HNO \u2192 NO (0.235) and N \u2192 NO (0.197) fluxes drive direct primary NOx formation."),
    ("Right Branch Stage 1 (b) vs. Stage 2 (c):", "Rich Stage 1 channels amines into N\u2013N coupling (N2H2 \u2192 N2H3 / NNH \u2192 N2), but Stage 2 oxidises carried-over NH3/NH2 via NH2/NH \u2192 HNO \u2192 NO (0.548)."),
], fs=14, space=5)


# ================================================================ SLIDE 9: PHASE 3A DECOUPLED TAU
s9 = prs.slides.add_slide(BLANK)
add_header(s9, "Phase 3a: Decoupled Residence Times (\u03c4\u2081 \u2260 \u03c4\u2082)", 9)
add_pic(s9, PLOTS / "decoupled_tau_2d_contour.png", 0.4, 1.6, 7.6, 5.4)
add_bullets(s9, 8.2, 1.75, 4.75, 5.1, "125-CASE (\u03c4\u2081, \u03c4\u2082) SWEEP", [
    ("Hypothesis Refuted:", "Short \u03c4\u2081 (10 ms) freezes Stage 1 far from equilibrium, doubling NH2 carry-over (282 ppm at \u03c6\u2081 = 2.0)."),
    ("Longer \u03c4\u2081 Helps:", "Increasing \u03c4\u2081 from 10 \u2192 50 ms relaxes amines (157 ppm NH2) and cuts NOx by 379\u2013607 ppm."),
    ("Role of \u03c4\u2082:", "Longer \u03c4\u2082 cuts right-branch NOx (4438 \u2192 3490 ppm) and slip, but slightly adds thermal NO in the valley."),
    ("Asymmetric Optimum:", "Grid minimum (1124 ppm) at \u03c4\u2081 = 50 ms, \u03c4\u2082 = 20 ms, \u03c6\u2081 = 1.2."),
], fs=15, space=10)


# ================================================================ SLIDE 10: PHASE 3B FINITE MIXING
s10 = prs.slides.add_slide(BLANK)
add_header(s10, "Phase 3b: Finite-Rate Progressive Dilution", 10)
add_pic(s10, PLOTS / "finite_mixing_nox_comparison.png", 0.4, 1.65, 6.2, 4.15)
add_pic(s10, PLOTS / "finite_mixing_temperature_trajectories.png", 6.75, 1.65, 6.2, 4.15)
add_bullets(s10, 0.55, 5.9, 12.2, 1.35, None, [
    ("Right-Branch Collapse:", "Splitting secondary air into N = 5 stages cuts \u03c6\u2081 = 2.0 NOx from 3693 \u2192 433 ppm (\u221288.3%, Friedman p = 1.67 \u00d7 10\u207b\u2075)."),
    ("Mechanism:", "Gradual dilution keeps intermediate zones hot and sub-rich for NH2 + NO de-NOx, crossing ~2180 K too briefly (12 ms) for thermal NO."),
], fs=14, space=4)


# ================================================================ SLIDE 11: PHASE 4A PRESSURE
s11 = prs.slides.add_slide(BLANK)
add_header(s11, "Phase 4a: Elevated Gas-Turbine Pressure", 11)
add_pic(s11, PLOTS / "pressure_effect_nox_u_curve.png", 0.45, 1.65, 7.6, 5.25)
add_bullets(s11, 8.25, 1.8, 4.7, 5.0, "1 TO 30 ATM SHIFTS", [
    ("Branch Suppression:", "Raising P from 1 \u2192 30 atm cuts \u03c6\u2081 = 1.0 NOx by 61.5% (4548 \u2192 1753 ppm) and \u03c6\u2081 = 2.0 NOx by 41.7%."),
    ("Valley Shift Left:", "Minimum moves from \u03c6\u2081 = 1.3 (1 atm) \u2192 1.2 (5 atm) \u2192 1.1 (10\u201330 atm)."),
    ("Variance Collapse:", "U-curve standard deviation shrinks by 73.7% (1109 \u2192 291 ppm, Levene p = 0.0125)."),
    ("NO2 Shift:", "NO2/NOx rises 6.6-fold (0.032% \u2192 0.209%, \u03c1 = 0.988) via HO2 recombination."),
], fs=15, space=11)


# ================================================================ SLIDE 12: PHASE 4B & 4C PREHEAT & HEAT LOSS
s12 = prs.slides.add_slide(BLANK)
add_header(s12, "Phase 4b & 4c: Air Preheat & Liner Cooling", 12)
add_pic(s12, PLOTS / "preheat_flame_temperature_and_nox.png", 0.4, 1.65, 6.2, 4.15)
add_pic(s12, PLOTS / "wall_heat_loss_mitigation.png", 6.75, 1.65, 6.2, 4.15)
add_bullets(s12, 0.55, 5.9, 12.2, 1.35, None, [
    ("Compressor Preheat (10 atm):", "Raising T_in (300 \u2192 750 K) adds +0.663 K/K to T_final and +6.1 ppm/K to mean NOx (1957 \u2192 4699 ppm)."),
    ("Liner Wall Cooling (15 atm, 650 K):", "U = 3000 W/m\u00b2K cools exhaust by 34.9 K and cuts NOx by 386 ppm (p = 2.04 \u00d7 10\u207b\u2076) with NH3 slip < 0.07 ppm."),
], fs=14, space=4)


# ================================================================ SLIDE 13: STATISTICAL SIGNIFICANCE & DESIGN WINDOW
s13 = prs.slides.add_slide(BLANK)
add_header(s13, "Statistical Significance & Design Window", 13)
add_pic(s13, PLOTS / "stat_staging_benefit_and_variance_share.png", 0.4, 1.65, 7.3, 3.2)
add_bullets(s13, 0.5, 4.95, 7.1, 2.2, "KEY INFERENTIAL TESTS (47-TEST SUITE)", [
    ("Phases 1\u20133:", "Staging d_z = 1.56 (p = 1.3 \u00d7 10\u207b\u00b9\u00b2\u2077); U-curvature p = 8.3 \u00d7 10\u207b\u2074; N=1,3,5 Friedman p = 1.7 \u00d7 10\u207b\u2075."),
    ("Phase 4 Pressure:", "Pooled p = 0.19 hides sign reversal: valley \u03c1 = +0.666 (p = 0.0068) vs. right branch \u03c1 = \u22120.766 (p = 8.1 \u00d7 10\u207b\u2075)."),
], fs=13.5, h_fs=15, space=5)

add_bullets(s13, 7.95, 1.75, 4.9, 5.1, "INTEGRATED DESIGN WINDOW", [
    ("Primary Staging:", "\u03c6\u2081 \u2248 1.1\u20131.3 (shifting toward 1.1 at 10\u201330 atm)."),
    ("Stage Sizing:", "Long rich zone (\u03c4\u2081 \u2248 40\u201350 ms) to relax NH2; compact lean burnout (\u03c4\u2082 \u2248 20 ms)."),
    ("Secondary Mixing:", "Progressive multi-point air injection (N \u2265 3\u20135) to prevent HNO + OH surges."),
    ("Thermal Control:", "Liner cooling offsets preheat thermal NOx without hurting burnout."),
], fs=15.5, space=12)


# ================================================================ SLIDE 14: CONCLUSIONS & FUTURE WORK
s14 = prs.slides.add_slide(BLANK)
add_header(s14, "Conclusions & Future Work", 14)
add_bullets(s14, 0.55, 1.75, 6.0, 5.2, "CONCLUSIONS", [
    ("Staging Proven:", "55.1% mean NOx cut across 469 matched cases (60.1% in NH3 blends, up to 90.4%)."),
    ("U-Curve Resolved:", "Competition between falling Stage-1 NOx and Stage-2 HNO + OH oxidation of carried-over NH2/NH3."),
    ("Architecture Matters:", "Longer \u03c4\u2081 relaxes amines; 5-stage progressive mixing cuts right-branch NOx by 88.3%."),
    ("Engine Realism:", "Pressure shifts optimum to \u03c6\u2081 = 1.1; cooling mitigates preheat NOx by 386 ppm."),
], fs=15.5, space=12)

add_bullets(s14, 6.85, 1.75, 5.9, 5.2, "FUTURE WORK", [
    ("Mechanism Uncertainty:", "Benchmark against Glarborg, Okafor, and Stagni mechanisms."),
    ("Experimental Validation:", "Compare against jet-stirred reactor and gas-turbine combustor rigs."),
    ("Full-Blend Engine Maps:", "Extend Phases 3\u20134 across 0\u2013100% NH3 and run high-P ROP + N2O/GWP tracking."),
    ("Higher-Fidelity Mixing:", "Replace discrete parcels with PaSR mixing timescales and CFD-informed networks."),
], fs=15.5, space=12)


# ================================================================ SLIDE 15: THANK YOU
s15 = prs.slides.add_slide(BLANK)
set_bg(s15, NAVY)
s15.shapes.add_picture(str(THEME / "title_bg.png"), Inches(0), Inches(0), width=Inches(13.333), height=Inches(7.5))
tb = s15.shapes.add_textbox(Inches(7.3), Inches(2.5), Inches(5.3), Inches(2.5))
tf = tb.text_frame
tf.word_wrap = True
p = tf.paragraphs[0]
p.alignment = PP_ALIGN.RIGHT
r = p.add_run()
r.text = "THANK\nYOU"
r.font.name = FONT
r.font.size = Pt(64)
r.font.bold = True
r.font.color.rgb = NAVY

prs.save(OUT)
print(f"Saved {OUT}: {len(prs.slides)} slides")
