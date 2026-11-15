# Ammonia–Hydrogen Staged Combustion

Cantera-based, zero-dimensional numerical investigation of ammonia–hydrogen combustion in two perfectly stirred reactors (PSRs) in series. The primary stage receives fuel and a controlled fraction of the air ($\phi_1 = 1.0 - 2.0$); the secondary stage receives the remaining air to complete lean combustion at fixed overall equivalence ratio ($\phi_{\mathrm{overall}} = 0.9$).

This repository contains the full 605-case parametric study along with **Phase-1 (Single-Stage Baseline Comparison)** and **Phase-2 (Chemical Kinetic Rate of Production & Pathway Deconstruction)** implementations.

---

## Repository Contents

| Path | Purpose |
| --- | --- |
| `single_stage_baseline.py` | **Phase 1:** Single-stage PSR baseline sweep, staged vs. single-stage comparison, and staging benefit quantification |
| `single_stage_NH3_H2.ipynb` | **Phase 1:** Interactive Jupyter notebook for the single-stage baseline study |
| `rate_of_production_analysis.py` | **Phase 2:** Kinetic Rate of Production (ROP) analysis, elementary reaction progress tracking, and Graphviz reaction-path generation |
| `reaction_paths.ipynb` | **Phase 2:** Interactive Jupyter notebook for reaction-path flux diagrams and U-curve kinetic deconstruction |
| `PHASE_1_2_IMPLEMENTATION_SUMMARY.md` | Comprehensive research report detailing mathematical formulations, baseline findings, and elementary kinetic mechanisms |
| `full_results_modified.ipynb` | Main study: model setup, 605-case sweep, plots, sensitivity ($\eta^2$), regression, and reliability analyses |
| `staged_combustion.py` | Shared model constants, air-split calculation, and universal Cantera steady-state integrator |
| `TamaokiNH3.yaml` | Cantera gas-phase reaction mechanism (Tamaoki et al., *Combustion and Flame*, 2024; 33 species, 228 reactions) |
| `single_stage_results.csv` | Single-stage PSR baseline dataset across 11 blends and 8 residence times |
| `staged_vs_single_stage_comparison.csv` | 469 matched case comparisons with delta emissions ($\Delta \mathrm{NO}_x$, $\Delta T$, $\Delta \text{slip}$) and percentage $\mathrm{NO}_x$ reduction |
| `rop_analysis_summary.csv` | Stage-by-stage thermodynamic, emission, and intermediate species carryover across $\phi_1 \in [1.0, 2.0]$ |
| `rop_no_reactions_by_phi1.csv` | Local elementary reaction progress rates and $\mathrm{NO}$ contribution rates |
| `staged_combustion_results_full.csv` | Expanded 605-case two-stage sweep results |
| `staged_combustion_research_metrics.csv` | Derived stage-wise metrics |
| `staged_combustion_eta_squared.csv` | Main-effect variance fractions ($\eta^2$) |
| `staged_combustion_regression_summary.csv` | Response-surface regression and 5-fold cross-validation summary |
| `requirements.txt` | Python dependencies |

---

## Key Research Findings

### 1. Phase 1: Quantitative Benefit of Staging
Comparing the two-stage model directly against an identical single-stage PSR at fixed $\phi_{\mathrm{overall}} = 0.9$:
* **Average $\mathrm{NO}_x$ Reduction:** **$55.1\%$** across all converged cases.
* **Peak $\mathrm{NO}_x$ Reduction:** Exceeds **$90.4\%$** at $x_{\mathrm{NH_3}} = 0.20 - 0.30$, $\phi_1 \ge 1.6$, $\tau = 20\ \mathrm{ms}$ (dropping baseline $\mathrm{NO}_x$ from $>10,000\ \mathrm{ppm}$ to $<1,000\ \mathrm{ppm}$).
* **Operating Windows:**
  * **Staging Advantage Zone:** For all $\mathrm{NH_3}$ blends ($x_{\mathrm{NH_3}} \ge 0.10$), staging air via a moderately rich primary zone ($\phi_1 = 1.2 - 1.5$) reliably cuts $\mathrm{NO}_x$ by $60\% - 86\%$ while ensuring complete fuel burnout in Stage 2.
  * **Staging Penalty Zone:** For pure $\mathrm{H_2}$ ($x_{\mathrm{NH_3}} = 0.0$), staging adds extra residence time at high temperatures without fuel nitrogen to suppress, increasing thermal $\mathrm{NO}$. For very rich ammonia staging ($\phi_1 \ge 1.7, x_{\mathrm{NH_3}} \ge 0.7$), excess radical carryover increases Stage 2 $\mathrm{NO}_x$.

### 2. Phase 2: Elementary Kinetic Origin of the U-Shaped $\mathrm{NO}_x$ Curve
Through local Rate of Production (ROP) analysis, the non-monotonic U-curve across $\phi_1$ was identified as the exact superposition of two counteracting mechanisms:
1. **Monotonic Drop in Stage 1 ($4400\ \mathrm{ppm} \rightarrow 29\ \mathrm{ppm}$):** As $\phi_1$ increases from 1.0 to 2.0, Stage 1 becomes oxygen-starved, reducing temperature from $2168\ \mathrm{K} \rightarrow 1720\ \mathrm{K}$ and shutting down thermal/prompt $\mathrm{NO}$ pathways ($\mathrm{HNO + OH \Leftrightarrow H_2O + NO}$, $\mathrm{N_2 + O \Leftrightarrow NO + N}$).
2. **Thermal DeNOx Valley ($\phi_1 \approx 1.2 - 1.4$):** Moderate richness suppresses oxygen radicals while promoting direct reduction:
   $$\mathrm{NH_2 + NO \Leftrightarrow N_2 + H_2O}$$
   $$\mathrm{NH_2 + NO \Leftrightarrow NNH + OH}$$
   $$\mathrm{N + NO \Leftrightarrow N_2 + O}$$
   Final $\mathrm{NO}_x$ reaches its absolute global minimum ($986\ \mathrm{ppm}$ at $x_{\mathrm{NH_3}} = 0.5, \tau = 60\ \mathrm{ms}$).
3. **Monotonic Surge in Stage 2 ($-190\ \mathrm{ppm} \rightarrow +3586\ \mathrm{ppm}$):** In rich Stage 1 ($\phi_1 > 1.6$), incomplete $\mathrm{NH_3}$ pyrolysis carries unburnt amine radicals ($\mathrm{NH_2}$ rising from $5\ \mathrm{ppm} \rightarrow 86\ \mathrm{ppm}$) into Stage 2. When mixed with the large secondary air stream ($A_2/A_{\mathrm{total}} = 55\%$), rapid oxidative branching ignites:
   $$\mathrm{HNO + OH \Leftrightarrow H_2O + NO} \quad (\text{rate increases by } 14\times)$$
   $$\mathrm{NH + O_2 \Leftrightarrow NO + OH} \quad (\text{rate increases by } >5000\times)$$
   driving total $\mathrm{NO}_x$ back up to $3615\ \mathrm{ppm}$.

---

## Setup & Execution

### 1. Environment Installation
Python 3.10 or later is recommended. Using Conda or virtualenv:

```bash
# Using Conda
conda env create -f cantera_environment.yml  # Or activate cantera_env
conda activate cantera_env

# Or using venv
python -m venv .venv-btp
source .venv-btp/bin/activate
pip install -r requirements.txt
```

### 2. Running Phase 1 (Single-Stage Baseline)
Execute the baseline sweep and generate comparative plots:
```bash
python single_stage_baseline.py
```
Outputs saved:
* `single_stage_results.csv`
* `staged_vs_single_stage_comparison.csv`
* `plots/baseline_nox_comparison.png`
* `plots/staging_benefit_heatmap.png`
* `plots/baseline_tradeoff_scatter.png`

### 3. Running Phase 2 (Chemical Kinetic ROP & Pathway Analysis)
Execute the ROP sweep and generate nitrogen reaction path diagrams:
```bash
python rate_of_production_analysis.py
```
*Note: Reaction-path rendering requires Graphviz (`dot`) on `PATH` (included in `cantera_env`).*  
Outputs saved:
* `rop_analysis_summary.csv`
* `rop_no_reactions_by_phi1.csv`
* `plots/rop_u_curve_pathway_mechanism.png`
* `plots/rop_top_no_reactions_stage1_vs_stage2.png`
* `plots/reaction_path_phi1_1p*.png`

### 4. Interactive Jupyter Notebooks
* Run `single_stage_NH3_H2.ipynb` for the step-by-step baseline analysis.
* Run `reaction_paths.ipynb` for interactive pathway exploration.
* Run `full_results_modified.ipynb` for the original 605-case parametric study.

---

## Future Roadmap (Phases 3 & 4)
* **Phase 3:** Decoupled stage residence times ($\tau_1 \neq \tau_2$) and finite-rate secondary air dilution.
* **Phase 4:** Elevated pressure combustor regimes ($P = 5 - 30\ \mathrm{atm}$) and non-adiabatic combustor liner heat loss.
