"""
Chemical Kinetic Rate of Production (ROP) & Reaction Pathway Analysis
Phase-2 Implementation for Ammonia-Hydrogen Staged Combustion Study

This script:
1. Simulates two-stage combustion across the primary equivalence ratio sweep (phi_1 = 1.0 to 2.0)
   at reference condition (x_NH3 = 0.50, tau = 60 ms).
2. Computes local elementary reaction rates of progress and species net rates of production
   for key target species (NO, NO2, NH2, NH, HNO, N2) in both Stage 1 and Stage 2.
3. Uncovers and isolates the chemical reactions driving the non-monotonic U-shaped NOx profile.
4. Generates nitrogen reaction-path flux diagrams (Graphviz dot) for the three characteristic regimes:
   - Left branch (phi_1 = 1.0): High thermal/prompt NOx in Stage 1
   - Valley minimum (phi_1 = 1.3): Active Thermal DeNOx (NH2 + NO -> N2 + ...)
   - Right branch (phi_1 = 1.8): Secondary oxidation surge of carried-over NH_i radicals
5. Exports detailed ROP tables and publication-grade kinetic figures.
"""

import os
import subprocess
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import cantera as ct

from double_stage.staged_combustion import (
    MECH,
    T_IN,
    P_IN,
    PHI_OVERALL,
    AIR,
    calculate_air_amounts,
    integrate_to_steady_state,
)

RESULTS_DIR = Path(__file__).resolve().parents[1] / "results"
PLOTS_DIR = RESULTS_DIR / "plots"
RESULTS_DIR.mkdir(exist_ok=True)
PLOTS_DIR.mkdir(exist_ok=True)

TRACKED_SPECIES = ["NH3", "H2", "NO", "NO2", "N2O", "NH2", "NH", "HNO", "N2", "O2", "OH", "H", "O"]


def simulate_two_stage_detailed(x_nh3: float, phi_1: float, tau: float):
    """
    Simulate two-stage combustion and return both the converged reactor objects
    and their underlying thermodynamic/kinetic gas states.
    """
    x_h2 = 1.0 - x_nh3
    n_air_stoic, n_air_1, n_air_2 = calculate_air_amounts(x_nh3, phi_1)

    fuel = {}
    if x_nh3 > 0:
        fuel["NH3"] = x_nh3
    if x_h2 > 0:
        fuel["H2"] = x_h2

    gas = ct.Solution(MECH)

    # ------------------ STAGE 1 ------------------
    fuel_stream = ct.Quantity(gas, constant="HP")
    fuel_stream.TPX = T_IN, P_IN, fuel
    fuel_stream.moles = 1.0

    air_stream_1 = ct.Quantity(gas, constant="HP")
    air_stream_1.TPX = T_IN, P_IN, AIR
    air_stream_1.moles = n_air_1

    primary_mix = fuel_stream + air_stream_1

    gas1 = ct.Solution(MECH)
    gas1.TPX = primary_mix.phase.TPX
    gas1.equilibrate("HP")

    reactor1 = ct.IdealGasReactor(gas1, energy="on")
    reactor1.volume = 1.0

    inlet1 = ct.Reservoir(primary_mix.phase)
    exhaust1 = ct.Reservoir(gas1)

    mfc1 = ct.MassFlowController(inlet1, reactor1, mdot=lambda t: reactor1.mass / tau)
    pc1 = ct.PressureController(reactor1, exhaust1, primary=mfc1, K=0.01)

    sim1 = ct.ReactorNet([reactor1])
    converged1, itime1 = integrate_to_steady_state(sim1, reactor1, tau)
    if not converged1:
        raise RuntimeError(f"Primary PSR did not converge for phi_1={phi_1:.2f}")

    # Copy primary reactor state
    phase1 = getattr(reactor1, "phase", getattr(reactor1, "thermo", None))
    primary_state = ct.Solution(MECH)
    primary_state.TDY = phase1.TDY

    # ------------------ STAGE 2 ------------------
    primary_products = ct.Quantity(primary_state, constant="HP")
    primary_products.moles = primary_mix.moles

    air_stream_2 = ct.Quantity(gas, constant="HP")
    air_stream_2.TPX = T_IN, P_IN, AIR
    air_stream_2.moles = n_air_2

    secondary_mix = primary_products + air_stream_2

    gas2 = ct.Solution(MECH)
    gas2.TPX = secondary_mix.phase.TPX

    reactor2 = ct.IdealGasReactor(gas2, energy="on")
    reactor2.volume = 1.0

    inlet2 = ct.Reservoir(secondary_mix.phase)
    exhaust2 = ct.Reservoir(gas2)

    mfc2 = ct.MassFlowController(inlet2, reactor2, mdot=lambda t: reactor2.mass / tau)
    pc2 = ct.PressureController(reactor2, exhaust2, primary=mfc2, K=0.01)

    sim2 = ct.ReactorNet([reactor2])
    converged2, itime2 = integrate_to_steady_state(sim2, reactor2, tau)
    if not converged2:
        raise RuntimeError(f"Secondary PSR did not converge for phi_1={phi_1:.2f}")

    phase2 = getattr(reactor2, "phase", getattr(reactor2, "thermo", None))
    secondary_state = ct.Solution(MECH)
    secondary_state.TDY = phase2.TDY

    return {
        "x_nh3": x_nh3,
        "phi_1": phi_1,
        "tau": tau,
        "n_air_1": n_air_1,
        "n_air_2": n_air_2,
        "T_stage1": reactor1.T,
        "T_stage2": reactor2.T,
        "gas_stage1": primary_state,
        "gas_stage2": secondary_state,
    }


def compute_species_reaction_contributions(gas: ct.Solution, target_species: str, top_n: int = 8):
    """
    Compute reaction-by-reaction contributions to the net rate of production of a target species.
    Contribution = (nu''_k,i - nu'_k,i) * q_net,i  [kmol / m^3 / s]
    """
    if target_species not in gas.species_names:
        return pd.DataFrame()

    k = gas.species_index(target_species)
    q_net = gas.net_rates_of_progress  # shape: (n_reactions,)
    nu = gas.product_stoich_coeffs[k, :] - gas.reactant_stoich_coeffs[k, :]
    contributions = nu * q_net

    records = []
    for i in range(gas.n_reactions):
        if abs(contributions[i]) > 1e-12:
            records.append({
                "Reaction_idx": i,
                "Equation": gas.reaction(i).equation,
                "Net_rate_of_progress": q_net[i],
                "Stoich_coeff": nu[i],
                "Contribution_kmol_m3_s": contributions[i],
            })

    df = pd.DataFrame(records)
    if df.empty:
        return pd.DataFrame(columns=["Reaction_idx", "Equation", "Contribution_kmol_m3_s"])

    df = df.sort_values("Contribution_kmol_m3_s", ascending=False).reset_index(drop=True)
    return df


def sweep_rop_across_phi1(x_nh3: float = 0.50, tau: float = 0.060):
    """
    Perform detailed ROP and species tracking across the full phi_1 sweep (1.0 to 2.0).
    """
    phi1_range = np.linspace(1.0, 2.0, 11)
    summary_records = []
    reaction_progress_records = []

    print(f"Executing ROP sweep for x_NH3={x_nh3:.2f}, tau={tau*1000:.0f} ms across {len(phi1_range)} phi_1 levels...")

    for phi_1 in phi1_range:
        res = simulate_two_stage_detailed(x_nh3, phi_1, tau)
        g1 = res["gas_stage1"]
        g2 = res["gas_stage2"]

        X1 = {sp: float(g1.X[g1.species_index(sp)]) if sp in g1.species_names else 0.0 for sp in TRACKED_SPECIES}
        X2 = {sp: float(g2.X[g2.species_index(sp)]) if sp in g2.species_names else 0.0 for sp in TRACKED_SPECIES}

        nox_stage1_ppm = (X1["NO"] + X1["NO2"]) * 1e6
        nox_stage2_ppm = (X2["NO"] + X2["NO2"]) * 1e6

        # Net production rates of NO in each stage
        no_idx = g1.species_index("NO")
        w_dot_no_s1 = g1.net_production_rates[no_idx]
        w_dot_no_s2 = g2.net_production_rates[no_idx]

        summary_records.append({
            "NH3_frac": x_nh3,
            "Phi_1": round(phi_1, 2),
            "Tau_ms": tau * 1000.0,
            "T_stage1_K": round(res["T_stage1"], 2),
            "T_stage2_K": round(res["T_stage2"], 2),
            "Delta_T_K": round(res["T_stage2"] - res["T_stage1"], 2),
            "NOx_stage1_ppm": round(nox_stage1_ppm, 2),
            "NOx_stage2_ppm": round(nox_stage2_ppm, 2),
            "Delta_NOx_ppm": round(nox_stage2_ppm - nox_stage1_ppm, 2),
            "NO_stage1_ppm": round(X1["NO"] * 1e6, 2),
            "NO_stage2_ppm": round(X2["NO"] * 1e6, 2),
            "NH3_stage1_ppm": round(X1["NH3"] * 1e6, 2),
            "NH3_stage2_slip_ppm": round(X2["NH3"] * 1e6, 4),
            "NH2_stage1_ppm": round(X1["NH2"] * 1e6, 2),
            "NH2_stage2_ppm": round(X2["NH2"] * 1e6, 4),
            "NH_stage1_ppm": round(X1["NH"] * 1e6, 2),
            "HNO_stage1_ppm": round(X1["HNO"] * 1e6, 2),
            "HNO_stage2_ppm": round(X2["HNO"] * 1e6, 4),
            "O2_stage1_pct": round(X1["O2"] * 100, 3),
            "O2_stage2_pct": round(X2["O2"] * 100, 3),
            "OH_stage1_ppm": round(X1["OH"] * 1e6, 2),
            "OH_stage2_ppm": round(X2["OH"] * 1e6, 2),
            "Net_NO_prod_rate_stage1": w_dot_no_s1,
            "Net_NO_prod_rate_stage2": w_dot_no_s2,
        })

        # Track specific key elementary reaction rates in Stage 1 and Stage 2
        # We search by reaction string or reactant/product pairs
        for stage_name, gas_obj in [("Stage 1", g1), ("Stage 2", g2)]:
            q_net = gas_obj.net_rates_of_progress
            for rxn_i in range(gas_obj.n_reactions):
                eq = gas_obj.reaction(rxn_i).equation
                # Focus on influential nitrogen pathways
                interesting_signatures = [
                    "NH2 + NO", "N + NO", "N2 + O", "NH + O2", "NH2 + O2",
                    "HNO + OH", "HNO + M", "NH2 + OH", "NH3 + OH"
                ]
                if any(sig in eq for sig in interesting_signatures):
                    k_no = gas_obj.species_index("NO")
                    nu_no = gas_obj.product_stoich_coeffs[k_no, rxn_i] - gas_obj.reactant_stoich_coeffs[k_no, rxn_i]
                    reaction_progress_records.append({
                        "Phi_1": round(phi_1, 2),
                        "Stage": stage_name,
                        "Reaction_idx": rxn_i,
                        "Equation": eq,
                        "Net_rate_of_progress": q_net[rxn_i],
                        "NO_contribution_kmol_m3_s": nu_no * q_net[rxn_i],
                    })

    df_summary = pd.DataFrame(summary_records)
    df_rxns = pd.DataFrame(reaction_progress_records)

    df_summary.to_csv(RESULTS_DIR / "rop_analysis_summary.csv", index=False)
    df_rxns.to_csv(RESULTS_DIR / "rop_no_reactions_by_phi1.csv", index=False)
    print("Saved rop_analysis_summary.csv and rop_no_reactions_by_phi1.csv")
    return df_summary, df_rxns


def generate_reaction_path_diagrams(x_nh3: float = 0.50, tau: float = 0.060):
    """
    Generate Graphviz reaction path diagrams for element 'N' in Stage 1 and Stage 2
    at the three characteristic regimes:
    phi_1 = 1.0 (Left branch), 1.3 (Valley), 1.8 (Right branch).
    """
    PLOTS_DIR.mkdir(exist_ok=True)
    dot_bin = "/opt/miniconda3/envs/cantera_env/bin/dot"
    cases = [
        (1.0, "phi1_1p0"),
        (1.3, "phi1_1p3"),
        (1.8, "phi1_1p8"),
    ]

    print("\nGenerating Nitrogen Reaction Path Diagrams via Graphviz dot...")
    for phi_1, label in cases:
        res = simulate_two_stage_detailed(x_nh3, phi_1, tau)

        for stage_name, gas_obj, stage_suffix in [
            ("Stage 1", res["gas_stage1"], "stage1"),
            ("Stage 2", res["gas_stage2"], "stage2"),
        ]:
            diagram = ct.ReactionPathDiagram(gas_obj, "N")
            diagram.title = f"Nitrogen Reaction Paths: {stage_name} (phi_1={phi_1:.1f}, x_NH3={x_nh3*100:.0f}%)"
            diagram.threshold = 0.005  # Show paths carrying >= 0.5% of flux
            diagram.scale = 1.0
            diagram.bold_threshold = 0.10
            diagram.normal_threshold = 0.02
            diagram.label_threshold = 0.01

            dot_content = diagram.get_dot()
            dot_file = PLOTS_DIR / f"reaction_path_{label}_{stage_suffix}.dot"
            png_file = PLOTS_DIR / f"reaction_path_{label}_{stage_suffix}.png"

            with open(dot_file, "w") as f:
                f.write(dot_content)

            if os.path.exists(dot_bin):
                proc = subprocess.run([dot_bin, "-Tpng", dot_file, "-o", png_file], capture_output=True, text=True)
                if proc.returncode == 0:
                    print(f"  Generated {png_file}")
                else:
                    print(f"  Dot warning on {dot_file}: {proc.stderr}")


def generate_rop_figures(df_summary: pd.DataFrame, df_rxns: pd.DataFrame):
    """
    Generate high-impact kinetic figures explaining the U-curve.
    """
    PLOTS_DIR.mkdir(exist_ok=True)
    plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")

    # -------------------------------------------------------------
    # Figure 1: The Chemical Mechanism of the U-Curve
    # Multi-panel: (A) Final vs Stage NOx & Temp, (B) N-Intermediates Carryover, (C) Key Reaction Rates
    # -------------------------------------------------------------
    fig, axes = plt.subplots(1, 3, figsize=(18, 5.5), dpi=300)

    # Panel A: Thermal & Emission Profile
    ax1 = axes[0]
    ax1_twin = ax1.twinx()

    l1 = ax1.plot(df_summary["Phi_1"], df_summary["NOx_stage2_ppm"], "b-o", linewidth=2.5, markersize=6, label=r"Final $\mathrm{NO}_x$ (Stage 2)")
    l2 = ax1.plot(df_summary["Phi_1"], df_summary["NOx_stage1_ppm"], "c--s", linewidth=2.0, markersize=5, label=r"Stage 1 $\mathrm{NO}_x$")
    l3 = ax1_twin.plot(df_summary["Phi_1"], df_summary["T_stage1_K"], "r-^", linewidth=2.0, markersize=5, label=r"Stage 1 Temp ($T_1$)")
    l4 = ax1_twin.plot(df_summary["Phi_1"], df_summary["T_stage2_K"], "m:d", linewidth=2.0, markersize=5, label=r"Stage 2 Temp ($T_2$)")

    # Annotate regimes
    ax1.axvspan(1.0, 1.2, color="orange", alpha=0.15, label="Thermal/Prompt Zone")
    ax1.axvspan(1.2, 1.45, color="green", alpha=0.15, label="Thermal DeNOx Valley")
    ax1.axvspan(1.45, 2.0, color="purple", alpha=0.15, label="Secondary Oxidation Zone")

    ax1.set_xlabel(r"Primary Equivalence Ratio $\phi_1$", fontsize=11, fontweight="bold")
    ax1.set_ylabel(r"$\mathrm{NO}_x$ Emissions (ppm)", fontsize=11, fontweight="bold", color="darkblue")
    ax1_twin.set_ylabel(r"Reactor Temperature (K)", fontsize=11, fontweight="bold", color="darkred")
    ax1.set_title(r"(a) Thermal & $\mathrm{NO}_x$ Evolution Across Staging", fontsize=12, pad=10)
    ax1.grid(True, linestyle="--", alpha=0.5)

    # Combine legends
    lines = l1 + l2 + l3 + l4
    labels = [l.get_label() for l in lines]
    ax1.legend(lines, labels, loc="upper center", fontsize=8, frameon=True)

    # Panel B: Carryover of Fuel-Nitrogen Intermediates from Stage 1 into Stage 2
    ax2 = axes[1]
    ax2.plot(df_summary["Phi_1"], df_summary["NH2_stage1_ppm"], "g-o", linewidth=2.2, label=r"$\mathrm{NH_2}$ exiting Stage 1")
    ax2.plot(df_summary["Phi_1"], df_summary["NH_stage1_ppm"], "orange", linestyle="-", marker="s", linewidth=2.0, label=r"$\mathrm{NH}$ exiting Stage 1")
    ax2.plot(df_summary["Phi_1"], df_summary["HNO_stage1_ppm"], "purple", linestyle="-", marker="^", linewidth=2.0, label=r"$\mathrm{HNO}$ exiting Stage 1")
    ax2.plot(df_summary["Phi_1"], df_summary["NH3_stage1_ppm"] / 10.0, "r--d", linewidth=2.0, label=r"$\mathrm{NH_3}$ exiting Stage 1 (/10)")

    ax2.set_yscale("log")
    ax2.set_xlabel(r"Primary Equivalence Ratio $\phi_1$", fontsize=11, fontweight="bold")
    ax2.set_ylabel(r"Stage 1 Outlet Mole Fraction (ppm, log scale)", fontsize=11, fontweight="bold")
    ax2.set_title(r"(b) Nitrogen Intermediates Carried to Stage 2", fontsize=12, pad=10)
    ax2.grid(True, which="both", linestyle="--", alpha=0.5)
    ax2.legend(frameon=True, fontsize=9, loc="upper left")

    # Panel C: Net Elementary NO Formation/Destruction Rates in Stage 2
    ax3 = axes[2]
    # Filter for Stage 2 prominent reactions
    s2_rxns = df_rxns[df_rxns["Stage"] == "Stage 2"]

    # Select representative reactions
    # 1. Thermal DeNOx: NH2 + NO <=> N2 + H2O
    denox_data = s2_rxns[s2_rxns["Equation"].str.contains(r"NH2 \+ NO <=> N2 \+ H2O", regex=True)]
    # 2. DeNOx radical: NH2 + NO <=> NNH + OH
    denox2_data = s2_rxns[s2_rxns["Equation"].str.contains(r"NH2 \+ NO <=> NNH \+ OH", regex=True)]
    # 3. Intermediate oxidation: NH + O2 <=> NO + OH
    nho2_data = s2_rxns[s2_rxns["Equation"].str.contains(r"NH \+ O2 <=> NO \+ OH", regex=True)]
    # 4. HNO oxidation: HNO + OH <=> NO + H2O
    hno_data = s2_rxns[s2_rxns["Equation"].str.contains(r"HNO \+ OH <=> NO \+ H2O", regex=True)]

    if not denox_data.empty:
        ax3.plot(denox_data["Phi_1"], denox_data["NO_contribution_kmol_m3_s"], "g-o", linewidth=2.2, label=r"$\mathrm{NH_2 + NO \Leftrightarrow N_2 + H_2O}$ (DeNOx)")
    if not denox2_data.empty:
        ax3.plot(denox2_data["Phi_1"], denox2_data["NO_contribution_kmol_m3_s"], "c--s", linewidth=2.0, label=r"$\mathrm{NH_2 + NO \Leftrightarrow NNH + OH}$")
    if not nho2_data.empty:
        ax3.plot(nho2_data["Phi_1"], nho2_data["NO_contribution_kmol_m3_s"], "r-^", linewidth=2.2, label=r"$\mathrm{NH + O_2 \Leftrightarrow NO + OH}$ (Oxidation)")
    if not hno_data.empty:
        ax3.plot(hno_data["Phi_1"], hno_data["NO_contribution_kmol_m3_s"], "m-d", linewidth=2.0, label=r"$\mathrm{HNO + OH \Leftrightarrow NO + H_2O}$ (Oxidation)")

    ax3.axhline(0.0, color="black", linestyle="--", alpha=0.7)
    ax3.set_xlabel(r"Primary Equivalence Ratio $\phi_1$", fontsize=11, fontweight="bold")
    ax3.set_ylabel(r"Contribution to Local $\mathrm{NO}$ Rate ($\mathrm{kmol\ m^{-3}\ s^{-1}}$)", fontsize=11, fontweight="bold")
    ax3.set_title(r"(c) Dominant $\mathrm{NO}$ Elementary Reactions in Stage 2", fontsize=12, pad=10)
    ax3.grid(True, linestyle="--", alpha=0.5)
    ax3.legend(frameon=True, fontsize=8.5, loc="lower left")

    plt.tight_layout()
    plt.savefig(PLOTS_DIR / "rop_u_curve_pathway_mechanism.png")
    plt.close()
    print(f"Saved {PLOTS_DIR / 'rop_u_curve_pathway_mechanism.png'}")

    # -------------------------------------------------------------
    # Figure 2: Top NO Formation & Destruction Reactions Breakdown
    # Compare Stage 1 vs Stage 2 at the three characteristic regimes
    # -------------------------------------------------------------
    fig, axes = plt.subplots(3, 2, figsize=(16, 12), dpi=300)
    regimes = [
        (1.0, "Left Branch: phi_1 = 1.0 (Stoichiometric Stage 1)"),
        (1.3, "Valley Minimum: phi_1 = 1.3 (Optimal DeNOx Window)"),
        (1.8, "Right Branch: phi_1 = 1.8 (Severe Staging / Rich Stage 1)"),
    ]

    for row_idx, (phi1_val, title_text) in enumerate(regimes):
        res = simulate_two_stage_detailed(x_nh3=0.50, phi_1=phi1_val, tau=0.060)

        # Stage 1 contributions
        df_s1 = compute_species_reaction_contributions(res["gas_stage1"], "NO")
        # Stage 2 contributions
        df_s2 = compute_species_reaction_contributions(res["gas_stage2"], "NO")

        for col_idx, (df_stage, stage_label) in enumerate([(df_s1, "Stage 1"), (df_s2, "Stage 2")]):
            ax = axes[row_idx, col_idx]
            if df_stage.empty:
                ax.text(0.5, 0.5, "No significant NO reactions", ha="center", va="center")
                continue

            top_prod = df_stage[df_stage["Contribution_kmol_m3_s"] > 0].head(4)
            top_dest = df_stage[df_stage["Contribution_kmol_m3_s"] < 0].tail(4)
            combined = pd.concat([top_dest, top_prod]).sort_values("Contribution_kmol_m3_s")

            bar_colors = ["darkred" if v < 0 else "navy" for v in combined["Contribution_kmol_m3_s"]]
            bars = ax.barh(np.arange(len(combined)), combined["Contribution_kmol_m3_s"], color=bar_colors, alpha=0.85)

            ax.set_yticks(np.arange(len(combined)))
            ax.set_yticklabels(combined["Equation"], fontsize=8.5)
            ax.axvline(0.0, color="black", linestyle="--", alpha=0.6)
            ax.grid(True, axis="x", linestyle="--", alpha=0.4)
            ax.set_title(f"{title_text} — {stage_label}", fontsize=10, fontweight="bold")
            if row_idx == 2:
                ax.set_xlabel(r"$\mathrm{NO}$ Production / Consumption Rate ($\mathrm{kmol\ m^{-3}\ s^{-1}}$)", fontsize=10)

    plt.tight_layout()
    plt.savefig(PLOTS_DIR / "rop_top_no_reactions_stage1_vs_stage2.png")
    plt.close()
    print(f"Saved {PLOTS_DIR / 'rop_top_no_reactions_stage1_vs_stage2.png'}")


if __name__ == "__main__":
    df_summary, df_rxns = sweep_rop_across_phi1()
    generate_reaction_path_diagrams()
    generate_rop_figures(df_summary, df_rxns)
    print("\nPhase-2 Kinetic ROP & Pathway Analysis Complete!")
