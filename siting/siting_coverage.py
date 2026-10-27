"""Coverage and weighting robustness for the siting results (Section 4.4-4.5).

1. Capacity uncertainty: each Epoch campus's planned capacity is multiplied by
   independent log-normal noise (sigma = 0.5, so a typical site is off by a
   factor of about 1.65), 5,000 draws.
2. Leave-one-out: drop one US state (carbon) or one country (water) at a time.
3. Missing sites: how much extra capacity, at sites the sample does not
   contain, would be needed to change each conclusion.
Run after siting_results.py.
"""
import json
import numpy as np
import pandas as pd

RNG = np.random.default_rng(20261025)
e = pd.read_csv("results/results_epoch_sites.csv")
e = e[e.planned_it_mw > 0].reset_index(drop=True)
r = json.load(open("results/results_final.json"))
REF_WATER = r["water"]["cities_pop"]["value"]
st = pd.read_csv("data/ember_us_states_2024.psv", sep="|")
US_AVG = float(st[st.state_code == "US"].intensity_g_per_kwh.iloc[0])

w = e.planned_it_mw.to_numpy(); hw = (e.bws_cat >= 3).to_numpy()
us = (e.name_0 == "United States").to_numpy(); ci = e.grid_ci.to_numpy()


def water_share(wt):
    return (wt * hw).sum() / wt.sum()


def us_mean(wt):
    return (wt[us] * ci[us]).sum() / wt[us].sum()


def us_above(wt):
    return (wt[us] * (ci[us] > US_AVG)).sum() / wt[us].sum()


base = dict(water=water_share(w), us_mean=us_mean(w), us_above=us_above(w))
noise = [w * RNG.lognormal(0, 0.5, len(w)) for _ in range(5000)]
cap_unc = {k: [float(np.percentile([f(x) for x in noise], p)) for p in (5, 95)]
           for k, f in dict(water=water_share, us_mean=us_mean, us_above=us_above).items()}

loo_state = {}
for s_ in sorted(e[us].name_1.unique()):
    keep = ~(us & (e.name_1 == s_).to_numpy())
    wk = np.where(keep, w, 0)
    loo_state[s_] = float(us_mean(wk))
loo_country = {}
for c_ in sorted(e.name_0.unique()):
    wk = np.where((e.name_0 != c_).to_numpy(), w, 0)
    loo_country[c_] = float(water_share(wk))

# Missing capacity needed to change conclusions.
W_ALL, W_US = w.sum() / 1000, w[us].sum() / 1000
DIFF = json.load(open("results/results_difference.json"))["ai_capacity_minus_pop"]
EDGE = -DIFF["ci"][0]                    # lower edge of the 95% interval of the capacity-weighted gap
target_water = REF_WATER - EDGE
miss_water_gw = W_ALL * (base["water"] / target_water - 1)
CLEAN = 300.0                            # grams; a clean state grid, e.g. the passing sites' average
miss_carbon_gw = W_US * (base["us_mean"] - US_AVG) / (US_AVG - CLEAN)

# Sensitivity of the missing-capacity thresholds to their two assumptions:
# how far below the reference counts as "avoidance", and how clean the
# missing capacity's grid is assumed to be.
miss_water_variants = {f"ref_minus_{round(d*100)}pp": W_ALL * (base["water"] / (REF_WATER - d) - 1)
                       for d in (0.10, EDGE, 0.20)}
miss_carbon_variants = {f"clean_{int(g)}g": W_US * (base["us_mean"] - US_AVG) / (US_AVG - g)
                        for g in (250.0, 300.0, 350.0)}
out = dict(base=base, capacity_uncertainty_90=cap_unc,
           loo_state_us_mean=[min(loo_state.values()), max(loo_state.values())],
           loo_state_extremes={k: v for k, v in loo_state.items()
                               if v in (min(loo_state.values()), max(loo_state.values()))},
           loo_country_water=[min(loo_country.values()), max(loo_country.values())],
           sample_gw=W_ALL, sample_us_gw=W_US,
           missing_lowstress_gw_to_reach_ci_edge=miss_water_gw, ci_edge_pp=EDGE*100,
           missing_lowstress_share_of_sample=miss_water_gw / W_ALL,
           missing_clean_gw_to_reach_us_avg=miss_carbon_gw,
           missing_clean_share_of_us_sample=miss_carbon_gw / W_US,
           missing_water_variants_gw=miss_water_variants, missing_carbon_variants_gw=miss_carbon_variants,
           ref_water=REF_WATER, us_avg=US_AVG,
           assumptions=dict(capacity_noise="independent log-normal multiplier per campus, mean of log 0, sd 0.5, 5,000 draws, seed 20261025",
                            missing_water="extra capacity X (GW) with zero high-stress share: share' = share*W/(W+X); solve share' = ref - d",
                            missing_carbon="extra US capacity X (GW) at grid g: mean' = (mean*W + g*X)/(W+X); solve mean' = US average"))
json.dump(out, open("results/results_coverage.json", "w"), indent=1)
print(json.dumps(out, indent=1))
