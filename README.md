# HappyMonkey Site Selection App

This project implements the workflow from:
- `快乐猴 RDC 候选点生成全流程.docx`
- `快乐猴社区超市联合选址优化模型.docx`

It contains a Python backend and a browser UI for end-to-end analysis.

## Model Pipeline

1. Stage 1: single block screening
- Compute 5-year NPV and discounted payback period (DPP)
- Apply hard gates from the document:
  - `NPV >= threshold` (Beijing 25, Hangzhou 28, default 30; unit: 10k CNY)
  - `DPP <= 2.5 years`
  - `revenue per sqm >= 1.2` (10k CNY per sqm)

2. Stage 2: new-store cannibalization optimization
- Distance rule:
  - `<300m`: cannot open together
  - `300m-500m`: attenuation penalty
- Enumerate combinations up to `max_new_stores`, maximize adjusted total NPV

3. Stage 3: RDC + store joint optimization (P-median style)
- Filter RDCs with hard constraints (truck access, clear height, fire, three-temp, lease term, rent cap, etc.)
- For each scenario `P` (e.g. `1,2,3`):
  - choose `P` RDCs
  - assign every store to one opened RDC
  - minimize `RDC lifecycle cost + discounted delivery cost`

## Quick Start

```bash
python3 -m pip install -r requirements.txt
python3 main.py
```

Open `http://127.0.0.1:5000` in your browser.

## Input CSV Format

### 1) stores.csv (required)

Required columns:
- `store_id`
- `name`
- `city`
- `lat`
- `lon`
- `rf_sales_10k`
- `area_sqm`
- `initial_investment_10k`
- `annual_fixed_cost_10k`
- `is_existing` (1/0)

Notes:
- Existing stores use `is_existing=1` and are forced into stage-3 network.
- New candidates use `is_existing=0` and pass through stage-1 and stage-2.

### 2) rdcs.csv (required)

Required columns:
- `rdc_id,name,city,lat,lon,area_sqm`
- `initial_investment_10k`
- `annual_rent_10k,annual_property_10k,annual_operating_10k,annual_labor_10k,annual_utility_10k`
- `residual_rate`
- `rent_per_sqm_day,lease_years`
- `blue_access,core_travel_min,clear_height_m,loading_dock,can_three_temp,fire_pass,disturbance_risk`

### 3) distances.csv (optional)

Columns:
- `rdc_id,store_id,distance_km`

If omitted for a pair, the model uses haversine distance from lat/lon.

## Sample Data

Files in `sample_data/`:
- `stores.csv`
- `rdcs.csv`
- `distances.csv`

You can run them directly from the UI via "Run Sample Data".
