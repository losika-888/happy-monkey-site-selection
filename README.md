# HappyMonkey Site Selection App

个人运筹优化的算法学习。

This project implements the workflow from:
- `快乐猴 RDC 候选点生成全流程.docx`
- `快乐猴社区超市联合选址优化模型.docx`

It contains a Python backend and a browser UI for end-to-end analysis.
The frontend follows `快乐猴选址展示前端系统设计方案.docx` with:
- Parameter panel (city switch + thresholds + P stepper)
- GIS canvas timeline (stage1/stage2/stage3 map views)
- Finance & network dashboard (RDC vs delivery cost split)

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
- Enforce same-city assignment (`beijing` stores only served by `beijing` RDCs, likewise for `hangzhou`)
- For each scenario `P` (e.g. `1,2,3`):
  - choose `P` RDCs
  - assign every store to one opened RDC
  - minimize `RDC lifecycle cost + discounted delivery cost`

## Quick Start

```bash
python3 -m pip install -r requirements.txt
python3 main.py
```

Open `http://43.133.46.51:5001` in your browser.

## GIS Features

- City map switch: Beijing / Hangzhou / combined
- Stage-1 map: pass/fail points with popup cashflow sparkline
- Stage-2 map: selected new stores + 300m / 500m rings
- Stage-3 map: RDC-store assignment lines for the best scenario
- Inner-ring hard alert:
  - Beijing: approximate 5th-ring policy circle
  - Hangzhou: approximate ring-expressway policy circle
- Custom RDC pinning: click map to add candidate RDC points (outside hard-red zone)
- Optional real road-distance mode:
  - Enable `use_road_distance`
  - Fill `amap_key`
  - Backend calls AMap distance API and uses driving distance matrix

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

## Optional APIs

- `GET /api/cities`: city GIS + default parameter metadata
- `POST /api/validate-rdc-point`: validate custom RDC point against inner-ring hard constraint

## Sample Data

Files in `sample_data/`:
- `stores.csv`
- `rdcs.csv`
- `distances.csv`

You can run them directly from the UI via "Run Sample Data".
