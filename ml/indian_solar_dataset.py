"""Dataset loader for the Indian solar plant Kaggle dataset.

Expected files are from:
https://www.kaggle.com/datasets/anikannal/solar-power-generation-data
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import numpy as np
import pandas as pd


DATASET_SLUG = "anikannal/solar-power-generation-data"
RAW_DIR = Path(__file__).resolve().parent / "data" / "raw" / "indian_solar"
PROCESSED_DIR = Path(__file__).resolve().parent / "data" / "processed"
ARTIFACTS_DIR = Path(__file__).resolve().parent / "artifacts"

PLANT_FILES = {
    "plant_1": {
        "generation": RAW_DIR / "Plant_1_Generation_Data.csv",
        "weather": RAW_DIR / "Plant_1_Weather_Sensor_Data.csv",
        "latitude": 14.8141,
        "longitude": 78.1984,
        "timezone": "Asia/Kolkata",
        "location_note": "Approximate Gandikotta, Andhra Pradesh region from public dataset literature.",
    },
    "plant_2": {
        "generation": RAW_DIR / "Plant_2_Generation_Data.csv",
        "weather": RAW_DIR / "Plant_2_Weather_Sensor_Data.csv",
        "latitude": 20.0059,
        "longitude": 73.7919,
        "timezone": "Asia/Kolkata",
        "location_note": "Approximate Nashik, Maharashtra region from public dataset literature.",
    },
}


def available_plants() -> list[str]:
    return list(PLANT_FILES)


def validate_indian_solar_files() -> None:
    missing = [
        str(path)
        for plant in PLANT_FILES.values()
        for path in (plant["generation"], plant["weather"])
        if not Path(path).exists()
    ]
    if missing:
        joined = "\n".join(f"- {path}" for path in missing)
        raise FileNotFoundError(
            "Indian solar dataset files are missing. Download the Kaggle dataset "
            f"'{DATASET_SLUG}' and place/extract the CSV files under:\n"
            f"{RAW_DIR}\n\nMissing:\n{joined}"
        )


def _parse_generation_datetime(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, format="%d-%m-%Y %H:%M", errors="coerce")


def _parse_weather_datetime(series: pd.Series) -> pd.Series:
    parsed = pd.to_datetime(series, format="%Y-%m-%d %H:%M:%S", errors="coerce")
    fallback = pd.to_datetime(series, format="%d-%m-%Y %H:%M", errors="coerce")
    return parsed.fillna(fallback)


def _load_generation(path: Path, aggregation: Literal["plant", "inverter"]) -> pd.DataFrame:
    generation = pd.read_csv(path)
    generation["timestamp"] = _parse_generation_datetime(generation["DATE_TIME"])
    generation = generation.dropna(subset=["timestamp"]).sort_values("timestamp")

    if aggregation == "plant":
        grouped = (
            generation.groupby("timestamp", as_index=False)
            .agg(
                dc_power=("DC_POWER", "sum"),
                ac_power=("AC_POWER", "sum"),
                daily_yield=("DAILY_YIELD", "sum"),
                inverter_count=("SOURCE_KEY", "nunique"),
            )
            .sort_values("timestamp")
            .reset_index(drop=True)
        )
        return grouped

    generation = generation.rename(columns={"SOURCE_KEY": "inverter_id"})
    return generation[
        ["timestamp", "inverter_id", "DC_POWER", "AC_POWER", "DAILY_YIELD", "TOTAL_YIELD"]
    ].rename(
        columns={
            "DC_POWER": "dc_power",
            "AC_POWER": "ac_power",
            "DAILY_YIELD": "daily_yield",
            "TOTAL_YIELD": "total_yield",
        }
    )


def _load_weather(path: Path) -> pd.DataFrame:
    weather = pd.read_csv(path)
    weather["timestamp"] = _parse_weather_datetime(weather["DATE_TIME"])
    weather = weather.dropna(subset=["timestamp"]).sort_values("timestamp")
    weather = weather.rename(
        columns={
            "AMBIENT_TEMPERATURE": "ambient_temperature",
            "MODULE_TEMPERATURE": "module_temperature",
            "IRRADIATION": "irradiation",
        }
    )
    return weather[["timestamp", "ambient_temperature", "module_temperature", "irradiation"]]


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


def add_solarcast_inference_features(frame: pd.DataFrame) -> pd.DataFrame:
    """Map Indian plant sensor columns to the feature names used by live inference."""
    features = frame.copy()
    features["temperature_2m"] = features["ambient_temperature"]
    features["cloud_cover"] = 0.0
    # Kaggle IRRADIATION is reported around 0-1.2, while live Open-Meteo
    # shortwave_radiation is W/m2. Scale to the live inference convention.
    features["shortwave_radiation"] = features["irradiation"].clip(lower=0) * 1000.0
    features["direct_radiation"] = 0.0
    features["diffuse_radiation"] = 0.0
    return features


def load_indian_solar_dataset(
    plant: str = "plant_1",
    aggregation: Literal["plant", "inverter"] = "plant",
) -> tuple[pd.DataFrame, dict[str, object]]:
    if plant not in PLANT_FILES:
        raise ValueError(f"Unknown plant {plant!r}. Choose one of: {', '.join(PLANT_FILES)}")

    validate_indian_solar_files()
    config = PLANT_FILES[plant]
    generation = _load_generation(Path(config["generation"]), aggregation=aggregation)
    weather = _load_weather(Path(config["weather"]))

    frame = generation.merge(weather, on="timestamp", how="inner")
    frame = frame.sort_values("timestamp").reset_index(drop=True)
    frame["target_kwh"] = frame["ac_power"].clip(lower=0) * 0.25
    frame["target_kw"] = frame["ac_power"].clip(lower=0)
    frame = add_solarcast_inference_features(frame)
    frame = add_time_features(frame)

    metadata = {
        "dataset": "Kaggle Solar Power Generation Data",
        "dataset_slug": DATASET_SLUG,
        "plant": plant,
        "aggregation": aggregation,
        "latitude": config["latitude"],
        "longitude": config["longitude"],
        "timezone": config["timezone"],
        "location_note": config["location_note"],
        "target": "15-minute AC energy computed as AC_POWER * 0.25",
    }
    return frame, metadata


def cold_start_feature_columns(frame: pd.DataFrame) -> list[str]:
    return [
        "temperature_2m",
        "cloud_cover",
        "shortwave_radiation",
        "direct_radiation",
        "diffuse_radiation",
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


def adaptive_feature_columns(frame: pd.DataFrame) -> list[str]:
    columns = cold_start_feature_columns(frame)
    return columns + [column for column in frame.columns if column.startswith("lag_") or column.startswith("rolling_mean_")]


def add_lag_features(frame: pd.DataFrame) -> pd.DataFrame:
    features = frame.copy()
    for lag in (1, 2, 4, 96):
        features[f"lag_{lag}"] = features["target_kwh"].shift(lag)
    features["rolling_mean_4"] = features["target_kwh"].shift(1).rolling(4).mean()
    features["rolling_mean_16"] = features["target_kwh"].shift(1).rolling(16).mean()
    return features.dropna().reset_index(drop=True)


def split_train_validation_test(
    frame: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    train_end = int(len(frame) * 0.7)
    validation_end = int(len(frame) * 0.85)
    return (
        frame.iloc[:train_end].copy(),
        frame.iloc[train_end:validation_end].copy(),
        frame.iloc[validation_end:].copy(),
    )
