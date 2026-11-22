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
| `single_stage/` | Single-stage baseline simulation and its notebook |
| `double_stage/` | Shared two-stage model, main parametric study, and Phase 2–4 analyses/notebooks |
| `results/` | All generated and supplied CSV datasets; figures and reaction-path files are in `results/plots/` |
| `mechanisms/` | Cantera gas-phase mechanism |
| `docs/` | Phase implementation summaries and project reports |
| `references/` | Source papers and background reference material |
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
python -m single_stage.single_stage_baseline

# Phase 2: Kinetic ROP and reaction path diagrams
python -m double_stage.rate_of_production_analysis

# Phase 3: Decoupled residence times & progressive finite mixing
python -m double_stage.decoupled_mixing_analysis

# Phase 4: Gas turbine conditions (pressure, preheat, wall cooling)
python -m double_stage.gas_turbine_regimes_analysis
```

### 3. Interactive Jupyter Notebooks
Launch Jupyter from the repository root so notebook imports and paths resolve correctly.
* `single_stage/single_stage_NH3_H2.ipynb`: Baseline quantification workflows.
* `double_stage/reaction_paths.ipynb`: Nitrogen reaction-path diagrams and ROP analysis.
* `double_stage/decoupled_and_finite_mixing.ipynb`: Architecture decoupling and progressive mixing physics.
* `double_stage/gas_turbine_conditions.ipynb`: Gas turbine operating regimes.
* `double_stage/full_results_modified.ipynb`: Main 605-case parametric study.

---

## End-Semester Report & Statistical Significance
* `docs/reports/BTP_End_Semester_Report.docx` – full end-semester report (Phases 1–4, pathway analysis, statistics); regenerate with `python docs/reports/build_end_semester_report.py` (figures from the mid-semester report are in `docs/reports/mid_sem_figures/`).
* `python -m double_stage.statistical_significance_analysis` → `results/statistical_significance_summary.csv` (ANOVA, paired/non-parametric tests, bootstrap CIs, effect sizes for every phase).
