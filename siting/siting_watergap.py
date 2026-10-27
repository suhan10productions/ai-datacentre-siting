"""Water-stress benchmark on Rosa et al.'s metric (Section 4.1).

Rosa and Sangiorgio (2025) publish a 0.5-degree global grid of the annual water
gap: the sum over months of water use in excess of available renewable supply
(km3/yr; negative values mark a gap). Rosa et al. (2026) count a data centre as
exposed if it sits where there is at least one month of gap a year, which is
equivalent to a non-zero annual gap in this grid. This script applies that test
to the same three groups as the main analysis: the urban population (Natural
Earth populated places, weighted by pop_max), PeeringDB facilities (one per
facility) and large AI campuses (weighted by planned IT capacity), for the
2001-2010 baseline and the 3 C warming multi-model average. Differences from the
population reference use a joint bootstrap (5,000 replicates), as in
siting_difference.py.

Inputs (data/ext/): water_gap_baseline.nc, water_gap_3C_average.nc
(zenodo.org/records/14882216, CC BY 4.0), ne_places.geojson (Natural Earth),
plus data/peeringdb_water.csv (see fetch_peeringdb.py) and data/epoch_coords.csv.
Outputs results/results_watergap.json.
"""
import json
import re
import numpy as np
import pandas as pd
import geopandas as gpd
import xarray as xr

EXT = "data/ext/"
RNG = np.random.default_rng(20261028)
NBOOT = 5000


def sampler(path):
    d = xr.open_dataset(path)
    a = d["water gap"].values
    lat, lon = d.lat.values, d.lon.values
    def f(lo, la):
        i = np.abs(lat[None, :] - np.asarray(la)[:, None]).argmin(1)
        j = np.abs(lon[None, :] - np.asarray(lo)[:, None]).argmin(1)
        v = a[i, j]
        return np.nan_to_num(v, nan=0.0) < 0
    return f


GAP = {"baseline": sampler(EXT + "water_gap_baseline.nc"), "3C": sampler(EXT + "water_gap_3C_average.nc")}

pl = gpd.read_file(EXT + "ne_places.geojson")
pl = pl[pl.pop_max > 0]
pdb = pd.read_csv("data/peeringdb_water.csv")
pdb = pdb[pdb.bws_cat.isin([-1, 0, 1, 2, 3, 4])]  # same 5,254 facilities as the main analysis
norm = lambda x: re.sub(r"[^a-z0-9]", "", str(x).lower())
e = pd.read_csv("results/results_epoch_sites.csv")
co = pd.read_csv("data/epoch_coords.csv")
co["k"] = co.site_id.map(norm); e["k"] = e.Name.map(norm)
left = sorted(set(e.k) - set(co.k))
if (co.site_id == "UNKNOWN_New_Mexico").any() and len(left) == 1:
    co.loc[co.site_id == "UNKNOWN_New_Mexico", "k"] = left[0]
e = e.merge(co[["k", "lon", "lat"]], on="k", how="left")


def share(x, w):
    return float((x * w).sum() / w.sum())


out = {"n": dict(places=int(len(pl)), peeringdb=int(len(pdb)), campuses=int(len(e)))}
for sc, f in GAP.items():
    xp, wp = f(pl.longitude, pl.latitude), pl.pop_max.to_numpy(float)
    xf, wf = f(pdb.longitude, pdb.latitude), np.ones(len(pdb))
    xa, wa = f(e.lon, e.lat), e.planned_it_mw.to_numpy(float)
    us_p = (pl.adm0name == "United States of America").to_numpy()
    us_f = (pdb.country == "US").to_numpy()
    us_a = (e.name_0 == "United States").to_numpy()
    res = dict(pop=share(xp, wp), fleet=share(xf, wf), ai_capacity=share(xa, wa), ai_count=share(xa, np.ones(len(xa))),
               us_pop=share(xp[us_p], wp[us_p]), us_fleet=share(xf[us_f], wf[us_f]), us_ai_capacity=share(xa[us_a], wa[us_a]))
    boot = {"ai_minus_pop": [], "fleet_minus_pop": [], "us_ai_minus_us_pop": []}
    for _ in range(NBOOT):
        ip = RNG.integers(0, len(xp), len(xp)); ia = RNG.integers(0, len(xa), len(xa)); jf = RNG.integers(0, len(xf), len(xf))
        p = share(xp[ip], wp[ip])
        boot["ai_minus_pop"].append(share(xa[ia], wa[ia]) - p)
        boot["fleet_minus_pop"].append(share(xf[jf], wf[jf]) - p)
        iu = np.where(us_p)[0]; iu = iu[RNG.integers(0, len(iu), len(iu))]
        ja = np.where(us_a)[0]; ja = ja[RNG.integers(0, len(ja), len(ja))]
        boot["us_ai_minus_us_pop"].append(share(xa[ja], wa[ja]) - share(xp[iu], wp[iu]))
    res["diff"] = {k: dict(point=dict(ai_minus_pop=res["ai_capacity"] - res["pop"], fleet_minus_pop=res["fleet"] - res["pop"],
                                      us_ai_minus_us_pop=res["us_ai_capacity"] - res["us_pop"])[k],
                           ci=[float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))])
                   for k, v in boot.items()}
    out[sc] = res
json.dump(out, open("results/results_watergap.json", "w"), indent=1)
print(json.dumps(out, indent=1))
