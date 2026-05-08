"""Run the saved SolarCast ML-only cold-start model on forecast weather."""

from __future__ import annotations

import argparse
import json
import pickle
from pathlib import Path

import pandas as pd
import requests

try:
    from .ml_only_model import MODEL_ARTIFACT_PATH, MODEL_METADATA_PATH, WEATHER_FEATURES, build_cold_start_features
except ImportError:
    from ml_only_model import MODEL_ARTIFACT_PATH, MODEL_METADATA_PATH, WEATHER_FEATURES, build_cold_start_features


OPEN_METEO_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the SolarCast ML-only cold-start forecast.")
    parser.add_argument("--latitude", type=float, help="Latitude for the forecast location.")
    parser.add_argument("--longitude", type=float, help="Longitude for the forecast location.")
    parser.add_argument("--forecast-hours", type=int, default=24, help="Forecast horizon in hours.")
    parser.add_argument("--timezone", default="auto", help="Timezone for the forecast API request.")
    parser.add_argument(
        "--weather-csv",
        type=Path,
        help="Optional local weather CSV to use instead of calling Open-Meteo. Must contain timestamp and weather columns.",
    )
    return parser.parse_args()


def load_model() -> tuple[object, dict]:
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


def fetch_forecast_weather(latitude: float, longitude: float, forecast_hours: int, timezone: str) -> pd.DataFrame:
    response = requests.get(
        OPEN_METEO_FORECAST_URL,
        params={
            "latitude": latitude,
            "longitude": longitude,
            "timezone": timezone,
            "forecast_hours": forecast_hours,
            "hourly": ",".join(WEATHER_FEATURES),
        },
        timeout=60,
    )
    response.raise_for_status()
    payload = response.json()
    hourly = payload["hourly"]
    weather = pd.DataFrame(hourly).rename(columns={"time": "timestamp"})
    weather["timestamp"] = pd.to_datetime(weather["timestamp"])
    return weather


def load_weather_frame(args: argparse.Namespace) -> pd.DataFrame:
    if args.weather_csv:
        weather = pd.read_csv(args.weather_csv)
        if "timestamp" not in weather.columns:
            raise ValueError("Local weather CSV must contain a `timestamp` column.")
        weather["timestamp"] = pd.to_datetime(weather["timestamp"])
        return weather

    if args.latitude is None or args.longitude is None:
        raise ValueError("Either provide --weather-csv or both --latitude and --longitude.")
    return fetch_forecast_weather(args.latitude, args.longitude, args.forecast_hours, args.timezone)


def summarize_predictions(frame: pd.DataFrame) -> dict:
    daily = frame.copy()
    daily["date"] = pd.to_datetime(daily["timestamp"]).dt.date
    daily_summary = (
        daily.groupby("date", as_index=False)["predicted_kwh"]
        .sum()
        .rename(columns={"predicted_kwh": "predicted_total_kwh"})
    )

    peak_row = frame.loc[frame["predicted_kwh"].idxmax()]
    return {
        "total_predicted_kwh": float(frame["predicted_kwh"].sum()),
        "peak_prediction_kwh": float(peak_row["predicted_kwh"]),
        "peak_prediction_time": pd.Timestamp(peak_row["timestamp"]).isoformat(),
        "daily_totals": [
            {
                "date": str(row["date"]),
                "predicted_total_kwh": float(row["predicted_total_kwh"]),
            }
            for _, row in daily_summary.iterrows()
        ],
    }


def main() -> int:
    args = parse_args()
    model, metadata = load_model()
    weather = load_weather_frame(args)
    features = build_cold_start_features(weather)
    selected_columns = metadata["feature_columns"]
    missing = [column for column in selected_columns if column not in features.columns]
    if missing:
        raise ValueError(f"Prepared inference frame is missing required feature columns: {missing}")

    forecast_frame = features[["timestamp"]].copy()
    forecast_frame["predicted_kwh"] = model.predict(features[selected_columns]).clip(min=0)
    if args.forecast_hours:
        forecast_frame = forecast_frame.head(args.forecast_hours * 4).copy()

    result = {
        "forecast_mode": "ml_only_cold_start",
        "forecast_hours": int(args.forecast_hours),
        "model_family": type(model).__name__,
        "summary": summarize_predictions(forecast_frame),
        "forecast": [
            {
                "timestamp": pd.Timestamp(row["timestamp"]).isoformat(),
                "predicted_kwh": float(row["predicted_kwh"]),
            }
            for _, row in forecast_frame.iterrows()
        ],
    }

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
