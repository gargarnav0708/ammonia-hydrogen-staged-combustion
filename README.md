# Ammonia–Hydrogen Staged Combustion

Cantera-based, zero-dimensional numerical investigation of ammonia–hydrogen combustion in two perfectly stirred reactors (PSRs) in series. The primary stage receives fuel and a controlled fraction of the air ($\phi_1 = 1.0 - 2.0$); the secondary stage receives the remaining air to complete lean combustion at fixed overall equivalence ratio ($\phi_{\mathrm{overall}} = 0.9$).

This repository contains the complete research program, executing all four phases of the future scope:
* **Initial 605-Case Parametric Study:** Fuel blend, air split, and residence time sweeps with global sensitivity analysis ($\eta^2$).
* **Phase 1 (Single-Stage Baseline):** Quantitative baseline proving an average **$55.1\%$ $\mathrm{NO}_x$ cut** (up to **$90.4\%$**).
* **Phase 2 (Chemical Kinetic ROP & Pathway Analysis):** Elementary kinetic explanation of the non-monotonic U-shaped $\mathrm{NO}_x$ response.
* **Phase 3 (Reactor Architecture & Mixing Physics):** Decoupled stage residence times ($\tau_1 \neq \tau_2$) and finite-rate progressive secondary air dilution ($N=1, 3, 5$ stages) reducing right-branch $\mathrm{NO}_x$ by **$88.3\%$**.
* **Phase 4 (Gas Turbine Operating Regimes):** Elevated combustor pressures ($P = 1 - 30\ \mathrm{atm}$), compressor discharge preheating ($T_{\mathrm{in}} = 300 - 750\ \mathrm{K}$), and non-adiabatic combustor liner wall cooling ($U_{\mathrm{wall}} = 0 - 3000\ \mathrm{W/m^2/K}$).

---

## Repository Contents

| Path | Purpose |
| --- | --- |
| `staged_combustion.py` | Shared model constants, air-split calculation, universal Cantera steady-state integrator, decoupled solver ($\tau_1 \neq \tau_2$), multi-stage finite mixing simulator, and gas turbine conditions engine |
| `single_stage_baseline.py` | **Phase 1:** Single-stage PSR baseline sweep, staged vs. single-stage comparison, and benefit quantification |
| `single_stage_NH3_H2.ipynb` | **Phase 1:** Interactive Jupyter notebook for single-stage baseline study |
| `rate_of_production_analysis.py` | **Phase 2:** Kinetic Rate of Production (ROP) analysis, elementary reaction tracking, and Graphviz reaction-path generation |
| `reaction_paths.ipynb` | **Phase 2:** Interactive Jupyter notebook for reaction-path flux diagrams and U-curve kinetic deconstruction |
| `decoupled_mixing_analysis.py` | **Phase 3:** Parametric engine for decoupled residence times ($\tau_1 \neq \tau_2$) and multi-stage progressive dilution ($N = 1, 3, 5$) |
| `decoupled_and_finite_mixing.ipynb` | **Phase 3:** Interactive Jupyter notebook for Phase 3 architecture and mixing physics |
| `gas_turbine_regimes_analysis.py` | **Phase 4:** Parametric engine for high-pressure ($1 - 30\ \mathrm{atm}$), preheat ($300 - 750\ \mathrm{K}$), and liner cooling sweeps |
| `gas_turbine_conditions.ipynb` | **Phase 4:** Interactive Jupyter notebook for gas turbine combustor regimes |
| `PHASE_1_2_IMPLEMENTATION_SUMMARY.md` | Comprehensive report on Phase 1 baseline quantification and Phase 2 chemical kinetics |
| `PHASE_3_IMPLEMENTATION_SUMMARY.md` | Comprehensive report on Phase 3 decoupled sizing and progressive finite-rate mixing physics |
| `PHASE_4_IMPLEMENTATION_SUMMARY.md` | Comprehensive report on Phase 4 gas turbine conditions, pressure shifts, preheating, and liner cooling |
| `full_results_modified.ipynb` | Main study: model setup, 605-case sweep, sensitivity ($\eta^2$), regression, and reliability analyses |
| `TamaokiNH3.yaml` | Cantera gas-phase reaction mechanism (Tamaoki et al., *Combustion and Flame*, 2024; 33 species, 228 reactions) |
| `single_stage_results.csv` | Single-stage PSR baseline dataset across 11 blends and 8 residence times |
| `staged_vs_single_stage_comparison.csv` | 469 matched case comparisons with delta emissions ($\Delta \mathrm{NO}_x$, $\Delta T$, $\Delta \text{slip}$) and percentage $\mathrm{NO}_x$ reduction |
| `rop_analysis_summary.csv` | Stage-by-stage thermodynamic, emission, and intermediate species carryover across $\phi_1 \in [1.0, 2.0]$ |
| `rop_no_reactions_by_phi1.csv` | Local elementary reaction progress rates and $\mathrm{NO}$ contribution rates |
| `decoupled_residence_time_results.csv` | 125 cases of independent $(\tau_1, \tau_2)$ sweeps across $\phi_1$ |
| `finite_mixing_comparison_results.csv` | Comparison of Instantaneous ($N=1$) vs. 3-stage vs. 5-stage progressive dilution across $\phi_1$ |
| `pressure_sweep_results.csv` | 55 cases of combustor pressure sweeps ($P = 1 - 30\ \mathrm{atm}$) across $\phi_1$ |
| `preheat_sweep_results.csv` | 28 cases of inlet preheat sweeps ($T_{\mathrm{in}} = 300 - 750\ \mathrm{K}$) at $10\ \mathrm{atm}$ |
| `heat_loss_sweep_results.csv` | 28 cases of combustor liner cooling sweeps ($U = 0 - 3000\ \mathrm{W/m^2/K}$) at $15\ \mathrm{atm}, 650\ \mathrm{K}$ |
| `staged_combustion_results_full.csv` | Expanded 605-case two-stage sweep results |
| `staged_combustion_research_metrics.csv` | Derived stage-wise metrics |
| `staged_combustion_eta_squared.csv` | Main-effect variance fractions ($\eta^2$) |
| `staged_combustion_regression_summary.csv` | Response-surface regression and cross-validation summary |
| `requirements.txt` | Python dependencies |

---

## Executive Summary of Findings

### 1. Phase 1: Baseline Quantification
* Staging achieves an average **$55.1\%$ reduction in $\mathrm{NO}_x$** compared to single-stage lean combustion at matched stoichiometry, with peak reductions exceeding **$90.4\%$** at $x_{\mathrm{NH_3}} = 0.20 - 0.30$.
* Staging is advantageous across all ammonia blends ($x_{\mathrm{NH_3}} \ge 0.10$).

### 2. Phase 2: Elementary Kinetic Origin of the U-Curve
* **Left branch ($\phi_1 = 1.0 - 1.2$):** High thermal/prompt $\mathrm{NO}$ formed directly in the hot Stage 1 ($\mathrm{HNO + OH \Leftrightarrow H_2O + NO}$).
* **Valley minimum ($\phi_1 \approx 1.2 - 1.4$):** Sub-stoichiometric oxygen depletion promotes **Thermal DeNOx** ($\mathrm{NH_2 + NO \Leftrightarrow N_2 + H_2O}$).
* **Right branch ($\phi_1 \ge 1.6 - 2.0$):** Severe oxygen starvation in Stage 1 causes incomplete pyrolysis, carrying unburnt $\mathrm{NH_2}$ into Stage 2 where sudden secondary oxygen addition triggers violent oxidation ($\mathrm{NH + O_2 \Leftrightarrow NO + OH}$).

### 3. Phase 3: Decoupled Residence Times & Finite-Rate Secondary Mixing
* **Decoupled Sizing ($\tau_1 \neq \tau_2$):** Longer primary residence times ($\tau_1 \approx 40 - 50\ \mathrm{ms}$) allow rich radicals to relax closer to equilibrium, lowering emissions by $300 - 600\ \mathrm{ppm}$.
* **Progressive Finite Dilution:** Replacing instantaneous air addition ($N=1$) with 5 progressive dilution stages ($N=5$) drops final $\mathrm{NO}_x$ at $\phi_1 = 2.0$ from **$3693\ \mathrm{ppm}$ to $433\ \mathrm{ppm}$ ($88.3\%$ cut!)** by enabling in-situ Thermal DeNOx in intermediate sub-rich stages.

### 4. Phase 4: Gas Turbine Combustor Regimes
* **Elevated Pressure ($1 - 30\ \mathrm{atm}$):** High pressure shifts the low-$\mathrm{NO}_x$ valley from $\phi_1 = 1.30$ down to $\phi_1 = 1.10$, suppresses near-stoichiometric prompt $\mathrm{NO}_x$ by $61.5\%$, and increases the $\mathrm{NO_2} / \mathrm{NO}_x$ ratio due to accelerated third-body $\mathrm{HO_2}$ radical recombination.
* **Preheat Escalation ($300 - 750\ \mathrm{K}$):** Higher inlet air temperatures raise flame temperatures by $\approx 100\ \mathrm{K}$ per $150\ \mathrm{K}$ preheat, accelerating thermal $\mathrm{NO}_x$; staging remains vital to prevent excessive emissions.
* **Combustor Liner Cooling:** Liner heat loss ($U = 3000\ \mathrm{W/m^2/K}$) lowers flame temperatures by $\approx 60\ \mathrm{K}$, cutting $\mathrm{NO}_x$ by over **$430\ \mathrm{ppm}$** without penalizing burnout ($<0.05\ \mathrm{ppm}$ unburnt fuel slip).

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

### 2. Running Simulation Modules
```bash
# Phase 1: Single-stage baseline
python single_stage_baseline.py

# Phase 2: Kinetic ROP and reaction path diagrams
python rate_of_production_analysis.py

# Phase 3: Decoupled residence times & progressive finite mixing
python decoupled_mixing_analysis.py

# Phase 4: Gas turbine conditions (pressure, preheat, wall cooling)
python gas_turbine_regimes_analysis.py
```

### 3. Interactive Jupyter Notebooks
* `single_stage_NH3_H2.ipynb`: Baseline quantification workflows.
* `reaction_paths.ipynb`: Nitrogen reaction-path diagrams and ROP analysis.
* `decoupled_and_finite_mixing.ipynb`: Architecture decoupling and progressive mixing physics.
* `gas_turbine_conditions.ipynb`: Gas turbine operating regimes.
* `full_results_modified.ipynb`: Main 605-case parametric study.
