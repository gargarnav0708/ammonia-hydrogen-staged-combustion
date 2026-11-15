from typing import Any
import numpy as np
import cantera as ct

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
    phase = getattr(reactor, "phase", getattr(reactor, "thermo", None))
    previous_temperature = reactor.T
    previous_mass_fractions = phase.Y.copy()

    minimum_time = t + min_residence_times * tau
    maximum_time = t + max_residence_times * tau

    while t < maximum_time:
        sim.advance(min(t + tau, maximum_time))
        t = sim.time

        current_temperature = reactor.T
        current_mass_fractions = phase.Y

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


def simulate_two_stage_decoupled(
    x_nh3: float,
    phi_1: float,
    tau_1: float,
    tau_2: float,
    phi_overall: float = PHI_OVERALL,
) -> dict[str, Any]:
    """
    Simulate two-stage combustion with independent residence times (tau_1 != tau_2).
    """
    x_h2 = 1.0 - x_nh3

    try:
        n_air_stoic, n_air_1, n_air_2 = calculate_air_amounts(x_nh3, phi_1)
        if n_air_2 < 0:
            raise ValueError("Secondary air amount is negative.")

        fuel = {}
        if x_nh3 > 0:
            fuel["NH3"] = x_nh3
        if x_h2 > 0:
            fuel["H2"] = x_h2

        gas = ct.Solution(MECH)

        # ------------------ PRIMARY STAGE (tau_1) ------------------
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

        mfc1 = ct.MassFlowController(inlet1, reactor1, mdot=lambda t: reactor1.mass / tau_1)
        pc1 = ct.PressureController(reactor1, exhaust1, primary=mfc1, K=0.01)

        sim1 = ct.ReactorNet([reactor1])
        converged1, itime1 = integrate_to_steady_state(sim1, reactor1, tau_1)
        if not converged1:
            raise RuntimeError(f"Primary PSR did not reach steady state for tau_1={tau_1*1000:.1f}ms")

        phase1 = getattr(reactor1, "phase", getattr(reactor1, "thermo", None))
        T_primary = reactor1.T

        primary_outlet_gas = ct.Solution(MECH)
        primary_outlet_gas.TDY = phase1.TDY

        primary_products = ct.Quantity(primary_outlet_gas, constant="HP")
        primary_products.moles = primary_mix.moles

        # ------------------ SECONDARY STAGE (tau_2) ------------------
        air_stream_2 = ct.Quantity(gas, constant="HP")
        air_stream_2.TPX = T_IN, P_IN, AIR
        air_stream_2.moles = n_air_2

        secondary_mix = primary_products + air_stream_2
        actual_overall_phi = n_air_stoic / (n_air_1 + n_air_2)

        gas2 = ct.Solution(MECH)
        gas2.TPX = secondary_mix.phase.TPX

        reactor2 = ct.IdealGasReactor(gas2, energy="on")
        reactor2.volume = 1.0

        inlet2 = ct.Reservoir(secondary_mix.phase)
        exhaust2 = ct.Reservoir(gas2)

        mfc2 = ct.MassFlowController(inlet2, reactor2, mdot=lambda t: reactor2.mass / tau_2)
        pc2 = ct.PressureController(reactor2, exhaust2, primary=mfc2, K=0.01)

        sim2 = ct.ReactorNet([reactor2])
        converged2, itime2 = integrate_to_steady_state(sim2, reactor2, tau_2)
        if not converged2:
            raise RuntimeError(f"Secondary PSR did not reach steady state for tau_2={tau_2*1000:.1f}ms")

        phase2 = getattr(reactor2, "phase", getattr(reactor2, "thermo", None))
        T_final = reactor2.T

        def get_mole_frac(phase, sp):
            return float(phase.X[phase.species_index(sp)]) if sp in phase.species_names else 0.0

        nox_primary = (get_mole_frac(phase1, "NO") + get_mole_frac(phase1, "NO2")) * 1e6
        nox_final = (get_mole_frac(phase2, "NO") + get_mole_frac(phase2, "NO2")) * 1e6

        return {
            "NH3_frac": round(x_nh3, 4),
            "H2_frac": round(x_h2, 4),
            "Phi_1": round(phi_1, 3),
            "Phi_overall": round(actual_overall_phi, 4),
            "Tau_1_ms": round(tau_1 * 1000.0, 2),
            "Tau_2_ms": round(tau_2 * 1000.0, 2),
            "Tau_ratio": round(tau_1 / tau_2, 3),
            "Tau_total_ms": round((tau_1 + tau_2) * 1000.0, 2),
            "T_primary_K": round(T_primary, 2),
            "T_final_K": round(T_final, 2),
            "Delta_T_K": round(T_final - T_primary, 2),
            "NOx_primary_ppm": round(nox_primary, 3),
            "NOx_final_ppm": round(nox_final, 3),
            "Delta_NOx_ppm": round(nox_final - nox_primary, 3),
            "NO_ppm": round(get_mole_frac(phase2, "NO") * 1e6, 3),
            "NO2_ppm": round(get_mole_frac(phase2, "NO2") * 1e6, 3),
            "N2O_ppm": round(get_mole_frac(phase2, "N2O") * 1e6, 3),
            "NH3_slip_ppm": round(get_mole_frac(phase2, "NH3") * 1e6, 4),
            "H2_slip_ppm": round(get_mole_frac(phase2, "H2") * 1e6, 4),
            "NH2_primary_ppm": round(get_mole_frac(phase1, "NH2") * 1e6, 4),
            "NH_primary_ppm": round(get_mole_frac(phase1, "NH") * 1e6, 4),
            "HNO_primary_ppm": round(get_mole_frac(phase1, "HNO") * 1e6, 4),
            "Status": "Converged",
        }

    except Exception as exc:
        return {
            "NH3_frac": round(x_nh3, 4),
            "H2_frac": round(x_h2, 4),
            "Phi_1": round(phi_1, 3),
            "Tau_1_ms": round(tau_1 * 1000.0, 2),
            "Tau_2_ms": round(tau_2 * 1000.0, 2),
            "Status": f"FAILED: {type(exc).__name__}: {exc}",
        }


def simulate_two_stage_finite_mixing(
    x_nh3: float,
    phi_1: float,
    tau_1: float,
    tau_2: float,
    n_mixing_stages: int = 3,
    phi_overall: float = PHI_OVERALL,
) -> dict[str, Any]:
    """
    Simulate two-stage combustion with progressive finite-rate secondary air dilution.
    """
    x_h2 = 1.0 - x_nh3

    try:
        n_air_stoic, n_air_1, n_air_2 = calculate_air_amounts(x_nh3, phi_1)
        if n_air_2 < 0:
            raise ValueError("Secondary air amount is negative.")

        fuel = {}
        if x_nh3 > 0:
            fuel["NH3"] = x_nh3
        if x_h2 > 0:
            fuel["H2"] = x_h2

        gas = ct.Solution(MECH)

        # ------------------ PRIMARY STAGE ------------------
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
        mfc1 = ct.MassFlowController(inlet1, reactor1, mdot=lambda t: reactor1.mass / tau_1)
        pc1 = ct.PressureController(reactor1, exhaust1, primary=mfc1, K=0.01)

        sim1 = ct.ReactorNet([reactor1])
        converged1, _ = integrate_to_steady_state(sim1, reactor1, tau_1)
        if not converged1:
            raise RuntimeError(f"Primary PSR did not converge for tau_1={tau_1*1000:.1f}ms")

        phase1 = getattr(reactor1, "phase", getattr(reactor1, "thermo", None))
        current_state = ct.Solution(MECH)
        current_state.TDY = phase1.TDY
        current_moles = primary_mix.moles

        # ------------------ PROGRESSIVE FINITE DILUTION STAGES ------------------
        d_air2 = n_air_2 / n_mixing_stages
        tau_sub = tau_2 / n_mixing_stages

        stage_temperatures = [round(reactor1.T, 2)]
        stage_nox_ppm = []
        air_injected_so_far = n_air_1

        for k in range(n_mixing_stages):
            prod_k = ct.Quantity(current_state, constant="HP")
            prod_k.moles = current_moles

            air_k = ct.Quantity(gas, constant="HP")
            air_k.TPX = T_IN, P_IN, AIR
            air_k.moles = d_air2

            mix_k = prod_k + air_k
            current_moles = mix_k.moles
            air_injected_so_far += d_air2

            gk = ct.Solution(MECH)
            gk.TPX = mix_k.phase.TPX

            rk = ct.IdealGasReactor(gk, energy="on")
            rk.volume = 1.0
            inlet_k = ct.Reservoir(mix_k.phase)
            exhaust_k = ct.Reservoir(gk)
            mfck = ct.MassFlowController(inlet_k, rk, mdot=lambda t: rk.mass / tau_sub)
            pck = ct.PressureController(rk, exhaust_k, primary=mfck, K=0.01)

            sim_k = ct.ReactorNet([rk])
            converged_k, _ = integrate_to_steady_state(sim_k, rk, tau_sub)
            if not converged_k:
                raise RuntimeError(f"Mixing stage {k+1}/{n_mixing_stages} did not converge.")

            phase_k = getattr(rk, "phase", getattr(rk, "thermo", None))
            current_state = ct.Solution(MECH)
            current_state.TDY = phase_k.TDY

            stage_temperatures.append(round(rk.T, 2))
            nox_k = (float(phase_k.X[phase_k.species_index("NO")]) + float(phase_k.X[phase_k.species_index("NO2")])) * 1e6
            stage_nox_ppm.append(round(nox_k, 3))

        final_phase = current_state
        def get_final_mole_frac(sp):
            return float(final_phase.X[final_phase.species_index(sp)]) if sp in final_phase.species_names else 0.0

        return {
            "NH3_frac": round(x_nh3, 4),
            "H2_frac": round(x_h2, 4),
            "Phi_1": round(phi_1, 3),
            "Phi_overall": round(n_air_stoic / air_injected_so_far, 4),
            "Tau_1_ms": round(tau_1 * 1000.0, 2),
            "Tau_2_ms": round(tau_2 * 1000.0, 2),
            "N_mixing_stages": n_mixing_stages,
            "T_primary_K": stage_temperatures[0],
            "T_final_K": stage_temperatures[-1],
            "T_peak_mixing_K": max(stage_temperatures),
            "Stage_temperatures": stage_temperatures,
            "Stage_NOx_ppm": stage_nox_ppm,
            "NOx_final_ppm": stage_nox_ppm[-1],
            "NO_ppm": round(get_final_mole_frac("NO") * 1e6, 3),
            "NO2_ppm": round(get_final_mole_frac("NO2") * 1e6, 3),
            "N2O_ppm": round(get_final_mole_frac("N2O") * 1e6, 3),
            "NH3_slip_ppm": round(get_final_mole_frac("NH3") * 1e6, 4),
            "H2_slip_ppm": round(get_final_mole_frac("H2") * 1e6, 4),
            "Status": "Converged",
        }

    except Exception as exc:
        return {
            "NH3_frac": round(x_nh3, 4),
            "Phi_1": round(phi_1, 3),
            "Tau_1_ms": round(tau_1 * 1000.0, 2),
            "Tau_2_ms": round(tau_2 * 1000.0, 2),
            "N_mixing_stages": n_mixing_stages,
            "Status": f"FAILED: {type(exc).__name__}: {exc}",
        }


def simulate_two_stage_gas_turbine(
    x_nh3: float,
    phi_1: float,
    tau_1: float = 0.040,
    tau_2: float = 0.060,
    p_atm: float = 1.0,
    t_in: float = 300.0,
    u_wall: float = 0.0,
    wall_area: float = 0.25,
    phi_overall: float = PHI_OVERALL,
) -> dict[str, Any]:
    """
    Simulate two-stage combustion under realistic gas turbine conditions:
    elevated pressure (P = 1 to 30 atm), preheated air (T_in = 300 to 750 K),
    and non-adiabatic combustor liner cooling (U_wall in W/m^2/K).
    """
    x_h2 = 1.0 - x_nh3
    p_pa = p_atm * 101325.0

    try:
        n_air_stoic, n_air_1, n_air_2 = calculate_air_amounts(x_nh3, phi_1)
        if n_air_2 < 0:
            raise ValueError("Secondary air amount is negative.")

        fuel = {}
        if x_nh3 > 0:
            fuel["NH3"] = x_nh3
        if x_h2 > 0:
            fuel["H2"] = x_h2

        gas = ct.Solution(MECH)

        # ------------------ PRIMARY STAGE ------------------
        fuel_stream = ct.Quantity(gas, constant="HP")
        fuel_stream.TPX = t_in, p_pa, fuel
        fuel_stream.moles = 1.0

        air_stream_1 = ct.Quantity(gas, constant="HP")
        air_stream_1.TPX = t_in, p_pa, AIR
        air_stream_1.moles = n_air_1

        primary_mix = fuel_stream + air_stream_1

        gas1 = ct.Solution(MECH)
        gas1.TPX = primary_mix.phase.TPX
        gas1.equilibrate("HP")

        reactor1 = ct.IdealGasReactor(gas1, energy="on")
        reactor1.volume = 1.0
        inlet1 = ct.Reservoir(primary_mix.phase)
        exhaust1 = ct.Reservoir(gas1)
        mfc1 = ct.MassFlowController(inlet1, reactor1, mdot=lambda t: reactor1.mass / tau_1)
        pc1 = ct.PressureController(reactor1, exhaust1, primary=mfc1, K=0.01)

        if u_wall > 0:
            amb1 = ct.Solution(MECH)
            amb1.TPX = 300.0, p_pa, AIR
            env1 = ct.Reservoir(amb1)
            w1 = ct.Wall(reactor1, env1)
            w1.area = wall_area
            w1.heat_transfer_coeff = u_wall

        sim1 = ct.ReactorNet([reactor1])
        converged1, itime1 = integrate_to_steady_state(sim1, reactor1, tau_1)
        if not converged1:
            raise RuntimeError(f"Primary PSR did not converge for P={p_atm:.1f}atm, Tin={t_in:.0f}K")

        phase1 = getattr(reactor1, "phase", getattr(reactor1, "thermo", None))
        T_primary = reactor1.T

        primary_outlet_gas = ct.Solution(MECH)
        primary_outlet_gas.TDY = phase1.TDY
        primary_products = ct.Quantity(primary_outlet_gas, constant="HP")
        primary_products.moles = primary_mix.moles

        # ------------------ SECONDARY STAGE ------------------
        air_stream_2 = ct.Quantity(gas, constant="HP")
        air_stream_2.TPX = t_in, p_pa, AIR
        air_stream_2.moles = n_air_2

        secondary_mix = primary_products + air_stream_2
        actual_overall_phi = n_air_stoic / (n_air_1 + n_air_2)

        gas2 = ct.Solution(MECH)
        gas2.TPX = secondary_mix.phase.TPX

        reactor2 = ct.IdealGasReactor(gas2, energy="on")
        reactor2.volume = 1.0
        inlet2 = ct.Reservoir(secondary_mix.phase)
        exhaust2 = ct.Reservoir(gas2)
        mfc2 = ct.MassFlowController(inlet2, reactor2, mdot=lambda t: reactor2.mass / tau_2)
        pc2 = ct.PressureController(reactor2, exhaust2, primary=mfc2, K=0.01)

        if u_wall > 0:
            amb2 = ct.Solution(MECH)
            amb2.TPX = 300.0, p_pa, AIR
            env2 = ct.Reservoir(amb2)
            w2 = ct.Wall(reactor2, env2)
            w2.area = wall_area
            w2.heat_transfer_coeff = u_wall

        sim2 = ct.ReactorNet([reactor2])
        converged2, itime2 = integrate_to_steady_state(sim2, reactor2, tau_2)
        if not converged2:
            raise RuntimeError(f"Secondary PSR did not converge for P={p_atm:.1f}atm, Tin={t_in:.0f}K")

        phase2 = getattr(reactor2, "phase", getattr(reactor2, "thermo", None))
        T_final = reactor2.T

        def get_mole_frac(phase, sp):
            return float(phase.X[phase.species_index(sp)]) if sp in phase.species_names else 0.0

        nox_ppm = (get_mole_frac(phase2, "NO") + get_mole_frac(phase2, "NO2")) * 1e6
        no2_ppm = get_mole_frac(phase2, "NO2") * 1e6
        no_ppm = get_mole_frac(phase2, "NO") * 1e6
        no2_ratio = no2_ppm / nox_ppm if nox_ppm > 0 else 0.0

        return {
            "NH3_frac": round(x_nh3, 4),
            "H2_frac": round(x_h2, 4),
            "Phi_1": round(phi_1, 3),
            "Phi_overall": round(actual_overall_phi, 4),
            "P_atm": round(p_atm, 2),
            "T_in_K": round(t_in, 1),
            "U_wall_W_m2K": round(u_wall, 1),
            "Tau_1_ms": round(tau_1 * 1000.0, 2),
            "Tau_2_ms": round(tau_2 * 1000.0, 2),
            "T_primary_K": round(T_primary, 2),
            "T_final_K": round(T_final, 2),
            "Delta_T_K": round(T_final - T_primary, 2),
            "NOx_ppm": round(nox_ppm, 3),
            "NO_ppm": round(no_ppm, 3),
            "NO2_ppm": round(no2_ppm, 3),
            "NO2_ratio": round(no2_ratio, 4),
            "N2O_ppm": round(get_mole_frac(phase2, "N2O") * 1e6, 3),
            "NH3_slip_ppm": round(get_mole_frac(phase2, "NH3") * 1e6, 4),
            "H2_slip_ppm": round(get_mole_frac(phase2, "H2") * 1e6, 4),
            "Status": "Converged",
        }

    except Exception as exc:
        return {
            "NH3_frac": round(x_nh3, 4),
            "Phi_1": round(phi_1, 3),
            "P_atm": round(p_atm, 2),
            "T_in_K": round(t_in, 1),
            "U_wall_W_m2K": round(u_wall, 1),
            "Status": f"FAILED: {type(exc).__name__}: {exc}",
        }


def simulate_case(
    params: tuple[Any, ...],
    steady_state_integrator: Any = integrate_to_steady_state,
) -> dict[str, Any]:
    """
    Backward-compatible wrapper supporting 3-tuple (x_nh3, phi_1, tau)
    and 4-tuple (x_nh3, phi_1, tau_1, tau_2).
    """
    if len(params) == 3:
        x_nh3, phi_1, tau = params
        return simulate_two_stage_decoupled(x_nh3, phi_1, tau, tau)
    elif len(params) == 4:
        x_nh3, phi_1, tau_1, tau_2 = params
        return simulate_two_stage_decoupled(x_nh3, phi_1, tau_1, tau_2)
    else:
        raise ValueError(f"Expected 3 or 4 parameters, got {len(params)}")
