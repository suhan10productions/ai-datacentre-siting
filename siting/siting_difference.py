"""Direct tests of the siting comparisons (Section 4.4-4.5, criterion 2).

Water: difference between the share of a data-centre sample in high or
extremely high stress and the population-weighted share of the urban
reference, using the SAME weighting as the headline figure, by joint
bootstrap (both samples resampled independently in every replicate).
Carbon (US): difference between the capacity-weighted grid intensity of the
large AI campuses and the US average (a fixed reference), and between their
share in above-average states and the share of US generation in those states.
Reports the 95% interval and the share of replicates on each side of zero.
"""
import json
import numpy as np
import siting_analysis as sa

RNG = np.random.default_rng(20261026)
NB = 5000
cities = sa.cities.reset_index(drop=True)
ep = sa.ep[sa.ep.planned_it_mw > 0].reset_index(drop=True)
pdb = sa.pdb.reset_index(drop=True)
cw = cities.pop_max.to_numpy(float); ch = cities.high_water.to_numpy(float)


def share(h, w):
    return (h * w).sum() / w.sum()


def diff(sample_h, sample_w, ref_h, ref_w, us_mask_s=None, us_mask_r=None):
    out = []
    ns, nr = len(sample_h), len(ref_h)
    for _ in range(NB):
        i = RNG.integers(0, ns, ns); j = RNG.integers(0, nr, nr)
        out.append(share(sample_h[i], sample_w[i]) - share(ref_h[j], ref_w[j]))
    out = np.array(out)
    point = share(sample_h, sample_w) - share(ref_h, ref_w)
    return dict(point=float(point), ci=[float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5))],
                share_below_zero=float((out < 0).mean()), share_below_minus10=float((out < -0.10).mean()))


eh = ep.high_water.to_numpy(float)
res = dict(
    ai_capacity_minus_pop=diff(eh, ep.planned_it_mw.to_numpy(float), ch, cw),
    ai_count_minus_pop=diff(eh, np.ones(len(ep)), ch, cw),
    fleet_minus_pop=diff(pdb.high_water.to_numpy(float), np.ones(len(pdb)), ch, cw),
)
# US only
cu = cities[cities.gid_0 == "USA"]; eu = ep[ep.gid_0 == "USA"]; pu = pdb[pdb.gid_0 == "USA"]
res["us_ai_capacity_minus_us_pop"] = diff(eu.high_water.to_numpy(float), eu.planned_it_mw.to_numpy(float),
                                          cu.high_water.to_numpy(float), cu.pop_max.to_numpy(float))
res["us_fleet_minus_us_pop"] = diff(pu.high_water.to_numpy(float), np.ones(len(pu)),
                                    cu.high_water.to_numpy(float), cu.pop_max.to_numpy(float))

# Carbon, US: fixed national references
st = sa.st
US_AVG = float(st[st.state_code == "US"].intensity_g_per_kwh.iloc[0])
w = eu.planned_it_mw.to_numpy(float); c = eu.grid_ci.to_numpy(float)
gen = st[st.state_code != "US"]
gen_above = gen.loc[gen.intensity_g_per_kwh > US_AVG, "generation_twh"].sum() / gen.generation_twh.sum()
bm, ba = [], []
for _ in range(NB):
    i = RNG.integers(0, len(w), len(w))
    bm.append((c[i] * w[i]).sum() / w[i].sum() - US_AVG)
    ba.append((w[i] * (c[i] > US_AVG)).sum() / w[i].sum() - gen_above)
bm, ba = np.array(bm), np.array(ba)
res["us_ai_grid_minus_us_avg_g"] = dict(point=float((c * w).sum() / w.sum() - US_AVG),
                                        ci=[float(np.percentile(bm, 2.5)), float(np.percentile(bm, 97.5))],
                                        share_below_zero=float((bm < 0).mean()))
res["us_ai_share_above_minus_gen_share"] = dict(point=float((w * (c > US_AVG)).sum() / w.sum() - gen_above),
                                                ci=[float(np.percentile(ba, 2.5)), float(np.percentile(ba, 97.5))],
                                                share_below_zero=float((ba < 0).mean()))

# Import sensitivity: shrink each state's intensity towards the US average by
# a fraction lam (a crude stand-in for interstate trade pooling electricity).
res["import_shrinkage_us_ai_mean"] = {str(lam): float(((1 - lam) * c + lam * US_AVG) @ w / w.sum())
                                       for lam in (0.0, 0.25, 0.5, 0.75)}
res["nb"] = NB; res["seed"] = 20261026
json.dump(res, open("results/results_difference.json", "w"), indent=1)
for k, v in res.items():
    print(k, v)
