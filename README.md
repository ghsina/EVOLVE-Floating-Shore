# EVOLVE-Floating-Shore (EVOLVE Planner)

Lowest-cost design of a floating (or bottom-fixed) offshore energy island and its onshore plant, for
electricity, hydrogen or both, on one year of hourly data reduced with topological data analysis (TDA).

**What it sizes:** offshore wind, floating PV, electrolysers (island and onshore), desalination, compressors,
fuel cells, batteries, hydrogen tanks, the export cable (HVAC or HVDC by route length) and the hydrogen
pipeline (new or repurposed classes).
**What it delivers:** capacities, annualised costs, revenues, the levelized cost of electricity (LCOE) and of
hydrogen (LCOH) with a component breakdown, the 8,760-hour operation, and three drawings generated from every
design:

- **Route section** – side view from the island down the export cable and pipeline, through the landfall,
  to the onshore plant (only what was built is drawn).
- **Island** – isometric view of the platform with the sized equipment laid out on the deck to scale, and
  the deck area used.
- **Connection atlas** – a chart of the site drawn from the real coastline (1 km GLOBE land mask in
  `assets/landmask_120.npz`), with the wind-farm zone, sea routes around islands and headlands, the grid
  and hydrogen points, waterlines, graticule, scale bar and legend.

## Connections to existing infrastructure

The island can export power through its own cable to the onshore grid point, or through a short cable to a
nearby offshore substation or cable with spare capacity (MW), a voltage (kV) and an access fee; hydrogen can
leave through its own pipeline or tie into a nearby pipeline with spare capacity (kg/h) and an operating
pressure. With "let the model choose" every combination is sized on the reduced year and the cheapest is
checked on the full year. The export voltage (66–275 kV AC, 320 or 525 kV DC) sets the rating per circuit and
the number of circuits reported.

## Route lengths and connection points

The island, grid point, hydrogen offtake, hub and tie-in are coordinates you enter; the app does not look up
substations or pipelines in a database. From those coordinates it measures each route in one of three ways
(Site step, "How route lengths are found"):

1. **Sea route** (default): shortest path through the sea on the bundled 1 km coastline, around islands and
   headlands, to the coast nearest the onshore point, plus a straight onshore leg. Large areas are coarsened so a
   route across a whole sea takes about a second.
2. **Straight line × routing factor** (1.1–1.3 typical).
3. **Entered length**: a cable or pipeline length from a route study replaces both.

The Site step shows the length used and how it was found, the nearest coast to the island (with buttons to put
the grid point or offtake there as a first guess), and links to OpenInfraMap, EMODnet Human Activities and the
ENTSO-E grid map to find real substations, cables and pipelines. The voltage, HVAC/HVDC choice, cable cost and
losses follow from the length.

## Interactive map

Before a run the map shows what the model will assume: the island and sea area, every candidate link with the
length it measures, and hub or tie-in points. After a run it shows what was built: turbines in the sea area, the
export cable and pipeline with widths proportional to MW and peak kg/h, voltage and circuits, and the existing
links of a hub or pipeline, with tooltips. The coastline is drawn from the bundled mask, so the map reads even if
the basemap cannot load.

## LCOE and LCOH

Annual cost (annualised investment + O&M + fees) is split between the two products: hydrogen-only equipment
to hydrogen, fuel cells to electricity, and shared assets (wind, PV, cable, platform, batteries, fees) in
proportion to the electricity each product uses (power to the grid vs power to the electrolysers).
LCOE = electricity share / MWh delivered; LCOH = hydrogen share / kg delivered.

## How a run works

1. **Reduce.** The cumulative surplus-and-deficit curve of each hourly series is analysed with 0-dimensional
   persistent homology. Persistent extrema (deep lulls, long surpluses) become fixed cuts; neighbouring hours are
   merged where the curve stays within a chord error. Default: 1,460 variable-length blocks.
2. **Size.** A Pyomo capacity-expansion LP is solved on the blocks, with storage tracked across the whole
   year (min/max-bounded state of charge). Pipeline classes are handled exactly.
3. **Check.** The design is operated on all 8,760 hours. If an hour falls short, capacities are scaled by the
   smallest group factor that delivers every contract and the year is re-optimised.

In the Step 2 tests (Belle-Île, 2019 and 2024, three cases) the cost stayed within 0.3 % of the full-year
optimum and every contract was delivered.

## Run it on your computer

```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

GLPK is optional (`packages.txt` installs it on Streamlit Cloud; locally `apt install glpk-utils` or
`conda install glpk`). HiGHS is installed with `highspy` and is the default.

## Inputs

Everything can be typed in the app (every number has − and + buttons; the Technologies step lists every
cost and performance input, and the Run step lists every input of the run with what the model derives) or loaded from one Excel workbook (sidebar, "Open an inputs workbook").
The workbook has an `Inputs` sheet (one row per parameter, edit the `value` column) and a `TimeSeries` sheet
with one calendar year: `wind_cf`, `pv_cf` (0–1), `price_eur_mwh`, `elec_demand_mw`, `h2_demand_kgh` (the last
two only for profile delivery). Hourly files have 8,760 rows; 30, 15, 10 and 5-minute files are averaged to
hours, and a leap year loses 29 February.

`examples/EVOLVE_data_guide.xlsx` (also downloadable from the app's sidebar) lists every series and input,
the file format and resolution, and where to get the data.

Without files, the app can download wind and solar capacity factors from ERA5 (Open-Meteo archive API) and
day-ahead prices from Energy-Charts (Fraunhofer ISE) for the island coordinates.

Cost values flagged "placeholder" will be replaced with referenced values in Step 3.

## Repository layout

```
app.py                      Streamlit app (wizard: Site, Use case, Data, Technologies, Run, Results)
evolve_planner/
  params.py                 every input: label, unit, default, help; derived quantities
  tda.py                    topology-preserving chronological aggregation (TPCA)
  timestructure.py          variable-length time steps
  model.py                  Pyomo capacity-expansion model
  workflow.py               reduce -> size -> check on the full year
  weather.py                uploads, ERA5 and price downloads, CF conversion
  workbook.py, report.py    input and results workbooks
  geo.py                    coastline, sea routes, nearest shore (1 km land mask)
ui/                         theme, Plotly charts, interactive map (livemap.py), drawings (atlas, isometric, section)
assets/landmask_120.npz     1 km land/water grid for the atlas (GLOBE via global-land-mask, bit-packed)
examples/                   data guide, blank inputs workbook; belle_ile/ has 2019 and 2024 series and presets
tests/                      TDA properties and an end-to-end check
```

## Tests

```bash
pip install pytest
pytest -q                 # about one minute
```

## Hosting

Streamlit Community Cloud: connect the GitHub repository, main file `app.py`, Python 3.12. The free tier
has limited memory; the app runs one solve at a time and queues the next. For heavier use, the `Dockerfile`
runs the same app on any server: `docker build -t evolve-planner . && docker run -p 8501:8501 evolve-planner`.
