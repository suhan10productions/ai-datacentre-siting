# Replication package: water-stress and grid-carbon exposure of AI data centres

Code and data behind the paper *Water-Stress and Grid-Carbon Exposure of New AI
Data Centre Capacity against Population and Grid Benchmarks, with Emissions
Projected to 2031*
by Suhan Ali (2026).

Every number in the paper's projection model (Sections 3.3 and 4.3-4.4) and
siting analysis (Sections 3.2, 4.1-4.2 and 5.2) can be regenerated from this folder.

## Contents

```
model/                  Projection model, 2031 (Sections 3.3 and 4.3-4.4)
  model.py              Single source for every model number
  model_results.json    Every model number the article quotes
  make_figures.py       Figures 1-5
  build_xlsx.py         Rebuilds the spreadsheet version of the model
  datacentre_model_calculations.xlsx   Same model with live formulas

siting/                 Siting analysis (Sections 3.2 and 4.1-4.2)
  join.py               Spatial join of points to Aqueduct 4.0 sub-basins
  siting_analysis.py    Loads the joined data, assigns grid intensity, core tables
  siting_results.py     Every reported share and average, with bootstrap CIs
  siting_trend.py       Campuses started before 2024 versus since
  siting_screen.py      Illustrative water and carbon screen (Section 5.2)
  siting_coverage.py    Coverage and weighting robustness tests (Section 4.2)
  siting_difference.py  Direct tests of the siting differences and import allowance (Sections 4.1-4.2)
  siting_virginia.py    Consumption-basis check for Virginia (Section 4.2)
  siting_marginal.py    Short-run marginal proxy (eGRID non-baseload), screen variant, leave-one-state-out (Sections 4.2, 5.2)
  siting_lrmer.py       Long-run marginal emission rates (NREL Cambium 2023), screen variant (Sections 4.2, 5.2)
  siting_watergap.py    Water benchmark on Rosa et al.'s monthly water-gap metric, today and at 3 C (Section 4.1)
  siting_watergap_robust.py  Water-gap comparison by climate model, model agreement, 1.5 C and 3x3 neighbourhood (Section 4.1, S3)
  siting_lrmer_regional.py   Long-run screen with relocation only within each interconnection (Section 5.2, S3)
  siting_grid.py        Grid intensity where capacity sits, for the projection variant (Section 4.4)
  siting_figures.py     Figures 6 and 7
  data/                 Inputs (see Sources below)
  results/              Outputs as reported in the paper
```

## How to reproduce

Python 3.10 or later with pandas, numpy, matplotlib and geopandas
(`pip install pandas numpy matplotlib geopandas openpyxl`).

```
cd model
python model.py             # prints every model figure
python make_figures.py      # writes figs/fig1-5

cd ../siting
python siting_results.py    # writes results/results_final.json (about 4 minutes)
python siting_trend.py      # writes results/results_trend.json
python siting_grid.py       # writes results/results_grid.json
python siting_screen.py     # writes results/results_screen.json
python siting_difference.py # writes results/results_difference.json (run before siting_coverage.py)
python siting_coverage.py   # writes results/results_coverage.json
python siting_virginia.py   # writes results/results_virginia_imports.json
python siting_marginal.py   # writes results/results_marginal.json
python siting_lrmer.py      # writes results/results_lrmer.json (needs data/ext files, below)
python siting_watergap.py   # writes results/results_watergap.json (needs data/ext files, below)
python siting_watergap_robust.py  # writes results/results_watergap_robust.json
python siting_lrmer_regional.py   # writes results/results_lrmer_regional.json
python siting_figures.py    # writes figs/fig6-7
```

Bootstrap intervals use fixed random seeds, so results repeat exactly.

`data/` contains the Epoch AI and Natural Earth points already joined to
Aqueduct. **PeeringDB facility records are not included**, because PeeringDB's
Acceptable Use Policy does not allow bulk redistribution without permission.
Download them with `python fetch_peeringdb.py data/peeringdb_fac.csv`, then
download the Aqueduct 4.0 baseline annual geodatabase (link below) and run:

```
python join.py <path to Aqueduct40_baseline.gdb> data data/peeringdb_fac.csv <natural earth populated places> data/epoch_coords.csv
```

`data/ext/` holds the water-gap grids (baseline, 1.5 C and 3 C averages, and the five 3 C model runs) (Rosa and Sangiorgio 2025, CC BY 4.0,
https://zenodo.org/records/14882216). Three further public files are not
redistributed here and should be downloaded into `data/ext/` before running
`siting_lrmer.py` and `siting_watergap.py`:

- `Cambium23_LRMER_GEAregions.xlsx`: NREL Cambium 2023 long-run marginal
  emission rate workbook, https://data.nrel.gov/submissions/230 (DOI 10.7799/2305481)
- `counties.json`: US county boundaries,
  https://raw.githubusercontent.com/plotly/datasets/master/geojson-counties-fips.json
- `ne_places.geojson`: Natural Earth populated places,
  https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_10m_populated_places_simple.geojson

To download exactly the PeeringDB facility set used in the paper, run
`python fetch_peeringdb.py data/peeringdb_fac.csv --ids data/peeringdb_ids_2026-10-14.csv`.

See `DATA_DICTIONARY.md` for every file and field, and the electronic
supplementary material of the paper for the assumptions behind each test.

## Method in brief

- **Projection.** Eqs. (1)-(5) of the paper. The model is first run for 2025
  and calibrated to the IEA's estimate of 2025 use (factor 0.628, Eq. 5); the
  uncalibrated model is the high case. `model.py` also runs the Monte Carlo
  analysis (100,000 draws, fixed seed). The `Calibration` sheet of the
  spreadsheet shows every step of the calibration.
- **Locations.** PeeringDB facility registry (5,254 facilities with
  coordinates and water data, 140 countries, accessed 14 October 2026) and
  Epoch AI's Frontier Data Centers database (94 large AI campuses, 37.7 GW of
  planned IT capacity).
- **Water stress.** Each point takes the baseline water stress of its
  Aqueduct 4.0 sub-basin. "High" means the high or extremely high category
  (withdrawals above 40% of renewable supply).
- **Grid carbon.** 2024 average generation intensity on Ember's lifecycle
  basis: US states from Ember's US data, other countries from Ember via Our
  World in Data. Marginal proxy for US campuses: EPA eGRID2023 non-baseload
  CO2 rates by subregion (hard-coded in `siting_marginal.py` with the source).
- **Reference for water.** Natural Earth populated places, weighted by urban
  population.
- **Uncertainty.** 95% bootstrap intervals from 5,000 resamples.

## Sources and licences

| Data | Source | Licence |
|---|---|---|
| Facility locations | PeeringDB, https://www.peeringdb.com | PeeringDB terms of use |
| Large AI campuses | Epoch AI, Frontier Data Centers, https://epoch.ai/data/data-centers | CC BY 4.0 |
| Water stress | WRI Aqueduct 4.0 (Kuzma et al., 2023), https://www.wri.org/data/aqueduct-global-maps-40-data | CC BY 4.0 |
| US state grid intensity | Ember, US Electricity Data, https://ember-energy.org/data/us-electricity-data/ | CC BY 4.0 |
| Country grid intensity | Our World in Data energy dataset (Ember), https://github.com/owid/energy-data | CC BY 4.0 |
| US marginal emission rates (short-run) | EPA eGRID2023 summary tables, https://www.epa.gov/egrid/summary-data | Public domain (US government) |
| US marginal emission rates (long-run) | NREL Cambium 2023 LRMER workbook (Gagnon, 2024), https://data.nrel.gov/submissions/230 | NREL data terms (not redistributed) |
| Monthly water gap | Rosa and Sangiorgio (2025), https://zenodo.org/records/14882216 | CC BY 4.0 |
| US county boundaries | plotly/datasets (US Census) | Public domain |
| Populated places, country outlines | Natural Earth, https://www.naturalearthdata.com | Public domain |

Third-party data remain under their original licences and should be cited to
their sources. The code in this package is released under the MIT licence
(see LICENSE).

## Citation

See CITATION.cff. Please cite the paper and this package.
