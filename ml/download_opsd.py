"""Download the OPSD household PV dataset for ML experiments."""

from __future__ import annotations

from pathlib import Path
import sys

import requests


DATASET_URL = (
    "https://data.open-power-system-data.org/household_data/2020-04-15/"
    "household_data_15min_singleindex.csv"
)


def download_file(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)

    with requests.get(url, stream=True, timeout=60) as response:
        response.raise_for_status()
        with destination.open("wb") as file_handle:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    file_handle.write(chunk)


def main() -> int:
    project_root = Path(__file__).resolve().parent
    destination = project_root / "data" / "raw" / "household_data_15min_singleindex.csv"

    if destination.exists():
        print(f"Dataset already exists at {destination}")
        return 0

    print(f"Downloading OPSD dataset to {destination} ...")
    download_file(DATASET_URL, destination)
    print("Download complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
