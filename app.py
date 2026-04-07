from __future__ import annotations

import csv
import io
from pathlib import Path
from typing import Dict, List

from flask import Flask, jsonify, render_template, request, send_from_directory

from optimizer import run_full_model


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


@app.get("/")
def index():
    return render_template("index.html")


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
    distance_rows = parse_csv_upload(request.files.get("distance_file"))

    if not store_rows:
        return jsonify({"error": "store_file is required and must be a valid CSV"}), 400
    if not rdc_rows:
        return jsonify({"error": "rdc_file is required and must be a valid CSV"}), 400

    max_new_stores = int(request.form.get("max_new_stores", 8) or 8)
    p_values = parse_p_values(request.form.get("p_values", "1,2,3"))

    try:
        result = run_full_model(
            store_rows=store_rows,
            rdc_rows=rdc_rows,
            distance_rows=distance_rows,
            max_new_stores=max_new_stores,
            p_values=p_values,
        )
    except Exception as exc:
        return jsonify({"error": f"model execution failed: {exc}"}), 500

    return jsonify(result)


@app.post("/api/run-sample")
def run_sample_model():
    store_rows = parse_csv_file(SAMPLE_DIR / "stores.csv")
    rdc_rows = parse_csv_file(SAMPLE_DIR / "rdcs.csv")
    distance_rows = parse_csv_file(SAMPLE_DIR / "distances.csv")

    max_new_stores = int(request.form.get("max_new_stores", 8) or 8)
    p_values = parse_p_values(request.form.get("p_values", "1,2,3"))

    try:
        result = run_full_model(
            store_rows=store_rows,
            rdc_rows=rdc_rows,
            distance_rows=distance_rows,
            max_new_stores=max_new_stores,
            p_values=p_values,
        )
    except Exception as exc:
        return jsonify({"error": f"sample model execution failed: {exc}"}), 500

    return jsonify(result)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
