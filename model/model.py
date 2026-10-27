"""Environmental model for 'The Environmental Cost of Growth'.

Every number reported in the projection model of the paper is produced here.
Run `python model.py` to print them, or import and call results() for a dict.

Chain (Section 3.2; equation numbers as in the compiled paper):
  1. utilisation u -> electrical load factor L = p_idle + (1 - p_idle) * u
     (LBNL 2024, pp. 18-19: average power is a linear interpolation between
     idle and maximum power; p_idle from p. 27)
  2. IT energy       = rho * capacity (GW) * L * 8,760 h
     rho is a base-year calibration factor: the ratio of the IEA's estimate of
     2025 data centre electricity use to what the uncalibrated model gives for
     2025 (Eq. 7). It absorbs the share of installed capacity that is not
     drawing power (unleased or newly commissioned space, provisioning above
     servers' actual peak draw) and any difference in how capacity is counted.
  3. facility energy = IT energy * PUE
  4. emissions       = facility energy * grid intensity
  5. direct water    = IT energy * WUE
"""

HOURS = 8760

# --- LBNL 2024 facility-type utilisation, extrapolated linearly to 2031 (p. 28)
def extrap(v2014, v2027, year=2031):
    return v2027 + (v2027 - v2014) / 13 * (year - 2027)

U_HYPER = extrap(45, 50)   # 51.54
U_COLO = extrap(21, 35)    # 39.31
U_SMALL = extrap(11, 20)   # 22.77

def weighted(h, c, s):
    # shares and rates are both in percent, so divide by 100 * 100
    return (h * U_HYPER + c * U_COLO + s * U_SMALL) / 10000

# Capacity shares, 2031 (hyperscale, colocation, on-premises/internal), from
# Synergy Research Group (April 2026): hyperscale 67%, on-premises 19%, so
# colocation 14%. Low: slower consolidation, hyperscale 60% with the rest split
# in the same 14:19 ratio. High: an all-hyperscale fleet.
SH_LOW = (60, 40 * 14 / 33, 40 * 19 / 33)
SH_CENTRAL = (67, 14, 19)
U = {"low": weighted(*SH_LOW), "central": weighted(*SH_CENTRAL),
     "high": weighted(100, 0, 0)}

# --- Idle power as a fraction of maximum (LBNL 2024, p. 27)
# central: 27%, LBNL's 2028 value for conventional servers, held flat to 2031
# low: 20%, LBNL's AI-server value and roughly where the conventional-server
#      trend (51% 2014 -> 36% 2023 -> 27% 2028) reaches by 2031
# high: 36%, LBNL's 2023 value (no further improvement)
IDLE = {"low": 0.20, "central": 0.27, "high": 0.36}

CAP = {"low": 180, "central": 200, "high": 220}
PUE = {"low": 1.04, "central": 1.30, "high": 1.57}
GRID = {"low": 345, "central": 395, "high": 445}       # g CO2 / kWh
# Direct (site) water per kWh of IT energy (WUE).
# central: 0.48, upper end of LBNL 2024's projected US average after 2023
#          (0.45-0.48; p. 49), held flat to 2031. LBNL 2024 puts the 2023
#          average just over 0.36 (p. 49).
# low:     0.32, LBNL 2024's median for hyperscale facilities (p. 48)
# high:    1.8, the average reported in LBNL's 2016 report, representing a
#          fleet still dominated by evaporative cooling
WUE = {"low": 0.32, "central": 0.48, "high": 1.8}       # L / kWh (IT energy)

UNU_WATER_TN = 9.3     # trillion litres, 2030
UNU_ENERGY_TWH = 945   # IEA 2030 base case underlying the UNU figure
COMBINED_INTENSITY = UNU_WATER_TN * 1e12 / (UNU_ENERGY_TWH * 1e9)  # L/kWh


def load_factor(u, idle):
    return idle + (1 - idle) * u


# --- Base-year check and calibration (Eq. 7)
# Calibrated against 2025, the latest year with published estimates of actual
# use, rather than an interpolated 2026 value.
# Capacity: JLL (2026) reports 103 GW at the start of 2026; JLL (2025) expected
#   about 7 GW of completions during 2025, so average 2025 capacity is taken
#   as 103 - 7/2 = 99.5 GW.
# Utilisation: LBNL facility-type trends evaluated at 2025, weighted by 2025
#   capacity shares (Synergy: hyperscale 48%, colocation 20%, on-premises 32%).
# Idle share: LBNL conventional-server values, 36% (2023) to 27% (2028),
#   interpolated to 2025.
# PUE: 1.56, the 2024 fleet average (Uptime Institute), flat through the 2020s.
# Published estimates of 2025 use:
#   IEA: 415 TWh in 2024 and growth of 17% in 2025 -> 485.6 TWh
#   451 Research: 860 TWh (includes cryptocurrency mining)
def base_year(year, cap, shares, idle, pue=1.56):
    u = (shares[0] * extrap(45, 50, year) + shares[1] * extrap(21, 35, year)
         + shares[2] * extrap(11, 20, year)) / 10000
    lf = load_factor(u, idle)
    it = cap * lf * HOURS / 1000
    return dict(year=year, cap=cap, shares=shares, u=u, idle=idle, lf=lf, pue=pue,
                model_it=it, model_fac=it * pue)


IEA_2025 = 415 * 1.17
S451_2025 = 860
# 2025 shares: hyperscale 48%, colocation about 20%, on-premises about 32%
# (Synergy Research Group, end of 2025).
BY2025 = base_year(2025, 103 - 7 / 2, (48, 20, 32), 0.36 - (0.36 - 0.27) * 2 / 5)
RHO_IEA = IEA_2025 / BY2025["model_fac"]
# Cross-check: the same procedure for 2026 against the IEA path interpolated
# to its 2030 projection (945 TWh) and against 451 Research's path to 1,587.
IEA_2026 = IEA_2025 * (945 / IEA_2025) ** (1 / 5)
S451_2026 = 860 * (1587 / 860) ** (1 / 5)
_h26 = 48 + (67 - 48) / 6
BY2026 = base_year(2026, 103, (_h26, 20 + (14 - 20) / 6, 32 + (19 - 32) / 6), 0.36 - (0.36 - 0.27) * 3 / 5)
RHO_IEA_2026 = IEA_2026 / BY2026["model_fac"]
RHO = {"low": RHO_IEA, "central": RHO_IEA, "high": 1.0}

# --- Grid intensity where capacity sits (siting/siting_grid.py), as a ratio
# to the world average on the same (Ember lifecycle) basis, so it can be
# applied to the IEA-basis grid values. Existing fleet: PeeringDB sites,
# unweighted (0.699). New capacity: Epoch AI campuses by planned capacity
# (0.945). 2031 mix: 103/200 existing, 97/200 new.
GRID_RATIO_FLEET = 0.6994
GRID_RATIO_NEW = 0.9452
GRID_SITED_FACTOR = (103 * GRID_RATIO_FLEET + 97 * GRID_RATIO_NEW) / 200


def run(cap, u, idle, pue, grid, wue, rho=None):
    rho = RHO["central"] if rho is None else rho
    lf = load_factor(u, idle)
    it = rho * cap * lf * HOURS / 1000      # TWh  (GW * h = GWh; /1000 -> TWh)
    fac = it * pue                          # TWh
    co2 = fac * grid / 1000                 # Mt   (TWh * g/kWh = kt... see below)
    water = it * wue / 1000                 # trillion litres (TWh*L/kWh = bn L)
    combined = fac * COMBINED_INTENSITY / 1000
    return dict(lf=lf, it=it, fac=fac, co2=co2, water=water, combined=combined)

# Unit check: 1 TWh = 1e9 kWh; * g/kWh = 1e9 g per (g/kWh) = 1e3 t = 1e-3 Mt.
# So Mt = TWh * (g/kWh) / 1000. Water: TWh * L/kWh = 1e9 L = 1e-3 trillion L.


def scenario(name):
    return run(CAP[name], U[name], IDLE[name], PUE[name], GRID[name], WUE[name], RHO[name])


C = {k: v["central"] for k, v in
     dict(cap=CAP, u=U, idle=IDLE, pue=PUE, grid=GRID, wue=WUE, rho=RHO).items()}


def central(**over):
    p = dict(C)
    p.update(over)
    return run(p["cap"], p["u"], p["idle"], p["pue"], p["grid"], p["wue"], p["rho"])


def monte_carlo(n=100_000, seed=20261024):
    """Independent triangular distributions over each parameter's low, central
    and high values (rho: mode at the calibrated value, upper limit 1).
    Returns percentiles and each parameter's share of output variance, from
    squared rank correlations normalised to sum to one."""
    import numpy as np
    rng = np.random.default_rng(seed)
    draws = {}
    for k, d in dict(cap=CAP, u=U, idle=IDLE, pue=PUE, grid=GRID, wue=WUE, rho=RHO).items():
        lo, mo, hi = d["low"], d["central"], d["high"]
        lo, hi = min(lo, hi), max(lo, hi)
        draws[k] = rng.triangular(lo, mo, hi, n) if hi > lo else np.full(n, mo)
    lf = draws["idle"] + (1 - draws["idle"]) * draws["u"]
    it = draws["rho"] * draws["cap"] * lf * HOURS / 1000
    fac = it * draws["pue"]
    co2 = fac * draws["grid"] / 1000
    water = it * draws["wue"] / 1000

    def rank(x):
        return np.argsort(np.argsort(x))

    def contrib(y, keys):
        ry = rank(y)
        r2 = {k: float(np.corrcoef(rank(draws[k]), ry)[0, 1] ** 2) for k in keys}
        tot = sum(r2.values())
        return {k: v / tot for k, v in r2.items()}

    def first_order(y, keys, bins=100):
        """First-order (Sobol) variance shares, Var(E[Y|X_k]) / Var(Y),
        estimated by averaging Y within quantile bins of X_k."""
        vy = y.var()
        out = {}
        for k in keys:
            x = draws[k]
            if np.ptp(x) == 0:
                out[k] = 0.0
                continue
            edges = np.quantile(x, np.linspace(0, 1, bins + 1))
            idx = np.clip(np.searchsorted(edges, x, side="right") - 1, 0, bins - 1)
            cnt = np.bincount(idx, minlength=bins)
            means = np.bincount(idx, weights=y, minlength=bins) / np.maximum(cnt, 1)
            out[k] = float((cnt * (means - y.mean()) ** 2).sum() / len(y) / vy)
        out["interactions"] = float(max(0.0, 1 - sum(out.values())))
        return out

    pct = lambda y: {p: float(np.percentile(y, p)) for p in (5, 50, 95)}
    return dict(n=n, co2=pct(co2), water=pct(water), fac=pct(fac),
                co2_share_below_2024=float((co2 < 415 * 445 / 1000).mean()),
                co2_contrib=contrib(co2, ["rho", "pue", "grid", "cap", "idle", "u"]),
                co2_sobol=first_order(co2, ["rho", "pue", "grid", "cap", "idle", "u"]),
                water_sobol=first_order(water, ["wue", "rho", "cap", "idle", "u"]),
                water_contrib=contrib(water, ["wue", "rho", "cap", "idle", "u"]))


def results():
    """Every model number the article quotes, in one dict."""
    c = central()
    out = dict(utilisation={k: U[k] for k in U}, load_factor={k: load_factor(U[k], IDLE["central"]) for k in U},
               central=c, combined_intensity=COMBINED_INTENSITY)
    out["base_year"] = dict(by2025=BY2025, by2026=BY2026, iea_2025=IEA_2025, s451_2025=S451_2025,
                            iea_2026=IEA_2026, s451_2026=S451_2026, rho_iea=RHO_IEA,
                            rho_iea_2026=RHO_IEA_2026,
                            model_over_iea=BY2025["model_fac"] / IEA_2025,
                            model_over_451=BY2025["model_fac"] / S451_2025,
                            twh_per_gw_iea_2025=IEA_2025 / BY2025["cap"], twh_per_gw_iea_2030=945 / 200)
    out["grid_sited"] = dict(factor=GRID_SITED_FACTOR, central_g=GRID["central"] * GRID_SITED_FACTOR,
                             result=central(grid=GRID["central"] * GRID_SITED_FACTOR))
    out["monte_carlo"] = monte_carlo()
    out["calibration_alternatives"] = calibration_alternatives()
    out["assumption_alternatives"] = assumption_alternatives()
    out["criterion1_margins"] = criterion1_margins()
    out["hot_climate_water"] = hot_climate_water()
    out["uncalibrated_central"] = central(rho=1.0)
    out["pue_table"] = {str(PUE[k]): dict(static=central(pue=PUE[k], grid=445),
                                          decarb=central(pue=PUE[k], grid=345)) for k in PUE}
    out["bundled"] = {k: scenario(k) for k in ("low", "central", "high")}
    sens = {}
    for par, rng in (("rho", RHO), ("pue", PUE), ("grid", GRID), ("cap", CAP), ("idle", IDLE), ("u", U)):
        lo, hi = central(**{par: rng["low"]})["co2"], central(**{par: rng["high"]})["co2"]
        sens[par] = dict(lo=lo, hi=hi, swing_pct=(hi - lo) / c["co2"] * 100)
    out["sens_co2"] = sens
    wsens = {}
    for par, rng in (("wue", WUE), ("rho", RHO), ("cap", CAP), ("idle", IDLE), ("u", U)):
        lo, hi = central(**{par: rng["low"]})["water"], central(**{par: rng["high"]})["water"]
        wsens[par] = dict(lo=lo, hi=hi, swing=hi - lo)
    out["sens_water"] = wsens
    nuc = 9.8 * 0.9 * HOURS / 1000
    out["nuclear_twh"] = nuc
    out["nuclear_share"] = nuc / c["fac"]
    out["combined_over_direct"] = c["combined"] / c["water"]
    out["combined_vs_unu"] = c["combined"] / UNU_WATER_TN
    # Path comparison with the IEA: energy per GW of capacity, 2025 vs 2031
    lf25 = load_factor(BY2025["u"], BY2025["idle"])
    out["iea_reconciliation"] = dict(
        twh_per_gw_2025=IEA_2025 / BY2025["cap"], twh_per_gw_2031=c["fac"] / CAP["central"],
        twh_per_gw_iea_2030=945 / 200, change_pct=(c["fac"] / CAP["central"]) / (IEA_2025 / BY2025["cap"]) - 1,
        lf_2025=lf25, lf_2031=c["lf"], lf_change_pct=c["lf"] / lf25 - 1, pue_change_pct=PUE["central"] / 1.56 - 1,
        central_vs_iea_2030=c["fac"] / 945 - 1,
        fac_at_pue_156=central(pue=1.56)["fac"], fac_at_pue_157=central(pue=1.57)["fac"],
        pue157_vs_iea_2030=central(pue=1.57)["fac"] / 945 - 1)
    return out


if __name__ == "__main__":
    print(f"Extrapolated 2031 utilisation: hyperscale {U_HYPER:.2f}%, "
          f"colocation {U_COLO:.2f}%, internal/small {U_SMALL:.2f}%")
    for k in ("low", "central", "high"):
        print(f"  weighted {k}: {U[k]*100:.2f}%  -> load factor at central idle "
              f"{load_factor(U[k], IDLE['central'])*100:.2f}%")
    print(f"Combined UNU intensity: {COMBINED_INTENSITY:.2f} L/kWh")

    R = results(); by = R["base_year"]
    for y in ("by2025", "by2026"):
        b = by[y]
        print(f"\nBase year {b['year']}: cap {b['cap']} GW, shares {[round(x,1) for x in b['shares']]}, "
              f"u {b['u']*100:.2f}%, idle {b['idle']*100:.1f}%, LF {b['lf']*100:.2f}%, "
              f"model facility {b['model_fac']:.0f} TWh")
    print(f"  IEA 2025 {by['iea_2025']:.0f}, 451 2025 {by['s451_2025']}; model/IEA {by['model_over_iea']:.3f}, "
          f"model/451 {by['model_over_451']:.3f}; rho {by['rho_iea']:.3f} (2026 check {by['rho_iea_2026']:.3f})")
    print(f"  TWh per GW: 2025 {by['twh_per_gw_iea_2025']:.2f}, 2030 {by['twh_per_gw_iea_2030']:.2f}")
    g = R["grid_sited"]; print(f"Sited grid factor {g['factor']:.3f} -> central {g['central_g']:.0f} g, CO2 {g['result']['co2']:.1f}")
    mcr = R["monte_carlo"]; print("Monte Carlo CO2", {k: round(v) for k, v in mcr["co2"].items()},
                                 "water", {k: round(v, 2) for k, v in mcr["water"].items()})
    print("  CO2 variance shares", {k: round(v, 3) for k, v in mcr["co2_contrib"].items()})
    print("  water variance shares", {k: round(v, 3) for k, v in mcr["water_contrib"].items()})
    print("  uncalibrated central:", {k: round(v, 3) for k, v in central(rho=1.0).items()})
    c = central()
    print("\nCENTRAL:", {k: round(v, 4) for k, v in c.items()})

    print("\n8.1 table (central u, central idle, cap 200):")
    for pk in ("low", "central", "high"):
        r445 = central(pue=PUE[pk], grid=445)
        r345 = central(pue=PUE[pk], grid=345)
        print(f"  PUE {PUE[pk]}: IT {r445['it']:.1f} fac {r445['fac']:.1f} "
              f"CO2@445 {r445['co2']:.1f} CO2@345 {r345['co2']:.1f} "
              f"water {r445['water']:.3f}")

    print("\nBundled scenarios:")
    for k in ("low", "central", "high"):
        s = scenario(k)
        print(f"  {k}: LF {s['lf']*100:.1f}% IT {s['it']:.1f} fac {s['fac']:.1f} "
              f"CO2 {s['co2']:.1f} water {s['water']:.3f} combined {s['combined']:.2f}")

    print("\nOne-at-a-time sensitivity (emissions):")
    base = c["co2"]
    rows = []
    for par, rng in (("rho", RHO), ("pue", PUE), ("grid", GRID), ("cap", CAP),
                     ("idle", IDLE), ("u", U)):
        lo = central(**{par: rng["low"]})["co2"]
        hi = central(**{par: rng["high"]})["co2"]
        rows.append((par, lo, hi, (hi - lo) / base * 100))
    for par, lo, hi, sw in sorted(rows, key=lambda r: -r[3]):
        print(f"  {par:5s} {lo:6.1f} - {hi:6.1f} Mt  swing {sw:.1f}%")

    print("\nWater one-at-a-time:")
    for par, rng in (("wue", WUE), ("rho", RHO), ("cap", CAP), ("idle", IDLE), ("u", U)):
        lo = central(**{par: rng["low"]})["water"]
        hi = central(**{par: rng["high"]})["water"]
        print(f"  {par}: {lo:.3f} - {hi:.3f} tn L  swing {hi-lo:.3f}")

    nuc = 9.8 * 0.9 * HOURS / 1000
    print(f"\nNuclear 9.8 GW @90%: {nuc:.1f} TWh = {nuc/c['fac']*100:.1f}% of central facility")
    print(f"Combined central vs UNU: {c['combined']:.2f} vs 9.3 -> ratio {c['combined']/9.3:.3f}; "
          f"energy ratio {c['fac']/945:.3f}")
    print(f"Combined/direct ratio central: {c['combined']/c['water']:.2f}")
    print(f"Elasticity of LF wrt u: {(1-C['idle'])*C['u']/c['lf']:.3f}; wrt idle: "
          f"{C['idle']*(1-C['u'])/c['lf']:.3f}")


# ---------------------------------------------------------------- robustness
def mc_with_rho(rho_sampler, n=100_000, seed=20261024):
    """Monte Carlo as in monte_carlo(), but with a supplied sampler for rho."""
    import numpy as np
    rng = np.random.default_rng(seed)
    d = {}
    for k, r in dict(cap=CAP, u=U, idle=IDLE, pue=PUE, grid=GRID).items():
        lo, mo, hi = min(r["low"], r["high"]), r["central"], max(r["low"], r["high"])
        d[k] = rng.triangular(lo, mo, hi, n)
    d["rho"] = rho_sampler(rng, n)
    lf = d["idle"] + (1 - d["idle"]) * d["u"]
    co2 = d["rho"] * d["cap"] * lf * HOURS / 1000 * d["pue"] * d["grid"] / 1000

    def first_order(x, y, bins=100):
        """First-order Sobol share Var(E[Y|X])/Var(Y), binned estimator as in monte_carlo()."""
        if np.ptp(x) == 0:
            return 0.0
        edges = np.quantile(x, np.linspace(0, 1, bins + 1))
        idx = np.clip(np.searchsorted(edges, x, side="right") - 1, 0, bins - 1)
        cnt = np.bincount(idx, minlength=bins)
        means = np.bincount(idx, weights=y, minlength=bins) / np.maximum(cnt, 1)
        return float((cnt * (means - y.mean()) ** 2).sum() / len(y) / y.var())
    s1 = {k: first_order(d[k], co2) for k in d}
    base24 = 415 * 445 / 1000
    return dict(p5=float(np.percentile(co2, 5)), p50=float(np.percentile(co2, 50)),
                p95=float(np.percentile(co2, 95)), rho_share=s1["rho"],
                top_forward=max((k for k in s1 if k != "rho"), key=lambda k: s1[k]),
                share_below_2024=float((co2 < base24).mean()))


def calibration_alternatives():
    """How the Monte Carlo result changes under other calibration assumptions."""
    lo = RHO_IEA
    r451 = S451_2025 / BY2025["model_fac"]
    alts = {
        "fixed at IEA fit": lambda g, n: __import__("numpy").full(n, lo),
        "triangular, mode at IEA fit, max 1 (main)": lambda g, n: g.triangular(lo, lo, 1.0, n),
        "uniform, IEA fit to 1": lambda g, n: g.uniform(lo, 1.0, n),
        "IEA 2025 estimate +/-10%, uniform": lambda g, n: g.uniform(lo * 0.9, lo * 1.1, n),
        "fitted to 451 Research (incl. crypto)": lambda g, n: __import__("numpy").full(n, r451),
    }
    return {k: dict(mc_with_rho(f), central=central(rho=float(f(__import__("numpy").random.default_rng(0), 1)[0]))["co2"]
                    if k.startswith(("fixed", "fitted")) else None)
            for k, f in alts.items()} | {"rho_451": r451}


def assumption_alternatives():
    """Central 2031 emissions under alternative inputs, re-fitting the
    calibration where the input also enters the 2025 base year."""
    out = {}
    base = central()["co2"]

    def refit(u2025, u2031, idle2025=BY2025["idle"], idle2031=IDLE["central"], scale2031=1.0):
        fac25 = BY2025["cap"] * load_factor(u2025, idle2025) * HOURS / 1000 * BY2025["pue"]
        rho = IEA_2025 / fac25
        lf31 = load_factor(u2031, idle2031) * scale2031
        co2 = rho * CAP["central"] * lf31 * HOURS / 1000 * PUE["central"] * GRID["central"] / 1000
        return co2

    u25 = BY2025["u"]
    # 1. utilisation trends stop at LBNL's 2027 values instead of extrapolating
    u31_2027 = (67 * 50 + 14 * 35 + 19 * 20) / 10000
    out["utilisation held at LBNL 2027 values"] = refit(u25, u31_2027)
    # 2. no consolidation: 2031 shares equal to 2025 shares
    out["no consolidation (2025 shares in 2031)"] = refit(u25, weighted(48, 20, 32))
    # 3. faster consolidation: 80% hyperscale
    out["faster consolidation (80% hyperscale)"] = refit(u25, weighted(80, 20 * 14 / 33, 20 * 19 / 33))
    # 4. utilisation not counted at all as load (old reading), refitted
    out["utilisation read directly as load factor"] = refit(u25, U["central"], idle2025=0.0, idle2031=0.0)
    # 5. LBNL 2025 update direction: higher AI-server idle power and
    #    utilisation raise US 2030 use by about a fifth (782 vs 649 TWh),
    #    applied to 2031 but not to the 2025 calibration
    out["LBNL 2025 high AI-server scenario (+20% load in 2031)"] = refit(u25, U["central"], scale2031=782 / 649)
    # 6. grid weighted by where capacity sits
    out["grid weighted by where capacity sits"] = central(grid=GRID["central"] * GRID_SITED_FACTOR)["co2"]
    return {k: dict(co2=v, change=v / base - 1) for k, v in out.items()}


def criterion1_margins():
    """How far the low case and the central case sit above the 2024 baseline,
    and how the baseline moves with its inputs."""
    low = scenario("low")["co2"]
    c = central()["co2"]
    out = {}
    for lab, twh, g in (("IEA 415 TWh at 445 g", 415, 445), ("+10% use", 456.5, 445),
                        ("+10% grid intensity", 415, 489.5), ("US-style +48% grid gap", 415, 445 * 1.48)):
        b = twh * g / 1000
        out[lab] = dict(baseline=b, low_over=low / b - 1, central_over=c / b - 1)
    return out


def hot_climate_water(shares=(0.25, 0.40, 0.60), wue_hot=1.8):
    """Direct water if a share f of 2031 IT energy runs at an evaporative-
    cooling WUE typical of hot, dry sites (LBNL 2016 average, 1.8 L/kWh) and
    the rest at the central 0.48. 0.40 is the share of planned AI capacity in
    high or extremely high water stress (siting analysis)."""
    it = central()["it"]
    return {str(f): dict(wue=f * wue_hot + (1 - f) * WUE["central"],
                         water=it * (f * wue_hot + (1 - f) * WUE["central"]) / 1000) for f in shares}
