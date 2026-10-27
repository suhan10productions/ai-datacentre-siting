"""Collects every number the paper quotes from the siting analysis into
results_final.json. Run after siting_analysis.py's data files are in data/."""
import importlib.util
import json
import sys

import numpy as np

spec = importlib.util.spec_from_file_location("sa", "siting_analysis.py")
sa = importlib.util.module_from_spec(spec)
sys.argv = ["sa"]
spec.loader.exec_module(sa)

rng = np.random.default_rng(42)
NB = 5000


def wshare(df, col, w=None):
    return float(df[col].mean()) if w is None else float((df[col] * df[w]).sum() / df[w].sum())


def ci(df, f):
    vals = []
    for _ in range(NB):
        vals.append(f(df.iloc[rng.integers(0, len(df), len(df))]))
    return [float(v) for v in np.nanpercentile(vals, [2.5, 97.5])]


def stat(df, col, w=None):
    return dict(value=wshare(df, col, w), ci=ci(df, lambda d: wshare(d, col, w)))


def wmean(df, col, w=None):
    f = (lambda d: float(d[col].mean())) if w is None else (
        lambda d: float((d[col] * d[w]).sum() / d[w].sum()))
    return dict(value=f(df), ci=ci(df, f))


ep, pdb, cities = sa.ep, sa.pdb, sa.cities
us_avg = float(sa.state_ci["US"])
eu = ep[ep.gid_0 == "USA"].copy()
pu = pdb[pdb.gid_0 == "USA"].copy()
cu = cities[cities.gid_0 == "USA"]
for d in (eu, pu):
    d["above_us"] = (d.grid_ci > us_avg).astype(float)
    d["above_us10"] = (d.grid_ci > 1.10 * us_avg).astype(float)
s = sa.st[sa.st.state_code != "US"]
gen_above = float(s.loc[s.intensity_g_per_kwh > us_avg, "generation_twh"].sum() / s.generation_twh.sum())
gen_above10 = float(s.loc[s.intensity_g_per_kwh > 1.10 * us_avg, "generation_twh"].sum()
                    / s.generation_twh.sum())

R = dict(
    data=dict(
        n_peeringdb=len(pdb), n_peeringdb_dedup=len(sa.pdb_dedup), n_peeringdb_countries=int(pdb.gid_0.nunique()),
        n_epoch=len(ep), n_epoch_us=len(eu), epoch_planned_it_gw=float(ep.planned_it_mw.sum() / 1000),
        epoch_current_gw=float(ep.current_mw.sum() / 1000), n_cities=len(cities), n_us_cities=len(cu),
        peeringdb_nodata_excluded=sa.summary["pdb_nodata_excluded"],
        world_ci=float(sa.world_ci), us_avg_ci=us_avg,
    ),
    water=dict(
        epoch_count=stat(ep, "high_water"),
        epoch_planned=stat(ep, "high_water", "planned_it_mw"),
        epoch_current=stat(ep, "high_water", "current_mw"),
        pdb=stat(pdb, "high_water"),
        pdb_dedup=stat(sa.pdb_dedup, "high_water"),
        cities_pop=stat(cities, "high_water", "pop_max"),
        cities_count=stat(cities, "high_water"),
        epoch_planned_medhigh=stat(ep, "medhigh_water", "planned_it_mw"),
        pdb_medhigh=stat(pdb, "medhigh_water"),
        cities_pop_medhigh=stat(cities, "medhigh_water", "pop_max"),
        us_epoch_planned=stat(eu, "high_water", "planned_it_mw"),
        us_pdb=stat(pu, "high_water"),
        us_cities_pop=stat(cu, "high_water", "pop_max"),
        pdb_within_only=float(pdb[pdb.matched == "within"].high_water.mean()),
        epoch_minus_cities_pp=sa.summary["diff_epoch_minus_cities_pp"],
        pdb_minus_cities_pp=sa.summary["diff_pdb_minus_cities_pp"],
    ),
    carbon_us=dict(
        gen_share_states_above_avg=gen_above,
        gen_share_states_above_avg10=gen_above10,
        epoch_planned_share_above=stat(eu, "above_us", "planned_it_mw"),
        epoch_count_share_above=stat(eu, "above_us"),
        epoch_planned_share_above10=stat(eu, "above_us10", "planned_it_mw"),
        pdb_share_above=stat(pu, "above_us"),
        epoch_planned_wmean=wmean(eu, "grid_ci", "planned_it_mw"),
        epoch_current_wmean=wmean(eu, "grid_ci", "current_mw"),
        epoch_count_mean=wmean(eu, "grid_ci"),
        pdb_mean=wmean(pu, "grid_ci"),
        texas_share_planned=float(eu.loc[eu.name_1 == "Texas", "planned_it_mw"].sum() / eu.planned_it_mw.sum()),
        texas_ci=float(sa.state_ci["TX"]),
    ),
    carbon_global=dict(
        gen_share_above_world=float(sa.gen_ref_above),
        epoch_planned_share_above_world=stat(ep, "high_carbon", "planned_it_mw"),
        pdb_share_above_world=stat(pdb, "high_carbon"),
    ),
    both=dict(
        epoch_planned=stat(ep, "both", "planned_it_mw"),
        pdb=stat(pdb, "both"),
    ),
    robustness=dict(
        # weighted US mean with each of the three largest planned sites removed in turn
        loo_top3_planned_wmean={
            r.Name: float((eu.drop(i).grid_ci * eu.drop(i).planned_it_mw).sum() / eu.drop(i).planned_it_mw.sum())
            for i, r in eu.sort_values("planned_it_mw", ascending=False).head(3).iterrows()},
        epoch_planned_extreme_share=float(((ep.bws_cat == 4) * ep.planned_it_mw).sum() / ep.planned_it_mw.sum()),
        incl_arid=dict(epoch_planned=wshare(ep, "high_water_incl_arid", "planned_it_mw"),
                       pdb=wshare(pdb, "high_water_incl_arid"),
                       cities_pop=wshare(cities, "high_water_incl_arid", "pop_max")),
        us_states_planned=(eu.groupby("name_1").agg(mw=("planned_it_mw", "sum"), ci=("grid_ci", "first"))
                           .assign(share=lambda d: d.mw / d.mw.sum()).sort_values("mw", ascending=False)
                           .head(6).round(3).reset_index().to_dict(orient="records")),
    ),
    pakistan=dict(
        by_city=pdb[pdb.gid_0 == "PAK"].groupby("city").bws_label.agg(lambda s: s.value_counts().to_dict()).to_dict(),
        n=int((pdb.gid_0 == "PAK").sum()),
        high=int(pdb.loc[pdb.gid_0 == "PAK", "high_water"].sum()),
        extreme=int((pdb.loc[pdb.gid_0 == "PAK", "bws_cat"] == 4).sum()),
        cities=sorted(pdb.loc[pdb.gid_0 == "PAK", "city"].dropna().unique().tolist()),
        grid_ci=float(sa.country_ci["PAK"]),
    ),
    top_markets=sa.top.head(10).reset_index().to_dict(orient="records"),
)

if __name__ == "__main__":
    json.dump(R, open("results/results_final.json", "w"), indent=1, default=float)

    def pct(x):
        return f"{x['value']*100:.1f}% [{x['ci'][0]*100:.1f}-{x['ci'][1]*100:.1f}]"

    w, c = R["water"], R["carbon_us"]
    print("WATER high/extremely high:")
    for k in ("epoch_count", "epoch_planned", "epoch_current", "pdb", "pdb_dedup", "cities_pop", "cities_count",
              "epoch_planned_medhigh", "pdb_medhigh", "cities_pop_medhigh", "us_epoch_planned", "us_pdb", "us_cities_pop"):
        print(f"  {k:24s} {pct(w[k])}")
    print("  diffs pp:", w["epoch_minus_cities_pp"], w["pdb_minus_cities_pp"], "within-only pdb", round(w["pdb_within_only"], 3))
    print("CARBON US: gen share above avg", round(c["gen_share_states_above_avg"], 3), "above +10%", round(c["gen_share_states_above_avg10"], 3))
    for k in ("epoch_planned_share_above", "epoch_count_share_above", "epoch_planned_share_above10", "pdb_share_above"):
        print(f"  {k:30s} {pct(c[k])}")
    for k in ("epoch_planned_wmean", "epoch_current_wmean", "epoch_count_mean", "pdb_mean"):
        print(f"  {k:30s} {c[k]['value']:.0f} [{c[k]['ci'][0]:.0f}-{c[k]['ci'][1]:.0f}] g")
    print("  Texas share", round(c["texas_share_planned"], 3), c["texas_ci"])
    g = R["carbon_global"]
    print("GLOBAL: gen above world", round(g["gen_share_above_world"], 3), "epoch", pct(g["epoch_planned_share_above_world"]), "pdb", pct(g["pdb_share_above_world"]))
    print("BOTH:", pct(R["both"]["epoch_planned"]), pct(R["both"]["pdb"]))
    print("PAK:", R["pakistan"])
    print("DATA:", R["data"])
