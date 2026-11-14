from typing import Any

import numpy as np

MECH = "TamaokiNH3.yaml"
T_IN = 300.0
P_IN = 101325.0
PHI_OVERALL = 0.9
AIR = {"O2": 1.0, "N2": 3.76}


def calculate_air_amounts(
    x_nh3: float,
    phi_1: float,
) -> tuple[float, float, float]:
    """Return stoichiometric, primary, and secondary air moles per mole fuel."""
    x_h2 = 1.0 - x_nh3
    oxygen_stoichiometric = 0.75 * x_nh3 + 0.50 * x_h2
    air_stoichiometric = 4.76 * oxygen_stoichiometric
    air_primary = air_stoichiometric / phi_1
    air_total = air_stoichiometric / PHI_OVERALL
    air_secondary = air_total - air_primary
    return air_stoichiometric, air_primary, air_secondary


def integrate_to_steady_state(
    sim: Any,
    reactor: Any,
    tau: float,
    min_residence_times: float = 5.0,
    max_residence_times: float = 100.0,
    tolerance: float = 1e-8,
) -> tuple[bool, float]:
    """Advance a PSR until temperature and composition reach steady state.

    Steady state requires relative changes below ``tolerance`` after at least
    ``min_residence_times``. Integration stops at ``max_residence_times`` if
    the convergence criterion is not met. This replaces
    ``ReactorNet.solve_steady()`` for this model.
    """
    t = sim.time
    previous_temperature = reactor.T
    previous_mass_fractions = reactor.phase.Y.copy()

    minimum_time = t + min_residence_times * tau
    maximum_time = t + max_residence_times * tau

    while t < maximum_time:
        sim.advance(min(t + tau, maximum_time))
        t = sim.time

        current_temperature = reactor.T
        current_mass_fractions = reactor.phase.Y

        temperature_change = abs(current_temperature - previous_temperature) / max(
            abs(current_temperature), 1.0
        )
        composition_change = np.max(
            np.abs(current_mass_fractions - previous_mass_fractions)
            / np.maximum(np.abs(current_mass_fractions), 1e-30)
        )

        if (
            t >= minimum_time
            and temperature_change < tolerance
            and composition_change < tolerance
        ):
            return True, t

        previous_temperature = current_temperature
        previous_mass_fractions = current_mass_fractions.copy()

    return False, t
