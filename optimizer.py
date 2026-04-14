from __future__ import annotations

import itertools
import math
from dataclasses import dataclass, asdict
from typing import Dict, Iterable, List, Optional, Sequence, Tuple


CITY_PARAMS: Dict[str, Dict[str, object]] = {
    "beijing": {
        "horizon_years": 5,
        "discount_rate": 0.12,
        "gross_margin": 0.21,
        "variable_cost_rate": 0.045,
        "tax_rate": 0.025,
        "store_residual_rate": 0.15,
        "growth": [0.9, 1.0, 1.08, 1.12, 1.12],
        "delivery_freq": 104,
        "delivery_fixed_cost": 120.0,
        "delivery_var_cost_km": 3.5,
        "standard_store_sales_10k": 800.0,
        "npv_threshold_10k": 25.0,
        "dpp_threshold_years": 2.5,
        "revenue_per_sqm_threshold_10k": 1.2,
        "rent_cap_per_sqm_day": 1.8,
        "wacc": 0.12,
    },
    "hangzhou": {
        "horizon_years": 5,
        "discount_rate": 0.11,
        "gross_margin": 0.22,
        "variable_cost_rate": 0.042,
        "tax_rate": 0.025,
        "store_residual_rate": 0.15,
        "growth": [0.9, 1.0, 1.08, 1.12, 1.12],
        "delivery_freq": 104,
        "delivery_fixed_cost": 110.0,
        "delivery_var_cost_km": 3.2,
        "standard_store_sales_10k": 800.0,
        "npv_threshold_10k": 28.0,
        "dpp_threshold_years": 2.5,
        "revenue_per_sqm_threshold_10k": 1.2,
        "rent_cap_per_sqm_day": 1.5,
        "wacc": 0.11,
    },
}

DEFAULT_CITY_PARAMS = {
    "horizon_years": 5,
    "discount_rate": 0.115,
    "gross_margin": 0.215,
    "variable_cost_rate": 0.043,
    "tax_rate": 0.025,
    "store_residual_rate": 0.15,
    "growth": [0.9, 1.0, 1.08, 1.12, 1.12],
    "delivery_freq": 104,
    "delivery_fixed_cost": 115.0,
    "delivery_var_cost_km": 3.35,
    "standard_store_sales_10k": 800.0,
    "npv_threshold_10k": 30.0,
    "dpp_threshold_years": 2.5,
    "revenue_per_sqm_threshold_10k": 1.2,
    "rent_cap_per_sqm_day": 1.7,
    "wacc": 0.115,
}

CITY_GIS_META: Dict[str, Dict[str, object]] = {
    "beijing": {
        "label": "北京",
        "center": [39.9042, 116.4074],
        "zoom": 10.6,
        "inner_ring_radius_km": 15.5,
        "inner_ring_name": "五环内近似圈",
        "inner_ring_warning": "违反VV通行蓝区硬指标，该区域禁止蓝牌VV白天通行。",
        "logistics_belts": [
            {"name": "马驹桥物流带", "lat": 39.78, "lon": 116.57, "radius_km": 6.0},
            {"name": "大兴京南物流带", "lat": 39.73, "lon": 116.35, "radius_km": 6.2},
            {"name": "顺义空港物流带", "lat": 40.12, "lon": 116.63, "radius_km": 5.4},
        ],
    },
    "hangzhou": {
        "label": "杭州",
        "center": [30.2741, 120.1551],
        "zoom": 10.8,
        "inner_ring_radius_km": 12.0,
        "inner_ring_name": "绕城内近似圈",
        "inner_ring_warning": "违反VV通行蓝区硬指标，该区域禁止蓝牌VV白天通行。",
        "logistics_belts": [
            {"name": "余杭仁和物流带", "lat": 30.44, "lon": 120.04, "radius_km": 5.5},
            {"name": "萧山传化物流带", "lat": 30.16, "lon": 120.32, "radius_km": 5.2},
            {"name": "下沙综合物流带", "lat": 30.31, "lon": 120.37, "radius_km": 4.8},
        ],
    },
}


def normalize_city(city: str) -> str:
    city = (city or "").strip().lower()
    aliases = {
        "bj": "beijing",
        "beijing": "beijing",
        "北京": "beijing",
        "hz": "hangzhou",
        "hangzhou": "hangzhou",
        "杭州": "hangzhou",
    }
    return aliases.get(city, city)


def city_params(city: str) -> Dict[str, object]:
    key = normalize_city(city)
    base = dict(DEFAULT_CITY_PARAMS)
    base.update(CITY_PARAMS.get(key, {}))
    return base


def get_city_configs() -> Dict[str, object]:
    payload: Dict[str, object] = {}
    for key, meta in CITY_GIS_META.items():
        cp = city_params(key)
        payload[key] = {
            "city": key,
            "label": meta["label"],
            "center": list(meta["center"]),
            "zoom": meta["zoom"],
            "inner_ring_radius_km": meta["inner_ring_radius_km"],
            "inner_ring_name": meta["inner_ring_name"],
            "inner_ring_warning": meta["inner_ring_warning"],
            "logistics_belts": list(meta["logistics_belts"]),
            "params": {
                "wacc": cp["wacc"],
                "npv_threshold_10k": cp["npv_threshold_10k"],
                "dpp_threshold_years": cp["dpp_threshold_years"],
                "revenue_per_sqm_threshold_10k": cp["revenue_per_sqm_threshold_10k"],
            },
        }
    return payload


def parse_bool(value: object, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "y", "t", "ok", "pass", "qualified", "合格", "是"}:
        return True
    if text in {"0", "false", "no", "n", "f", "fail", "unqualified", "不合格", "否"}:
        return False
    return default


def to_float(value: object, default: float = 0.0) -> float:
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(",", "")
    if not text:
        return default
    try:
        return float(text)
    except ValueError:
        return default


def is_valid_coord(lat: float, lon: float) -> bool:
    return -90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0 and not (lat == 0 and lon == 0)


@dataclass
class Store:
    store_id: str
    name: str
    city: str
    lat: float
    lon: float
    rf_sales_10k: float
    area_sqm: float
    initial_investment_10k: float
    annual_fixed_cost_10k: float
    is_existing: bool = False


@dataclass
class RDC:
    rdc_id: str
    name: str
    city: str
    lat: float
    lon: float
    area_sqm: float
    initial_investment_10k: float
    annual_rent_10k: float
    annual_property_10k: float
    annual_operating_10k: float
    annual_labor_10k: float
    annual_utility_10k: float
    residual_rate: float
    rent_per_sqm_day: float
    lease_years: float
    blue_access: bool
    core_travel_min: float
    clear_height_m: float
    loading_dock: bool
    can_three_temp: bool
    fire_pass: bool
    disturbance_risk: bool


@dataclass
class Stage1Result:
    store: Store
    yearly_cashflow_10k: List[float]
    npv_10k: float
    dpp_years: Optional[float]
    revenue_per_sqm_10k: float
    passed: bool
    reasons: List[str]


@dataclass
class Stage2StoreResult:
    store: Store
    base_npv_10k: float
    base_sales_10k: float
    attenuation_ratio: float
    adjusted_sales_10k: float
    adjusted_npv_10k: float
    adjusted_dpp_years: Optional[float]


@dataclass
class Assignment:
    store_id: str
    store_name: str
    store_city: str
    demand_sales_10k: float
    rdc_id: str
    rdc_name: str
    rdc_city: str
    store_lat: float
    store_lon: float
    rdc_lat: float
    rdc_lon: float
    distance_km: float
    delivery_cost_pv_10k: float


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371.0
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2.0) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2.0) ** 2
    return radius * (2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a)))


def point_inner_ring_violation(city: str, lat: float, lon: float) -> Dict[str, object]:
    city_key = normalize_city(city)
    meta = CITY_GIS_META.get(city_key)
    if not meta or not is_valid_coord(lat, lon):
        return {"city": city_key, "violation": False, "distance_to_center_km": None}

    center_lat, center_lon = float(meta["center"][0]), float(meta["center"][1])
    radius = float(meta["inner_ring_radius_km"])
    distance = haversine_km(lat, lon, center_lat, center_lon)
    violation = distance <= radius
    return {
        "city": city_key,
        "violation": violation,
        "distance_to_center_km": round(distance, 4),
        "inner_ring_radius_km": radius,
        "message": meta["inner_ring_warning"] if violation else "ok",
    }


def parse_stores(records: Iterable[Dict[str, object]]) -> List[Store]:
    out: List[Store] = []
    for row in records:
        store_id = str(row.get("store_id") or row.get("id") or "").strip()
        if not store_id:
            continue

        city = normalize_city(str(row.get("city") or "beijing"))
        lat = to_float(row.get("lat"))
        lon = to_float(row.get("lon"))
        out.append(
            Store(
                store_id=store_id,
                name=str(row.get("name") or store_id),
                city=city,
                lat=lat,
                lon=lon,
                rf_sales_10k=to_float(row.get("rf_sales_10k"), to_float(row.get("annual_sales_10k"), 0.0)),
                area_sqm=to_float(row.get("area_sqm"), 100.0),
                initial_investment_10k=to_float(row.get("initial_investment_10k"), 0.0),
                annual_fixed_cost_10k=to_float(row.get("annual_fixed_cost_10k"), 0.0),
                is_existing=parse_bool(row.get("is_existing"), False),
            )
        )
    return out


def parse_rdcs(records: Iterable[Dict[str, object]]) -> List[RDC]:
    out: List[RDC] = []
    for row in records:
        rdc_id = str(row.get("rdc_id") or row.get("id") or "").strip()
        if not rdc_id:
            continue

        city = normalize_city(str(row.get("city") or "beijing"))
        out.append(
            RDC(
                rdc_id=rdc_id,
                name=str(row.get("name") or rdc_id),
                city=city,
                lat=to_float(row.get("lat")),
                lon=to_float(row.get("lon")),
                area_sqm=to_float(row.get("area_sqm"), 10000.0),
                initial_investment_10k=to_float(row.get("initial_investment_10k"), 0.0),
                annual_rent_10k=to_float(row.get("annual_rent_10k"), 0.0),
                annual_property_10k=to_float(row.get("annual_property_10k"), 0.0),
                annual_operating_10k=to_float(row.get("annual_operating_10k"), 0.0),
                annual_labor_10k=to_float(row.get("annual_labor_10k"), 0.0),
                annual_utility_10k=to_float(row.get("annual_utility_10k"), 0.0),
                residual_rate=to_float(row.get("residual_rate"), 0.25),
                rent_per_sqm_day=to_float(row.get("rent_per_sqm_day"), 0.0),
                lease_years=to_float(row.get("lease_years"), 0.0),
                blue_access=parse_bool(row.get("blue_access"), False),
                core_travel_min=to_float(row.get("core_travel_min"), 999.0),
                clear_height_m=to_float(row.get("clear_height_m"), 0.0),
                loading_dock=parse_bool(row.get("loading_dock"), False),
                can_three_temp=parse_bool(row.get("can_three_temp"), False),
                fire_pass=parse_bool(row.get("fire_pass"), False),
                disturbance_risk=parse_bool(row.get("disturbance_risk"), False),
            )
        )
    return out


def parse_distance_matrix(records: Iterable[Dict[str, object]]) -> Dict[Tuple[str, str], float]:
    matrix: Dict[Tuple[str, str], float] = {}
    for row in records:
        rdc_id = str(row.get("rdc_id") or "").strip()
        store_id = str(row.get("store_id") or "").strip()
        if not rdc_id or not store_id:
            continue
        matrix[(rdc_id, store_id)] = to_float(row.get("distance_km"), math.inf)
    return matrix


def compute_dpp(discounted_cashflows: Sequence[float], initial_investment_10k: float) -> Optional[float]:
    cumulative = -initial_investment_10k
    for year, cashflow in enumerate(discounted_cashflows, start=1):
        prev = cumulative
        cumulative += cashflow
        if cumulative >= 0:
            if cashflow <= 0:
                return float(year)
            ratio = (0.0 - prev) / cashflow
            return float(year - 1 + max(0.0, min(1.0, ratio)))
    return None


def evaluate_stage1(
    stores: Sequence[Store],
    threshold_overrides: Optional[Dict[str, Dict[str, float]]] = None,
) -> List[Stage1Result]:
    results: List[Stage1Result] = []
    for store in stores:
        if store.is_existing:
            continue

        cp = city_params(store.city)
        years = int(cp["horizon_years"])
        growth: List[float] = list(cp["growth"])[:years]
        discount_rate = float(cp["discount_rate"])
        gross_margin = float(cp["gross_margin"])
        variable_rate = float(cp["variable_cost_rate"])
        tax_rate = float(cp["tax_rate"])
        residual_rate = float(cp["store_residual_rate"])

        npv_threshold = float(cp["npv_threshold_10k"])
        dpp_threshold = float(cp["dpp_threshold_years"])
        rev_threshold = float(cp["revenue_per_sqm_threshold_10k"])

        if threshold_overrides:
            ov = threshold_overrides.get(normalize_city(store.city))
            if ov:
                npv_threshold = float(ov.get("npv_threshold_10k", npv_threshold))
                dpp_threshold = float(ov.get("dpp_threshold_years", dpp_threshold))
                rev_threshold = float(ov.get("revenue_per_sqm_threshold_10k", rev_threshold))

        yearly_cashflows: List[float] = []
        discounted: List[float] = []
        for idx, g in enumerate(growth, start=1):
            revenue_10k = store.rf_sales_10k * g
            gross_profit_10k = revenue_10k * gross_margin
            variable_cost_10k = revenue_10k * variable_rate
            operating_profit_10k = gross_profit_10k - variable_cost_10k - store.annual_fixed_cost_10k
            tax_10k = max(0.0, operating_profit_10k) * tax_rate
            cashflow_10k = operating_profit_10k - tax_10k
            if idx == years:
                cashflow_10k += store.initial_investment_10k * residual_rate
            yearly_cashflows.append(cashflow_10k)
            discounted.append(cashflow_10k / ((1.0 + discount_rate) ** idx))

        npv_10k = -store.initial_investment_10k + sum(discounted)
        dpp = compute_dpp(discounted, store.initial_investment_10k)

        revenue_per_sqm = 0.0
        if store.area_sqm > 0:
            revenue_per_sqm = store.rf_sales_10k / store.area_sqm

        reasons: List[str] = []
        passed = True
        if npv_10k < npv_threshold:
            passed = False
            reasons.append(f"NPV below threshold ({npv_10k:.2f} < {npv_threshold:.2f})")
        if dpp is None or dpp > dpp_threshold:
            passed = False
            reasons.append(f"DPP exceeds threshold ({dpp_threshold:.2f} years)")
        if revenue_per_sqm < rev_threshold:
            passed = False
            reasons.append(f"Revenue per sqm below threshold ({revenue_per_sqm:.2f} < {rev_threshold:.2f})")

        results.append(
            Stage1Result(
                store=store,
                yearly_cashflow_10k=yearly_cashflows,
                npv_10k=npv_10k,
                dpp_years=dpp,
                revenue_per_sqm_10k=revenue_per_sqm,
                passed=passed,
                reasons=reasons,
            )
        )
    return results


def pairwise_distance_km(stores: Sequence[Stage1Result]) -> Dict[Tuple[str, str], float]:
    dist: Dict[Tuple[str, str], float] = {}
    for i, a in enumerate(stores):
        for b in stores[i + 1 :]:
            key1 = (a.store.store_id, b.store.store_id)
            key2 = (b.store.store_id, a.store.store_id)
            if normalize_city(a.store.city) != normalize_city(b.store.city):
                dist[key1] = math.inf
                dist[key2] = math.inf
                continue
            d = haversine_km(a.store.lat, a.store.lon, b.store.lat, b.store.lon)
            dist[key1] = d
            dist[key2] = d
    return dist


def attenuation_for_pair(distance_km: float) -> float:
    # Hard conflict zone: d < 280m
    # Smooth transition 280-320m: penalty linearly drops from 1.0 -> 0.35
    # Soft zone 320-500m: penalty linearly drops from 0.35 -> 0
    # Beyond 500m: no penalty
    if distance_km < 0.28:
        return 1.0
    if distance_km < 0.32:
        t = (distance_km - 0.28) / 0.04
        return 1.0 + t * (0.35 - 1.0)
    if distance_km < 0.5:
        scaled = (0.5 - distance_km) / 0.18
        return 0.35 * max(0.0, min(1.0, scaled))
    return 0.0


def _recompute_adjusted_cashflows(base_result: Stage1Result, attenuation_ratio: float) -> Tuple[List[float], float]:
    """
    Attenuate operating cashflows by `attenuation_ratio` while keeping residual
    value untouched (residual is asset recovery, not demand-driven).
    Returns (discounted_cashflows, initial_investment).
    """
    cp = city_params(base_result.store.city)
    discount_rate = float(cp["discount_rate"])
    years = len(base_result.yearly_cashflow_10k)
    residual = base_result.store.initial_investment_10k * float(cp["store_residual_rate"])

    discounted: List[float] = []
    for idx, cf in enumerate(base_result.yearly_cashflow_10k, start=1):
        if idx == years:
            adjusted_cf = (cf - residual) * attenuation_ratio + residual
        else:
            adjusted_cf = cf * attenuation_ratio
        discounted.append(adjusted_cf / ((1.0 + discount_rate) ** idx))
    return discounted, base_result.store.initial_investment_10k


def recompute_adjusted_dpp(base_result: Stage1Result, attenuation_ratio: float) -> Optional[float]:
    discounted, initial = _recompute_adjusted_cashflows(base_result, attenuation_ratio)
    return compute_dpp(discounted, initial)


def recompute_adjusted_npv(base_result: Stage1Result, attenuation_ratio: float) -> float:
    discounted, initial = _recompute_adjusted_cashflows(base_result, attenuation_ratio)
    return -initial + sum(discounted)


def optimize_stage2(
    stage1_results: Sequence[Stage1Result],
    max_new_stores: int = 8,
) -> Dict[str, object]:
    candidates = [r for r in stage1_results if r.passed]
    if not candidates:
        return {
            "selected": [],
            "total_adjusted_npv_10k": 0.0,
            "total_base_npv_10k": 0.0,
            "total_investment_10k": 0.0,
            "distance_alerts": [],
        }

    max_new_stores = max(0, min(max_new_stores, len(candidates)))
    dist = pairwise_distance_km(candidates)

    conflict_pairs = set()
    penalty_pairs: Dict[Tuple[str, str], float] = {}
    for a in candidates:
        for b in candidates:
            if a.store.store_id >= b.store.store_id:
                continue
            if normalize_city(a.store.city) != normalize_city(b.store.city):
                continue
            d = dist.get((a.store.store_id, b.store.store_id), math.inf)
            pen = attenuation_for_pair(d)
            if pen >= 1.0:
                conflict_pairs.add((a.store.store_id, b.store.store_id))
            elif pen > 0.0:
                penalty_pairs[(a.store.store_id, b.store.store_id)] = pen

    candidate_by_id = {c.store.store_id: c for c in candidates}
    ids = [c.store.store_id for c in candidates]

    best_score = -math.inf
    best_bundle: Optional[List[Stage2StoreResult]] = None

    def has_conflict(combo_ids: Sequence[str]) -> bool:
        pool = set(combo_ids)
        for a, b in conflict_pairs:
            if a in pool and b in pool:
                return True
        return False

    for size in range(0, max_new_stores + 1):
        for combo in itertools.combinations(ids, size):
            if has_conflict(combo):
                continue

            combo_set = set(combo)
            score = 0.0
            bundle: List[Stage2StoreResult] = []

            for sid in combo:
                base = candidate_by_id[sid]
                penalty = 0.0
                for oid in combo_set:
                    if oid == sid:
                        continue
                    other = candidate_by_id[oid]
                    if normalize_city(other.store.city) != normalize_city(base.store.city):
                        continue
                    key = tuple(sorted((sid, oid)))
                    penalty += penalty_pairs.get(key, 0.0)

                penalty = min(0.45, penalty)
                attenuation_ratio = max(0.0, 1.0 - penalty)
                adjusted_sales = base.store.rf_sales_10k * attenuation_ratio
                # Only operating cashflows are attenuated; initial capex and
                # residual value are invariant to neighboring cannibalization.
                adjusted_npv = recompute_adjusted_npv(base, attenuation_ratio)
                adjusted_dpp = recompute_adjusted_dpp(base, attenuation_ratio)

                score += adjusted_npv
                bundle.append(
                    Stage2StoreResult(
                        store=base.store,
                        base_npv_10k=base.npv_10k,
                        base_sales_10k=base.store.rf_sales_10k,
                        attenuation_ratio=attenuation_ratio,
                        adjusted_sales_10k=adjusted_sales,
                        adjusted_npv_10k=adjusted_npv,
                        adjusted_dpp_years=adjusted_dpp,
                    )
                )

            if score > best_score:
                best_score = score
                best_bundle = bundle

    if best_bundle is None:
        best_bundle = []
        best_score = 0.0

    distance_alerts = []
    for a, b in conflict_pairs:
        da = candidate_by_id[a]
        db = candidate_by_id[b]
        d = dist.get((a, b), 0.0)
        distance_alerts.append(
            {
                "store_a": a,
                "store_b": b,
                "name_a": da.store.name,
                "name_b": db.store.name,
                "city": da.store.city,
                "distance_m": round(d * 1000.0, 1),
                "rule": "distance below 280m, cannot open together",
            }
        )

    total_base = sum(item.base_npv_10k for item in best_bundle)
    total_investment = sum(item.store.initial_investment_10k for item in best_bundle)

    return {
        "selected": [
            {
                "store_id": item.store.store_id,
                "name": item.store.name,
                "city": item.store.city,
                "base_sales_10k": round(item.base_sales_10k, 4),
                "attenuation_ratio": round(item.attenuation_ratio, 4),
                "adjusted_sales_10k": round(item.adjusted_sales_10k, 4),
                "base_npv_10k": round(item.base_npv_10k, 4),
                "adjusted_npv_10k": round(item.adjusted_npv_10k, 4),
                "adjusted_dpp_years": round(item.adjusted_dpp_years, 4) if item.adjusted_dpp_years else None,
                "lat": item.store.lat,
                "lon": item.store.lon,
                "radius_300_m": 300,
                "radius_500_m": 500,
            }
            for item in sorted(best_bundle, key=lambda x: x.adjusted_npv_10k, reverse=True)
        ],
        "total_adjusted_npv_10k": round(best_score, 4),
        "total_base_npv_10k": round(total_base, 4),
        "total_investment_10k": round(total_investment, 4),
        "distance_alerts": sorted(distance_alerts, key=lambda x: x["distance_m"]),
    }


def rdc_lifecycle_cost_10k(rdc: RDC) -> float:
    """
    Present value of RDC 5-year lifecycle cost:
        CapEx + PV(annual OpEx over horizon) - PV(residual at end-of-life)
    Using the same horizon_years and discount_rate as stores for dimensional
    consistency with `delivery_cost_pv_10k`.
    """
    cp = city_params(rdc.city)
    discount_rate = float(cp["discount_rate"])
    years = int(cp["horizon_years"])

    annual = (
        rdc.annual_rent_10k
        + rdc.annual_property_10k
        + rdc.annual_operating_10k
        + rdc.annual_labor_10k
        + rdc.annual_utility_10k
    )
    pv_annual = 0.0
    for y in range(1, years + 1):
        pv_annual += annual / ((1.0 + discount_rate) ** y)

    residual_nominal = rdc.initial_investment_10k * rdc.residual_rate
    pv_residual = residual_nominal / ((1.0 + discount_rate) ** years)

    return rdc.initial_investment_10k + pv_annual - pv_residual


def rdc_eligibility(rdc: RDC) -> Tuple[bool, List[str]]:
    cp = city_params(rdc.city)
    rent_cap = float(cp["rent_cap_per_sqm_day"])

    reasons: List[str] = []
    if not rdc.blue_access:
        reasons.append("[BLUE_ACCESS] blue plate truck access requirement not met")
    if rdc.core_travel_min > 30.0:
        reasons.append(f"[TRAVEL_TIME] core travel time above 30 min ({rdc.core_travel_min:.1f})")
    if rdc.clear_height_m < 6.0:
        reasons.append(f"[CLEAR_HEIGHT] clear height below 6m ({rdc.clear_height_m:.1f})")
    if not rdc.loading_dock:
        reasons.append("[LOADING_DOCK] missing loading dock")
    if not rdc.can_three_temp:
        reasons.append("[THREE_TEMP] cannot support three-temperature warehouse")
    if not rdc.fire_pass:
        reasons.append("[FIRE_SAFETY] fire safety requirement not met")
    if rdc.disturbance_risk:
        reasons.append("[DISTURBANCE] disturbance risk near residential/school/hospital")
    if rdc.rent_per_sqm_day > rent_cap:
        reasons.append(f"[RENT_CAP] rent exceeds city cap ({rdc.rent_per_sqm_day:.2f}>{rent_cap:.2f})")
    if rdc.lease_years < 5.0:
        reasons.append(f"[LEASE_TERM] remaining lease below 5 years ({rdc.lease_years:.1f})")

    # GIS hard warning: inner-ring placements are forbidden by blue-plate policy.
    rule = point_inner_ring_violation(rdc.city, rdc.lat, rdc.lon)
    if rule.get("violation"):
        reasons.append("[INNER_RING] RDC located inside inner-ring restricted zone")

    return (len(reasons) == 0), reasons


def distance_lookup_km(
    rdc: RDC,
    store: Store,
    matrix: Dict[Tuple[str, str], float],
) -> float:
    if normalize_city(rdc.city) != normalize_city(store.city):
        return math.inf

    key = (rdc.rdc_id, store.store_id)
    if key in matrix and math.isfinite(matrix[key]):
        return matrix[key]
    return haversine_km(rdc.lat, rdc.lon, store.lat, store.lon)


def delivery_cost_pv_10k(distance_km: float, sales_10k: float, city: str) -> float:
    cp = city_params(city)
    growth = list(cp["growth"])
    discount_rate = float(cp["discount_rate"])
    delivery_freq = float(cp["delivery_freq"])
    fixed_cost = float(cp["delivery_fixed_cost"])
    variable_cost = float(cp["delivery_var_cost_km"])
    std_sales = float(cp["standard_store_sales_10k"])

    if std_sales <= 0.0:
        demand_weight = 1.0
    else:
        demand_weight = max(0.05, sales_10k / std_sales)

    trip_cost_yuan = fixed_cost + variable_cost * distance_km
    pv_yuan = 0.0
    for year, g in enumerate(growth, start=1):
        annual_yuan = delivery_freq * demand_weight * trip_cost_yuan * g
        pv_yuan += annual_yuan / ((1.0 + discount_rate) ** year)
    return pv_yuan / 10000.0


def optimize_stage3(
    stores: Sequence[Store],
    selected_new_store_rows: Sequence[Dict[str, object]],
    rdcs: Sequence[RDC],
    distance_matrix: Dict[Tuple[str, str], float],
    p_values: Sequence[int],
) -> Dict[str, object]:
    selected_new_ids = {str(r.get("store_id")) for r in selected_new_store_rows}
    adjusted_sales_by_store: Dict[str, float] = {
        str(r.get("store_id")): to_float(r.get("adjusted_sales_10k"), to_float(r.get("base_sales_10k"), 0.0))
        for r in selected_new_store_rows
    }

    full_network_stores: List[Store] = []
    for store in stores:
        if store.is_existing:
            full_network_stores.append(store)
            continue
        if store.store_id in selected_new_ids:
            adjusted_sales = adjusted_sales_by_store.get(store.store_id, store.rf_sales_10k)
            full_network_stores.append(
                Store(
                    store_id=store.store_id,
                    name=store.name,
                    city=store.city,
                    lat=store.lat,
                    lon=store.lon,
                    rf_sales_10k=adjusted_sales,
                    area_sqm=store.area_sqm,
                    initial_investment_10k=store.initial_investment_10k,
                    annual_fixed_cost_10k=store.annual_fixed_cost_10k,
                    is_existing=store.is_existing,
                )
            )

    eligible_rdcs: List[Tuple[RDC, float]] = []
    rejected_rdcs: List[Dict[str, object]] = []

    for rdc in rdcs:
        ok, reasons = rdc_eligibility(rdc)
        lifecycle = rdc_lifecycle_cost_10k(rdc)
        row = {
            "rdc_id": rdc.rdc_id,
            "name": rdc.name,
            "city": rdc.city,
            "lat": rdc.lat,
            "lon": rdc.lon,
            "lifecycle_cost_10k": round(lifecycle, 4),
            "rent_per_sqm_day": rdc.rent_per_sqm_day,
        }
        if ok:
            eligible_rdcs.append((rdc, lifecycle))
        else:
            row["reasons"] = reasons
            rejected_rdcs.append(row)

    scenarios: List[Dict[str, object]] = []
    if not full_network_stores or not eligible_rdcs:
        return {
            "eligible_rdcs": [
                {
                    "rdc_id": r.rdc_id,
                    "name": r.name,
                    "city": r.city,
                    "lat": r.lat,
                    "lon": r.lon,
                    "lifecycle_cost_10k": round(c, 4),
                }
                for r, c in eligible_rdcs
            ],
            "rejected_rdcs": rejected_rdcs,
            "network_stores": [asdict(s) for s in full_network_stores],
            "scenarios": [],
            "best_scenario": None,
        }

    valid_p_values = sorted({p for p in p_values if p > 0})
    for p in valid_p_values:
        if p > len(eligible_rdcs):
            continue

        best_cost = math.inf
        best_plan: Optional[Dict[str, object]] = None

        for combo in itertools.combinations(eligible_rdcs, p):
            open_rdcs = [x[0] for x in combo]
            rdc_cost = sum(x[1] for x in combo)
            delivery_total = 0.0
            assignments: List[Assignment] = []
            unassigned: List[Dict[str, object]] = []

            for store in full_network_stores:
                same_city_rdcs = [r for r in open_rdcs if normalize_city(r.city) == normalize_city(store.city)]
                if not same_city_rdcs:
                    unassigned.append(
                        {
                            "store_id": store.store_id,
                            "store_name": store.name,
                            "city": store.city,
                            "reason": "no opened RDC in same city",
                        }
                    )
                    continue

                best_rdc = None
                best_distance = math.inf
                best_delivery = math.inf
                for rdc in same_city_rdcs:
                    distance_km = distance_lookup_km(rdc, store, distance_matrix)
                    if not math.isfinite(distance_km):
                        continue
                    delivery_cost = delivery_cost_pv_10k(distance_km, store.rf_sales_10k, store.city)
                    if delivery_cost < best_delivery:
                        best_rdc = rdc
                        best_distance = distance_km
                        best_delivery = delivery_cost

                if best_rdc is None:
                    unassigned.append(
                        {
                            "store_id": store.store_id,
                            "store_name": store.name,
                            "city": store.city,
                            "reason": "distance lookup failed",
                        }
                    )
                    continue

                delivery_total += best_delivery
                assignments.append(
                    Assignment(
                        store_id=store.store_id,
                        store_name=store.name,
                        store_city=store.city,
                        demand_sales_10k=store.rf_sales_10k,
                        rdc_id=best_rdc.rdc_id,
                        rdc_name=best_rdc.name,
                        rdc_city=best_rdc.city,
                        store_lat=store.lat,
                        store_lon=store.lon,
                        rdc_lat=best_rdc.lat,
                        rdc_lon=best_rdc.lon,
                        distance_km=best_distance,
                        delivery_cost_pv_10k=best_delivery,
                    )
                )

            if unassigned:
                continue

            total_cost = rdc_cost + delivery_total
            if total_cost < best_cost:
                best_cost = total_cost
                best_plan = {
                    "p": p,
                    "rdc_cost_10k": rdc_cost,
                    "delivery_cost_10k": delivery_total,
                    "total_cost_10k": total_cost,
                    "open_rdcs": [
                        {
                            "rdc_id": r.rdc_id,
                            "name": r.name,
                            "city": r.city,
                            "lat": r.lat,
                            "lon": r.lon,
                            "lifecycle_cost_10k": round(rdc_lifecycle_cost_10k(r), 4),
                        }
                        for r in open_rdcs
                    ],
                    "assignments": assignments,
                }

        if best_plan is None:
            continue

        assignments = best_plan["assignments"]
        total_weight = sum(a.demand_sales_10k for a in assignments) or 1.0
        avg_distance = sum(a.distance_km * a.demand_sales_10k for a in assignments) / total_weight

        # ROI uses PV of gross profit (revenue * gross_margin) rather than raw
        # revenue, so it is dimensionally comparable with the PV-based total cost.
        total_gross_profit_pv_10k = 0.0
        for store in full_network_stores:
            cp = city_params(store.city)
            growth = list(cp["growth"])
            discount_rate = float(cp["discount_rate"])
            gross_margin = float(cp["gross_margin"])
            for year, g in enumerate(growth, start=1):
                total_gross_profit_pv_10k += (
                    store.rf_sales_10k * g * gross_margin / ((1.0 + discount_rate) ** year)
                )

        roi = 0.0
        if best_plan["total_cost_10k"] > 0:
            roi = (total_gross_profit_pv_10k - best_plan["total_cost_10k"]) / best_plan["total_cost_10k"]

        city_breakdown: Dict[str, Dict[str, float]] = {}
        for a in assignments:
            c = a.store_city
            city_breakdown.setdefault(c, {"delivery_cost_10k": 0.0, "distance_weight": 0.0, "sales_weight": 0.0, "stores": 0})
            city_breakdown[c]["delivery_cost_10k"] += a.delivery_cost_pv_10k
            city_breakdown[c]["distance_weight"] += a.distance_km * a.demand_sales_10k
            city_breakdown[c]["sales_weight"] += a.demand_sales_10k
            city_breakdown[c]["stores"] += 1

        for c in city_breakdown:
            sw = city_breakdown[c]["sales_weight"] or 1.0
            city_breakdown[c]["avg_distance_km"] = city_breakdown[c]["distance_weight"] / sw
            city_breakdown[c]["delivery_cost_10k"] = round(city_breakdown[c]["delivery_cost_10k"], 4)
            city_breakdown[c]["avg_distance_km"] = round(city_breakdown[c]["avg_distance_km"], 4)
            city_breakdown[c]["stores"] = int(city_breakdown[c]["stores"])
            del city_breakdown[c]["distance_weight"]
            del city_breakdown[c]["sales_weight"]

        scenarios.append(
            {
                "p": best_plan["p"],
                "rdc_cost_10k": round(best_plan["rdc_cost_10k"], 4),
                "delivery_cost_10k": round(best_plan["delivery_cost_10k"], 4),
                "total_cost_10k": round(best_plan["total_cost_10k"], 4),
                "avg_distance_km": round(avg_distance, 4),
                "roi": round(roi, 4),
                "open_rdcs": best_plan["open_rdcs"],
                "cost_components": {
                    "rdc_cost_10k": round(best_plan["rdc_cost_10k"], 4),
                    "delivery_cost_10k": round(best_plan["delivery_cost_10k"], 4),
                },
                "city_breakdown": city_breakdown,
                "assignments": [
                    {
                        "store_id": a.store_id,
                        "store_name": a.store_name,
                        "store_city": a.store_city,
                        "store_lat": a.store_lat,
                        "store_lon": a.store_lon,
                        "demand_sales_10k": round(a.demand_sales_10k, 4),
                        "rdc_id": a.rdc_id,
                        "rdc_name": a.rdc_name,
                        "rdc_city": a.rdc_city,
                        "rdc_lat": a.rdc_lat,
                        "rdc_lon": a.rdc_lon,
                        "distance_km": round(a.distance_km, 4),
                        "delivery_cost_pv_10k": round(a.delivery_cost_pv_10k, 4),
                    }
                    for a in sorted(best_plan["assignments"], key=lambda x: x.delivery_cost_pv_10k, reverse=True)
                ],
            }
        )

    scenarios = sorted(scenarios, key=lambda x: x["total_cost_10k"])
    best_scenario = scenarios[0] if scenarios else None

    return {
        "eligible_rdcs": [
            {
                "rdc_id": r.rdc_id,
                "name": r.name,
                "city": r.city,
                "lat": r.lat,
                "lon": r.lon,
                "lifecycle_cost_10k": round(c, 4),
            }
            for r, c in sorted(eligible_rdcs, key=lambda x: x[1])
        ],
        "rejected_rdcs": rejected_rdcs,
        "network_stores": [asdict(s) for s in full_network_stores],
        "scenarios": scenarios,
        "best_scenario": best_scenario,
    }


def filter_rows_by_city(rows: Sequence[Dict[str, object]], city: str) -> List[Dict[str, object]]:
    target = normalize_city(city)
    out: List[Dict[str, object]] = []
    for row in rows:
        c = normalize_city(str(row.get("city") or ""))
        if c == target:
            out.append(dict(row))
    return out


def run_full_model(
    store_rows: Sequence[Dict[str, object]],
    rdc_rows: Sequence[Dict[str, object]],
    distance_rows: Optional[Sequence[Dict[str, object]]] = None,
    max_new_stores: int = 8,
    p_values: Optional[Sequence[int]] = None,
    focus_city: Optional[str] = None,
    threshold_overrides: Optional[Dict[str, Dict[str, float]]] = None,
) -> Dict[str, object]:
    focus_city_norm = normalize_city(focus_city or "")
    if focus_city_norm in CITY_GIS_META:
        store_rows = filter_rows_by_city(store_rows, focus_city_norm)
        rdc_rows = filter_rows_by_city(rdc_rows, focus_city_norm)

    stores = parse_stores(store_rows)
    rdcs = parse_rdcs(rdc_rows)
    distance_matrix = parse_distance_matrix(distance_rows or [])

    stage1 = evaluate_stage1(stores, threshold_overrides=threshold_overrides)
    stage2 = optimize_stage2(stage1, max_new_stores=max_new_stores)

    if p_values is None:
        p_values = [1, 2, 3]
    stage3 = optimize_stage3(stores, stage2.get("selected", []), rdcs, distance_matrix, p_values)

    selected_ids = {str(s.get("store_id")) for s in stage2.get("selected", [])}

    stage1_rows: List[Dict[str, object]] = []
    for row in stage1:
        stage1_rows.append(
            {
                "store_id": row.store.store_id,
                "name": row.store.name,
                "city": row.store.city,
                "lat": row.store.lat,
                "lon": row.store.lon,
                "rf_sales_10k": round(row.store.rf_sales_10k, 4),
                "npv_10k": round(row.npv_10k, 4),
                "dpp_years": round(row.dpp_years, 4) if row.dpp_years else None,
                "revenue_per_sqm_10k": round(row.revenue_per_sqm_10k, 4),
                "yearly_cashflow_10k": [round(x, 4) for x in row.yearly_cashflow_10k],
                "passed": row.passed,
                "is_selected_stage2": row.store.store_id in selected_ids,
                "reasons": row.reasons,
            }
        )

    best_scenario = stage3.get("best_scenario") or {}
    best_assignments = best_scenario.get("assignments") or []

    gis_stage1_points = [
        {
            "store_id": r["store_id"],
            "name": r["name"],
            "city": r["city"],
            "lat": r["lat"],
            "lon": r["lon"],
            "passed": r["passed"],
            "npv_10k": r["npv_10k"],
            "dpp_years": r["dpp_years"],
            "yearly_cashflow_10k": r["yearly_cashflow_10k"],
        }
        for r in stage1_rows
        if is_valid_coord(float(r["lat"]), float(r["lon"]))
    ]

    gis_stage2_selected = [
        {
            "store_id": s["store_id"],
            "name": s["name"],
            "city": s["city"],
            "lat": s["lat"],
            "lon": s["lon"],
            "radius_300_m": 300,
            "radius_500_m": 500,
            "adjusted_npv_10k": s["adjusted_npv_10k"],
        }
        for s in stage2.get("selected", [])
        if is_valid_coord(float(s.get("lat", 0.0)), float(s.get("lon", 0.0)))
    ]

    gis_network_lines = [
        {
            "store_id": a["store_id"],
            "store_name": a["store_name"],
            "store_city": a["store_city"],
            "store_lat": a["store_lat"],
            "store_lon": a["store_lon"],
            "rdc_id": a["rdc_id"],
            "rdc_name": a["rdc_name"],
            "rdc_city": a["rdc_city"],
            "rdc_lat": a["rdc_lat"],
            "rdc_lon": a["rdc_lon"],
            "distance_km": a["distance_km"],
        }
        for a in best_assignments
    ]

    summary = {
        "total_store_rows": len(stores),
        "existing_stores": sum(1 for s in stores if s.is_existing),
        "new_store_candidates": sum(1 for s in stores if not s.is_existing),
        "stage1_passed": sum(1 for r in stage1 if r.passed),
        "stage2_selected": len(stage2.get("selected", [])),
        "eligible_rdcs": len(stage3.get("eligible_rdcs", [])),
        "best_p": best_scenario.get("p"),
        "best_total_cost_10k": best_scenario.get("total_cost_10k"),
        "focus_city": focus_city_norm if focus_city_norm in CITY_GIS_META else "all",
    }

    return {
        "summary": summary,
        "city_configs": get_city_configs(),
        "stage1": {"rows": stage1_rows},
        "stage2": stage2,
        "stage3": stage3,
        "gis": {
            "stage1_points": gis_stage1_points,
            "stage2_selected": gis_stage2_selected,
            "stage3_network_lines": gis_network_lines,
            "stage3_open_rdcs": best_scenario.get("open_rdcs") or [],
            "distance_alerts": stage2.get("distance_alerts", []),
        },
    }
