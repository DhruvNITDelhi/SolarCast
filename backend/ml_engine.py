"""ML-only experimental forecast engine for the SolarCast ML worktree."""

from __future__ import annotations

from functools import lru_cache
import json
import logging
import pickle
from pathlib import Path
import sys
from typing import Any, Dict

import numpy as np
import pandas as pd
import requests
from pvlib.location import Location


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ml.ml_only_model import MODEL_ARTIFACT_PATH, MODEL_METADATA_PATH, build_cold_start_features  # noqa: E402
from ml.predict_ml_only import fetch_forecast_weather  # noqa: E402
try:  # noqa: E402
    from .solar_engine import assess_confidence, build_daily_summaries, compute_poa_irradiance, get_sunrise_sunset, get_timezone
except ImportError:  # noqa: E402
    from solar_engine import assess_confidence, build_daily_summaries, compute_poa_irradiance, get_sunrise_sunset, get_timezone


DEFAULT_REFERENCE_SYSTEM_KW = 4.0
logger = logging.getLogger("solarcast")


def _resolve_system_defaults(lat: float, tilt: float | None, azimuth: float | None) -> tuple[float, float]:
    resolved_tilt = abs(lat) if tilt is None else tilt
    resolved_azimuth = 180.0 if azimuth is None else azimuth
    return resolved_tilt, resolved_azimuth


@lru_cache(maxsize=1)
def load_ml_artifacts() -> tuple[object, dict[str, Any]]:
    if not MODEL_ARTIFACT_PATH.exists():
        raise FileNotFoundError(
            f"Missing model artifact at {MODEL_ARTIFACT_PATH}. Run `python ml\\train_ml_only_model.py` first."
        )
    if not MODEL_METADATA_PATH.exists():
        raise FileNotFoundError(
            f"Missing model metadata at {MODEL_METADATA_PATH}. Run `python ml\\train_ml_only_model.py` first."
        )

    with MODEL_ARTIFACT_PATH.open("rb") as handle:
        model = pickle.load(handle)
    metadata = json.loads(MODEL_METADATA_PATH.read_text(encoding="utf-8"))
    return model, metadata


def _build_clearsky_weather(lat: float, lon: float, forecast_hours: int, timezone: str) -> pd.DataFrame:
    periods = max(forecast_hours * 4, 96)
    start = pd.Timestamp.now(tz=timezone).ceil("15min")
    times = pd.date_range(start=start, periods=periods, freq="15min")
    clearsky = Location(latitude=lat, longitude=lon, tz=timezone).get_clearsky(times)

    return pd.DataFrame(
        {
            "timestamp": times.tz_localize(None),
            "ghi": clearsky["ghi"].to_numpy(),
            "dni": clearsky["dni"].to_numpy(),
            "dhi": clearsky["dhi"].to_numpy(),
            "cloud_cover": np.zeros(periods),
            "temperature": np.full(periods, 30.0),
        }
    )


def _prepare_weather(lat: float, lon: float, forecast_hours: int, timezone: str) -> pd.DataFrame:
    try:
        weather = fetch_forecast_weather(lat, lon, forecast_hours=max(forecast_hours, 24), timezone=timezone)
    except requests.RequestException as exc:
        logger.warning("Open-Meteo unavailable for ML forecast; using local clear-sky fallback: %s", exc)
        return _build_clearsky_weather(lat, lon, forecast_hours, timezone)

    weather = weather.rename(
        columns={
            "shortwave_radiation": "ghi",
            "direct_radiation": "dni",
            "diffuse_radiation": "dhi",
            "temperature_2m": "temperature",
            "cloud_cover": "cloud_cover",
        }
    )
    weather["timestamp"] = pd.to_datetime(weather["timestamp"])
    return weather


def _build_display_frame(weather: pd.DataFrame, lat: float, lon: float, tilt: float, azimuth: float) -> pd.DataFrame:
    display = weather[["timestamp", "ghi", "dni", "dhi", "cloud_cover", "temperature"]].copy()
    display = display.set_index("timestamp")
    display.index = display.index.tz_localize(None)
    if len(display) > 1:
        median_step = display.index.to_series().diff().dropna().median()
        if median_step and median_step > pd.Timedelta(minutes=15):
            display = display.resample("15min").interpolate(method="time")
    display = compute_poa_irradiance(display, lat, lon, tilt, azimuth).reset_index().rename(columns={"index": "timestamp"})
    return display


def _build_smart_window(frame: pd.DataFrame) -> tuple[str | None, str | None]:
    positive = frame.loc[frame["kwh"] > 0].copy()
    if positive.empty:
        return None, None

    positive["rolling_hour_kwh"] = positive["kwh"].rolling(window=4, min_periods=4).sum()
    best = positive.loc[positive["rolling_hour_kwh"].idxmax()]
    end_time = pd.Timestamp(best["timestamp"])
    start_time = end_time - pd.Timedelta(minutes=45)
    return start_time.isoformat(), end_time.isoformat()


def _confidence_and_notes(daylight: pd.DataFrame, reference_kw: float) -> tuple[dict[str, Any], str]:
    confidence = assess_confidence(daylight)
    notes = (
        "Experimental ML-only cold-start forecast using weather + time features. "
        f"Predictions are scaled from a reference training system of about {reference_kw:.2f} kW."
    )
    return confidence, notes


def _safe_float(value: Any, default: float = 0.0) -> float:
    value = float(value)
    return value if np.isfinite(value) else default


def generate_ml_forecast(
    lat: float,
    lon: float,
    system_size_kw: float,
    tilt: float | None = None,
    azimuth: float | None = None,
    losses: float = 14.0,
    efficiency: float = 18.0,
    forecast_hours: int = 24,
) -> Dict[str, Any]:
    model, metadata = load_ml_artifacts()
    timezone = get_timezone(lat, lon)
    resolved_tilt, resolved_azimuth = _resolve_system_defaults(lat, tilt, azimuth)

    weather = _prepare_weather(lat, lon, forecast_hours=forecast_hours, timezone=timezone)
    return generate_ml_forecast_from_weather_dataframe(
        weather=weather,
        lat=lat,
        lon=lon,
        system_size_kw=system_size_kw,
        timezone=timezone,
        tilt=resolved_tilt,
        azimuth=resolved_azimuth,
        losses=losses,
        efficiency=efficiency,
        forecast_hours=forecast_hours,
        metadata=metadata,
        model=model,
    )


def generate_ml_forecast_from_weather_dataframe(
    weather: pd.DataFrame,
    lat: float,
    lon: float,
    system_size_kw: float,
    timezone: str,
    tilt: float,
    azimuth: float,
    losses: float = 14.0,
    efficiency: float = 18.0,
    forecast_hours: int = 24,
    metadata: dict[str, Any] | None = None,
    model: object | None = None,
) -> Dict[str, Any]:
    if model is None or metadata is None:
        model, metadata = load_ml_artifacts()

    feature_frame = build_cold_start_features(
        weather.rename(
            columns={
                "ghi": "shortwave_radiation",
                "dni": "direct_radiation",
                "dhi": "diffuse_radiation",
                "temperature": "temperature_2m",
                "cloud_cover": "cloud_cover",
            }
        )
    )
    selected_columns = metadata["feature_columns"]
    predictions = np.asarray(model.predict(feature_frame[selected_columns])).clip(min=0)
    reference_kw = float(metadata.get("reference_system_size_kw", DEFAULT_REFERENCE_SYSTEM_KW))
    scale_factor = system_size_kw / max(reference_kw, 0.1)
    predictions = predictions * scale_factor

    display = _build_display_frame(weather, lat, lon, tilt, azimuth)
    display = display.merge(feature_frame[["timestamp"]], on="timestamp", how="right")
    display = display.sort_values("timestamp").reset_index(drop=True)
    for column in ["poa_global", "ghi", "dni", "dhi", "cloud_cover", "temperature"]:
        if column in display.columns:
            display[column] = display[column].ffill().bfill()
    display["kwh"] = predictions[: len(display)]
    display["irradiance"] = display["poa_global"].fillna(display["ghi"]).clip(lower=0)
    display["ghi"] = display["ghi"].clip(lower=0)
    display["cloud_cover"] = display["cloud_cover"].clip(lower=0)
    display["temperature"] = display["temperature"].fillna(30.0)
    display = display.replace([np.inf, -np.inf], np.nan).fillna(
        {
            "kwh": 0.0,
            "irradiance": 0.0,
            "ghi": 0.0,
            "cloud_cover": 0.0,
            "temperature": 30.0,
        }
    )
    display = display.head(forecast_hours * 4).copy()

    daylight = display.loc[display["kwh"] > 0].copy()
    confidence, notes = _confidence_and_notes(daylight, reference_kw)
    total_kwh = round(float(display["kwh"].sum()), 2)
    peak_row = display.loc[display["kwh"].idxmax()]
    daily_summaries = build_daily_summaries(display.set_index("timestamp")[["kwh"]])
    sunrise, sunset = get_sunrise_sunset(lat, lon, timezone)
    smart_window_start, smart_window_end = _build_smart_window(display)

    hourly = [
        {
            "hour": pd.Timestamp(row["timestamp"]).isoformat(),
            "kwh": round(_safe_float(row["kwh"]), 3),
            "irradiance": round(_safe_float(row["irradiance"]), 1),
            "ghi": round(_safe_float(row["ghi"]), 1),
            "temperature": round(_safe_float(row["temperature"], 30.0), 1),
            "cloud_cover": round(_safe_float(row["cloud_cover"]), 1),
        }
        for _, row in display.iterrows()
    ]

    return {
        "forecast_mode": "ml_only",
        "engine_name": "Experimental ML-only cold-start",
        "engine_notes": notes,
        "hourly": hourly,
        "daily_summaries": daily_summaries,
        "forecast_hours": forecast_hours,
        "total_kwh": total_kwh,
        "peak_hour": pd.Timestamp(peak_row["timestamp"]).isoformat(),
        "peak_kwh": round(_safe_float(peak_row["kwh"]), 3),
        "confidence": confidence["confidence"],
        "confidence_score": confidence["confidence_score"],
        "confidence_reason": confidence["confidence_reason"],
        "location_info": {
            "latitude": lat,
            "longitude": lon,
            "timezone": timezone,
        },
        "system_params": {
            "system_size_kw": system_size_kw,
            "tilt": tilt,
            "azimuth": azimuth,
            "losses": losses,
            "efficiency": efficiency,
        },
        "sunrise": sunrise,
        "sunset": sunset,
        "smart_window_start": smart_window_start,
        "smart_window_end": smart_window_end,
        "yesterday_kwh": None,
        "yesterday_potential": None,
        "yesterday_loss_percent": None,
        "maintenance_alert": (
            "ML-only mode is experimental. Use it to study forecast behavior, then benchmark against the physics engine."
        ),
    }
