"""
Single-Stage PSR Baseline & Comparison against Two-Stage Staged Combustion
Phase-1 Implementation for Ammonia-Hydrogen Staged Combustion Study

This script:
1. Simulates single-stage PSR combustion at the identical overall equivalence ratio (phi=0.9),
   fuel blends (x_NH3 from 0.0 to 1.0), and residence times (both nominal tau and equivalent 2*tau).
2. Compares single-stage NOx, temperature, and fuel slip directly against the two-stage results.
3. Computes quantitative staging benefit metrics (% NOx reduction, delta T, delta slip).
4. Generates publication-ready comparative visualizations.
"""

import os
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import cantera as ct

from staged_combustion import (
    MECH,
    T_IN,
    P_IN,
    PHI_OVERALL,
    AIR,
    integrate_to_steady_state,
)

TRACKED_SPECIES = ["NH3", "H2", "NO", "NO2", "N2O"]


def get_mole_fractions(gas, species_list=TRACKED_SPECIES):
    """Extract mole fractions of tracked species safely."""
    names = set(gas.species_names)
    X = gas.X
    return {
        sp: float(X[gas.species_index(sp)]) if sp in names else 0.0
        for sp in species_list
    }


def simulate_single_stage_psr(x_nh3: float, tau: float, phi_overall: float = PHI_OVERALL):
    """
    Simulate a single-stage PSR at fixed overall equivalence ratio.
    
    Parameters
    ----------
    x_nh3 : float
        Ammonia mole fraction in the fuel blend (0.0 to 1.0).
    tau : float
        Reactor residence time in seconds.
    phi_overall : float
        Overall equivalence ratio (default 0.9).
        
    Returns
    -------
    dict with simulation outputs.
    """
    x_h2 = 1.0 - x_nh3

    try:
        # Stoichiometric oxygen and air requirement for 1 mole of blend:
        # NH3 + 0.75 O2 -> 0.5 N2 + 1.5 H2O
        # H2 + 0.5 O2 -> H2O
        n_o2_stoic = 0.75 * x_nh3 + 0.50 * x_h2
        n_air_stoic = 4.76 * n_o2_stoic
        n_air_total = n_air_stoic / phi_overall

        fuel_comp = {}
        if x_nh3 > 0.0:
            fuel_comp["NH3"] = x_nh3
        if x_h2 > 0.0:
            fuel_comp["H2"] = x_h2

        gas = ct.Solution(MECH)

        # Fresh fuel stream
        fuel_stream = ct.Quantity(gas, constant="HP")
        fuel_stream.TPX = T_IN, P_IN, fuel_comp
        fuel_stream.moles = 1.0

        # Fresh air stream
        air_stream = ct.Quantity(gas, constant="HP")
        air_stream.TPX = T_IN, P_IN, AIR
        air_stream.moles = n_air_total

        # Mixed unburnt feed
        feed_mix = fuel_stream + air_stream

        # Initial reactor state guess via equilibrium
        gas_init = ct.Solution(MECH)
        gas_init.TPX = feed_mix.phase.TPX
        gas_init.equilibrate("HP")

        reactor = ct.IdealGasReactor(gas_init, energy="on")
        reactor.volume = 1.0

        inlet = ct.Reservoir(feed_mix.phase)
        exhaust = ct.Reservoir(gas_init)

        mfc = ct.MassFlowController(
            inlet, reactor, mdot=lambda t: reactor.mass / tau
        )
        pc = ct.PressureController(
            reactor, exhaust, primary=mfc, K=0.01
        )

        sim = ct.ReactorNet([reactor])
        converged, itime = integrate_to_steady_state(sim, reactor, tau)

        if not converged:
            raise RuntimeError(f"Single-stage PSR did not reach steady state after {itime:.3g} s.")

        phase = getattr(reactor, "phase", getattr(reactor, "thermo", None))
        X = get_mole_fractions(phase)

        no_ppm = X["NO"] * 1e6
        no2_ppm = X["NO2"] * 1e6
        nox_ppm = (X["NO"] + X["NO2"]) * 1e6
        n2o_ppm = X["N2O"] * 1e6
        nh3_slip_ppm = X["NH3"] * 1e6
        h2_slip_ppm = X["H2"] * 1e6

        return {
            "NH3_frac": round(x_nh3, 4),
            "H2_frac": round(x_h2, 4),
            "Phi_overall": phi_overall,
            "Tau_s": tau,
            "Tau_ms": round(tau * 1000.0, 1),
            "T_single_K": round(reactor.T, 2),
            "X_NH3_single": X["NH3"],
            "X_H2_single": X["H2"],
            "X_NO_single": X["NO"],
            "X_NO2_single": X["NO2"],
            "X_N2O_single": X["N2O"],
            "NO_single_ppm": round(no_ppm, 3),
            "NO2_single_ppm": round(no2_ppm, 3),
            "NOx_single_ppm": round(nox_ppm, 3),
            "N2O_single_ppm": round(n2o_ppm, 3),
            "NH3_single_slip_ppm": round(nh3_slip_ppm, 4),
            "H2_single_slip_ppm": round(h2_slip_ppm, 4),
            "Integration_time_s": round(itime, 4),
            "Status": "Converged",
        }

    except Exception as exc:
        return {
            "NH3_frac": round(x_nh3, 4),
            "H2_frac": round(x_h2, 4),
            "Phi_overall": phi_overall,
            "Tau_s": tau,
            "Tau_ms": round(tau * 1000.0, 1),
            "Status": f"FAILED: {type(exc).__name__}: {exc}",
        }


def run_single_stage_grid():
    """Run full single-stage parameter sweep."""
    nh3_fractions = np.linspace(0.0, 1.0, 11)
    # Both nominal tau (20-100 ms) and matched total tau (40-200 ms)
    nominal_taus = [0.020, 0.040, 0.060, 0.080, 0.100]
    matched_taus = [0.040, 0.080, 0.120, 0.160, 0.200]
    all_taus = sorted(list(set(nominal_taus + matched_taus)))

    print(f"Running Single-Stage PSR Sweep: {len(nh3_fractions)} blends x {len(all_taus)} residence times = {len(nh3_fractions)*len(all_taus)} cases...")
    t0 = time.time()
    results = []

    for x_nh3 in nh3_fractions:
        for tau in all_taus:
            res = simulate_single_stage_psr(x_nh3, tau)
            results.append(res)

    df_single = pd.DataFrame(results)
    elapsed = time.time() - t0
    conv_count = (df_single["Status"] == "Converged").sum()
    print(f"Single-stage sweep completed in {elapsed:.2f} s: {conv_count}/{len(df_single)} converged.")

    df_single.to_csv("single_stage_results.csv", index=False)
    print("Saved single_stage_results.csv")
    return df_single


def compare_with_staged_combustion(df_single: pd.DataFrame):
    """
    Merge single-stage baseline with existing two-stage results and compute
    staging benefit metrics.
    """
    staged_file = "staged_combustion_results_full.csv"
    if not os.path.exists(staged_file):
        staged_file = "staged_combustion_results.csv"

    print(f"Loading staged results from {staged_file}...")
    df_staged = pd.read_csv(staged_file)
    df_staged = df_staged[df_staged["Status"] == "Converged"].copy()

    # Filter single-stage to nominal tau for direct per-stage tau comparison
    df_single_converged = df_single[df_single["Status"] == "Converged"].copy()

    # Merge on NH3_frac and Tau_ms
    merged = pd.merge(
        df_staged,
        df_single_converged[[
            "NH3_frac", "Tau_ms", "T_single_K", "NOx_single_ppm",
            "NH3_single_slip_ppm", "H2_single_slip_ppm", "N2O_single_ppm"
        ]],
        on=["NH3_frac", "Tau_ms"],
        how="inner",
    )

    # Compute comparative metrics
    # Delta NOx = Staged - Single (negative means staging reduced NOx)
    merged["Delta_NOx_ppm"] = merged["NOx_ppm"] - merged["NOx_single_ppm"]
    # NOx reduction percentage (>0 means staged is cleaner)
    merged["NOx_reduction_pct"] = (
        (merged["NOx_single_ppm"] - merged["NOx_ppm"]) / merged["NOx_single_ppm"]
    ) * 100.0

    merged["Delta_T_K"] = merged["T_final_K"] - merged["T_single_K"]
    merged["Delta_NH3_slip_ppm"] = merged["NH3_slip_ppm"] - merged["NH3_single_slip_ppm"]
    merged["Delta_H2_slip_ppm"] = merged["H2_slip_ppm"] - merged["H2_single_slip_ppm"]

    merged.to_csv("staged_vs_single_stage_comparison.csv", index=False)
    print("Saved staged_vs_single_stage_comparison.csv")
    return merged


def generate_baseline_plots(merged: pd.DataFrame, df_single: pd.DataFrame):
    """Generate publication-ready baseline comparison plots."""
    os.makedirs("plots", exist_ok=True)
    plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")

    # -------------------------------------------------------------
    # Plot 1: NOx comparison vs NH3 fraction at reference tau = 60 ms
    # -------------------------------------------------------------
    tau_ref = 60.0
    sub_merged = merged[merged["Tau_ms"] == tau_ref]
    sub_single = df_single[(df_single["Tau_ms"] == tau_ref) & (df_single["Status"] == "Converged")]
    # Also get single stage at matched 2*tau = 120 ms
    sub_single_2tau = df_single[(df_single["Tau_ms"] == 120.0) & (df_single["Status"] == "Converged")]

    fig, ax = plt.subplots(figsize=(9, 6), dpi=300)

    # Plot single-stage baselines
    ax.plot(
        sub_single["NH3_frac"] * 100,
        sub_single["NOx_single_ppm"],
        "k--o",
        linewidth=2.5,
        markersize=6,
        label=r"Single-Stage Baseline ($\tau = 60\ \mathrm{ms}$)",
        zorder=5,
    )
    if not sub_single_2tau.empty:
        ax.plot(
            sub_single_2tau["NH3_frac"] * 100,
            sub_single_2tau["NOx_single_ppm"],
            "k:s",
            linewidth=2.0,
            markersize=5,
            label=r"Single-Stage Baseline ($\tau_{\mathrm{total}} = 120\ \mathrm{ms}$)",
            zorder=4,
        )

    # Plot staged cases at selected phi_1 values
    selected_phi1 = [1.0, 1.2, 1.3, 1.4, 1.6, 1.8, 2.0]
    cmap = plt.cm.plasma
    colors = [cmap(i) for i in np.linspace(0.1, 0.9, len(selected_phi1))]

    for phi1, color in zip(selected_phi1, colors):
        case_data = sub_merged[np.isclose(sub_merged["Phi_1"], phi1)].sort_values("NH3_frac")
        if not case_data.empty:
            ax.plot(
                case_data["NH3_frac"] * 100,
                case_data["NOx_ppm"],
                "-^",
                color=color,
                linewidth=1.8,
                markersize=5,
                label=rf"Staged $\phi_1 = {phi1:.1f}$",
            )

    ax.set_xlabel(r"$\mathrm{NH_3}$ Mole Fraction in Fuel Blend (\%)", fontsize=12, fontweight="bold")
    ax.set_ylabel(r"Final $\mathrm{NO}_x$ Emissions (ppm)", fontsize=12, fontweight="bold")
    ax.set_title(
        r"$\mathrm{NO}_x$ Emissions: Two-Stage Staged Combustion vs. Single-Stage Baseline" + f"\n(Overall $\phi = 0.9$, $\\tau = {tau_ref:.0f}\\ \\mathrm{{ms}}$)",
        fontsize=13,
        pad=12,
    )
    ax.grid(True, linestyle="--", alpha=0.5)
    ax.legend(frameon=True, fontsize=9, loc="upper right")
    plt.tight_layout()
    plt.savefig("plots/baseline_nox_comparison.png")
    plt.close()
    print("Saved plots/baseline_nox_comparison.png")

    # -------------------------------------------------------------
    # Plot 2: 2D Contour of Staging Benefit (% NOx Reduction)
    # -------------------------------------------------------------
    sub_merged_ref = merged[merged["Tau_ms"] == tau_ref]
    pivot_benefit = sub_merged_ref.pivot(index="Phi_1", columns="NH3_frac", values="NOx_reduction_pct")

    fig, ax = plt.subplots(figsize=(9, 6.5), dpi=300)
    X_grid = pivot_benefit.columns.values * 100
    Y_grid = pivot_benefit.index.values
    Z_grid = pivot_benefit.values

    # Contour levels centered around 0 (0% = baseline parity)
    levels = np.linspace(-150, 80, 24)
    cs = ax.contourf(X_grid, Y_grid, Z_grid, levels=levels, cmap="RdYlBu", extend="both")
    cbar = plt.colorbar(cs, ax=ax)
    cbar.set_label(r"Staging Benefit: $\mathrm{NO}_x$ Reduction vs. Baseline (\%)", fontsize=11, fontweight="bold")

    # Overlay zero-line (where staged equals single stage)
    cs_zero = ax.contour(X_grid, Y_grid, Z_grid, levels=[0.0], colors="black", linewidths=2.5, linestyles="--")
    ax.clabel(cs_zero, inline=True, fmt=r"Parity (0%%)", fontsize=10)

    # Highlight optimal staging zone
    cs_opt = ax.contour(X_grid, Y_grid, Z_grid, levels=[40.0, 60.0], colors="green", linewidths=1.8, linestyles="-")
    ax.clabel(cs_opt, inline=True, fmt=r"%d%% Red.", fontsize=9)

    ax.set_xlabel(r"$\mathrm{NH_3}$ Fraction in Fuel (\%)", fontsize=12, fontweight="bold")
    ax.set_ylabel(r"Primary Equivalence Ratio $\phi_1$", fontsize=12, fontweight="bold")
    ax.set_title(
        r"Two-Stage Combustion Advantage Map over Single-Stage Baseline" + f"\n(Green = 40-70% $\\mathrm{{NO}}_x$ Cut; Red = Staging Penalty; $\\tau = {tau_ref:.0f}\\ \\mathrm{{ms}}$)",
        fontsize=12,
        pad=12,
    )
    plt.tight_layout()
    plt.savefig("plots/staging_benefit_heatmap.png")
    plt.close()
    print("Saved plots/staging_benefit_heatmap.png")

    # -------------------------------------------------------------
    # Plot 3: Scatter Trade-off Comparison: NOx vs Fuel Slip
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(8.5, 6), dpi=300)

    # Staged cases
    sc = ax.scatter(
        merged["NOx_ppm"],
        merged["NH3_slip_ppm"] + merged["H2_slip_ppm"],
        c=merged["Phi_1"],
        cmap="viridis",
        s=35,
        alpha=0.75,
        label="Two-Stage Cases",
    )
    cbar = plt.colorbar(sc, ax=ax)
    cbar.set_label(r"Primary $\phi_1$", fontsize=11)

    # Single-stage cases
    df_single_valid = df_single[df_single["Status"] == "Converged"]
    ax.scatter(
        df_single_valid["NOx_single_ppm"],
        df_single_valid["NH3_single_slip_ppm"] + df_single_valid["H2_single_slip_ppm"],
        color="crimson",
        marker="X",
        s=70,
        edgecolor="black",
        linewidth=1.0,
        label="Single-Stage Baseline",
        zorder=6,
    )

    ax.set_yscale("log")
    ax.set_xlabel(r"Final $\mathrm{NO}_x$ Emissions (ppm)", fontsize=12, fontweight="bold")
    ax.set_ylabel(r"Total Fuel Slip ($\mathrm{NH_3} + \mathrm{H_2}$) (ppm, log scale)", fontsize=12, fontweight="bold")
    ax.set_title(r"$\mathrm{NO}_x$ vs. Unburnt Fuel Slip: Staged vs. Single-Stage Baseline", fontsize=13, pad=12)
    ax.grid(True, which="both", linestyle="--", alpha=0.4)
    ax.legend(frameon=True, loc="upper right")
    plt.tight_layout()
    plt.savefig("plots/baseline_tradeoff_scatter.png")
    plt.close()
    print("Saved plots/baseline_tradeoff_scatter.png")


if __name__ == "__main__":
    df_single = run_single_stage_grid()
    merged = compare_with_staged_combustion(df_single)
    generate_baseline_plots(merged, df_single)
    print("\nPhase-1 Baseline Analysis Complete!")
