"""Optional weather enrichment for the ML experiment track."""

from __future__ import annotations

from pathlib import Path
import json

import pandas as pd
import requests


RAW_DATA_PATH = Path(__file__).resolve().parent / "data" / "raw" / "household_data_15min_singleindex.csv"
CONFIG_PATH = Path(__file__).resolve().parent / "site_config.json"
OUTPUT_PATH = Path(__file__).resolve().parent / "data" / "processed" / "weather_features.csv"
OPEN_METEO_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(
            f"Missing {CONFIG_PATH}. Copy ml\\site_config.example.json to ml\\site_config.json and fill it in."
        )
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def load_time_range() -> tuple[pd.Timestamp, pd.Timestamp]:
    if not RAW_DATA_PATH.exists():
        raise FileNotFoundError(
            f"Dataset not found at {RAW_DATA_PATH}. Run `python ml\\download_opsd.py` first."
        )

    frame = pd.read_csv(RAW_DATA_PATH, usecols=["cet_cest_timestamp"])
    timestamps = pd.to_datetime(frame["cet_cest_timestamp"])
    return timestamps.min(), timestamps.max()


def fetch_weather(config: dict, start_ts: pd.Timestamp, end_ts: pd.Timestamp) -> pd.DataFrame:
    params = {
        "latitude": config["latitude"],
        "longitude": config["longitude"],
        "start_date": start_ts.date().isoformat(),
        "end_date": end_ts.date().isoformat(),
        "timezone": config.get("timezone", "auto"),
        "hourly": ",".join(
            [
                "temperature_2m",
                "cloud_cover",
                "shortwave_radiation",
                "direct_radiation",
                "diffuse_radiation",
            ]
        ),
    }

    response = requests.get(OPEN_METEO_ARCHIVE_URL, params=params, timeout=60)
    response.raise_for_status()
    payload = response.json()
    hourly = payload["hourly"]

    weather = pd.DataFrame(hourly)
    weather["time"] = pd.to_datetime(weather["time"])
    return weather.rename(columns={"time": "timestamp"})


def main() -> int:
    config = load_config()
    start_ts, end_ts = load_time_range()
    weather = fetch_weather(config, start_ts, end_ts)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    weather.to_csv(OUTPUT_PATH, index=False)

    print(f"Saved optional weather features to {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
