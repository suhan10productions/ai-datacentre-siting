"""Average versus marginal grid intensity for the US AI campuses (Section 4.5, 5.3).

Marginal proxy: eGRID2023 non-baseload CO2 output emission rates by subregion
(EPA, eGRID2023 summary tables, rev. 1, January 2025), in lb/MWh. Each state is
assigned the eGRID subregion that covers most of it; this is an approximation
for states split between subregions (noted below). Compares the capacity-
weighted non-baseload rate of the campuses with the US non-baseload rate, and
recomputes the illustrative screen's conditional emissions change on this basis.
"""
import json
import numpy as np
import pandas as pd

NB = {"AZNM": 1260.4, "ERCT": 1264.9, "MROE": 1713.8, "MROW": 1776.6, "NWPP": 1613.4, "NYUP": 909.1,
      "RFCE": 1175.5, "RFCM": 1508.1, "RFCW": 1757.3, "RMPA": 1620.6, "SPSO": 1508.4, "SRMV": 1145.5,
      "SRMW": 1818.6, "SRSO": 1386.0, "SRTV": 1665.8, "SRVC": 1286.8}
US_NB = 1393.7
STATE = {"Alabama": "SRSO", "Arizona": "AZNM", "Georgia": "SRSO", "Idaho": "NWPP", "Indiana": "RFCW",
         "Iowa": "MROW", "Louisiana": "SRMV", "Michigan": "RFCM", "Minnesota": "MROW", "Mississippi": "SRMV",
         "Missouri": "SRMW", "Nebraska": "MROW", "Nevada": "NWPP", "New Jersey": "RFCE", "New Mexico": "AZNM",
         "New York": "NYUP", "North Carolina": "SRVC", "North Dakota": "MROW", "Ohio": "RFCW", "Oklahoma": "SPSO",
         "Oregon": "NWPP", "Pennsylvania": "RFCE", "South Carolina": "SRVC", "Tennessee": "SRTV", "Texas": "ERCT",
         "Utah": "NWPP", "Virginia": "SRVC", "Wisconsin": "MROE", "Wyoming": "RMPA"}
SPLIT = ["Mississippi", "Nevada", "Pennsylvania", "Wisconsin", "Missouri", "Michigan", "Indiana"]
LB_TO_G = 453.592 / 1000  # lb/MWh -> g/kWh

e = pd.read_csv("results/results_epoch_sites.csv")
us = e[(e.name_0 == "United States") & (e.planned_it_mw > 0)].copy()
us["nb"] = us.name_1.map(STATE).map(NB)
w = us.planned_it_mw.to_numpy(float); m = us.nb.to_numpy(float); c = us.grid_ci.to_numpy(float)
camp_nb = (m * w).sum() / w.sum()
st = pd.read_csv("data/ember_us_states_2024.psv", sep="|")
US_AVG = float(st[st.state_code == "US"].intensity_g_per_kwh.iloc[0])
ok = ~((us.bws_cat >= 3).to_numpy() | (c > US_AVG))
import sys
sys.path.insert(0, "../model")
sys.path.insert(0, "../work")
import model as mdl  # central energy per GW, as in siting_screen.py
E = mdl.RHO["central"] * mdl.load_factor(mdl.U["central"], mdl.IDLE["central"]) * mdl.HOURS / 1000 * mdl.PUE["central"]
pass_nb = (m[ok] * w[ok]).sum() / w[ok].sum()
fail = ~ok
saving_marginal = (w[fail] * (m[fail] - pass_nb)).sum() / 1000 * E * LB_TO_G / 1000
hw = (us.bws_cat >= 3).to_numpy()
ok_m = ~(hw | (m > US_NB))   # carbon test specified on the marginal proxy instead
RNG = np.random.default_rng(20261024)
def stat(idx):
    ww, mm, oo, om = w[idx], m[idx], ok[idx], ok_m[idx]
    a = (mm * ww).sum() / ww.sum()
    p = (mm[oo] * ww[oo]).sum() / ww[oo].sum() if ww[oo].sum() > 0 else np.nan
    pm = (mm[om] * ww[om]).sum() / ww[om].sum() if ww[om].sum() > 0 else np.nan
    f = ww.sum() / 1000 * E * LB_TO_G / 1000
    return dict(campus_over_us=a / US_NB - 1, saving_avgscreen=f * (a - p),
                pass_share_mscreen=ww[om].sum() / ww.sum(), saving_mscreen=f * (a - pm))
pt = stat(np.arange(len(w)))
bt = [stat(RNG.integers(0, len(w), len(w))) for _ in range(5000)]
ci95 = {k: [float(np.nanpercentile([b[k] for b in bt], 2.5)), float(np.nanpercentile([b[k] for b in bt], 97.5))] for k in pt}
out = dict(point=pt, ci95=ci95, us_nonbaseload_lb=US_NB, campus_nonbaseload_lb=camp_nb, campus_over_us=camp_nb / US_NB - 1,
           us_total_lb=771.5, nonbaseload_over_total_us=US_NB / 771.5,
           pass_nonbaseload_lb=pass_nb, fail_nonbaseload_lb=(m[fail] * w[fail]).sum() / w[fail].sum(),
           screen_saving_marginal_mt=saving_marginal, split_states=SPLIT,
           corr_average_vs_marginal=float(np.corrcoef(c, m)[0, 1]))

# Leave-one-state-out for the sign of the average-screen result on the marginal basis
states = us.name_1.to_numpy()
def avg_screen_change(mask):
    ww, mm, oo = w[mask], m[mask], ok[mask]
    a = (mm * ww).sum() / ww.sum(); p = (mm[oo] * ww[oo]).sum() / ww[oo].sum()
    return -(ww.sum() / 1000 * E * LB_TO_G / 1000 * (a - p))   # positive = emissions rise
loo = {s: float(avg_screen_change(states != s)) for s in sorted(set(states)) if ok[states == s].any() or (~ok[states == s]).any()}
out["loo_avgscreen_change_mt"] = loo
out["avgscreen_change_without_iowa_mt"] = loo["Iowa"]
out["loo_range_mt"] = [min(loo.values()), max(loo.values())]
json.dump(out, open("results/results_marginal.json", "w"), indent=1)
print(json.dumps(out, indent=1))
