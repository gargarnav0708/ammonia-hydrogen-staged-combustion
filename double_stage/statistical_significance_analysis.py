"""Statistical significance analysis for all phases of the NH3/H2 staged combustion study.

The Cantera simulations are deterministic, so "significance" is assessed over the
operating-condition grid: how likely is an effect of this size if the factor had no
systematic influence on the response across the sampled conditions?

Run:  python -m double_stage.statistical_significance_analysis
Outputs: results/statistical_significance_summary.csv
"""
from math import factorial
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results"
RNG = np.random.default_rng(42)
rows = []


def add(phase, test, quantity, n, statistic, p, effect, ci=""):
    rows.append(dict(Phase=phase, Test=test, Quantity=quantity, N=n,
                     Statistic=statistic, p_value=p, Effect=effect, CI95=ci))


def boot_ci(x, f=np.mean, B=10000):
    x = np.asarray(x)
    s = [f(RNG.choice(x, len(x))) for _ in range(B)]
    return np.percentile(s, [2.5, 97.5])


def ols_ftest(df, y, factors):
    """Type-I style OLS with categorical dummies -> partial F-test per factor (type II)."""
    n = len(df)
    Y = df[y].values.astype(float)

    def design(fs):
        X = [np.ones(n)]
        for f in fs:
            X.append(pd.get_dummies(df[f].astype(str), drop_first=True).values.astype(float))
        return np.column_stack(X)

    def rss(fs):
        X = design(fs)
        b, *_ = np.linalg.lstsq(X, Y, rcond=None)
        r = Y - X @ b
        return float(r @ r), X.shape[1]

    rss_full, k_full = rss(factors)
    out = {}
    for f in factors:
        rss_red, k_red = rss([g for g in factors if g != f])
        dfn, dfd = k_full - k_red, n - k_full
        F = ((rss_red - rss_full) / dfn) / (rss_full / dfd)
        sst = float(((Y - Y.mean()) ** 2).sum())
        out[f] = (F, dfn, dfd, stats.f.sf(F, dfn, dfd), (rss_red - rss_full) / sst)
    return out


# ---------------- Initial 605-case study ----------------
d = pd.read_csv(RES / "staged_combustion_results.csv")
d = d[d.Status == "Converged"].copy()
d["Delta_NOx_ppm"] = d.NOx_ppm - d.NOx_primary_ppm
d["Delta_T_K"] = d.T_final_K - d.T_primary_K
d["H2_slip"] = d.H2_slip_ppm
for y in ["T_final_K", "NOx_ppm", "H2_slip", "Delta_T_K", "Delta_NOx_ppm"]:
    res = ols_ftest(d, y, ["NH3_frac", "Phi_1", "Tau_ms"])
    for f, (F, dfn, dfd, p, pe) in res.items():
        add("Main 605-case", f"Type-II ANOVA F-test ({f})", y, len(d),
            round(F, 3), p, f"partial R2 contribution={pe:.4f} (df={dfn},{dfd})")
# Residence-time monotonic trend of NOx (within every fuel/phi1 cell)
rho = []
for _, g in d.groupby(["NH3_frac", "Phi_1"]):
    if len(g) >= 4:
        rho.append(stats.spearmanr(g.Tau_ms, g.NOx_ppm)[0])
rho = np.array(rho)
t, p = stats.ttest_1samp(rho, 0)
add("Main 605-case", "One-sample t on within-cell Spearman rho(tau, NOx)", "NOx_ppm", len(rho),
    round(t, 3), p, f"mean rho={rho.mean():.3f}", str(np.round(boot_ci(rho), 3)))

# ---------------- Phase 1: staged vs single-stage ----------------
c = pd.read_csv(RES / "staged_vs_single_stage_comparison.csv")
c = c[c.Status == "Converged"].dropna(subset=["NOx_ppm", "NOx_single_ppm"])
diff = c.NOx_single_ppm - c.NOx_ppm
add("Phase 1", "Paired t-test (single - staged)", "NOx_ppm", len(c),
    round(stats.ttest_rel(c.NOx_single_ppm, c.NOx_ppm)[0], 3),
    stats.ttest_rel(c.NOx_single_ppm, c.NOx_ppm)[1],
    f"mean diff={diff.mean():.1f} ppm; Cohen dz={diff.mean()/diff.std(ddof=1):.3f}",
    str(np.round(boot_ci(diff), 1)))
w = stats.wilcoxon(c.NOx_single_ppm, c.NOx_ppm)
add("Phase 1", "Wilcoxon signed-rank (single vs staged)", "NOx_ppm", len(c),
    w.statistic, w.pvalue, f"median diff={diff.median():.1f} ppm")
add("Phase 1", "Bootstrap CI of mean % reduction", "NOx_reduction_pct", len(c),
    "", "", f"mean={c.NOx_reduction_pct.mean():.2f}%",
    str(np.round(boot_ci(c.NOx_reduction_pct), 2)))
k = int((c.NOx_reduction_pct > 0).sum())
add("Phase 1", "Two-sided binomial sign test (staging wins)", "NOx_reduction_pct>0", len(c),
    k, stats.binomtest(k, len(c), 0.5).pvalue, f"win fraction={k/len(c):.3f}")
blend = c[c.NH3_frac >= 0.1]
add("Phase 1", "Wilcoxon signed-rank, blends x_NH3>=0.1", "NOx_ppm", len(blend),
    stats.wilcoxon(blend.NOx_single_ppm, blend.NOx_ppm).statistic,
    stats.wilcoxon(blend.NOx_single_ppm, blend.NOx_ppm).pvalue,
    f"mean reduction={blend.NOx_reduction_pct.mean():.2f}%",
    str(np.round(boot_ci(blend.NOx_reduction_pct), 2)))

# ---------------- Phase 2: U-curve (Stage 1 vs Stage 2 contributions) ----------------
r = pd.read_csv(RES / "rop_analysis_summary.csv")
for col, lab in [("NOx_stage1_ppm", "Stage-1 NOx"), ("Delta_NOx_ppm", "Stage-2 NOx change"),
                 ("NH2_stage1_ppm", "NH2 carryover")]:
    rs = stats.spearmanr(r.Phi_1, r[col])
    pexact = 2.0 / factorial(len(r)) if abs(rs[0]) == 1.0 else rs[1]  # exact two-sided permutation p for perfect rank order
    add("Phase 2", "Spearman trend vs phi1 (exact p for |rho|=1)", lab, len(r), round(rs[0], 3), pexact, "perfectly monotonic" if abs(rs[0]) == 1 else "")
# Quadratic (U) fit significance of final NOx vs phi1
fm = pd.read_csv(RES / "finite_mixing_comparison_results.csv")
n1 = fm[fm.N_mixing_stages == 1].sort_values("Phi_1")
x = n1.Phi_1.values - n1.Phi_1.mean()
X = np.column_stack([np.ones(len(x)), x, x ** 2])
y = n1.NOx_final_ppm.values
b, *_ = np.linalg.lstsq(X, y, rcond=None)
res_ = y - X @ b
s2 = res_ @ res_ / (len(y) - 3)
se = np.sqrt(np.diag(s2 * np.linalg.inv(X.T @ X)))
tq = b[2] / se[2]
add("Phase 2", "Quadratic coefficient t-test (U-shape)", "NOx_final vs phi1 (N=1)", len(y),
    round(tq, 3), 2 * stats.t.sf(abs(tq), len(y) - 3), f"curvature={b[2]:.0f} ppm/phi^2")

# ---------------- Phase 3 ----------------
piv = fm.pivot(index="Phi_1", columns="N_mixing_stages", values="NOx_final_ppm")
for a, bb in [(1, 3), (1, 5), (3, 5)]:
    dd = piv[a] - piv[bb]
    tt = stats.ttest_rel(piv[a], piv[bb])
    ww = stats.wilcoxon(piv[a], piv[bb])
    add("Phase 3", f"Paired t / Wilcoxon: N={a} vs N={bb}", "NOx_final_ppm", len(piv),
        round(tt[0], 3), tt[1], f"mean diff={dd.mean():.1f} ppm; Wilcoxon p={ww.pvalue:.4g}; dz={dd.mean()/dd.std(ddof=1):.2f}",
        str(np.round(boot_ci(dd), 1)))
fr = stats.friedmanchisquare(piv[1], piv[3], piv[5])
add("Phase 3", "Friedman test across N=1,3,5", "NOx_final_ppm", len(piv), round(fr.statistic, 3), fr.pvalue, "")
dc = pd.read_csv(RES / "decoupled_residence_time_results.csv")
for y in ["NOx_final_ppm", "NH3_slip_ppm"]:
    res = ols_ftest(dc, y, ["Tau_1_ms", "Tau_2_ms", "Phi_1"])
    for f, (F, dfn, dfd, p, pe) in res.items():
        add("Phase 3", f"Type-II ANOVA F-test ({f})", y, len(dc), round(F, 3), p,
            f"partial R2 contribution={pe:.4f} (df={dfn},{dfd})")
for f in ["Tau_1_ms", "Tau_2_ms"]:
    rs = stats.spearmanr(dc[f], dc.NOx_final_ppm)
    add("Phase 3", f"Spearman rho ({f})", "NOx_final_ppm", len(dc), round(rs[0], 3), rs[1], "")

# ---------------- Phase 4 ----------------
def trend(df, xcol, label, y="NOx_ppm"):
    rhos, slopes = [], []
    for _, g in df.groupby("Phi_1"):
        rhos.append(stats.spearmanr(g[xcol], g[y])[0])
        slopes.append(stats.linregress(g[xcol], g[y]).slope)
    rhos = np.array(rhos)
    if np.all(np.abs(rhos) == 1.0) and len(set(rhos)) == 1:
        t, p = float("nan"), 2 * 0.5 ** len(rhos)  # exact sign test: same direction at every phi1 level
        tname = f"Exact sign test, same monotone direction at every phi1 ({label})"
    else:
        t, p = stats.ttest_1samp(rhos, 0)
        tname = f"One-sample t on per-phi1 Spearman rho ({label})"
    add("Phase 4", tname, y, len(rhos),
        "" if np.isnan(t) else round(t, 3), p, f"mean rho={np.nanmean(rhos):.3f}; mean slope={np.mean(slopes):.4g} ppm/unit",
        str(np.round(boot_ci(rhos), 3)))
    return slopes

ps = pd.read_csv(RES / "pressure_sweep_results.csv")
trend(ps, "P_atm", "pressure")
a, b2 = ps[ps.P_atm == 1.0].set_index("Phi_1").NOx_ppm, ps[ps.P_atm == 30.0].set_index("Phi_1").NOx_ppm
tt = stats.ttest_rel(a, b2)
add("Phase 4", "Paired t-test 1 atm vs 30 atm", "NOx_ppm", len(a), round(tt[0], 3), tt[1],
    f"mean diff={(a-b2).mean():.1f} ppm", str(np.round(boot_ci((a - b2).values), 1)))
lev = stats.levene(a.values, b2.values)
add("Phase 4", "Levene variance test 1 atm vs 30 atm", "NOx_ppm", len(a) + len(b2), round(lev.statistic, 3), lev.pvalue,
    f"SD collapse: {a.std():.0f} -> {b2.std():.0f} ppm (-{(1-b2.std()/a.std())*100:.1f}%)")
for bname, mask in [("valley 1.2<=phi1<=1.4", (ps.Phi_1 >= 1.2) & (ps.Phi_1 <= 1.4)),
                    ("right branch phi1>=1.7", ps.Phi_1 >= 1.7)]:
    sub = ps[mask]
    rs = stats.spearmanr(sub.P_atm, sub.NOx_ppm)
    add("Phase 4", f"Spearman rho(P_atm, NOx), {bname}", "NOx_ppm", len(sub), round(rs[0], 3), rs[1],
        f"sign reversal across branches")
rs_no2 = stats.spearmanr(ps.P_atm, ps.NO2_ratio)
add("Phase 4", "Spearman rho(P_atm, NO2/NOx)", "NO2_ratio", len(ps), round(rs_no2[0], 3), rs_no2[1],
    f"mean ratio: {ps[ps.P_atm==1].NO2_ratio.mean()*100:.3f}% -> {ps[ps.P_atm==30].NO2_ratio.mean()*100:.3f}%")
trend(pd.read_csv(RES / "preheat_sweep_results.csv"), "T_in_K", "preheat")
hl = pd.read_csv(RES / "heat_loss_sweep_results.csv")
trend(hl, "U_wall_W_m2K", "liner cooling")
a, b2 = hl[hl.U_wall_W_m2K == 0].set_index("Phi_1").NOx_ppm, hl[hl.U_wall_W_m2K == 3000].set_index("Phi_1").NOx_ppm
tt = stats.ttest_rel(a, b2)
add("Phase 4", "Paired t-test adiabatic vs U=3000", "NOx_ppm", len(a), round(tt[0], 3), tt[1],
    f"mean diff={(a-b2).mean():.1f} ppm", str(np.round(boot_ci((a - b2).values), 1)))
pre = pd.read_csv(RES / "preheat_sweep_results.csv")
tf = pre.groupby("T_in_K").T_final_K.mean()
lr = stats.linregress(tf.index, tf.values)
add("Phase 4", "Linear regression T_final vs T_in", "T_final_K", len(tf), round(lr.slope, 4), lr.pvalue,
    f"slope={lr.slope:.3f} K/K, R2={lr.rvalue**2:.4f}")

out = pd.DataFrame(rows)
out.to_csv(RES / "statistical_significance_summary.csv", index=False)
pd.set_option("display.width", 250, "display.max_colwidth", 70, "display.max_rows", 200)
print(out.assign(p_value=out.p_value.map(lambda v: f"{v:.3g}" if v != "" else "")).to_string())
