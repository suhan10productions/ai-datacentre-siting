"""Time trend: are AI campuses that started construction more recently sited
differently from earlier ones? Splits Epoch sites by the date of the first
entry in their timeline (usually land clearing) and compares water stress and,
for US sites, grid carbon intensity. Writes results_trend.json."""
import importlib.util
import json
import sys

import numpy as np

spec = importlib.util.spec_from_file_location("sa", "siting_analysis.py")
sa = importlib.util.module_from_spec(spec)
sys.argv = ["sa"]
spec.loader.exec_module(sa)

rng = np.random.default_rng(7)
NB = 5000
CUT = "2024-01-01"

ep = sa.ep.copy()
ep["late"] = ep["first_date"] >= CUT


def wavg(d, col, w):
    return float((d[col] * d[w]).sum() / d[w].sum()) if w else float(d[col].mean())


def boot_diff(a, b, col, w):
    """Bootstrap of (late - early), resampling sites within each group."""
    out = []
    for _ in range(NB):
        aa = a.iloc[rng.integers(0, len(a), len(a))]
        bb = b.iloc[rng.integers(0, len(b), len(b))]
        out.append(wavg(bb, col, w) - wavg(aa, col, w))
    return [float(x) for x in np.percentile(out, [2.5, 97.5])]


def boot_ci(d, col, w):
    vals = [wavg(d.iloc[rng.integers(0, len(d), len(d))], col, w) for _ in range(NB)]
    return [float(x) for x in np.percentile(vals, [2.5, 97.5])]


def compare(df, col, w):
    early, late = df[~df.late], df[df.late]
    return dict(
        early=dict(n=len(early), value=wavg(early, col, w), ci=boot_ci(early, col, w),
                   planned_gw=float(early.planned_it_mw.sum() / 1000)),
        late=dict(n=len(late), value=wavg(late, col, w), ci=boot_ci(late, col, w),
                  planned_gw=float(late.planned_it_mw.sum() / 1000)),
        diff=wavg(late, col, w) - wavg(early, col, w),
        diff_ci=boot_diff(early, late, col, w),
    )


us = ep[ep.gid_0 == "USA"]
R = dict(
    cut=CUT,
    n_missing_date=int(ep.first_date.isna().sum()),
    water_planned=compare(ep, "high_water", "planned_it_mw"),
    water_count=compare(ep, "high_water", None),
    us_carbon_planned=compare(us, "grid_ci", "planned_it_mw"),
    us_carbon_count=compare(us, "grid_ci", None),
    first_year_counts={str(k): int(v) for k, v in ep.first_date.dt.year.value_counts().sort_index().items()},
)

if __name__ == "__main__":
    json.dump(R, open("results/results_trend.json", "w"), indent=1)
    for k in ("water_planned", "water_count", "us_carbon_planned", "us_carbon_count"):
        r = R[k]
        print(k, "early n=%d %.3f %s | late n=%d %.3f %s | diff %.3f %s" % (
            r["early"]["n"], r["early"]["value"], [round(x, 3) for x in r["early"]["ci"]],
            r["late"]["n"], r["late"]["value"], [round(x, 3) for x in r["late"]["ci"]],
            r["diff"], [round(x, 3) for x in r["diff_ci"]]))
    print("missing dates", R["n_missing_date"], R["first_year_counts"])
    print("GW early/late", R["water_planned"]["early"]["planned_gw"], R["water_planned"]["late"]["planned_gw"])
