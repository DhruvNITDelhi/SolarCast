"""Shared helpers for the SolarCast ML-only cold-start forecast track."""

from __future__ import annotations

from pathlib import Path
import json

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor


PROCESSED_DIR = Path(__file__).resolve().parent / "data" / "processed"
ARTIFACTS_DIR = Path(__file__).resolve().parent / "artifacts"
MODEL_ARTIFACT_PATH = ARTIFACTS_DIR / "ml_only_model.pkl"
MODEL_METADATA_PATH = ARTIFACTS_DIR / "ml_only_model_metadata.json"
WEATHER_FEATURES = [
    "temperature_2m",
    "cloud_cover",
    "shortwave_radiation",
    "direct_radiation",
    "diffuse_radiation",
]


def cold_start_feature_columns(frame: pd.DataFrame) -> list[str]:
    return [column for column in frame.columns if column not in {"timestamp", "target_kwh"}]


def add_time_features(frame: pd.DataFrame) -> pd.DataFrame:
    features = frame.copy()
    timestamp = pd.to_datetime(features["timestamp"])

    features["hour"] = timestamp.dt.hour
    features["minute"] = timestamp.dt.minute
    features["dayofweek"] = timestamp.dt.dayofweek
    features["month"] = timestamp.dt.month
    features["dayofyear"] = timestamp.dt.dayofyear
    features["is_weekend"] = (features["dayofweek"] >= 5).astype(int)
    features["sin_hour"] = np.sin(2 * np.pi * (features["hour"] * 60 + features["minute"]) / (24 * 60))
    features["cos_hour"] = np.cos(2 * np.pi * (features["hour"] * 60 + features["minute"]) / (24 * 60))
    features["sin_dayofyear"] = np.sin(2 * np.pi * features["dayofyear"] / 365.25)
    features["cos_dayofyear"] = np.cos(2 * np.pi * features["dayofyear"] / 365.25)
    return features


def ensure_weather_columns(frame: pd.DataFrame) -> pd.DataFrame:
    features = frame.copy()
    for column in WEATHER_FEATURES:
        if column not in features.columns:
            features[column] = 0.0
    return features


def resample_weather_to_15min(frame: pd.DataFrame) -> pd.DataFrame:
    weather = frame.copy()
    weather["timestamp"] = pd.to_datetime(weather["timestamp"])
    weather = weather.sort_values("timestamp").reset_index(drop=True)
    weather = ensure_weather_columns(weather)
    if len(weather) > 1:
        median_step = weather["timestamp"].diff().dropna().median()
        if median_step and median_step > pd.Timedelta(minutes=15):
            weather = (
                weather.set_index("timestamp")[WEATHER_FEATURES]
                .resample("15min")
                .interpolate(method="time")
                .reset_index()
            )
    return weather


def build_cold_start_features(frame: pd.DataFrame) -> pd.DataFrame:
    features = resample_weather_to_15min(frame)
    features = add_time_features(features)
    return features


def build_ml_only_model() -> RandomForestRegressor:
    return RandomForestRegressor(
        n_estimators=250,
        max_depth=18,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=1,
    )


def save_model_metadata(metadata: dict) -> None:
    MODEL_METADATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    MODEL_METADATA_PATH.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
