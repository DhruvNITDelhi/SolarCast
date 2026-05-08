"""Benchmark the ML-only cold-start forecast directly against SolarCast physics output."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.compare_engine import compare_forecasts  # noqa: E402
from backend.ml_engine import generate_ml_forecast, generate_ml_forecast_from_weather_dataframe  # noqa: E402
from backend.solar_engine import generate_forecast, generate_forecast_from_dataframe  # noqa: E402


OUTPUT_PATH = Path(__file__).resolve().parent / "artifacts" / "physics_vs_ml_benchmark.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare physics and ML-only SolarCast forecasts.")
    parser.add_argument("--latitude", type=float, required=True)
    parser.add_argument("--longitude", type=float, required=True)
    parser.add_argument("--system-size-kw", type=float, default=10.0)
    parser.add_argument("--tilt", type=float)
    parser.add_argument("--azimuth", type=float)
    parser.add_argument("--losses", type=float, default=14.0)
    parser.add_argument("--efficiency", type=float, default=18.0)
    parser.add_argument("--weather-csv", type=Path)
    parser.add_argument("--start-timestamp")
    parser.add_argument("--timezone", default="UTC")
    return parser.parse_args()


def load_local_weather(path: Path, start_timestamp: str | None) -> pd.DataFrame:
    weather = pd.read_csv(path)
    if "timestamp" not in weather.columns:
        raise ValueError("Local weather CSV must contain a timestamp column.")
    weather["timestamp"] = pd.to_datetime(weather["timestamp"])
    weather = weather.rename(
        columns={
            "shortwave_radiation": "ghi",
            "direct_radiation": "dni",
            "diffuse_radiation": "dhi",
            "temperature_2m": "temperature",
            "cloud_cover": "cloud_cover",
        }
    )

    if start_timestamp:
        start = pd.Timestamp(start_timestamp)
        end = start + pd.Timedelta(hours=24)
        weather = weather.loc[(weather["timestamp"] >= start) & (weather["timestamp"] < end)].copy()
    else:
        weather = weather.head(25).copy()

    weather = weather[["timestamp", "ghi", "dni", "dhi", "cloud_cover", "temperature"]].copy()
    weather = (
        weather.set_index("timestamp")
        .resample("15min")
        .interpolate(method="time")
        .reset_index()
    )
    return weather.head(96)


def main() -> int:
    args = parse_args()
    if args.weather_csv:
        weather = load_local_weather(args.weather_csv, args.start_timestamp)
        timezone = args.timezone
        window_start = pd.Timestamp(weather["timestamp"].min()).tz_localize(timezone)
        weather_indexed = weather.set_index("timestamp")
        physics = generate_forecast_from_dataframe(
            df=weather_indexed,
            lat=args.latitude,
            lon=args.longitude,
            system_size_kw=args.system_size_kw,
            timezone=timezone,
            tilt=args.tilt,
            azimuth=args.azimuth,
            losses=args.losses,
            efficiency=args.efficiency,
            window_start=window_start,
        )
        ml_only = generate_ml_forecast_from_weather_dataframe(
            weather=weather,
            lat=args.latitude,
            lon=args.longitude,
            system_size_kw=args.system_size_kw,
            timezone=timezone,
            tilt=abs(args.latitude) if args.tilt is None else args.tilt,
            azimuth=180.0 if args.azimuth is None else args.azimuth,
            losses=args.losses,
            efficiency=args.efficiency,
            forecast_hours=24,
        )
    else:
        physics = generate_forecast(
            lat=args.latitude,
            lon=args.longitude,
            system_size_kw=args.system_size_kw,
            tilt=args.tilt,
            azimuth=args.azimuth,
            losses=args.losses,
            efficiency=args.efficiency,
        )
        ml_only = generate_ml_forecast(
            lat=args.latitude,
            lon=args.longitude,
            system_size_kw=args.system_size_kw,
            tilt=args.tilt,
            azimuth=args.azimuth,
            losses=args.losses,
            efficiency=args.efficiency,
        )

    result = {
        "request": {
            "latitude": args.latitude,
            "longitude": args.longitude,
            "system_size_kw": args.system_size_kw,
            "tilt": args.tilt,
            "azimuth": args.azimuth,
            "losses": args.losses,
            "efficiency": args.efficiency,
        },
        "physics": {
            "total_kwh": physics["total_kwh"],
            "peak_kwh": physics["peak_kwh"],
            "peak_hour": physics["peak_hour"],
            "confidence": physics["confidence"],
        },
        "ml_only": {
            "total_kwh": ml_only["total_kwh"],
            "peak_kwh": ml_only["peak_kwh"],
            "peak_hour": ml_only["peak_hour"],
            "confidence": ml_only["confidence"],
        },
        "comparison": compare_forecasts(physics, ml_only),
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    print(f"Saved benchmark to {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
