"""Shared feature logic for SolarCast hybrid residual correction."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


ARTIFACTS_DIR = Path(__file__).resolve().parent / "artifacts"
HYBRID_MODEL_PATH = ARTIFACTS_DIR / "hybrid_residual_model.pkl"
HYBRID_METADATA_PATH = ARTIFACTS_DIR / "hybrid_residual_model_metadata.json"

HYBRID_FEATURE_COLUMNS = [
    "temperature_2m",
    "cloud_cover",
    "shortwave_radiation",
    "direct_radiation",
    "diffuse_radiation",
    "physics_cf",
    "hour",
    "minute",
    "dayofweek",
    "month",
    "dayofyear",
    "is_weekend",
    "sin_hour",
    "cos_hour",
    "sin_dayofyear",
    "cos_dayofyear",
]


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


def ensure_hybrid_columns(frame: pd.DataFrame) -> pd.DataFrame:
    features = frame.copy()
    for column in HYBRID_FEATURE_COLUMNS:
        if column not in features.columns:
            features[column] = 0.0
    return features[HYBRID_FEATURE_COLUMNS]
