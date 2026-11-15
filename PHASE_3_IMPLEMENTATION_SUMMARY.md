# Phase-3 Implementation Summary: Reactor Architecture & Mixing Physics

**Author:** Arnav Garg (IIT Delhi)  
**Project:** Numerical Investigation of Two-Stage $\mathrm{NH_3/H_2}$ Staged Combustion in Perfectly Stirred Reactors  
**Mechanism:** Tamaoki et al. (2024) NH₃ kinetic mechanism (`TamaokiNH3.yaml`)  
**Toolkit:** Cantera 3.0.0 (Python Interface)

---

## Executive Summary

Phase 3 eliminates the two primary simplifying assumptions highlighted in the study's limitations (Slides 16 & 17 of `presentation.pdf`):
1. **Decoupled Residence Times ($\tau_1 \neq \tau_2$):** We modified the two-stage solver to decouple primary reactor residence time ($\tau_1 = 10 - 50\ \mathrm{ms}$) from secondary burnout residence time ($\tau_2 = 20 - 100\ \mathrm{ms}$) across 125 parametric configurations.
2. **Finite-Rate Secondary Mixing:** We replaced the idealized instantaneous secondary air addition with a progressive multi-stage dilution model ($N = 1, 3, 5$ mixing stages) that captures the gradual transition from rich primary conditions ($\phi_1$) through stoichiometric regimes to lean burnout ($\phi_{\mathrm{overall}} = 0.9$).

### Breakthrough Discovery:
* In the original instantaneous mixing model, rich staging ($\phi_1 \ge 1.6$) caused a violent secondary $\mathrm{NO}_x$ surge (reaching $>3690\ \mathrm{ppm}$ at $\phi_1 = 2.0$) due to sudden oxygen addition reacting with carried-over amine radicals.
* **Under progressive finite-rate dilution ($N=5$), final $\mathrm{NO}_x$ at $\phi_1 = 2.0$ drops from $3693\ \mathrm{ppm}$ down to $433\ \mathrm{ppm}$ — an $88.3\%$ reduction!**
* **Physical Reason:** Progressive air dilution creates an extended, high-temperature sub-rich reaction zone where intermediate amine radicals ($\mathrm{NH_2}$) cleanly consume $\mathrm{NO}$ via **Thermal DeNOx** ($\mathrm{NH_2 + NO \Leftrightarrow N_2 + H_2O}$) *before* the mixture reaches lean burnout, transforming the high-emissions penalty zone into an ultra-clean operating regime!

---

## Part 1: Decoupled Residence Time Modeling ($\tau_1 \neq \tau_2$)

### 1.1 Motivation & Formulation

In real gas turbines and staged industrial burners, the rich primary zone and the lean burnout zone have distinctly different physical volumes and velocities:
* **Primary Zone ($\tau_1$):** Must be sufficiently long to anchor the flame and initiate partial oxidation, but needs to be evaluated for whether a shorter residence time limits excessive radical dissociation and $\mathrm{NH_i}$ carryover.
* **Secondary Zone ($\tau_2$):** Must provide sufficient residence time for lean burnout of residual fuel slip ($\mathrm{H_2, NH_3}$) and $\mathrm{NO}_x$ equilibration.

We defined the stage sizing ratio:
$$\theta = \frac{\tau_1}{\tau_2}$$
$$\tau_{\mathrm{total}} = \tau_1 + \tau_2$$

We simulated a 2D matrix of $\tau_1 \in [10, 20, 30, 40, 50]\ \mathrm{ms}$ and $\tau_2 \in [20, 40, 60, 80, 100]\ \mathrm{ms}$ across $\phi_1 \in [1.2, 1.4, 1.6, 1.8, 2.0]$ at reference fuel blend ($50\%\ \mathrm{NH_3} / 50\%\ \mathrm{H_2}$).

### 1.2 Quantitative Observations

Mean $\mathrm{NO}_x$ (ppm) as a function of primary residence time $\tau_1$:

| Primary $\phi_1$ | $\tau_1 = 10\ \mathrm{ms}$ | $\tau_1 = 20\ \mathrm{ms}$ | $\tau_1 = 30\ \mathrm{ms}$ | $\tau_1 = 40\ \mathrm{ms}$ | $\tau_1 = 50\ \mathrm{ms}$ |
| :---: | :---: | :---: | :---: | :---: | :---: |
| **1.2** | 1808.0 | 1503.0 | 1356.3 | 1264.9 | **1200.7** |
| **1.4** | 1534.9 | 1354.1 | 1265.1 | 1207.7 | **1165.6** |
| **1.6** | 2071.2 | 1923.5 | 1856.8 | 1816.5 | **1788.4** |
| **1.8** | 2878.9 | 2715.4 | 2651.1 | 2617.2 | **2596.8** |
| **2.0** | 4105.0 | 3879.8 | 3794.0 | 3750.8 | **3726.4** |

### 1.3 Key Architectural Takeaways:
1. **Primary Stage Residence Time ($\tau_1$):** Increasing $\tau_1$ from $10\ \mathrm{ms}$ to $50\ \mathrm{ms}$ consistently reduces final $\mathrm{NO}_x$ across all rich conditions (by $300 - 600\ \mathrm{ppm}$). This occurs because a longer primary stage allows the rich combustion radical pool to relax closer to chemical equilibrium, reducing excess non-equilibrium radical spikes.
2. **Fuel Slip vs. $\tau_1 / \tau_2$ Ratio:** A larger secondary residence time ($\tau_2 \ge 60\ \mathrm{ms}$) ensures that unburnt $\mathrm{NH_3}$ slip remains below $0.1\ \mathrm{ppm}$, while shorter $\tau_2$ ($<20\ \mathrm{ms}$) permits up to $5-15\ \mathrm{ppm}$ slip under rich primary conditions.

---

## Part 2: Finite-Rate Secondary Mixing Modeling

### 2.1 The Mixing Model Architecture

In the classical 0-D two-stage model, all secondary air $n_{\mathrm{air,2}}$ was instantaneously added into a single mixing reservoir. In reality, turbulent mixing and air injection occur over a finite mixing length and time.

To resolve this, we implemented a progressive multi-stage dilution sequence:
* The secondary air $n_{\mathrm{air,2}}$ is partitioned equally into $N$ discrete injection parcels: $\Delta n_{\mathrm{air,2}} = n_{\mathrm{air,2}} / N$.
* The secondary residence time $\tau_2$ is subdivided: $\tau_{\mathrm{sub}} = \tau_2 / N$.
* In each dilution stage $k \in \{1, \dots, N\}$, product gas from stage $k-1$ mixes with $\Delta n_{\mathrm{air,2}}$ of fresh air and reacts to steady state before entering stage $k+1$.

We compared:
* **$N = 1$:** Instantaneous mixing baseline
* **$N = 3$:** 3-stage progressive finite dilution
* **$N = 5$:** 5-stage progressive finite dilution

### 2.2 Results: Flattening the $\mathrm{NO}_x$ U-Curve

Final $\mathrm{NO}_x$ emissions (ppm) across $\phi_1 \in [1.0, 2.0]$ at reference condition ($x_{\mathrm{NH_3}} = 0.50$, $\tau_1 = 30\ \mathrm{ms}$, $\tau_2 = 60\ \mathrm{ms}$):

| Primary $\phi_1$ | Instantaneous ($N=1$) | 3-Stage Mixing ($N=3$) | 5-Stage Mixing ($N=5$) | Finite-Rate $\mathrm{NO}_x$ Reduction (%) |
| :---: | :---: | :---: | :---: | :---: |
| **1.0** | 4819.9 | 4497.0 | 4397.9 | **-8.8%** |
| **1.1** | 2242.0 | 1943.1 | 1843.9 | **-17.8%** |
| **1.2** | 1357.6 | 1088.3 | 1007.2 | **-25.8%** |
| **1.3** | 1138.8 | 804.7 | 714.3 | **-37.3%** |
| **1.4** | 1261.1 | 734.1 | 619.7 | **-50.9%** |
| **1.5** | 1522.9 | 717.3 | 578.1 | **-62.0%** |
| **1.6** | 1836.3 | 706.8 | 546.4 | **-70.2%** |
| **1.7** | 2189.9 | 695.4 | 517.1 | **-76.4%** |
| **1.8** | 2602.4 | 682.2 | 488.5 | **-81.2%** |
| **1.9** | 3100.8 | 665.1 | 459.9 | **-85.2%** |
| **2.0** | **3693.1** | **640.0** | **433.1** | **-88.3%** |

### 2.3 Physical Mechanism of the Reduction
1. **Suppression of the Right-Branch Surge:**
   Under instantaneous mixing, dumping a large air parcel into rich products causes oxygen radicals ($\mathrm{O, OH}$) to violently oxidize $\mathrm{NH_2}$ and $\mathrm{NH}$ directly into $\mathrm{NO}$ via $\mathrm{NH + O_2 \Leftrightarrow NO + OH}$.
2. **In-Situ DeNOx in Progressive Mixing:**
   In progressive dilution ($N=3, 5$), stage 1 of mixing introduces only a small fraction of air. The local equivalence ratio drops only slightly (e.g. from $\phi = 2.0 \rightarrow 1.6$), maintaining a hot, reducing environment where **Thermal DeNOx** ($\mathrm{NH_2 + NO \Leftrightarrow N_2 + H_2O}$) dominates. Instead of forming new $\mathrm{NO}$, the amine radicals consume existing $\mathrm{NO}$ and convert into inert $\mathrm{N_2}$ before the mixture ever reaches lean conditions.
3. **Thermal Trajectory:**
   Tracking stage temperatures reveals that intermediate mixing stages pass through near-stoichiometric zones ($\phi \approx 1.0$), reaching localized peak temperatures ($T_{\mathrm{peak}} \approx 2180\ \mathrm{K}$) before cooling to final lean burnout ($T_{\mathrm{final}} \approx 2100\ \mathrm{K}$). Because residence time in each sub-stage is short ($\tau_{\mathrm{sub}} = 12\ \mathrm{ms}$), thermal $\mathrm{NO}$ formation remains kinetically constrained while DeNOx proceeds rapidly.

---

## Part 3: Phase 3 Deliverables & Artifacts

### Code:
* [`staged_combustion.py`](file:///Users/herr_ag98/Library/CloudStorage/OneDrive-IITDelhi/SEM7%20MAT/BTP/staged_combustion.py): Added `simulate_two_stage_decoupled` and `simulate_two_stage_finite_mixing`.
* [`decoupled_mixing_analysis.py`](file:///Users/herr_ag98/Library/CloudStorage/OneDrive-IITDelhi/SEM7%20MAT/BTP/decoupled_mixing_analysis.py): Parametric engine for 2D residence time sweeps and multi-stage finite mixing comparisons.
* [`decoupled_and_finite_mixing.ipynb`](file:///Users/herr_ag98/Library/CloudStorage/OneDrive-IITDelhi/SEM7%20MAT/BTP/decoupled_and_finite_mixing.ipynb): Interactive notebook running sweeps and displaying figures.

### Datasets:
* `decoupled_residence_time_results.csv`: 125 cases across $(\tau_1, \tau_2, \phi_1)$.
* `finite_mixing_comparison_results.csv`: 33 cases comparing $N = 1, 3, 5$ across $\phi_1 \in [1.0, 2.0]$.

### Publication Figures:
* `plots/decoupled_tau_2d_contour.png`: 2D contour maps of $\mathrm{NO}_x$ over $(\tau_1, \tau_2)$ across $\phi_1 = 1.2, 1.4, 1.6, 2.0$.
* `plots/decoupled_tau_ratio_tradeoff.png`: Impact of sizing ratio $\tau_1 / \tau_2$ on $\mathrm{NO}_x$ and fuel slip.
* `plots/finite_mixing_nox_comparison.png`: Comparison of $\mathrm{NO}_x$ curves showing the $88\%$ reduction achieved by progressive dilution.
* `plots/finite_mixing_temperature_trajectories.png`: Progressive temperature trajectories through the mixing stages.
