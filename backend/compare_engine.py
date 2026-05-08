"""Helpers for comparing SolarCast physics and ML-only forecast outputs."""

from __future__ import annotations

from typing import Any, Dict

import pandas as pd


def _local_time_key(value: Any) -> pd.Timestamp:
    """Normalize aware/naive ISO timestamps to the same local wall-clock key."""
    timestamp = pd.Timestamp(value)
    if timestamp.tzinfo is not None:
        timestamp = timestamp.tz_localize(None)
    return timestamp


def compare_forecasts(physics: Dict[str, Any], ml_only: Dict[str, Any]) -> Dict[str, Any]:
    physics_frame = pd.DataFrame(physics["hourly"]).rename(columns={"hour": "timestamp", "kwh": "physics_kwh"})
    ml_frame = pd.DataFrame(ml_only["hourly"]).rename(columns={"hour": "timestamp", "kwh": "ml_kwh"})
    physics_frame["timestamp"] = physics_frame["timestamp"].map(_local_time_key)
    ml_frame["timestamp"] = ml_frame["timestamp"].map(_local_time_key)
    merged = physics_frame.merge(ml_frame, on="timestamp", how="inner")

    if merged.empty:
        return {
            "total_kwh_delta": 0.0,
            "total_kwh_delta_percent": None,
            "peak_kwh_delta": round(float(ml_only["peak_kwh"] - physics["peak_kwh"]), 3),
            "hourly_mae": 0.0,
            "compared_intervals": 0,
            "physics_matched_total_kwh": 0.0,
            "ml_matched_total_kwh": 0.0,
        }

    physics_matched_total = float(merged["physics_kwh"].sum())
    ml_matched_total = float(merged["ml_kwh"].sum())
    total_delta = ml_matched_total - physics_matched_total
    denominator = physics_matched_total
    percent_delta = (total_delta / denominator * 100.0) if denominator else None
    hourly_mae = float((merged["ml_kwh"] - merged["physics_kwh"]).abs().mean())

    return {
        "total_kwh_delta": round(total_delta, 3),
        "total_kwh_delta_percent": round(percent_delta, 2) if percent_delta is not None else None,
        "peak_kwh_delta": round(float(ml_only["peak_kwh"] - physics["peak_kwh"]), 3),
        "hourly_mae": round(hourly_mae, 4),
        "compared_intervals": int(len(merged)),
        "physics_matched_total_kwh": round(physics_matched_total, 3),
        "ml_matched_total_kwh": round(ml_matched_total, 3),
    }
