"""
Phase 3: Reactor Architecture & Mixing Physics
Ammonia-Hydrogen Staged Combustion Study

This script implements:
1. Decoupled Residence Time Modeling (tau_1 != tau_2):
   - Sizing of rich primary reactor (tau_1 = 10 to 50 ms) vs. lean secondary reactor (tau_2 = 20 to 100 ms).
   - Evaluates whether short rich residence time suppresses intermediate amine radical (NH_i) buildup
     and mitigates secondary NOx surges.
2. Finite-Rate Secondary Mixing Modeling:
   - Replaces idealized instantaneous air addition with a progressive multi-stage dilution sequence
     (N = 1, 3, 5 mixing stages).
   - Tracks intermediate equivalence ratios, localized near-stoichiometric temperature peaks, and
     in-situ Thermal DeNOx conversion.
3. Generates publication-ready figures and research datasets.
"""

import os
import time
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from double_stage.staged_combustion import (
    simulate_two_stage_decoupled,
    simulate_two_stage_finite_mixing,
)

RESULTS_DIR = Path(__file__).resolve().parents[1] / "results"
PLOTS_DIR = RESULTS_DIR / "plots"
RESULTS_DIR.mkdir(exist_ok=True)
PLOTS_DIR.mkdir(exist_ok=True)


def run_decoupled_residence_time_sweep(x_nh3: float = 0.50):
    """
    Run 2D parametric sweep over primary residence time (tau_1) and
    secondary residence time (tau_2) across multiple primary equivalence ratios (phi_1).
    """
    phi1_values = [1.2, 1.4, 1.6, 1.8, 2.0]
    tau1_values = [0.010, 0.020, 0.030, 0.040, 0.050]      # 10 to 50 ms
    tau2_values = [0.020, 0.040, 0.060, 0.080, 0.100]      # 20 to 100 ms

    total_cases = len(phi1_values) * len(tau1_values) * len(tau2_values)
    print(f"\n--- Running Phase 3 Task 1: Decoupled Residence Time Sweep ({total_cases} cases) ---")
    t0 = time.time()

    records = []
    for phi_1 in phi1_values:
        for tau_1 in tau1_values:
            for tau_2 in tau2_values:
                res = simulate_two_stage_decoupled(x_nh3, phi_1, tau_1, tau_2)
                records.append(res)

    df_decoupled = pd.DataFrame(records)
    elapsed = time.time() - t0
    conv = (df_decoupled["Status"] == "Converged").sum()
    print(f"Decoupled sweep completed in {elapsed:.2f} s: {conv}/{total_cases} converged.")

    output_file = RESULTS_DIR / "decoupled_residence_time_results.csv"
    df_decoupled.to_csv(output_file, index=False)
    print(f"Saved {output_file}")
    return df_decoupled


def run_finite_mixing_sweep(x_nh3: float = 0.50, tau_1: float = 0.030, tau_2: float = 0.060):
    """
    Compare instantaneous secondary mixing (N=1) against progressive finite-rate dilution
    (N=3 and N=5 mixing stages) across the primary equivalence ratio sweep (phi_1 = 1.0 to 2.0).
    """
    phi1_values = np.linspace(1.0, 2.0, 11)
    mixing_stages_list = [1, 3, 5]

    total_cases = len(phi1_values) * len(mixing_stages_list)
    print(f"\n--- Running Phase 3 Task 2: Finite-Rate Secondary Mixing Sweep ({total_cases} cases) ---")
    t0 = time.time()

    records = []
    for n_stages in mixing_stages_list:
        for phi_1 in phi1_values:
            res = simulate_two_stage_finite_mixing(x_nh3, phi_1, tau_1, tau_2, n_mixing_stages=n_stages)
            # Store flattened record for easy CSV export
            rec = {k: v for k, v in res.items() if k not in ["Stage_temperatures", "Stage_NOx_ppm"]}
            rec["Stage_temperatures_str"] = ";".join(str(t) for t in res.get("Stage_temperatures", []))
            rec["Stage_NOx_ppm_str"] = ";".join(str(n) for n in res.get("Stage_NOx_ppm", []))
            records.append(rec)

    df_mixing = pd.DataFrame(records)
    elapsed = time.time() - t0
    conv = (df_mixing["Status"] == "Converged").sum()
    print(f"Finite mixing sweep completed in {elapsed:.2f} s: {conv}/{total_cases} converged.")

    output_file = RESULTS_DIR / "finite_mixing_comparison_results.csv"
    df_mixing.to_csv(output_file, index=False)
    print(f"Saved {output_file}")
    return df_mixing


def generate_decoupled_plots(df_decoupled: pd.DataFrame):
    """Generate 2D contour maps and trade-off plots for decoupled residence times."""
    PLOTS_DIR.mkdir(exist_ok=True)
    plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")

    # -------------------------------------------------------------
    # Plot 1: 2D Contour Maps of NOx over (tau_1, tau_2) at 4 phi_1 levels
    # -------------------------------------------------------------
    fig, axes = plt.subplots(2, 2, figsize=(14, 11), dpi=300)
    selected_phi1 = [1.2, 1.4, 1.6, 2.0]

    for idx, phi1 in enumerate(selected_phi1):
        ax = axes[idx // 2, idx % 2]
        sub = df_decoupled[(np.isclose(df_decoupled["Phi_1"], phi1)) & (df_decoupled["Status"] == "Converged")]
        if sub.empty:
            continue

        pivot = sub.pivot(index="Tau_1_ms", columns="Tau_2_ms", values="NOx_final_ppm")
        X = pivot.columns.values
        Y = pivot.index.values
        Z = pivot.values

        cp = ax.contourf(X, Y, Z, levels=14, cmap="turbo")
        plt.colorbar(cp, ax=ax, label=r"Final $\mathrm{NO}_x$ (ppm)")

        # Contour lines
        cl = ax.contour(X, Y, Z, levels=8, colors="black", linewidths=0.8, alpha=0.6)
        ax.clabel(cl, inline=True, fmt="%d", fontsize=8)

        # Highlight tau_1 = tau_2 diagonal (the original assumption)
        diag = np.linspace(20, 50, 100)
        ax.plot(diag, diag, "r--", linewidth=1.5, label=r"Equal $\tau$ line ($\tau_1 = \tau_2$)")

        ax.set_xlabel(r"Secondary Residence Time $\tau_2$ (ms)", fontsize=10, fontweight="bold")
        ax.set_ylabel(r"Primary Residence Time $\tau_1$ (ms)", fontsize=10, fontweight="bold")
        ax.set_title(rf"$\phi_1 = {phi1:.1f}$", fontsize=12, fontweight="bold")
        ax.legend(loc="upper left", fontsize=8, frameon=True)

    fig.suptitle(
        r"Impact of Decoupled Residence Times ($\tau_1 \neq \tau_2$) on Final $\mathrm{NO}_x$ Emissions" + "\n(Fuel: 50% $\\mathrm{NH_3}$ / 50% $\\mathrm{H_2}$, Overall $\\phi = 0.9$)",
        fontsize=14,
        fontweight="bold",
        y=0.98,
    )
    plt.tight_layout()
    plt.savefig(PLOTS_DIR / "decoupled_tau_2d_contour.png")
    plt.close()
    print(f"Saved {PLOTS_DIR / 'decoupled_tau_2d_contour.png'}")

    # -------------------------------------------------------------
    # Plot 2: Influence of tau_1 / tau_2 ratio on NOx and NH3 slip
    # -------------------------------------------------------------
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5.5), dpi=300)

    # Filter at fixed total tau_total approx 80-90 ms
    phi1_colors = {1.2: "blue", 1.4: "green", 1.6: "orange", 2.0: "red"}

    for phi1, col in phi1_colors.items():
        sub = df_decoupled[np.isclose(df_decoupled["Phi_1"], phi1)].sort_values("Tau_ratio")
        ax1.plot(sub["Tau_ratio"], sub["NOx_final_ppm"], "o-", color=col, alpha=0.7, label=rf"$\phi_1 = {phi1:.1f}$")
        ax2.plot(sub["Tau_ratio"], sub["NH3_slip_ppm"], "s-", color=col, alpha=0.7, label=rf"$\phi_1 = {phi1:.1f}$")

    ax1.set_xlabel(r"Residence Time Ratio $\theta = \tau_1 / \tau_2$", fontsize=11, fontweight="bold")
    ax1.set_ylabel(r"Final $\mathrm{NO}_x$ Emissions (ppm)", fontsize=11, fontweight="bold")
    ax1.set_title(r"(a) Final $\mathrm{NO}_x$ vs. Stage Sizing Ratio $\tau_1/\tau_2$", fontsize=12, pad=10)
    ax1.grid(True, linestyle="--", alpha=0.5)
    ax1.legend(frameon=True, fontsize=9)

    ax2.set_xlabel(r"Residence Time Ratio $\theta = \tau_1 / \tau_2$", fontsize=11, fontweight="bold")
    ax2.set_ylabel(r"Unburnt $\mathrm{NH_3}$ Slip (ppm)", fontsize=11, fontweight="bold")
    ax2.set_title(r"(b) Fuel Slip vs. Stage Sizing Ratio $\tau_1/\tau_2$", fontsize=12, pad=10)
    ax2.set_yscale("log")
    ax2.grid(True, which="both", linestyle="--", alpha=0.5)
    ax2.legend(frameon=True, fontsize=9)

    plt.tight_layout()
    plt.savefig(PLOTS_DIR / "decoupled_tau_ratio_tradeoff.png")
    plt.close()
    print(f"Saved {PLOTS_DIR / 'decoupled_tau_ratio_tradeoff.png'}")


def generate_finite_mixing_plots(df_mixing: pd.DataFrame):
    """Generate plots comparing Instantaneous vs. Finite-Rate Progressive Mixing."""
    PLOTS_DIR.mkdir(exist_ok=True)
    plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")

    # -------------------------------------------------------------
    # Plot 1: NOx Comparison Across phi_1: N=1 vs N=3 vs N=5
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(9, 6), dpi=300)

    stage_styles = {
        1: ("Instantaneous Mixing (N=1)", "black", "o--", 2.0),
        3: ("Progressive 3-Stage Dilution (N=3)", "teal", "s-", 2.2),
        5: ("Progressive 5-Stage Dilution (N=5)", "darkviolet", "^-", 2.5),
    }

    for n_stages, (label, color, marker, lw) in stage_styles.items():
        sub = df_mixing[df_mixing["N_mixing_stages"] == n_stages].sort_values("Phi_1")
        ax.plot(sub["Phi_1"], sub["NOx_final_ppm"], marker, color=color, linewidth=lw, label=label, markersize=6)

    # Highlight optimal valley
    ax.axvspan(1.2, 1.45, color="green", alpha=0.12, label="Optimal DeNOx Window")

    ax.set_xlabel(r"Primary Equivalence Ratio $\phi_1$", fontsize=12, fontweight="bold")
    ax.set_ylabel(r"Final $\mathrm{NO}_x$ Emissions (ppm)", fontsize=12, fontweight="bold")
    ax.set_title(
        r"Effect of Finite-Rate Secondary Mixing on the $\mathrm{NO}_x$ U-Curve" + "\n(Fuel: 50% $\\mathrm{NH_3}$ / 50% $\\mathrm{H_2}$, $\\tau_1 = 30\\ \\mathrm{ms}$, $\\tau_2 = 60\\ \\mathrm{ms}$)",
        fontsize=12,
        pad=12,
    )
    ax.grid(True, linestyle="--", alpha=0.5)
    ax.legend(frameon=True, fontsize=10, loc="upper right")
    plt.tight_layout()
    plt.savefig(PLOTS_DIR / "finite_mixing_nox_comparison.png")
    plt.close()
    print(f"Saved {PLOTS_DIR / 'finite_mixing_nox_comparison.png'}")

    # -------------------------------------------------------------
    # Plot 2: Progressive Temperature Trajectories through Mixing Stages
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(9, 6), dpi=300)

    # Sample cases at phi_1 = 1.3, 1.5, 1.8 for N=5
    sub_5 = df_mixing[df_mixing["N_mixing_stages"] == 5]
    sample_phi1 = [1.2, 1.4, 1.6, 1.8, 2.0]
    colors = plt.cm.magma(np.linspace(0.2, 0.85, len(sample_phi1)))

    for phi1, col in zip(sample_phi1, colors):
        row = sub_5[np.isclose(sub_5["Phi_1"], phi1)]
        if not row.empty:
            temps = [float(t) for t in row.iloc[0]["Stage_temperatures_str"].split(";")]
            stage_indices = np.arange(len(temps))  # 0: Primary, 1-5: Dilution stages
            labels = ["Primary"] + [f"Dilution {k}" for k in range(1, len(temps))]
            ax.plot(stage_indices, temps, "-o", color=col, linewidth=2.2, markersize=6, label=rf"$\phi_1 = {phi1:.1f}$")

    ax.set_xticks(np.arange(6))
    ax.set_xticklabels(["Primary PSR", "Mix 1", "Mix 2", "Mix 3", "Mix 4", "Final Outlet (Lean)"], fontsize=10)
    ax.set_ylabel(r"Stage Gas Temperature (K)", fontsize=12, fontweight="bold")
    ax.set_title(
        r"Temperature Trajectories Across 5 Progressive Mixing Stages" + "\n(Reveals near-stoichiometric thermal peaks during finite-rate air dilution)",
        fontsize=12,
        pad=12,
    )
    ax.grid(True, linestyle="--", alpha=0.5)
    ax.legend(frameon=True, fontsize=10, loc="lower left")
    plt.tight_layout()
    plt.savefig(PLOTS_DIR / "finite_mixing_temperature_trajectories.png")
    plt.close()
    print(f"Saved {PLOTS_DIR / 'finite_mixing_temperature_trajectories.png'}")


if __name__ == "__main__":
    df_decoupled = run_decoupled_residence_time_sweep(x_nh3=0.50)
    generate_decoupled_plots(df_decoupled)

    df_mixing = run_finite_mixing_sweep(x_nh3=0.50, tau_1=0.030, tau_2=0.060)
    generate_finite_mixing_plots(df_mixing)

    print("\nPhase-3 Decoupled Residence Time & Finite-Rate Mixing Complete!")
