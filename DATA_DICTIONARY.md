# Data dictionary

All files are UTF-8 CSV unless stated. Water-stress fields come from WRI
Aqueduct 4.0 (baseline annual layer); grid fields from Ember (US states) and
Our World in Data / Ember (countries), 2024, lifecycle gCO2e/kWh.

## Inputs (`siting/data/`)

| File | Source and licence | Contents |
|---|---|---|
| `peeringdb_water.csv` | **Not included** (PeeringDB Acceptable Use Policy). Recreate with `fetch_peeringdb.py` then `join.py`. | One row per PeeringDB facility, with the Aqueduct fields below |
| `epoch_data_centers.csv` | Epoch AI, Frontier Data Centers (CC BY 4.0) | One row per campus: name, owner, location, current power (MW) |
| `epoch_data_center_timelines.csv` | Epoch AI (CC BY 4.0) | Dated timeline entries per campus, including IT power (MW) |
| `epoch_coords.csv` | Derived from Epoch AI | Campus identifier, latitude, longitude |
| `epoch_water.csv` | Epoch coordinates joined to Aqueduct 4.0 (CC BY 4.0) | Aqueduct fields below, per campus |
| `cities_water.csv` | Natural Earth populated places (public domain) joined to Aqueduct | name, country, `pop_max` (urban population), Aqueduct fields |
| `ember_us_states_2024.psv` | Ember, US Electricity Data (CC BY 4.0); pipe-separated | `state_code`, `generation_twh`, `intensity_g_per_kwh` (US row = national) |
| `owid-energy-data.csv` | Our World in Data energy dataset (CC BY 4.0) | `country`, `year`, `iso_code`, `carbon_intensity_elec` (gCO2e/kWh), `electricity_generation` (TWh) |
| `ne_110m_countries.geojson` | Natural Earth (public domain) | Country outlines for the map |

### Aqueduct fields (added by `join.py`)

| Field | Meaning |
|---|---|
| `string_id`, `pfaf_id` | Aqueduct sub-basin identifiers |
| `gid_0`, `name_0`, `name_1` | Country ISO3 code, country name, first-level region |
| `bws_raw` | Baseline water stress: withdrawals / available renewable supply |
| `bws_score` | Aqueduct 0-5 score |
| `bws_cat` | Category: -1 arid / low water use, 0 low (<10%), 1 low-medium (10-20%), 2 medium-high (20-40%), 3 high (40-80%), 4 extremely high (>80%) |
| `bws_label` | Text label of the category |
| `matched` | `within` (inside a polygon), `nearest` (within 0.1 degrees), `none` (dropped) |

"High water stress" in the paper means `bws_cat >= 3`.

## Results (`siting/results/`)

| File | Contents |
|---|---|
| `results_final.json` | Every share and average in Sections 4.1-4.2 with 95% bootstrap CIs (sampling uncertainty only) |
| `results_marginal.json` | Marginal-emissions proxy for US campuses (eGRID non-baseload rates): campus versus US rate, screen variants, 95% bootstrap CIs |
| `results_lrmer.json` | Long-run marginal rates (Cambium 2023, levelised 2027-2046, 3%): campus vs population reference, screen variants by scenario, bootstrap CIs, leave-one-state-out |
| `results_watergap.json` | Shares exposed to a monthly water gap (Rosa and Sangiorgio 2025 grid), baseline and 3 C, with joint-bootstrap differences |
| `results_watergap_robust.json` | Water-gap comparison by climate model, agreement threshold, 1.5 C and 3x3 neighbourhood, with joint-bootstrap intervals; main-text table values for 3-of-5 agreement |
| `results_lrmer_regional.json` | Long-run screen with within-interconnection relocation, by scenario, with bootstrap interval |
| `data/ext/water_gap_*.nc` | Annual water gap grids (km3/yr, negative = gap), 0.5 degree |
| `data/peeringdb_ids_2026-10-14.csv` | PeeringDB facility IDs used in the paper (IDs only) |
| `results_shares.csv` | Same shares in table form: sample, measure, weight, n, share, ci_lo, ci_hi |
| `results_epoch_sites.csv` | Per campus: name, owner, country, state, `bws_label`, `bws_cat`, `grid_ci`, `high_water`, `high_carbon` (above world average), `current_mw`, `planned_it_mw` |
| `results_pdb_by_country.csv` | Aggregates by country: `gid_0`, `n`, share in high stress, mean grid intensity |
| `results_trend.json` | Campuses started before 2024 versus since |
| `results_grid.json` | Grid intensity where capacity sits, as a ratio to the world average |
| `results_screen.json` | Illustrative screen: pass shares, threshold grid, conditional emissions scenario |
| `results_difference.json` | Joint-bootstrap tests of each siting difference, and the import allowance |
| `results_virginia_imports.json` | Virginia consumption-basis estimate and its effect on the campus average |
| `results_coverage.json` | Coverage and weighting tests, with their assumptions stated in the `assumptions` field |
| `results_within_us.json` | US-only comparisons |

## Model (`model/`)

| File | Contents |
|---|---|
| `model.py` | Every projection number; `python model.py` prints them |
| `model_results.json` | All model outputs, including Monte Carlo, calibration alternatives, assumption alternatives and criterion 1 margins |
| `datacentre_model_calculations.xlsx` | The same model with live formulas (sheets: Inputs, Utilisation, Calibration, Results) |
