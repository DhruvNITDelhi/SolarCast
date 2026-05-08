"""Download the Indian solar plant Kaggle dataset when Kaggle credentials exist.

Dataset:
https://www.kaggle.com/datasets/anikannal/solar-power-generation-data
"""

from __future__ import annotations

from pathlib import Path
import os
import site
import subprocess
import sys
import zipfile

from indian_solar_dataset import DATASET_SLUG, RAW_DIR


def main() -> int:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    kaggle_config_dir = RAW_DIR / ".kaggle"
    kaggle_config_dir.mkdir(parents=True, exist_ok=True)
    zip_path = RAW_DIR / "solar-power-generation-data.zip"

    kaggle_exe = Path(site.USER_BASE) / "Python312" / "Scripts" / "kaggle.exe"
    if not kaggle_exe.exists():
        kaggle_exe = Path(sys.executable).parent / "Scripts" / "kaggle.exe"

    command = [
        str(kaggle_exe),
        "datasets",
        "download",
        "-d",
        DATASET_SLUG,
        "-p",
        str(RAW_DIR),
        "--force",
    ]

    try:
        env = {**os.environ, "KAGGLE_CONFIG_DIR": str(kaggle_config_dir)}
        subprocess.run(command, check=True, env=env)
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        raise SystemExit(
            "Could not download from Kaggle automatically. Install/configure Kaggle API "
            "or manually download the dataset and place these files under:\n"
            f"{RAW_DIR}\n\n"
            "If using Kaggle API, place kaggle.json under:\n"
            f"{kaggle_config_dir}\n\n"
            "Required files:\n"
            "- Plant_1_Generation_Data.csv\n"
            "- Plant_1_Weather_Sensor_Data.csv\n"
            "- Plant_2_Generation_Data.csv\n"
            "- Plant_2_Weather_Sensor_Data.csv\n\n"
            f"Original error: {exc}"
        ) from exc

    if zip_path.exists():
        with zipfile.ZipFile(zip_path) as archive:
            archive.extractall(RAW_DIR)
        print(f"Extracted {zip_path} into {RAW_DIR}")
    else:
        print(f"Download finished. Check files in {RAW_DIR}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
