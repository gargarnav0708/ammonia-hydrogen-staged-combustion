"""
Phase 4: Realistic Combustor Conditions (Pressure, Temperature & Heat Loss)
Ammonia-Hydrogen Staged Combustion Study

This script implements:
1. Elevated Combustor Pressure Sweeps (P = 1 to 30 atm):
   - Investigates gas turbine pressure ratio effects on radical recombination (H + O2 + M -> HO2 + M),
     equilibrium shift, and NO2/NOx conversion ratios.
2. Compressor Discharge Air Preheating (T_in = 300 to 750 K):
   - Evaluates higher flame temperatures and thermal NOx acceleration under realistic industrial turbine preheat.
3. Non-Adiabatic Combustor Liner Wall Heat Loss (U_wall = 0 to 3000 W/m^2/K):
   - Models heat loss through combustor walls to evaluate thermal NOx suppression and lean burnout limits.
4. Generates publication-ready figures and comprehensive datasets.
"""

import os
import time
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from double_stage.staged_combustion import simulate_two_stage_gas_turbine

RESULTS_DIR = Path(__file__).resolve().parents[1] / "results"
PLOTS_DIR = RESULTS_DIR / "plots"
RESULTS_DIR.mkdir(exist_ok=True)
PLOTS_DIR.mkdir(exist_ok=True)


def run_pressure_sweep(x_nh3: float = 0.50):
    """
    Sweep combustor pressure from 1 to 30 atm across primary equivalence ratios (phi_1).
    """
    phi1_values = np.linspace(1.0, 2.0, 11)
    pressures = [1.0, 5.0, 10.0, 20.0, 30.0]  # atmospheres

    total = len(phi1_values) * len(pressures)
    print(f"\n--- Running Phase 4 Task 1: Combustor Pressure Sweep ({total} cases) ---")
    t0 = time.time()

    records = []
    for p_atm in pressures:
        for phi_1 in phi1_values:
            res = simulate_two_stage_gas_turbine(
                x_nh3=x_nh3,
                phi_1=phi_1,
                p_atm=p_atm,
                t_in=300.0,
                u_wall=0.0,
            )
            records.append(res)

    df_p = pd.DataFrame(records)
    elapsed = time.time() - t0
    conv = (df_p["Status"] == "Converged").sum()
    print(f"Pressure sweep completed in {elapsed:.2f} s: {conv}/{total} converged.")

    output_file = RESULTS_DIR / "pressure_sweep_results.csv"
    df_p.to_csv(output_file, index=False)
    print(f"Saved {output_file}")
    return df_p


def run_preheat_sweep(x_nh3: float = 0.50, p_atm: float = 10.0):
    """
    Sweep compressor discharge preheat temperatures from 300 to 750 K at P = 10 atm.
    """
    phi1_values = [1.0, 1.2, 1.3, 1.4, 1.6, 1.8, 2.0]
    temperatures = [300.0, 450.0, 600.0, 750.0]  # Kelvin

    total = len(phi1_values) * len(temperatures)
    print(f"\n--- Running Phase 4 Task 2: Inlet Preheat Sweep ({total} cases) ---")
    t0 = time.time()

    records = []
    for t_in in temperatures:
        for phi_1 in phi1_values:
            res = simulate_two_stage_gas_turbine(
                x_nh3=x_nh3,
                phi_1=phi_1,
                p_atm=p_atm,
                t_in=t_in,
                u_wall=0.0,
            )
            records.append(res)

    df_t = pd.DataFrame(records)
    elapsed = time.time() - t0
    conv = (df_t["Status"] == "Converged").sum()
    print(f"Preheat sweep completed in {elapsed:.2f} s: {conv}/{total} converged.")

    output_file = RESULTS_DIR / "preheat_sweep_results.csv"
    df_t.to_csv(output_file, index=False)
    print(f"Saved {output_file}")
    return df_t


def run_wall_heat_loss_sweep(x_nh3: float = 0.50, p_atm: float = 15.0, t_in: float = 650.0):
    """
    Sweep combustor liner wall heat transfer coefficients (U_wall = 0 to 3000 W/m^2/K)
    under realistic gas turbine operating conditions (P = 15 atm, T_in = 650 K).
    """
    phi1_values = [1.1, 1.2, 1.3, 1.4, 1.6, 1.8, 2.0]
    u_wall_values = [0.0, 500.0, 1500.0, 3000.0]  # W / m^2 / K

    total = len(phi1_values) * len(u_wall_values)
    print(f"\n--- Running Phase 4 Task 3: Combustor Wall Heat Loss Sweep ({total} cases) ---")
    t0 = time.time()

    records = []
    for u_wall in u_wall_values:
        for phi_1 in phi1_values:
            res = simulate_two_stage_gas_turbine(
                x_nh3=x_nh3,
                phi_1=phi_1,
                p_atm=p_atm,
                t_in=t_in,
                u_wall=u_wall,
                wall_area=0.25,
            )
            records.append(res)

    df_u = pd.DataFrame(records)
    elapsed = time.time() - t0
    conv = (df_u["Status"] == "Converged").sum()
    print(f"Heat loss sweep completed in {elapsed:.2f} s: {conv}/{total} converged.")

    output_file = RESULTS_DIR / "heat_loss_sweep_results.csv"
    df_u.to_csv(output_file, index=False)
    print(f"Saved {output_file}")
    return df_u


def generate_phase4_plots(df_p: pd.DataFrame, df_t: pd.DataFrame, df_u: pd.DataFrame):
    """Generate high-impact research figures for Phase 4."""
    PLOTS_DIR.mkdir(exist_ok=True)
    plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")

    # -------------------------------------------------------------
    # Plot 1: Pressure Effect on the NOx U-Curve (1 to 30 atm)
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(9, 6), dpi=300)
    p_colors = {1.0: "blue", 5.0: "darkcyan", 10.0: "goldenrod", 20.0: "darkorange", 30.0: "crimson"}

    for p_atm, col in p_colors.items():
        sub = df_p[np.isclose(df_p["P_atm"], p_atm)].sort_values("Phi_1")
        ax.plot(sub["Phi_1"], sub["NOx_ppm"], "-o", color=col, linewidth=2.2, label=f"P = {p_atm:.0f} atm", markersize=5)

    ax.set_xlabel(r"Primary Equivalence Ratio $\phi_1$", fontsize=12, fontweight="bold")
    ax.set_ylabel(r"Final $\mathrm{NO}_x$ Emissions (ppm)", fontsize=12, fontweight="bold")
    ax.set_title(
        r"Impact of Elevated Pressure on the Staged $\mathrm{NO}_x$ U-Curve" + "\n(Fuel: 50% $\\mathrm{NH_3}$ / 50% $\\mathrm{H_2}$, Overall $\\phi = 0.9$)",
        fontsize=12,
        pad=12,
    )
    ax.grid(True, linestyle="--", alpha=0.5)
    ax.legend(frameon=True, fontsize=10, loc="upper right")
    plt.tight_layout()
    plt.savefig(PLOTS_DIR / "pressure_effect_nox_u_curve.png")
    plt.close()
    print(f"Saved {PLOTS_DIR / 'pressure_effect_nox_u_curve.png'}")

    # -------------------------------------------------------------
    # Plot 2: Pressure-Induced NO2 Fraction Shift (HO2 recombination)
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(9, 5.5), dpi=300)

    for p_atm, col in p_colors.items():
        sub = df_p[np.isclose(df_p["P_atm"], p_atm)].sort_values("Phi_1")
        ax.plot(sub["Phi_1"], sub["NO2_ratio"] * 100, "-s", color=col, linewidth=2.0, label=f"P = {p_atm:.0f} atm", markersize=5)

    ax.set_xlabel(r"Primary Equivalence Ratio $\phi_1$", fontsize=12, fontweight="bold")
    ax.set_ylabel(r"$\mathrm{NO_2} / \mathrm{NO}_x$ Ratio (\%)", fontsize=12, fontweight="bold")
    ax.set_title(
        r"High-Pressure Shift in $\mathrm{NO_2}$ Partitioning" + "\n(Driven by accelerated $\\mathrm{H + O_2 + M \\Leftrightarrow HO_2 + M}$ recombination)",
        fontsize=12,
        pad=12,
    )
    ax.grid(True, linestyle="--", alpha=0.5)
    ax.legend(frameon=True, fontsize=10, loc="upper right")
    plt.tight_layout()
    plt.savefig(PLOTS_DIR / "pressure_no2_fraction_shift.png")
    plt.close()
    print(f"Saved {PLOTS_DIR / 'pressure_no2_fraction_shift.png'}")

    # -------------------------------------------------------------
    # Plot 3: Inlet Preheat Temperature Escalation (300 to 750 K at 10 atm)
    # -------------------------------------------------------------
    fig, ax1 = plt.subplots(figsize=(9, 6), dpi=300)
    ax2 = ax1.twinx()

    t_colors = {300.0: "navy", 450.0: "teal", 600.0: "darkorange", 750.0: "firebrick"}

    for t_in, col in t_colors.items():
        sub = df_t[np.isclose(df_t["T_in_K"], t_in)].sort_values("Phi_1")
        ax1.plot(sub["Phi_1"], sub["NOx_ppm"], "-o", color=col, linewidth=2.2, label=f"$T_{{\\mathrm{{in}}}} = {t_in:.0f}$ K", markersize=5)
        ax2.plot(sub["Phi_1"], sub["T_final_K"], "--", color=col, linewidth=1.5, alpha=0.6)

    ax1.set_xlabel(r"Primary Equivalence Ratio $\phi_1$", fontsize=12, fontweight="bold")
    ax1.set_ylabel(r"Final $\mathrm{NO}_x$ Emissions (ppm)", fontsize=12, fontweight="bold", color="darkblue")
    ax2.set_ylabel(r"Final Flame Temperature $T_{\mathrm{final}}$ (K)", fontsize=12, fontweight="bold", color="darkred")
    ax1.set_title(
        r"Thermal $\mathrm{NO}_x$ Escalation under Gas Turbine Air Preheating" + "\n(P = 10 atm, Solid = $\\mathrm{NO}_x$, Dashed = Temperature)",
        fontsize=12,
        pad=12,
    )
    ax1.grid(True, linestyle="--", alpha=0.5)
    ax1.legend(frameon=True, fontsize=9.5, loc="upper right")
    plt.tight_layout()
    plt.savefig(PLOTS_DIR / "preheat_flame_temperature_and_nox.png")
    plt.close()
    print(f"Saved {PLOTS_DIR / 'preheat_flame_temperature_and_nox.png'}")

    # -------------------------------------------------------------
    # Plot 4: Combustor Liner Wall Heat Loss Mitigation
    # -------------------------------------------------------------
    fig, (ax_nox, ax_temp) = plt.subplots(1, 2, figsize=(14, 5.5), dpi=300)
    u_colors = {0.0: "black", 500.0: "teal", 1500.0: "darkorange", 3000.0: "green"}

    for u_w, col in u_colors.items():
        sub = df_u[np.isclose(df_u["U_wall_W_m2K"], u_w)].sort_values("Phi_1")
        lbl = "Adiabatic ($U = 0$)" if u_w == 0 else f"$U = {u_w:.0f}$ W/m$^2$K"
        ax_nox.plot(sub["Phi_1"], sub["NOx_ppm"], "-o", color=col, linewidth=2.0, label=lbl, markersize=5)
        ax_temp.plot(sub["Phi_1"], sub["T_final_K"], "-s", color=col, linewidth=2.0, label=lbl, markersize=5)

    ax_nox.set_xlabel(r"Primary Equivalence Ratio $\phi_1$", fontsize=11, fontweight="bold")
    ax_nox.set_ylabel(r"Final $\mathrm{NO}_x$ Emissions (ppm)", fontsize=11, fontweight="bold")
    ax_nox.set_title(r"(a) $\mathrm{NO}_x$ Mitigation by Liner Cooling", fontsize=12, pad=10)
    ax_nox.grid(True, linestyle="--", alpha=0.5)
    ax_nox.legend(frameon=True, fontsize=9)

    ax_temp.set_xlabel(r"Primary Equivalence Ratio $\phi_1$", fontsize=11, fontweight="bold")
    ax_temp.set_ylabel(r"Final Temperature $T_{\mathrm{final}}$ (K)", fontsize=11, fontweight="bold")
    ax_temp.set_title(r"(b) Flame Temperature Reduction", fontsize=12, pad=10)
    ax_temp.grid(True, linestyle="--", alpha=0.5)
    ax_temp.legend(frameon=True, fontsize=9)

    fig.suptitle(
        r"Impact of Combustor Liner Wall Heat Loss ($P = 15\ \mathrm{atm},\ T_{\mathrm{in}} = 650\ \mathrm{K}$)",
        fontsize=13,
        fontweight="bold",
        y=0.98,
    )
    plt.tight_layout()
    plt.savefig(PLOTS_DIR / "wall_heat_loss_mitigation.png")
    plt.close()
    print(f"Saved {PLOTS_DIR / 'wall_heat_loss_mitigation.png'}")


if __name__ == "__main__":
    df_p = run_pressure_sweep(x_nh3=0.50)
    df_t = run_preheat_sweep(x_nh3=0.50, p_atm=10.0)
    df_u = run_wall_heat_loss_sweep(x_nh3=0.50, p_atm=15.0, t_in=650.0)
    generate_phase4_plots(df_p, df_t, df_u)
    print("\nPhase-4 Combustor Regimes Analysis Complete!")
