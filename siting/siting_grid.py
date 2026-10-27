"""Grid intensity where data centre capacity sits, for the projection's
grid-carbon sensitivity (Section 3.2). Ember lifecycle basis, 2024.

Fleet: PeeringDB facilities, one per site (deduplicated ~1 km), unweighted.
New capacity: Epoch AI campuses weighted by planned IT capacity.
Both expressed as a ratio to the world average, so they can be applied to
the IEA-basis grid values used in the projection.
"""
import json
import numpy as np
import siting_analysis as sa

RNG = np.random.default_rng(20261024)
NB = 5000
world = sa.world_ci
f = sa.pdb_dedup.dropna(subset=["grid_ci"])
e = sa.ep.dropna(subset=["grid_ci"])
e = e[e.planned_it_mw > 0]


def wmean(x, w=None):
    return float(np.average(x, weights=w))


def boot(x, w=None):
    x = np.asarray(x); w = None if w is None else np.asarray(w)
    out = []
    for _ in range(NB):
        i = RNG.integers(0, len(x), len(x))
        out.append(np.average(x[i], weights=None if w is None else w[i]))
    return [float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5))]


fleet = wmean(f.grid_ci); fleet_ci = boot(f.grid_ci)
new = wmean(e.grid_ci, e.planned_it_mw); new_ci = boot(e.grid_ci, e.planned_it_mw)
out = dict(world_ember=world, n_fleet=int(len(f)), n_new=int(len(e)),
           fleet_mean=fleet, fleet_ci=fleet_ci, fleet_ratio=fleet / world,
           new_mean=new, new_ci=new_ci, new_ratio=new / world)
json.dump(out, open("results/results_grid.json", "w"), indent=1)
print(json.dumps(out, indent=1))
