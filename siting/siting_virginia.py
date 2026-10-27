"""Consumption-basis check for Virginia (Section 4.5). Virginia imported 36% of
its electricity in 2023 (EIA). Assuming imports match the generation-weighted
average of the other full PJM member states (PA, NJ, MD, DE, WV, OH, DC;
Ember 2024, lifecycle), estimate Virginia's consumption intensity and its
effect on the capacity-weighted average of the US AI campuses."""
import json
import pandas as pd
st = pd.read_csv("data/ember_us_states_2024.psv", sep="|")
pjm = st[st.state_code.isin(["PA", "NJ", "MD", "DE", "WV", "OH", "DC"])]
avg = (pjm.generation_twh * pjm.intensity_g_per_kwh).sum() / pjm.generation_twh.sum()
va = float(st[st.state_code == "VA"].intensity_g_per_kwh.iloc[0])
va_cons = 0.64 * va + 0.36 * avg
e = pd.read_csv("results/results_epoch_sites.csv")
us = e[(e.name_0 == "United States") & (e.planned_it_mw > 0)].copy()
w = us.planned_it_mw
base = (us.grid_ci * w).sum() / w.sum()
us.loc[us.name_1 == "Virginia", "grid_ci"] = va_cons
new = (us.grid_ci * w).sum() / w.sum()
out = dict(pjm_ex_va=avg, va_production=va, va_consumption_est=va_cons, campus_avg_base=base,
           campus_avg_va_corrected=new, va_share_planned=float(w[us.name_1 == "Virginia"].sum() / w.sum()))
json.dump(out, open("results/results_virginia_imports.json", "w"), indent=1)
print(out)
