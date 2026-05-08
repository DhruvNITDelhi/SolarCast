"""Hybrid physics + ML residual correction engine."""

from __future__ import annotations

from functools import lru_cache
import json
import pickle
from pathlib import Path
import sys
from typing import Any, Dict

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ml.hybrid_residual_model import HYBRID_METADATA_PATH, HYBRID_MODEL_PATH, add_time_features, ensure_hybrid_columns  # noqa: E402
try:  # noqa: E402
    from .solar_engine import generate_forecast
except ImportError:  # noqa: E402
    from solar_engine import generate_forecast


@lru_cache(maxsize=1)
def load_hybrid_artifacts() -> tuple[object, dict[str, Any]]:
    if not HYBRID_MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Missing hybrid model artifact at {HYBRID_MODEL_PATH}. Run `python ml\\train_hybrid_residual_model.py` first."
        )
    if not HYBRID_METADATA_PATH.exists():
        raise FileNotFoundError(
            f"Missing hybrid model metadata at {HYBRID_METADATA_PATH}. Run `python ml\\train_hybrid_residual_model.py` first."
        )
    with HYBRID_MODEL_PATH.open("rb") as handle:
        model = pickle.load(handle)
    metadata = json.loads(HYBRID_METADATA_PATH.read_text(encoding="utf-8"))
    return model, metadata


def _feature_frame_from_physics(physics_result: Dict[str, Any], system_size_kw: float) -> pd.DataFrame:
    rows = []
    max_interval_kwh = system_size_kw * 0.25
    for item in physics_result["hourly"]:
        physics_kwh = float(item["kwh"])
        rows.append(
            {
                "timestamp": pd.Timestamp(item["hour"]).tz_localize(None),
                "temperature_2m": float(item["temperature"]),
                "cloud_cover": float(item["cloud_cover"]),
                "shortwave_radiation": float(item["ghi"]),
                "direct_radiation": 0.0,
                "diffuse_radiation": 0.0,
                "physics_cf": physics_kwh / max(max_interval_kwh, 0.001),
            }
        )
    return add_time_features(pd.DataFrame(rows))


def generate_hybrid_forecast(
    lat: float,
    lon: float,
    system_size_kw: float,
    tilt: float | None = None,
    azimuth: float | None = None,
    losses: float = 14.0,
    efficiency: float = 18.0,
    forecast_hours: int = 24,
) -> Dict[str, Any]:
    model, metadata = load_hybrid_artifacts()
    physics = generate_forecast(
        lat=lat,
        lon=lon,
        system_size_kw=system_size_kw,
        tilt=tilt,
        azimuth=azimuth,
        losses=losses,
        efficiency=efficiency,
        forecast_hours=forecast_hours,
    )
    features = _feature_frame_from_physics(physics, system_size_kw)
    residual_cf = np.asarray(model.predict(ensure_hybrid_columns(features)))

    max_interval_kwh = system_size_kw * 0.25
    hourly = []
    for item, correction in zip(physics["hourly"], residual_cf):
        physics_kwh = float(item["kwh"])
        raw_correction_kwh = float(correction) * max_interval_kwh
        correction_limit_kwh = max(0.03, physics_kwh * 0.12)
        bounded_correction_kwh = min(
            max(raw_correction_kwh, -correction_limit_kwh),
            correction_limit_kwh,
        )
        corrected_kwh = physics_kwh + bounded_correction_kwh
        corrected_kwh = min(max(corrected_kwh, 0.0), max_interval_kwh)
        updated = {**item, "kwh": round(corrected_kwh, 3)}
        hourly.append(updated)

    total_kwh = round(sum(item["kwh"] for item in hourly), 2)
    peak = max(hourly, key=lambda row: row["kwh"]) if hourly else {"hour": "", "kwh": 0.0}

    return {
        **physics,
        "forecast_mode": "hybrid",
        "engine_name": "Hybrid physics + ML residual correction",
        "engine_notes": (
            "Physics baseline corrected by an ML residual model trained on Indian solar plant data. "
            f"Residual target: {metadata.get('residual_target', 'actual - physics')}."
        ),
        "hourly": hourly,
        "total_kwh": total_kwh,
        "peak_hour": peak["hour"],
        "peak_kwh": peak["kwh"],
        "maintenance_alert": (
            "Hybrid mode is the patent-track engine: physics forecast plus learned residual correction."
        ),
    }
