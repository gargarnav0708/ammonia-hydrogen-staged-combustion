# Ammonia–Hydrogen Staged Combustion

Cantera-based, zero-dimensional numerical investigation of ammonia–hydrogen combustion in two perfectly stirred reactors (PSRs) in series. The primary stage receives fuel and a controlled fraction of the air ($\phi_1 = 1.0 - 2.0$); the secondary stage receives the remaining air to complete lean combustion at fixed overall equivalence ratio ($\phi_{\mathrm{overall}} = 0.9$).

This repository contains the complete progressive research roadmap:
* **Initial 605-Case Parametric Study:** Fuel blend, air split, and residence time sweeps.
* **Phase 1 (Single-Stage Baseline):** Quantitative baseline proving an average **$55.1\%$ $\mathrm{NO}_x$ cut** (up to **$90.4\%$**).
* **Phase 2 (Chemical Kinetic ROP & Pathway Analysis):** Elementary kinetic explanation of the non-monotonic U-shaped $\mathrm{NO}_x$ response.
* **Phase 3 (Reactor Architecture & Mixing Physics):** Decoupled stage residence times ($\tau_1 \neq \tau_2$) and finite-rate progressive secondary air dilution ($N=1, 3, 5$ stages) reducing right-branch $\mathrm{NO}_x$ by **$88.3\%$**.

---

## Repository Contents

| Path | Purpose |
| --- | --- |
| `staged_combustion.py` | Shared model constants, air-split calculation, universal Cantera steady-state integrator, decoupled solver ($\tau_1 \neq \tau_2$), and multi-stage finite mixing simulator |
| `single_stage_baseline.py` | **Phase 1:** Single-stage PSR baseline sweep, staged vs. single-stage comparison, and benefit quantification |
| `single_stage_NH3_H2.ipynb` | **Phase 1:** Interactive Jupyter notebook for single-stage baseline study |
| `rate_of_production_analysis.py` | **Phase 2:** Kinetic Rate of Production (ROP) analysis, elementary reaction tracking, and Graphviz reaction-path generation |
| `reaction_paths.ipynb` | **Phase 2:** Interactive Jupyter notebook for reaction-path flux diagrams and U-curve kinetic deconstruction |
| `decoupled_mixing_analysis.py` | **Phase 3:** Parametric engine for decoupled residence times ($\tau_1 \neq \tau_2$) and multi-stage progressive dilution ($N = 1, 3, 5$) |
| `decoupled_and_finite_mixing.ipynb` | **Phase 3:** Interactive Jupyter notebook for Phase 3 architecture and mixing physics |
| `PHASE_1_2_IMPLEMENTATION_SUMMARY.md` | Comprehensive report on Phase 1 baseline quantification and Phase 2 chemical kinetics |
| `PHASE_3_IMPLEMENTATION_SUMMARY.md` | Comprehensive report on Phase 3 decoupled sizing and progressive finite-rate mixing physics |
| `full_results_modified.ipynb` | Main study: model setup, 605-case sweep, sensitivity ($\eta^2$), regression, and reliability analyses |
| `TamaokiNH3.yaml` | Cantera gas-phase reaction mechanism (Tamaoki et al., *Combustion and Flame*, 2024; 33 species, 228 reactions) |
| `single_stage_results.csv` | Single-stage PSR baseline dataset across 11 blends and 8 residence times |
| `staged_vs_single_stage_comparison.csv` | 469 matched case comparisons with delta emissions ($\Delta \mathrm{NO}_x$, $\Delta T$, $\Delta \text{slip}$) and percentage $\mathrm{NO}_x$ reduction |
| `rop_analysis_summary.csv` | Stage-by-stage thermodynamic, emission, and intermediate species carryover across $\phi_1 \in [1.0, 2.0]$ |
| `rop_no_reactions_by_phi1.csv` | Local elementary reaction progress rates and $\mathrm{NO}$ contribution rates |
| `decoupled_residence_time_results.csv` | 125 cases of independent $(\tau_1, \tau_2)$ sweeps across $\phi_1$ |
| `finite_mixing_comparison_results.csv` | Comparison of Instantaneous ($N=1$) vs. 3-stage vs. 5-stage progressive dilution across $\phi_1$ |
| `staged_combustion_results_full.csv` | Expanded 605-case two-stage sweep results |
| `staged_combustion_research_metrics.csv` | Derived stage-wise metrics |
| `staged_combustion_eta_squared.csv` | Main-effect variance fractions ($\eta^2$) |
| `staged_combustion_regression_summary.csv` | Response-surface regression and cross-validation summary |
| `requirements.txt` | Python dependencies |

---

## Key Research Findings

### 1. Phase 1: Baseline Quantification
* **Average $\mathrm{NO}_x$ Reduction:** **$55.1\%$** across all converged cases compared to an identical single PSR at $\phi_{\mathrm{overall}} = 0.9$.
* **Peak $\mathrm{NO}_x$ Reduction:** Exceeds **$90.4\%$** at $x_{\mathrm{NH_3}} = 0.20 - 0.30$, $\phi_1 \ge 1.6$, $\tau = 20\ \mathrm{ms}$.
* **Staging Envelope:** Staging is advantageous across all ammonia blends ($x_{\mathrm{NH_3}} \ge 0.10$), cutting emissions while maintaining complete burnout in Stage 2.

### 2. Phase 2: Elementary Kinetic Origin of the U-Curve
The U-curve across $\phi_1$ is an exact superposition of two counteracting mechanisms:
1. **Monotonic Drop in Stage 1 ($4400\ \mathrm{ppm} \rightarrow 29\ \mathrm{ppm}$):** Oxygen starvation in Stage 1 drops temperature from $2168\ \mathrm{K} \rightarrow 1720\ \mathrm{K}$, shutting down thermal $\mathrm{NO}$ pathways ($\mathrm{HNO + OH \Leftrightarrow H_2O + NO}$, $\mathrm{N_2 + O \Leftrightarrow NO + N}$).
2. **Thermal DeNOx Valley ($\phi_1 \approx 1.2 - 1.4$):** Moderate richness suppresses oxygen radicals while promoting direct reduction:
   $$\mathrm{NH_2 + NO \Leftrightarrow N_2 + H_2O}$$
   $$\mathrm{NH_2 + NO \Leftrightarrow NNH + OH}$$
   reaching global minimum emissions ($986\ \mathrm{ppm}$ at $x_{\mathrm{NH_3}} = 0.5, \tau = 60\ \mathrm{ms}$).
3. **Monotonic Surge in Stage 2 ($-190\ \mathrm{ppm} \rightarrow +3586\ \mathrm{ppm}$):** In rich Stage 1 ($\phi_1 > 1.6$), incomplete $\mathrm{NH_3}$ pyrolysis carries unburnt amine radicals ($\mathrm{NH_2}$ rising to $86\ \mathrm{ppm}$) into Stage 2. Instantaneous mixing with secondary air ignites rapid oxidative branching:
   $$\mathrm{HNO + OH \Leftrightarrow H_2O + NO} \quad (14\times \text{ increase})$$
   $$\mathrm{NH + O_2 \Leftrightarrow NO + OH} \quad (>5000\times \text{ increase})$$

### 3. Phase 3: Decoupled Residence Times & Finite-Rate Secondary Mixing
* **Decoupled Stage Sizing ($\tau_1 \neq \tau_2$):** Increasing primary residence time $\tau_1$ from $10\ \mathrm{ms}$ to $50\ \mathrm{ms}$ allows rich radicals to relax closer to equilibrium, lowering final $\mathrm{NO}_x$ by $300 - 600\ \mathrm{ppm}$. Sizing ratio $\tau_1 / \tau_2 \approx 0.5$ with $\tau_2 \ge 60\ \mathrm{ms}$ ensures virtually zero fuel slip ($<0.1\ \mathrm{ppm}$).
* **Progressive Finite Dilution:** Replacing instantaneous air addition ($N=1$) with 5 progressive dilution stages ($N=5$) drops final $\mathrm{NO}_x$ at $\phi_1 = 2.0$ from **$3693\ \mathrm{ppm}$ to $433\ \mathrm{ppm}$ — an $88.3\%$ reduction!**
  * *Mechanism:* Progressive dilution allows intermediate parcels to pass through sub-rich states where **in-situ Thermal DeNOx** consumes $\mathrm{NO}$ before reaching lean conditions, preventing the radical oxidation surge seen in idealized instantaneous mixing.

---

## Setup & Execution

### 1. Environment Installation
Python 3.10 or later is recommended.
```bash
# Using Conda
conda activate cantera_env

# Or using venv
source .venv-btp/bin/activate
pip install -r requirements.txt
```

### 2. Running Simulations
```bash
# Phase 1: Single-stage baseline
python single_stage_baseline.py

# Phase 2: Kinetic ROP and reaction path diagrams
python rate_of_production_analysis.py

# Phase 3: Decoupled residence times & progressive finite mixing
python decoupled_mixing_analysis.py
```

### 3. Interactive Jupyter Notebooks
* `single_stage_NH3_H2.ipynb`: Baseline quantification workflows.
* `reaction_paths.ipynb`: Nitrogen reaction-path diagrams and ROP analysis.
* `decoupled_and_finite_mixing.ipynb`: Architecture decoupling and progressive mixing physics.
* `full_results_modified.ipynb`: Main 605-case parametric study.

---

## Future Roadmap (Phase 4)
* **Phase 4:** High-pressure combustor regimes ($P = 5 - 30\ \mathrm{atm}$), compressor discharge preheating ($T_{\mathrm{in}} = 400 - 750\ \mathrm{K}$), and non-adiabatic combustor liner heat losses.
