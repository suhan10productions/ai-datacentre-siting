"""Criterion 2 test: is data centre capacity sited according to water
availability and grid carbon intensity?

Inputs (data/):
  peeringdb_water.csv  PeeringDB facilities joined to Aqueduct 4.0 sub-basins
  epoch_water.csv      Epoch AI frontier sites joined to Aqueduct 4.0
  cities_water.csv     Natural Earth populated places joined to Aqueduct 4.0
  epoch_data_centers.csv, epoch_data_center_timelines.csv   Epoch capacity
  owid-energy-data.csv           country grid carbon intensity (Ember, via OWID)
  ember_us_states_2024.psv       US state grid carbon intensity (Ember)
Spatial join: join.py (run with geopandas on the Aqueduct baseline_annual layer).
"""
import json
import re

import numpy as np
import pandas as pd

D = "data/"
YEAR = 2024
RNG = np.random.default_rng(20261014)
NBOOT = 2000

US_STATES = {
    "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR", "California": "CA",
    "Colorado": "CO", "Connecticut": "CT", "Delaware": "DE", "District of Columbia": "DC",
    "Florida": "FL", "Georgia": "GA", "Hawaii": "HI", "Idaho": "ID", "Illinois": "IL",
    "Indiana": "IN", "Iowa": "IA", "Kansas": "KS", "Kentucky": "KY", "Louisiana": "LA",
    "Maine": "ME", "Maryland": "MD", "Massachusetts": "MA", "Michigan": "MI", "Minnesota": "MN",
    "Mississippi": "MS", "Missouri": "MO", "Montana": "MT", "Nebraska": "NE", "Nevada": "NV",
    "New Hampshire": "NH", "New Jersey": "NJ", "New Mexico": "NM", "New York": "NY",
    "North Carolina": "NC", "North Dakota": "ND", "Ohio": "OH", "Oklahoma": "OK", "Oregon": "OR",
    "Pennsylvania": "PA", "Rhode Island": "RI", "South Carolina": "SC", "South Dakota": "SD",
    "Tennessee": "TN", "Texas": "TX", "Utah": "UT", "Vermont": "VT", "Virginia": "VA",
    "Washington": "WA", "West Virginia": "WV", "Wisconsin": "WI", "Wyoming": "WY",
}

# ------------------------------------------------------------------ grid carbon
owid = pd.read_csv(D + "owid-energy-data.csv",
                   usecols=["country", "year", "iso_code", "carbon_intensity_elec",
                            "electricity_generation"])
o = owid[(owid.year == YEAR) & owid.iso_code.notna() & ~owid.iso_code.str.startswith("OWID", na=True)]
o = o.dropna(subset=["carbon_intensity_elec"])
country_ci = dict(zip(o.iso_code, o.carbon_intensity_elec))
world_ci = float(owid[(owid.year == YEAR) & (owid.country == "World")].carbon_intensity_elec.iloc[0])

st = pd.read_csv(D + "ember_us_states_2024.psv", sep="|")
state_ci = dict(zip(st.state_code, st.intensity_g_per_kwh))

# Reference distribution: world generation by grid unit (US states + other countries)
gen_units = pd.concat([
    st[st.state_code != "US"].rename(columns={"state_code": "unit", "generation_twh": "gen",
                                              "intensity_g_per_kwh": "ci"})[["unit", "gen", "ci"]],
    o[o.iso_code != "USA"].rename(columns={"iso_code": "unit", "electricity_generation": "gen",
                                           "carbon_intensity_elec": "ci"})[["unit", "gen", "ci"]],
]).dropna()
gen_ref_above = gen_units.loc[gen_units.ci > world_ci, "gen"].sum() / gen_units.gen.sum()


def grid_ci(row):
    """State intensity for US points, country intensity elsewhere."""
    if row["gid_0"] == "USA":
        code = US_STATES.get(row["name_1"])
        if code in state_ci:
            return state_ci[code], "US state"
        return country_ci.get("USA"), "US national (state missing)"
    return country_ci.get(row["gid_0"], np.nan), "country"


def prep(df):
    df = df.copy()
    df["has_water"] = df["bws_cat"].isin([-1, 0, 1, 2, 3, 4])
    df["high_water"] = df["bws_cat"] >= 3
    df["high_water_incl_arid"] = (df["bws_cat"] >= 3) | (df["bws_cat"] == -1)
    df["medhigh_water"] = df["bws_cat"] >= 2
    ci = df.apply(grid_ci, axis=1, result_type="expand")
    df["grid_ci"], df["grid_level"] = ci[0], ci[1]
    df["high_carbon"] = df["grid_ci"] > world_ci
    df["both"] = df["high_water"] & df["high_carbon"]
    return df


# ------------------------------------------------------------------ load points
pdb = prep(pd.read_csv(D + "peeringdb_water.csv"))
pdb = pdb[pdb.has_water]
# de-duplicate facilities on the same site (~1 km grid)
pdb["cell"] = pdb.latitude.round(2).astype(str) + "," + pdb.longitude.round(2).astype(str)
pdb_dedup = pdb.drop_duplicates("cell")

cities = prep(pd.read_csv(D + "cities_water.csv"))
cities = cities[cities.has_water & (cities.pop_max > 0)]

ep = prep(pd.read_csv(D + "epoch_water.csv"))
dc = pd.read_csv(D + "epoch_data_centers.csv")
norm = lambda s: re.sub(r"[^a-z0-9]", "", str(s).lower())
dc["k"] = dc["Name"].map(norm)
ep["k"] = ep["site_id"].map(norm)
# the one map entry without a slug is resolved by elimination against the CSV
unmatched_names = sorted(set(dc.k) - set(ep.k))
if (ep.site_id == "UNKNOWN_New_Mexico").any() and len(unmatched_names) == 1:
    ep.loc[ep.site_id == "UNKNOWN_New_Mexico", "k"] = unmatched_names[0]
ep = ep.merge(dc[["k", "Name", "Owner", "Current power (MW)"]], on="k", how="left")
tl = pd.read_csv(D + "epoch_data_center_timelines.csv")
tl["k"] = tl["Data center"].map(norm)
tl["Date"] = pd.to_datetime(tl["Date"])
planned = tl.sort_values("Date").groupby("k").agg(planned_it_mw=("IT power (MW)", "max"),
                                                    first_date=("Date", "min"))
ep = ep.merge(planned, on="k", how="left")
ep["current_mw"] = ep["Current power (MW)"].fillna(0)
ep["planned_it_mw"] = ep["planned_it_mw"].fillna(0)


# ------------------------------------------------------------------ statistics
def share(df, col, w=None):
    if w is None:
        return df[col].mean()
    return (df[col] * df[w]).sum() / df[w].sum()


def boot(df, col, w=None):
    n = len(df)
    vals = []
    arr = df[col].to_numpy(float)
    wt = None if w is None else df[w].to_numpy(float)
    for _ in range(NBOOT):
        idx = RNG.integers(0, n, n)
        if wt is None:
            vals.append(arr[idx].mean())
        else:
            ww = wt[idx]
            vals.append((arr[idx] * ww).sum() / ww.sum() if ww.sum() > 0 else np.nan)
    lo, hi = np.nanpercentile(vals, [2.5, 97.5])
    return lo, hi


def row(label, df, col, w=None):
    s = share(df, col, w)
    lo, hi = boot(df, col, w)
    return dict(sample=label, measure=col, weight=w or "count", n=len(df), share=s, ci_lo=lo, ci_hi=hi)


results = []
for col in ["high_water", "high_carbon", "both", "medhigh_water", "high_water_incl_arid"]:
    results += [
        row("Epoch AI frontier sites", ep, col),
        row("Epoch AI frontier sites", ep, col, "current_mw"),
        row("Epoch AI frontier sites", ep, col, "planned_it_mw"),
        row("PeeringDB facilities", pdb, col),
        row("PeeringDB sites (1 km dedup)", pdb_dedup, col),
    ]
    if col != "high_carbon" and col != "both":
        results += [row("World cities (population-weighted)", cities, col, "pop_max"),
                    row("World cities (count)", cities, col)]
res = pd.DataFrame(results)

# Robustness: exclude points matched by nearest polygon rather than containment
rob = []
for label, df in [("PeeringDB facilities", pdb), ("Epoch AI frontier sites", ep)]:
    sub = df[df.matched == "within"]
    rob.append(dict(check="within-polygon matches only", sample=label, n=len(sub),
                    high_water=sub.high_water.mean()))
rob = pd.DataFrame(rob)

# Two-proportion comparison: Epoch (count) vs population-weighted cities, by bootstrap
def diff_boot(a, b, col, wb):
    d = []
    for _ in range(NBOOT):
        ia = RNG.integers(0, len(a), len(a)); ib = RNG.integers(0, len(b), len(b))
        sa = a[col].to_numpy(float)[ia].mean()
        bb = b.iloc[ib]
        sb = (bb[col] * bb[wb]).sum() / bb[wb].sum()
        d.append(sa - sb)
    return np.percentile(d, [2.5, 50, 97.5])

diff_ep_cities = diff_boot(ep, cities, "high_water", "pop_max")
diff_pdb_cities = diff_boot(pdb, cities, "high_water", "pop_max")

# Country breakdown for PeeringDB (top markets) and Pakistan
top = (pdb.groupby("gid_0").agg(n=("high_water", "size"), high_water=("high_water", "mean"),
                               grid_ci=("grid_ci", "mean"))
       .sort_values("n", ascending=False))
pak = pdb[pdb.gid_0 == "PAK"][["name", "city", "bws_label", "grid_ci"]]

# Epoch site table
ep_tab = ep[["Name", "Owner", "name_0", "name_1", "bws_label", "bws_cat", "grid_ci",
             "high_water", "high_carbon", "current_mw", "planned_it_mw"]].sort_values(
    "planned_it_mw", ascending=False)

summary = dict(
    world_ci_2024=world_ci,
    gen_share_above_world_ci=gen_ref_above,
    n_pdb=len(pdb), n_pdb_dedup=len(pdb_dedup), n_cities=len(cities), n_epoch=len(ep),
    epoch_current_gw=ep.current_mw.sum() / 1000, epoch_planned_it_gw=ep.planned_it_mw.sum() / 1000,
    epoch_us_share_count=(ep.gid_0 == "USA").mean(),
    epoch_us_share_planned=ep.loc[ep.gid_0 == "USA", "planned_it_mw"].sum() / ep.planned_it_mw.sum(),
    diff_epoch_minus_cities_pp=list(np.round(diff_ep_cities * 100, 1)),
    diff_pdb_minus_cities_pp=list(np.round(diff_pdb_cities * 100, 1)),
    pdb_nodata_excluded=int((pd.read_csv(D + "peeringdb_water.csv").bws_cat == -9999).sum()),
    epoch_unmatched_capacity=int(ep.Name.isna().sum()),
)

if __name__ == "__main__":
    pd.set_option("display.width", 200)
    print(json.dumps(summary, indent=1, default=float))
    print(res.assign(share=lambda d: (d.share * 100).round(1), ci_lo=lambda d: (d.ci_lo * 100).round(1),
                     ci_hi=lambda d: (d.ci_hi * 100).round(1)).to_string(index=False))
    print(rob.to_string(index=False))
    print(top.head(15).round(2).to_string())
    print("Pakistan:\n", pak.to_string(index=False))
    print(ep_tab.head(20).to_string(index=False))
    res.to_csv("results/results_shares.csv", index=False)
    ep_tab.to_csv("results/results_epoch_sites.csv", index=False)
    top.to_csv("results/results_pdb_by_country.csv")
    json.dump(summary, open("results/results_summary.json", "w"), indent=1, default=float)


# ------------------------------------------------------------------ within-US tests
def within_us():
    us_avg = state_ci["US"]
    s = st[st.state_code != "US"]
    gen_above = s.loc[s.intensity_g_per_kwh > us_avg, "generation_twh"].sum() / s.generation_twh.sum()
    eu = ep[ep.gid_0 == "USA"].copy()
    eu["above_us"] = eu.grid_ci > us_avg
    pu = pdb[pdb.gid_0 == "USA"].copy()
    pu["above_us"] = pu.grid_ci > us_avg
    cu = cities[cities.gid_0 == "USA"]
    out = dict(
        us_avg_ci=us_avg,
        us_gen_share_in_states_above_avg=gen_above,
        epoch_us_n=len(eu),
        epoch_us_planned_gw=eu.planned_it_mw.sum() / 1000,
        epoch_us_planned_weighted_ci=(eu.grid_ci * eu.planned_it_mw).sum() / eu.planned_it_mw.sum(),
        epoch_us_current_weighted_ci=(eu.grid_ci * eu.current_mw).sum() / eu.current_mw.sum(),
        epoch_us_count_mean_ci=eu.grid_ci.mean(),
        epoch_us_share_above_avg_count=eu.above_us.mean(),
        epoch_us_share_above_avg_planned=(eu.above_us * eu.planned_it_mw).sum() / eu.planned_it_mw.sum(),
        epoch_us_share_above_avg_planned_ci=boot(eu.assign(a=eu.above_us.astype(float)), "a", "planned_it_mw"),
        pdb_us_n=len(pu),
        pdb_us_share_above_avg=pu.above_us.mean(),
        pdb_us_mean_ci=pu.grid_ci.mean(),
        epoch_us_high_water_planned=(eu.high_water * eu.planned_it_mw).sum() / eu.planned_it_mw.sum(),
        epoch_us_high_water_count=eu.high_water.mean(),
        pdb_us_high_water=pu.high_water.mean(),
        us_cities_high_water_popw=(cu.high_water * cu.pop_max).sum() / cu.pop_max.sum(),
        us_cities_n=len(cu),
        epoch_global_planned_weighted_ci=(ep.grid_ci * ep.planned_it_mw).sum() / ep.planned_it_mw.sum(),
        pdb_global_mean_ci=pdb.grid_ci.mean(),
        pak_n=int((pdb.gid_0 == "PAK").sum()),
        pak_high_water=float(pdb.loc[pdb.gid_0 == "PAK", "high_water"].mean()),
        pak_extreme=int((pdb.loc[pdb.gid_0 == "PAK", "bws_cat"] == 4).sum()),
        pak_grid_ci=country_ci.get("PAK"),
    )
    return out


if __name__ == "__main__":
    us = within_us()
    print(json.dumps(us, indent=1, default=lambda x: [float(v) for v in x] if hasattr(x, "__len__") else float(x)))
    json.dump(us, open("results/results_within_us.json", "w"), indent=1,
              default=lambda x: [float(v) for v in x] if hasattr(x, "__len__") else float(x))
