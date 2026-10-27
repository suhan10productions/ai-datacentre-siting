"""Robustness of the water-gap comparison (Section 4.1; supplement S3).

Repeats siting_watergap.py for (a) 1.5 C of warming (multi-model average),
(b) each of the five climate models behind the 3 C average (H08 hydrological
model driven by GFDL-ESM4, IPSL-CM6A-LR, MPI-ESM1-2-HR, MRI-ESM2-0 and
UKESM1-0-LL), and (c) a neighbourhood test in which a location counts as exposed
if any cell in the surrounding 3 x 3 block (about 150 km) has a gap, for the
baseline and the 3 C average. Joint bootstrap of AI capacity minus urban
population, 2,000 replicates. Inputs: data/ext/water_gap_*.nc from
zenodo.org/records/14882216. Output: results/results_watergap_robust.json.
"""
import json, re
import numpy as np, pandas as pd, geopandas as gpd, xarray as xr

EXT = "data/ext/"
RNG = np.random.default_rng(20261029)
NB = 2000


def sampler(path, neighbourhood=False):
    d = xr.open_dataset(path)
    a = np.nan_to_num(d["water gap"].values, nan=0.0) < 0
    if neighbourhood:
        b = a.copy()
        for di in (-1, 0, 1):
            for dj in (-1, 0, 1):
                b |= np.roll(np.roll(a, di, 0), dj, 1)
        a = b
    lat, lon = d.lat.values, d.lon.values
    def f(lo, la):
        i = np.abs(lat[None, :] - np.asarray(la)[:, None]).argmin(1)
        j = np.abs(lon[None, :] - np.asarray(lo)[:, None]).argmin(1)
        return a[i, j]
    return f


pl = gpd.read_file(EXT + "ne_places.geojson"); pl = pl[pl.pop_max > 0]
norm = lambda x: re.sub(r"[^a-z0-9]", "", str(x).lower())
e = pd.read_csv("results/results_epoch_sites.csv"); co = pd.read_csv("data/epoch_coords.csv")
co["k"] = co.site_id.map(norm); e["k"] = e.Name.map(norm)
left = sorted(set(e.k) - set(co.k))
if (co.site_id == "UNKNOWN_New_Mexico").any() and len(left) == 1:
    co.loc[co.site_id == "UNKNOWN_New_Mexico", "k"] = left[0]
e = e.merge(co[["k", "lon", "lat"]], on="k", how="left")
wp = pl.pop_max.to_numpy(float); wa = e.planned_it_mw.to_numpy(float)
share = lambda x, w: float((x * w).sum() / w.sum())

cases = {"1.5C average": ("water_gap_15C_average.nc", False)}
for m in ("gfdl-esm4", "ipsl-cm6a-lr", "mpi-esm1-2-hr", "mri-esm2-0", "ukesm1-0-ll"):
    cases[f"3C {m}"] = (f"water_gap_3C_h08_{m}.nc", False)
cases["baseline, 3x3 neighbourhood"] = ("water_gap_baseline.nc", True)
cases["3C average, 3x3 neighbourhood"] = ("water_gap_3C_average.nc", True)
out = {}
for name, (fn, nbh) in cases.items():
    f = sampler(EXT + fn, nbh)
    xp, xa = f(pl.longitude, pl.latitude), f(e.lon, e.lat)
    d = []
    for _ in range(NB):
        ip = RNG.integers(0, len(xp), len(xp)); ia = RNG.integers(0, len(xa), len(xa))
        d.append(share(xa[ia], wa[ia]) - share(xp[ip], wp[ip]))
    out[name] = dict(ai=share(xa, wa), pop=share(xp, wp), diff=share(xa, wa) - share(xp, wp),
                     ci=[float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))])
json.dump(out, open("results/results_watergap_robust.json", "w"), indent=1)
for k, v in out.items():
    print(f"{k:32s} AI {v['ai']*100:5.1f}  pop {v['pop']*100:5.1f}  diff {v['diff']*100:+5.1f} ({v['ci'][0]*100:+.0f} to {v['ci'][1]*100:+.0f})")

# Model agreement at 3 C: exposed if at least k of the five models show a gap.
# (The multi-model average is non-zero wherever any one model has a gap, so it
# behaves like k = 1.)
fs = [sampler(EXT + f"water_gap_3C_h08_{m}.nc") for m in ("gfdl-esm4", "ipsl-cm6a-lr", "mpi-esm1-2-hr", "mri-esm2-0", "ukesm1-0-ll")]
cp = sum(f(pl.longitude, pl.latitude).astype(int) for f in fs); ca = sum(f(e.lon, e.lat).astype(int) for f in fs)
fb = sampler(EXT + "water_gap_baseline.nc"); xb_p, xb_a = fb(pl.longitude, pl.latitude), fb(e.lon, e.lat)
agree = {}
for k in (1, 3, 5):
    xp, xa = cp >= k, ca >= k
    d = []
    for _ in range(NB):
        ip = RNG.integers(0, len(xp), len(xp)); ia = RNG.integers(0, len(xa), len(xa))
        d.append(share(xa[ia], wa[ia]) - share(xp[ip], wp[ip]))
    agree[f"3C, at least {k} of 5 models"] = dict(ai=share(xa, wa), pop=share(xp, wp), diff=share(xa, wa) - share(xp, wp),
                                                  ci=[float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))],
                                                  new_ai=share(xa & ~xb_a, wa), new_pop=share(xp & ~xb_p, wp))
out.update(agree)
json.dump(out, open("results/results_watergap_robust.json", "w"), indent=1)
for k, v in agree.items():
    print(f"{k:32s} AI {v['ai']*100:5.1f}  pop {v['pop']*100:5.1f}  diff {v['diff']*100:+5.1f} ({v['ci'][0]*100:+.0f} to {v['ci'][1]*100:+.0f})  newly exposed AI {v['new_ai']*100:.0f} pop {v['new_pop']*100:.0f}")

# Group shares for the main-text table (majority agreement, at least 3 of 5 models)
pdb = pd.read_csv("data/peeringdb_water.csv"); pdb = pdb[pdb.bws_cat.isin([-1, 0, 1, 2, 3, 4])]
cf = sum(f(pdb.longitude, pdb.latitude).astype(int) for f in fs) >= 3
us_p = (pl.adm0name == "United States of America").to_numpy(); us_a = (e.name_0 == "United States").to_numpy()
tab = dict(pop=share(cp >= 3, wp), fleet=float(cf.mean()), ai_capacity=share(ca >= 3, wa), ai_count=float((ca >= 3).mean()),
           us_pop=share((cp >= 3)[us_p], wp[us_p]), us_ai_capacity=share((ca >= 3)[us_a], wa[us_a]))
out["table_3of5"] = tab
json.dump(out, open("results/results_watergap_robust.json", "w"), indent=1)
print({k: round(v * 100) for k, v in tab.items()})
