"""Siting screen (Section 5.3): how much planned US AI capacity would pass a
simple pre-approval screen on water and carbon, and what the screen would do
to the average grid intensity of that capacity.

Screen: the campus is (a) not in a high or extremely high water-stress
sub-basin (Aqueduct 4.0 baseline, withdrawals <= 40% of supply) and (b) in a
state whose 2024 grid intensity (Ember, lifecycle) is at or below the US
average. Weighted by planned IT capacity. 95% bootstrap CIs over sites.
Run after siting_results.py (reads results/results_epoch_sites.csv).
"""
import json
import numpy as np
import pandas as pd

RNG = np.random.default_rng(20261023)
NBOOT = 5000
e = pd.read_csv("results/results_epoch_sites.csv")
st = pd.read_csv("data/ember_us_states_2024.psv", sep="|")
US_AVG = float(st[st.state_code == "US"].intensity_g_per_kwh.iloc[0])
us = e[e.name_0 == "United States"].reset_index(drop=True)
w = us.planned_it_mw.to_numpy()
ci = us.grid_ci.to_numpy()
hw = (us.bws_cat >= 3).to_numpy()
hc = ci > US_AVG
ok = ~(hw | hc)

# Energy per GW of planned IT capacity, from the central projection model:
# rho * load factor * 8,760 h * PUE  (model.py)
import sys
sys.path.insert(0, "../model")
sys.path.insert(0, "../work")
import model as m
TWH_PER_GW = m.RHO["central"] * m.load_factor(m.U["central"], m.IDLE["central"]) * m.HOURS / 1000 * m.PUE["central"]


def stats(idx):
    ww, cc, hww, hcc, okk = w[idx], ci[idx], hw[idx], hc[idx], ok[idx]
    tot = ww.sum()
    avg_all = (cc * ww).sum() / tot
    avg_ok = (cc[okk] * ww[okk]).sum() / ww[okk].sum() if ww[okk].sum() > 0 else np.nan
    return dict(pass_share=ww[okk].sum() / tot, fail_both=ww[hww & hcc].sum() / tot,
                fail_water_only=ww[hww & ~hcc].sum() / tot, fail_carbon_only=ww[~hww & hcc].sum() / tot,
                avg_all=avg_all, avg_pass=avg_ok, cut=1 - avg_ok / avg_all,
                saving_mt=tot / 1000 * TWH_PER_GW * (avg_all - avg_ok) / 1000)


point = stats(np.arange(len(us)))
boot = [stats(RNG.integers(0, len(us), len(us))) for _ in range(NBOOT)]
ci95 = {k: [float(np.nanpercentile([b[k] for b in boot], 2.5)), float(np.nanpercentile([b[k] for b in boot], 97.5))]
        for k in point}
# Threshold sensitivity: carbon test at US average + 5% (lets Texas, 394 g, pass)
hc5 = ci > US_AVG * 1.05
ok5 = ~(hw | hc5)
alt = dict(pass_share=w[ok5].sum() / w.sum(),
           avg_pass=(ci[ok5] * w[ok5]).sum() / w[ok5].sum())
# Threshold sensitivity grid: carbon at 90/100/110% of the US average, water at
# high (>40%) or medium-high (>20%) stress.
grid_tests = []
for cf in (0.9, 1.0, 1.1):
    for wcat, wlab in ((3, "high"), (2, "medium-high")):
        okk = ~((us.bws_cat >= wcat).to_numpy() | (ci > US_AVG * cf))
        grid_tests.append(dict(carbon_factor=cf, water=wlab, pass_share=float(w[okk].sum() / w.sum()),
                               avg_pass=float((ci[okk] * w[okk]).sum() / w[okk].sum()) if okk.any() else None))
# Upper bound versus capacity not yet built: only the planned capacity that is
# not yet operating (planned - current, floored at zero) is assumed movable.
unbuilt = np.clip(us.planned_it_mw.to_numpy() - us.current_mw.to_numpy(), 0, None)
avg_pass = point["avg_pass"]
fail = ~ok
sav_all = (w[fail] * (ci[fail] - avg_pass)).sum() / 1000 * TWH_PER_GW / 1000
sav_unbuilt = (unbuilt[fail] * (ci[fail] - avg_pass)).sum() / 1000 * TWH_PER_GW / 1000
out_extra = dict(threshold_grid=grid_tests, unbuilt_gw=float(unbuilt.sum() / 1000),
                 unbuilt_fail_gw=float(unbuilt[fail].sum() / 1000),
                 saving_all_mt=float(sav_all), saving_unbuilt_mt=float(sav_unbuilt))
out = dict(us_avg=US_AVG, n_sites=int(len(us)), n_pass=int(ok.sum()), planned_gw=float(w.sum() / 1000),
           twh_per_gw=TWH_PER_GW, point={k: float(v) for k, v in point.items()}, ci95=ci95,
           threshold_plus5pct={k: float(v) for k, v in alt.items()},
           pass_states=us[ok].groupby("name_1").planned_it_mw.sum().sort_values(ascending=False).round(0).to_dict(),
           fail_states=us[~ok].groupby("name_1").planned_it_mw.sum().sort_values(ascending=False).round(0).to_dict())
out.update(out_extra)
json.dump(out, open("results/results_screen.json", "w"), indent=1)
print(json.dumps({k: out[k] for k in ("n_sites", "n_pass", "planned_gw", "twh_per_gw", "point", "ci95", "threshold_plus5pct",
                                       "threshold_grid", "unbuilt_gw", "unbuilt_fail_gw", "saving_all_mt", "saving_unbuilt_mt")}, indent=1))
