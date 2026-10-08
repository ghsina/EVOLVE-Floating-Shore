"""All user-editable inputs of the planner, with defaults, units and help text.

One flat dictionary holds every input. ``SPEC`` describes each entry for the
interface and the Excel workbook; ``derive`` turns the flat inputs into the
quantities the optimisation model uses (configuration, export technology,
compression work, nested storage/pipeline tables, ...).

Default values are the v9 techno-economic set (Step 2 validation). Entries
marked ``step3=True`` are placeholders that Step 3 replaces with referenced
values; the interface flags them.
"""
from __future__ import annotations

import copy
import math
from dataclasses import dataclass, field


@dataclass
class P:
    key: str
    group: str
    label: str
    unit: str
    default: object
    kind: str = "float"            # float | int | bool | choice | text
    options: tuple = ()
    help: str = ""
    step3: bool = False
    advanced: bool = False
    min: float | None = None
    max: float | None = None


SPEC: list[P] = [
    # ------------------------------------------------------------------ use case
    P("use_case", "Use case", "What the island supplies", "-", "Hybrid", "choice",
      ("Power-led", "Hydrogen-led", "Hybrid"),
      "Power-led: electricity to the grid, hydrogen only as internal storage. Hydrogen-led: hydrogen to an "
      "offtaker, electricity optional. Hybrid: both contracts."),
    P("annual_demand_mwh", "Use case", "Electricity to deliver per year", "MWh/yr", 200_000.0, min=0.0,
      help="Contracted electricity at the grid point. Ignored in merchant and CfD modes, where volume is free."),
    P("annual_h2_demand_kg", "Use case", "Hydrogen to deliver per year", "kg/yr", 2.0e6, min=0.0),
    P("elec_delivery", "Use case", "Electricity delivery profile", "-", "annual", "choice",
      ("annual", "firm", "profile"),
      "annual: only the yearly volume counts. firm: the same power every hour. profile: follow the hourly "
      "profile uploaded with the time series (column elec_demand_mw)."),
    P("h2_delivery", "Use case", "Hydrogen delivery profile", "-", "annual", "choice", ("annual", "firm", "profile"),
      "As for electricity; profile uses column h2_demand_kgh."),
    P("elec_revenue", "Use case", "Electricity revenue", "-", "ppa", "choice", ("ppa", "merchant", "cfd"),
      "ppa: fixed volume at the PPA price. merchant: every MWh sold at the hourly day-ahead price. cfd: two-sided "
      "contract for difference, strike price paid in hours with non-negative price (French offshore scheme)."),
    P("ppa_price_eur_mwh", "Use case", "PPA price", "EUR/MWh", 100.0, min=0.0),
    P("cfd_strike_eur_mwh", "Use case", "CfD strike price", "EUR/MWh", 86.45, min=0.0,
      help="Bretagne Sud 1 (Pennavel) award, 15 May 2024: EUR 86.45/MWh."),
    P("h2_price_eur_kg", "Use case", "Hydrogen sales price", "EUR/kg", 6.0, min=0.0),
    P("sell_surplus", "Use case", "Sell the other carrier as a by-product", "-", False, "bool",
      help="Power-led: sell hydrogen made from surplus power at the hydrogen price. Hydrogen-led: sell "
           "surplus electricity (merchant or CfD). Off: only the main product earns revenue."),
    P("grid_injection_cap_mw", "Use case", "Maximum grid injection", "MW", 100.0, min=0.0,
      help="Firm capacity of the grid connection."),
    # ------------------------------------------------------------------ site
    P("site_name", "Site", "Site name", "-", "My floating island", "text"),
    P("site_lat", "Site", "Island latitude", "deg", 47.38, min=-90.0, max=90.0),
    P("site_lon", "Site", "Island longitude", "deg", -3.55, min=-180.0, max=180.0),
    P("grid_name", "Site", "Grid connection point", "-", "Grid substation", "text"),
    P("grid_lat", "Site", "Grid point latitude", "deg", 47.64, min=-90.0, max=90.0),
    P("grid_lon", "Site", "Grid point longitude", "deg", -3.16, min=-180.0, max=180.0),
    P("h2_name", "Site", "Hydrogen offtake point", "-", "Hydrogen offtaker", "text"),
    P("h2_lat", "Site", "Hydrogen offtake latitude", "deg", 47.27, min=-90.0, max=90.0),
    P("h2_lon", "Site", "Hydrogen offtake longitude", "deg", -2.20, min=-180.0, max=180.0),
    P("route_method", "Site", "How route lengths are found", "-", "sea route", "choice",
      ("sea route", "straight line"),
      "sea route: shortest path through the sea on the bundled 1 km coastline (around islands and headlands) "
      "from the island to the coast nearest the onshore point, plus a straight onshore leg. straight line: "
      "great-circle distance x routing factor. An entered route length below always wins."),
    P("routing_factor", "Site", "Routing factor (route / straight line)", "-", 1.2, min=1.0, max=3.0,
      help="Used with the straight-line method. Cables and pipes rarely run straight; 1.1-1.3 is typical."),
    P("link_distance_override_km", "Site", "Export cable route length (0 = computed)", "km", 0.0, min=0.0,
      help="Enter the routed length from a cable route study if you have it; it replaces the computed length "
           "(to the grid point, or to the hub when the island connects to a hub)."),
    P("pipe_distance_override_km", "Site", "Pipeline route length (0 = computed)", "km", 0.0, min=0.0,
      help="Routed pipeline length if known (to the offtake point, or to the tie-in point)."),
    P("avg_water_depth_m", "Site", "Water depth at the island", "m", 75.0, min=0.0,
      help="Up to the fixed/floating threshold the island is bottom-fixed; deeper it floats."),
    P("fixed_floating_depth_m", "Site", "Fixed/floating threshold depth", "m", 60.0, min=0.0, advanced=True),
    P("decentralized_h2", "Site", "Turbine-level electrolysis (no power cable)", "-", False, "bool",
      help="Floating, decentralised concept (Dolphyn type): hydrogen made in each turbine, pipeline export only."),
    P("existing_pipeline_available", "Site", "Existing gas pipeline on the route can be repurposed", "-", False, "bool"),
    P("sea_area_km2", "Site", "Usable sea area", "km2", 38.0, min=0.0,
      help="Polygon available for turbines and floating PV."),
    P("wind_density_mw_km2", "Site", "Wind power density", "MW/km2", 6.3, min=0.1,
      help="Bretagne Sud: 250 MW on 40 km2 and 500 MW on 75 km2 (State brochure, 2026)."),
    P("pv_density_mw_km2", "Site", "Floating PV density", "MW/km2", 60.0, min=0.1, step3=True),
    P("deck_area_max_m2", "Site", "Island deck area available", "m2", 200_000.0, min=0.0,
      help="Area for electrolysers, compressors, fuel cells, batteries and tanks on the island."),
    P("area_onshore_max_m2", "Site", "Onshore plot area", "m2", 1_000_000.0, min=0.0),
    # ------------------------------------------------------------------ connections to existing infrastructure
    P("elec_connection", "Connections", "Electricity connection", "-", "direct", "choice",
      options=("direct", "hub", "choose"),
      help="Direct: own export cable to the onshore grid point. Hub: short cable to a nearby offshore substation "
           "or cable with spare capacity (its owner carries the power to shore for an access fee). Choose: the "
           "model sizes both and keeps the cheaper."),
    P("hub_name", "Connections", "Nearby offshore substation or cable", "-", "Nearby offshore substation", "text"),
    P("hub_lat", "Connections", "Hub latitude", "deg", 47.42, min=-90.0, max=90.0),
    P("hub_lon", "Connections", "Hub longitude", "deg", -3.45, min=-180.0, max=180.0),
    P("hub_spare_mw", "Connections", "Spare capacity at the hub", "MW", 100.0, min=0.0,
      help="Capacity the hub owner can offer; it caps the power the island can export through the hub."),
    P("hub_voltage_kv", "Connections", "Hub voltage", "kV", 225.0, min=1.0,
      help="AC voltage of the hub; sets the rating of the cable from the island."),
    P("hub_access_fee_eur_mw_yr", "Connections", "Hub access fee", "EUR/MW/yr", 42_000.0, min=0.0, step3=True,
      help="Annual charge per MW of connection for using the hub and its link to shore."),
    P("export_voltage", "Connections", "Export cable voltage", "-", "auto", "choice",
      options=("auto", "66 kV AC", "132 kV AC", "220 kV AC", "275 kV AC", "320 kV DC", "525 kV DC"),
      help="Auto: 220 kV AC up to the HVAC/HVDC distance threshold, 320 kV DC beyond. A DC choice forces HVDC "
           "costs and losses. The voltage sets the rating per circuit and so the number of circuits."),
    P("rating_66", "Connections", "Rating per circuit, 66 kV AC", "MW", 100.0, step3=True, advanced=True),
    P("rating_132", "Connections", "Rating per circuit, 132 kV AC", "MW", 180.0, step3=True, advanced=True),
    P("rating_220", "Connections", "Rating per circuit, 220 kV AC", "MW", 300.0, step3=True, advanced=True,
      help="RTE Bretagne Sud: about 250 MW per 225 kV circuit."),
    P("rating_275", "Connections", "Rating per circuit, 275 kV AC", "MW", 450.0, step3=True, advanced=True),
    P("rating_320dc", "Connections", "Rating per circuit, 320 kV DC", "MW", 1000.0, step3=True, advanced=True),
    P("rating_525dc", "Connections", "Rating per circuit, 525 kV DC", "MW", 2000.0, step3=True, advanced=True),
    P("h2_connection", "Connections", "Hydrogen connection", "-", "direct", "choice",
      options=("direct", "tiein", "choose"),
      help="Direct: own pipeline to the offtake point. Tie-in: short pipeline to a nearby pipeline with spare "
           "capacity. Choose: the model sizes both and keeps the cheaper."),
    P("tiein_name", "Connections", "Nearby pipeline tie-in point", "-", "Nearby pipeline", "text"),
    P("tiein_lat", "Connections", "Tie-in latitude", "deg", 47.45, min=-90.0, max=90.0),
    P("tiein_lon", "Connections", "Tie-in longitude", "deg", -3.30, min=-180.0, max=180.0),
    P("tiein_spare_kgh", "Connections", "Spare capacity in the pipeline", "kg/h", 20_000.0, min=0.0),
    P("tiein_pressure_bar", "Connections", "Pipeline operating pressure", "bar", 70.0, min=1.0,
      help="Compressors deliver hydrogen at this pressure when tying in."),
    P("tiein_fee_eur", "Connections", "Tie-in cost (hot tap, metering)", "EUR", 5.0e6, min=0.0, step3=True),
    # ------------------------------------------------------------------ technology switches
    P("enable_pv", "Technologies", "Floating PV", "-", True, "bool"),
    P("enable_ez_off", "Technologies", "Electrolyser on the island", "-", True, "bool"),
    P("enable_ez_on", "Technologies", "Electrolyser onshore", "-", True, "bool"),
    P("enable_fc_off", "Technologies", "Fuel cell on the island", "-", True, "bool"),
    P("enable_fc_on", "Technologies", "Fuel cell onshore", "-", True, "bool"),
    P("enable_batt_off", "Technologies", "Battery on the island", "-", True, "bool"),
    P("enable_batt_on", "Technologies", "Battery onshore", "-", True, "bool"),
    P("enable_tank_off", "Technologies", "Hydrogen tank on the island", "-", True, "bool"),
    P("enable_tank_on", "Technologies", "Hydrogen tank onshore", "-", True, "bool"),
    P("enable_cable", "Technologies", "Electricity export cable", "-", True, "bool"),
    P("enable_pipe", "Technologies", "Hydrogen export pipeline", "-", True, "bool"),
    # ------------------------------------------------------------------ finance
    P("discount_rate", "Finance", "Discount rate (real WACC)", "fraction", 0.07, min=0.0, max=0.3),
    P("offshore_premium", "Finance", "Offshore cost premium on island equipment", "x", 1.10, min=1.0, step3=True),
    # ------------------------------------------------------------------ wind
    P("wind_capex_eur_mw", "Offshore wind", "CAPEX, bottom-fixed", "EUR/MW", 2_540_000.0, min=0.0, step3=True),
    P("wind_capex_floating_eur_mw", "Offshore wind", "CAPEX, floating", "EUR/MW", 2_540_000.0, min=0.0, step3=True,
      help="Placeholder equal to bottom-fixed (v9). Step 3 sets the referenced floating value."),
    P("wind_life", "Offshore wind", "Lifetime", "yr", 25, "int", min=1),
    P("wind_fom", "Offshore wind", "Fixed O&M, bottom-fixed", "fraction/yr", 0.025, min=0.0),
    P("wind_fom_floating", "Offshore wind", "Fixed O&M, floating", "fraction/yr", 0.03, min=0.0),
    P("turbine_mw", "Offshore wind", "Turbine rating (for the drawing)", "MW", 15.0, min=1.0, advanced=True),
    # ------------------------------------------------------------------ PV
    P("pv_capex_eur_kw", "Floating PV", "CAPEX", "EUR/kW", 1500.0, min=0.0, step3=True),
    P("pv_life", "Floating PV", "Lifetime", "yr", 25, "int", min=1),
    P("pv_fom", "Floating PV", "Fixed O&M", "fraction/yr", 0.02, min=0.0),
    # ------------------------------------------------------------------ electrolysis
    P("elec_capex_eur_kw", "Electrolysis", "CAPEX (stack + balance of plant)", "EUR/kW", 2000.0, min=0.0, step3=True),
    P("electrolyzer_efficiency", "Electrolysis", "Efficiency (LHV)", "fraction", 0.75, min=0.3, max=1.0),
    P("elec_life", "Electrolysis", "Lifetime (stack replacement)", "yr", 15, "int", min=1),
    P("elec_fom", "Electrolysis", "Fixed O&M", "fraction/yr", 0.015, min=0.0),
    P("area_elec_m2_mw", "Electrolysis", "Deck area", "m2/MW", 200.0, min=0.0, advanced=True),
    P("wt_capex_eur_mw", "Electrolysis", "Water treatment CAPEX", "EUR/MW", 20_750.0, min=0.0, advanced=True),
    P("wt_life", "Electrolysis", "Water treatment lifetime", "yr", 20, "int", advanced=True),
    P("wt_fom", "Electrolysis", "Water treatment O&M", "fraction/yr", 0.10, advanced=True),
    # ------------------------------------------------------------------ compression
    P("comp_p_in_bar", "Compression", "Inlet pressure", "bar", 30.0, min=1.0),
    P("comp_p_out_bar", "Compression", "Outlet pressure", "bar", 70.0, min=1.0),
    P("comp_isentropic_eff", "Compression", "Isentropic efficiency", "fraction", 0.75, min=0.3, max=1.0),
    P("comp_stages", "Compression", "Stages", "-", 2, "int", min=1, advanced=True),
    P("comp_inlet_temp_k", "Compression", "Inlet temperature", "K", 313.0, advanced=True),
    P("comp_z", "Compression", "Compressibility factor", "-", 1.05, advanced=True),
    P("comp_gamma", "Compression", "Heat capacity ratio of hydrogen", "-", 1.41, min=1.01, max=1.67,
      advanced=True),
    P("comp_capex_eur_mw", "Compression", "CAPEX", "EUR/MW", 2.0e6, min=0.0, step3=True),
    P("comp_life", "Compression", "Lifetime", "yr", 20, "int", min=1),
    P("comp_fom", "Compression", "Fixed O&M", "fraction/yr", 0.03, min=0.0),
    P("area_comp_m2_mw", "Compression", "Deck area", "m2/MW", 100.0, advanced=True),
    # ------------------------------------------------------------------ fuel cell
    P("fc_efficiency_lhv", "Fuel cell", "Efficiency (LHV)", "fraction", 0.50, min=0.1, max=1.0),
    P("fc_capex_eur_kw", "Fuel cell", "CAPEX", "EUR/kW", 1170.0, min=0.0),
    P("fc_life", "Fuel cell", "Lifetime", "yr", 15, "int", min=1),
    P("fc_fom", "Fuel cell", "Fixed O&M", "fraction/yr", 0.03, min=0.0),
    P("area_fc_m2_mw", "Fuel cell", "Deck area", "m2/MW", 120.0, advanced=True),
    # ------------------------------------------------------------------ batteries
    P("batt_capex_e_eur_mwh", "Battery", "Energy CAPEX", "EUR/MWh", 160_000.0, min=0.0),
    P("batt_capex_p_eur_mw", "Battery", "Power CAPEX", "EUR/MW", 5_343_913.0, min=0.0, step3=True),
    P("batt_eta", "Battery", "Charge and discharge efficiency (each way)", "fraction", 0.95, min=0.5, max=1.0),
    P("batt_life", "Battery", "Lifetime", "yr", 15, "int", min=1),
    P("batt_fom", "Battery", "Fixed O&M", "fraction/yr", 0.02, min=0.0),
    P("batt_vom", "Battery", "Variable O&M", "EUR/MWh", 1.19, min=0.0),
    P("area_batt_m2_mwh", "Battery", "Deck area", "m2/MWh", 25.0, advanced=True),
    P("batt_max_mwh", "Battery", "Largest battery allowed, energy (each site)", "MWh", 1.0e5, min=0.0,
      advanced=True),
    P("batt_max_mw", "Battery", "Largest battery allowed, power (each site)", "MW", 2.0e4, min=0.0, advanced=True),
    # ------------------------------------------------------------------ tanks
    P("tank_capex_eur_kg", "Hydrogen tank", "CAPEX", "EUR/kg", 650.0, min=0.0),
    P("tank_life", "Hydrogen tank", "Lifetime", "yr", 20, "int", min=1),
    P("tank_fom", "Hydrogen tank", "Fixed O&M", "fraction/yr", 0.02, min=0.0),
    P("tank_vom", "Hydrogen tank", "Variable O&M", "EUR/kg", 0.01, min=0.0),
    P("area_tank_m2_kg", "Hydrogen tank", "Deck area", "m2/kg", 1.5, advanced=True),
    P("tank_max_kg", "Hydrogen tank", "Largest tank allowed (each site)", "kg", 5.0e6, min=0.0, advanced=True),
    # ------------------------------------------------------------------ export cable
    P("hvac_hvdc_threshold_km", "Export cable", "HVAC up to (beyond: HVDC)", "km", 60.0, min=0.0),
    P("hvac_var_eur_mw_km", "Export cable", "HVAC cost per MW per km", "EUR/MW/km", 1360.0, step3=True),
    P("hvac_fix_eur_km", "Export cable", "HVAC fixed cost per km", "EUR/km", 206_130.0, step3=True),
    P("hvac_loss_per_km", "Export cable", "HVAC loss per km", "fraction/km", 6.7e-5),
    P("hvdc_converter_pair_eur_mw", "Export cable", "HVDC converter pair", "EUR/MW", 300_000.0, step3=True,
      help="ACER 2026 median is 0.21 M EUR/MW per station (0.42 per pair); Step 3 updates this."),
    P("hvdc_cable_eur_mw_km", "Export cable", "HVDC cable", "EUR/MW/km", 1000.0, step3=True),
    P("hvdc_converter_loss", "Export cable", "HVDC converter losses (pair)", "fraction", 0.02),
    P("hvdc_cable_loss_per_km", "Export cable", "HVDC cable loss per km", "fraction/km", 3.5e-5),
    P("tso_fee_eur_mw_yr", "Export cable", "TSO grid fee, HVAC export", "EUR/MW/yr", 42_000.0, min=0.0,
      help="Annual charge per MW of export cable paid to the transmission operator when the island exports "
           "through its own HVAC cable (French offshore scheme: the TSO owns the shore connection). With a "
           "hub, the hub access fee replaces it."),
    P("tso_fee_hvdc_eur_mw_yr", "Export cable", "TSO grid fee, HVDC export", "EUR/MW/yr", 0.0, min=0.0,
      help="Same charge for an HVDC export. 0 by default: the converter pair is already in the cable cost."),
    P("cable_fom_hvac", "Export cable", "Fixed O&M, HVAC cable", "fraction/yr", 0.005, min=0.0),
    P("cable_fom_hvdc", "Export cable", "Fixed O&M, HVDC link", "fraction/yr", 0.01, min=0.0),
    P("hvdc_float_premium", "Export cable", "Floating converter premium (floating island)", "x", 1.5, min=1.0,
      help="Multiplies the HVDC converter cost when the island floats and makes its own power (concept B)."),
    P("cable_life", "Export cable", "Lifetime", "yr", 30, "int", min=1),
    # ------------------------------------------------------------------ pipeline
    P("pipe_small_capex_eur_km", "Hydrogen pipeline", "New 12-inch: cost", "EUR/km", 1.0e6, step3=True),
    P("pipe_small_cap_kgh", "Hydrogen pipeline", "New 12-inch: capacity", "kg/h", 33_264.0),
    P("pipe_medium_capex_eur_km", "Hydrogen pipeline", "New 36-inch: cost", "EUR/km", 3.7e6),
    P("pipe_medium_cap_kgh", "Hydrogen pipeline", "New 36-inch: capacity", "kg/h", 141_000.0),
    P("pipe_repurposed_capex_eur_km", "Hydrogen pipeline", "Repurposed 36-inch: cost", "EUR/km", 0.4e6),
    P("pipe_repurposed_cap_kgh", "Hydrogen pipeline", "Repurposed 36-inch: capacity", "kg/h", 108_000.0),
    P("pipeline_efficiency", "Hydrogen pipeline", "Delivery efficiency", "fraction", 0.99),
    P("pipeline_life", "Hydrogen pipeline", "Lifetime", "yr", 40, "int"),
    P("pipeline_fom", "Hydrogen pipeline", "Fixed O&M", "fraction/yr", 0.009),
    # ------------------------------------------------------------------ platform
    P("platform_cable_coef", "Island platform", "Platform cost per MW of export cable", "kEUR/MW", 84.651, step3=True),
    P("platform_elec_coef", "Island platform", "Platform cost per MW of island equipment", "kEUR/MW", 139.281, step3=True),
    P("platform_install_factor", "Island platform", "Installation factor", "x", 1.5),
    P("platform_float_factor", "Island platform", "Floating platform factor", "x", 2.0, min=1.0,
      help="Multiplies the platform cost when the island floats and hosts the electrical plant (concept B)."),
    P("platform_life", "Island platform", "Lifetime", "yr", 25, "int"),
    P("platform_fom", "Island platform", "Fixed O&M", "fraction/yr", 0.02),
    # ------------------------------------------------------------------ penalties
    P("shortfall_penalty_eur_mwh", "Solver", "Penalty for undelivered electricity", "EUR/MWh", 3000.0, advanced=True),
    P("shortfall_penalty_eur_kg", "Solver", "Penalty for undelivered hydrogen", "EUR/kg", 100.0, advanced=True),
    P("lhv_h2_kwh_kg", "Solver", "Hydrogen LHV", "kWh/kg", 33.3, advanced=True),
    P("cap_ub_mw", "Solver", "Upper bound on any converter or cable capacity", "MW", 5000.0, advanced=True),
    P("cap_renewable_ub_mw", "Solver", "Upper bound on wind and PV capacity", "MW", 10_000.0, advanced=True,
      help="The usable sea area and power densities normally limit wind and PV first."),
]

BY_KEY = {s.key: s for s in SPEC}
GROUP_ORDER = []
for s in SPEC:
    if s.group not in GROUP_ORDER:
        GROUP_ORDER.append(s.group)


def defaults() -> dict:
    return {s.key: copy.deepcopy(s.default) for s in SPEC}


def crf(r: float, n: float) -> float:
    return r * (1 + r) ** n / ((1 + r) ** n - 1) if r > 0 else 1.0 / n


def haversine_km(lat1, lon1, lat2, lon2) -> float:
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def route_length(p: dict, a, b, override_km=0.0, sea=False) -> tuple[float, str]:
    """Route length from a to b and how it was found.

    Entered length > sea route on the coastline (to the coast nearest b, then straight onshore; for an
    offshore end point such as a hub, `sea` keeps the whole route at sea) > straight line x routing factor."""
    if override_km and override_km > 0:
        return float(override_km), "entered"
    straight = haversine_km(a[0], a[1], b[0], b[1])
    if p.get("route_method", "sea route") == "sea route" and straight > 0.5:
        try:
            from . import geo
            km = geo.sea_km(a[0], a[1], b[0], b[1]) if sea else geo.route_km(a[0], a[1], b[0], b[1])[0]
            if km and math.isfinite(km):
                return float(max(km, straight)), "sea route"
        except Exception:      # no coastline file or an odd window: fall back to the straight line
            pass
    return straight * p["routing_factor"], "straight line x factor"


def derive(user: dict, elec=None, h2=None) -> dict:
    """Flat user inputs -> everything the model needs. `elec`/`h2` force a connection option."""
    p = defaults()
    p.update({k: v for k, v in user.items() if v is not None})
    if elec:
        p["elec_connection"] = elec
    if h2:
        p["h2_connection"] = h2
    d = dict(p)
    # use case
    if p["use_case"] == "Power-led":
        d["annual_h2_demand_kg"] = 0.0
        if not p.get("sell_surplus", False):
            d["h2_price_eur_kg"] = 0.0
        if p["h2_delivery"] == "profile":
            d["h2_delivery"] = "annual"
    elif p["use_case"] == "Hydrogen-led":
        d["annual_demand_mwh"] = 0.0
        if p["elec_revenue"] == "ppa" or not p.get("sell_surplus", False):
            d["elec_revenue"] = "none"
    # distances
    site = (p["site_lat"], p["site_lon"])
    d["straight_grid_km"] = haversine_km(*site, p["grid_lat"], p["grid_lon"])
    d["grid_distance_km"], d["grid_route_how"] = route_length(p, site, (p["grid_lat"], p["grid_lon"]),
                                                              p["link_distance_override_km"])
    d["h2_distance_km"], d["h2_route_how"] = route_length(p, site, (p["h2_lat"], p["h2_lon"]),
                                                          p["pipe_distance_override_km"])
    d["link_distance_km"] = d["grid_distance_km"]
    # configuration (v9 rule)
    floating = p["avg_water_depth_m"] > p["fixed_floating_depth_m"]
    if not floating:
        d.update(config="A_fixed", platform_float_factor=1.0, hvdc_float_premium=1.0, elec_export_allowed=True)
    elif not p["decentralized_h2"]:
        d.update(config="B_floating_centralized", platform_float_factor=p["platform_float_factor"],
                 hvdc_float_premium=p["hvdc_float_premium"], elec_export_allowed=True)
    else:
        d.update(config="C_floating_decentralized", platform_float_factor=1.0, hvdc_float_premium=1.0,
                 elec_export_allowed=False)
    d["floating"] = floating
    if floating:
        d["wind_capex_eur_mw"] = p["wind_capex_floating_eur_mw"]
        d["wind_fom"] = p["wind_fom_floating"]
    if not p["enable_cable"]:
        d["elec_export_allowed"] = False
    # conversion constants
    d["h2_kg_per_mwh"] = 1000.0 * p["electrolyzer_efficiency"] / p["lhv_h2_kwh_kg"]
    d["fc_mwh_per_kg"] = p["fc_efficiency_lhv"] * p["lhv_h2_kwh_kg"] / 1000.0
    k, n = float(p["comp_gamma"]), int(p["comp_stages"])
    ratio = (p["comp_p_out_bar"] / p["comp_p_in_bar"]) ** ((k - 1.0) / (n * k))
    w = (p["comp_z"] * 8.314 * p["comp_inlet_temp_k"] / (p["comp_isentropic_eff"] * 2.016e-3)
         * n * (k / (k - 1.0)) * (ratio - 1.0))
    d["comp_mwh_per_kg"] = max(w, 0.0) / 3.6e6 / 1000.0
    # export link: direct to shore or to a nearby hub; technology and voltage
    ec = p.get("elec_connection", "direct")
    ec = "direct" if ec == "choose" else ec
    d["elec_connection_used"] = ec
    ratings = {"66 kV AC": p["rating_66"], "132 kV AC": p["rating_132"], "220 kV AC": p["rating_220"],
               "275 kV AC": p["rating_275"], "320 kV DC": p["rating_320dc"], "525 kV DC": p["rating_525dc"]}
    if ec == "hub":
        km, how = route_length(p, site, (p["hub_lat"], p["hub_lon"]), p["link_distance_override_km"], sea=True)
        d["grid_distance_km"] = d["link_distance_km"] = km
        d["grid_route_how"] = how
        d["grid_injection_cap_mw"] = min(p["grid_injection_cap_mw"], p["hub_spare_mw"])
        kv = p["hub_voltage_kv"]
        volt = min(("66 kV AC", "132 kV AC", "220 kV AC", "275 kV AC"),
                   key=lambda v: abs(float(v.split()[0]) - kv))
        mode = "HVAC"
    else:
        volt = p.get("export_voltage", "auto")
        if volt == "auto":
            mode = "HVAC" if d["link_distance_km"] <= p["hvac_hvdc_threshold_km"] else "HVDC"
            volt = "220 kV AC" if mode == "HVAC" else "320 kV DC"
        else:
            mode = "HVDC" if volt.endswith("DC") else "HVAC"
    d["export_voltage_used"] = volt if ec != "hub" else f"{p['hub_voltage_kv']:.0f} kV AC"
    d["circuit_rating_mw"] = ratings[volt]
    L = d["link_distance_km"]
    if mode == "HVAC":
        d["link_mode"] = "HVAC"
        d["cable_capex_eur_mw"] = (p["hvac_var_eur_mw_km"]
                                   + p["hvac_fix_eur_km"] / max(d.get("grid_injection_cap_mw",
                                                                      p["grid_injection_cap_mw"]), 1.0)) * L
        d["cable_eff"] = 1.0 - p["hvac_loss_per_km"] * L
        d["cable_fom"] = p["cable_fom_hvac"]
        d["tso_fee"] = p["hub_access_fee_eur_mw_yr"] if ec == "hub" else p["tso_fee_eur_mw_yr"]
    else:
        d["link_mode"] = "HVDC"
        d["cable_capex_eur_mw"] = (p["hvdc_converter_pair_eur_mw"] * d["hvdc_float_premium"]
                                   + p["hvdc_cable_eur_mw_km"] * L)
        d["cable_eff"] = 1.0 - (p["hvdc_converter_loss"] + p["hvdc_cable_loss_per_km"] * L)
        d["cable_fom"] = p["cable_fom_hvdc"]
        d["tso_fee"] = p["tso_fee_hvdc_eur_mw_yr"]
    if not d["elec_export_allowed"]:
        d["cable_capex_eur_mw"], d["tso_fee"] = 0.0, 0.0
    # nested tables used by the model
    op = p["offshore_premium"]
    big_e, big_p, big_kg = p["batt_max_mwh"], p["batt_max_mw"], p["tank_max_kg"]
    d["batt"] = {
        "on": {"capex_e": p["batt_capex_e_eur_mwh"], "capex_p": p["batt_capex_p_eur_mw"], "life": p["batt_life"],
               "max_e": big_e if p["enable_batt_on"] else 0.0, "max_p": big_p if p["enable_batt_on"] else 0.0,
               "eta_ch": p["batt_eta"], "eta_dis": p["batt_eta"], "lam": 0.0, "fom": p["batt_fom"],
               "vom": p["batt_vom"]},
        "off": {"capex_e": p["batt_capex_e_eur_mwh"] * op, "capex_p": p["batt_capex_p_eur_mw"] * op,
                "life": p["batt_life"], "max_e": big_e if p["enable_batt_off"] else 0.0,
                "max_p": big_p if p["enable_batt_off"] else 0.0, "eta_ch": p["batt_eta"],
                "eta_dis": p["batt_eta"], "lam": 0.0, "fom": p["batt_fom"] + 0.005, "vom": p["batt_vom"]},
    }
    d["tank"] = {
        "on": {"capex_kg": p["tank_capex_eur_kg"], "life": p["tank_life"], "fom": p["tank_fom"], "lam": 0.0,
               "max_kg": big_kg if p["enable_tank_on"] else 0.0, "vom": p["tank_vom"]},
        "off": {"capex_kg": p["tank_capex_eur_kg"] * op, "life": p["tank_life"], "fom": p["tank_fom"] + 0.005,
                "lam": 0.0, "max_kg": big_kg if p["enable_tank_off"] else 0.0, "vom": p["tank_vom"]},
    }
    classes = {
        "new_small_12in": {"capex_per_km": p["pipe_small_capex_eur_km"], "cap_kgh": p["pipe_small_cap_kgh"]},
        "new_medium_36in": {"capex_per_km": p["pipe_medium_capex_eur_km"], "cap_kgh": p["pipe_medium_cap_kgh"]},
        "repurposed_36in": {"capex_per_km": p["pipe_repurposed_capex_eur_km"],
                            "cap_kgh": p["pipe_repurposed_cap_kgh"], "repurposed": True},
    }
    d["pipe_classes"] = classes
    d["pipe_allowed"] = [] if not p["enable_pipe"] else [
        kk for kk, c in classes.items() if not c.get("repurposed") or p["existing_pipeline_available"]]
    hc = p.get("h2_connection", "direct")
    hc = "direct" if hc == "choose" else hc
    d["h2_connection_used"] = hc
    if hc == "tiein":
        d["pipe_distance_km"], d["pipe_route_how"] = route_length(
            p, site, (p["tiein_lat"], p["tiein_lon"]), p["pipe_distance_override_km"], sea=True)
        d["pipe_spare_kgh"] = p["tiein_spare_kgh"]
        d["pipe_fixed_eur"] = p["tiein_fee_eur"]
        ratio_t = (p["tiein_pressure_bar"] / p["comp_p_in_bar"]) ** ((k - 1.0) / (n * k))
        w_t = (p["comp_z"] * 8.314 * p["comp_inlet_temp_k"] / (p["comp_isentropic_eff"] * 2.016e-3)
               * n * (k / (k - 1.0)) * (ratio_t - 1.0))
        d["comp_mwh_per_kg"] = max(w_t, 0.0) / 3.6e6 / 1000.0
    else:
        d["pipe_distance_km"] = d["h2_distance_km"]
        d["pipe_route_how"] = d["h2_route_how"]
        d["pipe_spare_kgh"] = 0.0
        d["pipe_fixed_eur"] = 0.0
    return d


def connection_variants(user: dict) -> list[tuple[str, str]]:
    """The (electricity, hydrogen) connection options the model should compare."""
    p = defaults()
    p.update({k: v for k, v in user.items() if v is not None})
    ev = ["direct", "hub"] if (p.get("elec_connection") == "choose" and p["enable_cable"]) else [
        "direct" if p.get("elec_connection") == "choose" else p.get("elec_connection", "direct")]
    hv = ["direct", "tiein"] if (p.get("h2_connection") == "choose" and p["enable_pipe"]) else [
        "direct" if p.get("h2_connection") == "choose" else p.get("h2_connection", "direct")]
    return [(e, h) for e in ev for h in hv]
