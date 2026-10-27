"""Stricter relocation test for the long-run-marginal screen (Section 5.2).

Instead of moving failing capacity to the average rate of all passing capacity
nationally, each failing campus is moved only within its own interconnection
(Western, ERCOT or Eastern, grouped from Cambium regions), to the
capacity-weighted average long-run marginal rate of passing campuses in that
interconnection. Campuses in an interconnection with no passing capacity stay
where they are. Mid-case and the five other scenarios; 5,000 bootstrap
replicates for the Mid-case. Reads the same inputs as siting_lrmer.py.
Output: results/results_lrmer_regional.json.
"""
import json, runpy, numpy as np
G = runpy.run_path("siting_lrmer.py", run_name="lrmer_lib")
us, pl, LR, w, hw, E = G["us"], G["pl"], G["LR"], G["w"], G["hw"], G["E"]
WEST = {"CAISO", "NorthernGrid_East", "NorthernGrid_South", "NorthernGrid_West", "WestConnect_North", "WestConnect_South"}
ic = np.array(["West" if g in WEST else ("ERCOT" if g == "ERCOT" else "East") for g in us.gea])
RNG = np.random.default_rng(20261030)


def change(scen, idx=None, pidx=None):
    m = us.gea.map(LR[scen]).to_numpy(float)
    pm = pl.gea.map(LR[scen]).to_numpy(float); pw = pl.pop_max.to_numpy(float)
    idx = np.arange(len(w)) if idx is None else idx
    pidx = np.arange(len(pm)) if pidx is None else pidx
    ref = (pm[pidx] * pw[pidx]).sum() / pw[pidx].sum()
    ww, mm, hh, cc = w[idx], m[idx], hw[idx], ic[idx]
    ok = ~(hh | (mm > ref))
    delta = 0.0  # kg/MWh x MW
    moved = 0.0
    for g in ("West", "ERCOT", "East"):
        sel = cc == g
        p = sel & ok
        if ww[p].sum() == 0:
            continue
        target = (mm[p] * ww[p]).sum() / ww[p].sum()
        f = sel & ~ok
        delta += (ww[f] * (target - mm[f])).sum()
        moved += ww[f].sum()
    return dict(change_mt=delta / 1000 * E / 1000,  # MW*kg/MWh -> GW * TWh/GW * kg/MWh = kt; /1000 -> Mt
                moved_share=moved / ww.sum())


out = {s: change(s) for s in LR}
pt = out["Mid-case"]
bt = [change("Mid-case", RNG.integers(0, len(w), len(w)), RNG.integers(0, len(pl), len(pl)))["change_mt"] for _ in range(5000)]
out["mid_ci95"] = [float(np.percentile(bt, 2.5)), float(np.percentile(bt, 97.5))]
json.dump(out, open("results/results_lrmer_regional.json", "w"), indent=1)
print({k: (round(v["change_mt"], 2), round(v["moved_share"], 2)) for k, v in out.items() if isinstance(v, dict)}, out["mid_ci95"])
