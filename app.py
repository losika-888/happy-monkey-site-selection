from __future__ import annotations

import csv
import io
import json
import os
from pathlib import Path
from typing import Dict, List, Sequence, Tuple
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

DEEPSEEK_BASE = "https://api.deepseek.com/v1"
DEEPSEEK_TOKEN = os.environ.get("DEEPSEEK_TOKEN", "")
DEEPSEEK_MODEL = "deepseek-chat"

from flask import Flask, jsonify, render_template, request, send_from_directory
from openclaw_client import openclaw_chat

from optimizer import (
    city_params,
    get_city_configs,
    normalize_city,
    parse_rdcs,
    parse_stores,
    point_inner_ring_violation,
    run_full_model,
)


BASE_DIR = Path(__file__).resolve().parent
SAMPLE_DIR = BASE_DIR / "sample_data"

app = Flask(__name__, template_folder=str(BASE_DIR / "templates"), static_folder=str(BASE_DIR / "static"))


def parse_csv_upload(file_obj) -> List[Dict[str, str]]:
    if file_obj is None or not file_obj.filename:
        return []
    raw = file_obj.read()
    text = raw.decode("utf-8-sig", errors="ignore")
    reader = csv.DictReader(io.StringIO(text))
    return [dict(row) for row in reader]


def parse_csv_file(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return [dict(row) for row in reader]


def parse_p_values(raw: str) -> List[int]:
    values = []
    for part in (raw or "").split(","):
        part = part.strip()
        if not part:
            continue
        try:
            values.append(int(part))
        except ValueError:
            continue
    return values or [1, 2, 3]


def parse_int(raw: str, default: int) -> int:
    try:
        return int(raw)
    except (TypeError, ValueError):
        return default


def parse_bool(raw: str, default: bool = False) -> bool:
    if raw is None:
        return default
    text = str(raw).strip().lower()
    if text in {"1", "true", "yes", "y", "t", "on"}:
        return True
    if text in {"0", "false", "no", "n", "f", "off"}:
        return False
    return default


def parse_float(raw: str, default: float | None = None) -> float | None:
    try:
        return float(raw)
    except (TypeError, ValueError):
        return default


def chunked(seq: Sequence, size: int):
    for i in range(0, len(seq), size):
        yield seq[i : i + size]


def merge_distance_rows(primary_rows: List[Dict[str, object]], secondary_rows: List[Dict[str, object]]) -> List[Dict[str, object]]:
    merged: Dict[Tuple[str, str], Dict[str, object]] = {}
    for row in primary_rows:
        key = (str(row.get("rdc_id") or ""), str(row.get("store_id") or ""))
        if key[0] and key[1]:
            merged[key] = dict(row)
    for row in secondary_rows:
        key = (str(row.get("rdc_id") or ""), str(row.get("store_id") or ""))
        if key[0] and key[1]:
            merged[key] = dict(row)
    return list(merged.values())


def amap_distance_batch(origins: List[Tuple[str, float, float]], destination_lon: float, destination_lat: float, amap_key: str, timeout_sec: int):
    origin_text = "|".join(f"{lon},{lat}" for _, lat, lon in origins)
    params = {
        "origins": origin_text,
        "destination": f"{destination_lon},{destination_lat}",
        "type": 1,
        "key": amap_key,
    }
    url = "https://restapi.amap.com/v3/distance?" + urlencode(params)
    req = Request(url, headers={"User-Agent": "happy-monkey-site-model/1.0"})
    with urlopen(req, timeout=timeout_sec) as resp:
        payload = resp.read().decode("utf-8", errors="ignore")
    data = json.loads(payload)
    if str(data.get("status")) != "1":
        raise RuntimeError(data.get("info") or "unknown amap api error")

    results = data.get("results") or []
    out = []
    for idx, row in enumerate(origins):
        r = results[idx] if idx < len(results) else None
        if not r:
            continue
        distance_m = float(r.get("distance") or 0.0)
        out.append((row[0], distance_m / 1000.0))
    return out


def build_amap_distance_rows(store_rows: List[Dict[str, object]], rdc_rows: List[Dict[str, object]], amap_key: str, timeout_sec: int = 8):
    stores = [s for s in parse_stores(store_rows) if -90 <= s.lat <= 90 and -180 <= s.lon <= 180]
    rdcs = [r for r in parse_rdcs(rdc_rows) if -90 <= r.lat <= 90 and -180 <= r.lon <= 180]

    warnings: List[str] = []
    rows: List[Dict[str, object]] = []

    stores_by_city: Dict[str, List] = {}
    rdcs_by_city: Dict[str, List] = {}
    for s in stores:
        stores_by_city.setdefault(s.city, []).append(s)
    for r in rdcs:
        rdcs_by_city.setdefault(r.city, []).append(r)

    for city, city_stores in stores_by_city.items():
        city_rdcs = rdcs_by_city.get(city, [])
        if not city_rdcs:
            continue

        origins = [(r.rdc_id, r.lat, r.lon) for r in city_rdcs]
        for store in city_stores:
            for batch in chunked(origins, 20):
                try:
                    results = amap_distance_batch(batch, store.lon, store.lat, amap_key, timeout_sec=timeout_sec)
                except (HTTPError, URLError, TimeoutError, RuntimeError, ValueError) as exc:
                    warnings.append(f"amap distance failed for {city}/{store.store_id}: {exc}")
                    continue

                for rdc_id, km in results:
                    rows.append({"rdc_id": rdc_id, "store_id": store.store_id, "distance_km": round(km, 6)})

    return rows, warnings


def parse_custom_rdcs(raw_json: str, focus_city: str | None = None) -> List[Dict[str, object]]:
    if not raw_json:
        return []
    try:
        arr = json.loads(raw_json)
    except json.JSONDecodeError:
        return []
    if not isinstance(arr, list):
        return []

    out: List[Dict[str, object]] = []
    for idx, item in enumerate(arr, start=1):
        if not isinstance(item, dict):
            continue

        city = normalize_city(str(item.get("city") or focus_city or "beijing"))
        cp = city_params(city)
        lat = float(item.get("lat") or 0.0)
        lon = float(item.get("lon") or 0.0)
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            continue

        rent_cap = float(cp.get("rent_cap_per_sqm_day") or 1.7)
        out.append(
            {
                "rdc_id": str(item.get("rdc_id") or f"CUSTOM_{idx}"),
                "name": str(item.get("name") or f"Custom RDC {idx}"),
                "city": city,
                "lat": lat,
                "lon": lon,
                "area_sqm": float(item.get("area_sqm") or 10000),
                "initial_investment_10k": float(item.get("initial_investment_10k") or 220),
                "annual_rent_10k": float(item.get("annual_rent_10k") or 500),
                "annual_property_10k": float(item.get("annual_property_10k") or 38),
                "annual_operating_10k": float(item.get("annual_operating_10k") or 58),
                "annual_labor_10k": float(item.get("annual_labor_10k") or 53),
                "annual_utility_10k": float(item.get("annual_utility_10k") or 33),
                "residual_rate": float(item.get("residual_rate") or 0.25),
                "rent_per_sqm_day": float(item.get("rent_per_sqm_day") or max(rent_cap - 0.08, 0.5)),
                "lease_years": float(item.get("lease_years") or 6),
                "blue_access": int(item.get("blue_access") if item.get("blue_access") is not None else 1),
                "core_travel_min": float(item.get("core_travel_min") or 28),
                "clear_height_m": float(item.get("clear_height_m") or 7.5),
                "loading_dock": int(item.get("loading_dock") if item.get("loading_dock") is not None else 1),
                "can_three_temp": int(item.get("can_three_temp") if item.get("can_three_temp") is not None else 1),
                "fire_pass": int(item.get("fire_pass") if item.get("fire_pass") is not None else 1),
                "disturbance_risk": int(item.get("disturbance_risk") if item.get("disturbance_risk") is not None else 0),
            }
        )

    return out


def build_threshold_overrides(focus_city: str, npv_raw: str, dpp_raw: str, rev_raw: str):
    npv_val = parse_float(npv_raw)
    dpp_val = parse_float(dpp_raw)
    rev_val = parse_float(rev_raw)
    if npv_val is None and dpp_val is None and rev_val is None:
        return None

    payload = {}
    targets = ["beijing", "hangzhou"] if focus_city not in {"beijing", "hangzhou"} else [focus_city]
    for city in targets:
        payload[city] = {}
        if npv_val is not None:
            payload[city]["npv_threshold_10k"] = npv_val
        if dpp_val is not None:
            payload[city]["dpp_threshold_years"] = dpp_val
        if rev_val is not None:
            payload[city]["revenue_per_sqm_threshold_10k"] = rev_val
    return payload


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/cities")
def city_configs():
    return jsonify({"cities": get_city_configs()})


@app.post("/api/validate-rdc-point")
def validate_rdc_point():
    payload = request.get_json(silent=True) or {}
    city = str(payload.get("city") or "")
    lat = float(payload.get("lat") or 0.0)
    lon = float(payload.get("lon") or 0.0)
    return jsonify(point_inner_ring_violation(city, lat, lon))


@app.get("/api/sample/<filename>")
def sample_file(filename: str):
    safe = {
        "stores.csv": "stores.csv",
        "rdcs.csv": "rdcs.csv",
        "distances.csv": "distances.csv",
    }
    if filename not in safe:
        return jsonify({"error": "unknown sample file"}), 404
    return send_from_directory(SAMPLE_DIR, safe[filename], as_attachment=True)


@app.post("/api/run")
def run_model():
    store_rows = parse_csv_upload(request.files.get("store_file"))
    rdc_rows = parse_csv_upload(request.files.get("rdc_file"))
    uploaded_distance_rows = parse_csv_upload(request.files.get("distance_file"))

    if not store_rows:
        return jsonify({"error": "store_file is required and must be a valid CSV"}), 400
    if not rdc_rows:
        return jsonify({"error": "rdc_file is required and must be a valid CSV"}), 400

    focus_city = normalize_city(request.form.get("focus_city", ""))
    max_new_stores = parse_int(request.form.get("max_new_stores"), 8)
    p_values = parse_p_values(request.form.get("p_values", "1,2,3"))
    threshold_overrides = build_threshold_overrides(
        focus_city,
        request.form.get("npv_threshold_10k"),
        request.form.get("dpp_threshold_years"),
        request.form.get("revenue_per_sqm_threshold_10k"),
    )

    custom_rdcs = parse_custom_rdcs(request.form.get("custom_rdcs_json", ""), focus_city=focus_city)
    if custom_rdcs:
        rdc_rows = list(rdc_rows) + custom_rdcs

    use_road_distance = parse_bool(request.form.get("use_road_distance"), False)
    amap_key = (request.form.get("amap_key") or "").strip()

    generated_distance_rows: List[Dict[str, object]] = []
    amap_warnings: List[str] = []
    distance_source = "uploaded_or_haversine"

    if use_road_distance and amap_key:
        generated_distance_rows, amap_warnings = build_amap_distance_rows(store_rows, rdc_rows, amap_key)
        distance_source = "amap_driving+uploaded_fallback"

    distance_rows = merge_distance_rows(generated_distance_rows, uploaded_distance_rows)

    try:
        result = run_full_model(
            store_rows=store_rows,
            rdc_rows=rdc_rows,
            distance_rows=distance_rows,
            max_new_stores=max_new_stores,
            p_values=p_values,
            focus_city=focus_city if focus_city in {"beijing", "hangzhou"} else None,
            threshold_overrides=threshold_overrides,
        )
    except Exception as exc:
        return jsonify({"error": f"model execution failed: {exc}"}), 500

    result["meta"] = {
        "distance_source": distance_source,
        "uploaded_distance_rows": len(uploaded_distance_rows),
        "amap_distance_rows": len(generated_distance_rows),
        "amap_warnings": amap_warnings[:40],
        "custom_rdcs": len(custom_rdcs),
    }

    return jsonify(result)


@app.post("/api/run-sample")
def run_sample_model():
    store_rows = parse_csv_file(SAMPLE_DIR / "stores.csv")
    rdc_rows = parse_csv_file(SAMPLE_DIR / "rdcs.csv")
    uploaded_distance_rows = parse_csv_file(SAMPLE_DIR / "distances.csv")

    focus_city = normalize_city(request.form.get("focus_city", ""))
    max_new_stores = parse_int(request.form.get("max_new_stores"), 8)
    p_values = parse_p_values(request.form.get("p_values", "1,2,3"))
    threshold_overrides = build_threshold_overrides(
        focus_city,
        request.form.get("npv_threshold_10k"),
        request.form.get("dpp_threshold_years"),
        request.form.get("revenue_per_sqm_threshold_10k"),
    )

    custom_rdcs = parse_custom_rdcs(request.form.get("custom_rdcs_json", ""), focus_city=focus_city)
    if custom_rdcs:
        rdc_rows = list(rdc_rows) + custom_rdcs

    use_road_distance = parse_bool(request.form.get("use_road_distance"), False)
    amap_key = (request.form.get("amap_key") or "").strip()

    generated_distance_rows: List[Dict[str, object]] = []
    amap_warnings: List[str] = []
    distance_source = "sample+uploaded_or_haversine"

    if use_road_distance and amap_key:
        generated_distance_rows, amap_warnings = build_amap_distance_rows(store_rows, rdc_rows, amap_key)
        distance_source = "sample+amap_driving+uploaded_fallback"

    distance_rows = merge_distance_rows(generated_distance_rows, uploaded_distance_rows)

    try:
        result = run_full_model(
            store_rows=store_rows,
            rdc_rows=rdc_rows,
            distance_rows=distance_rows,
            max_new_stores=max_new_stores,
            p_values=p_values,
            focus_city=focus_city if focus_city in {"beijing", "hangzhou"} else None,
            threshold_overrides=threshold_overrides,
        )
    except Exception as exc:
        return jsonify({"error": f"sample model execution failed: {exc}"}), 500

    result["meta"] = {
        "distance_source": distance_source,
        "uploaded_distance_rows": len(uploaded_distance_rows),
        "amap_distance_rows": len(generated_distance_rows),
        "amap_warnings": amap_warnings[:40],
        "custom_rdcs": len(custom_rdcs),
    }

    return jsonify(result)


@app.get("/api/chat/models")
def chat_models():
    return jsonify({"data": [{"id": "openclaw/main", "name": "OpenClaw · main agent (DeepSeek)"}]})


@app.post("/api/chat")
def chat():
    payload = request.get_json(silent=True) or {}
    messages = payload.get("messages") or []
    session_key = str(payload.get("session_key") or "")
    if not messages:
        return jsonify({"error": "messages required"}), 400

    # 取最后一条用户消息作为本次输入
    user_message = ""
    for m in reversed(messages):
        if m.get("role") == "user":
            user_message = m.get("content", "")
            break
    if not user_message:
        return jsonify({"error": "no user message found"}), 400

    try:
        reply, new_session_key = openclaw_chat(
            user_message=user_message,
            session_key=session_key or None,
            timeout=90,
        )
        return jsonify({
            "choices": [{"message": {"role": "assistant", "content": reply}}],
            "session_key": new_session_key,
        })
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 502


if __name__ == "__main__":
    host = os.environ.get("FLASK_HOST", "127.0.0.1")
    port = int(os.environ.get("FLASK_PORT", "5000"))
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(host=host, port=port, debug=debug)
