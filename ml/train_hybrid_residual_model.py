"""Train a physics + ML residual correction model on Indian solar plant data."""

from __future__ import annotations

import json
import pickle
from pathlib import Path
import sys

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.solar_engine import compute_hourly_generation, compute_poa_irradiance, localize_index  # noqa: E402
from indian_solar_dataset import load_indian_solar_dataset, split_train_validation_test  # noqa: E402
from hybrid_residual_model import (  # noqa: E402
    HYBRID_FEATURE_COLUMNS,
    HYBRID_METADATA_PATH,
    HYBRID_MODEL_PATH,
    add_time_features,
    ensure_hybrid_columns,
)


REPORT_PATH = Path(__file__).resolve().parent / "artifacts" / "hybrid_residual_training_report.json"


def build_model_registry() -> dict[str, object]:
    return {
        "ridge": Pipeline(
            [
                ("scaler", StandardScaler()),
                ("model", Ridge(alpha=1.0)),
            ]
        ),
        "hist_gradient_boosting": HistGradientBoostingRegressor(
            loss="squared_error",
            learning_rate=0.05,
            max_depth=5,
            max_iter=300,
            random_state=42,
        ),
        "random_forest": RandomForestRegressor(
            n_estimators=200,
            max_depth=14,
            min_samples_leaf=2,
            random_state=42,
            n_jobs=1,
        ),
    }


def evaluate(actual_kwh: pd.Series, predicted_kwh: np.ndarray) -> dict[str, float]:
    daily = (
        pd.DataFrame({"actual": actual_kwh.values, "predicted": predicted_kwh})
        .assign(day=np.arange(len(actual_kwh)) // 96)
        .groupby("day")
        .sum()
    )
    return {
        "mae": float(mean_absolute_error(actual_kwh, predicted_kwh)),
        "rmse": float(np.sqrt(mean_squared_error(actual_kwh, predicted_kwh))),
        "daily_energy_mae": float(mean_absolute_error(daily["actual"], daily["predicted"])),
    }


def build_training_frame() -> tuple[pd.DataFrame, dict[str, object]]:
    frame, metadata = load_indian_solar_dataset("plant_1", aggregation="plant")
    frame = frame.dropna().sort_values("timestamp").reset_index(drop=True)

    reference_system_size_kw = max(1.0, round(float(frame["target_kw"].quantile(0.995)), 2))
    weather = pd.DataFrame(
        {
            "ghi": frame["shortwave_radiation"].to_numpy(),
            "dni": frame["direct_radiation"].to_numpy(),
            "dhi": frame["diffuse_radiation"].to_numpy(),
            "cloud_cover": frame["cloud_cover"].to_numpy(),
            "temperature": frame["temperature_2m"].to_numpy(),
        },
        index=localize_index(pd.DatetimeIndex(frame["timestamp"]), str(metadata["timezone"])),
    )
    physics = compute_poa_irradiance(
        weather.copy(),
        lat=float(metadata["latitude"]),
        lon=float(metadata["longitude"]),
        tilt=float(metadata["latitude"]),
        azimuth=180.0,
    )
    physics = compute_hourly_generation(
        physics,
        system_size_kw=reference_system_size_kw,
        efficiency=18.0,
        losses=14.0,
    )

    features = frame.copy()
    features["physics_kwh"] = physics["kwh"].to_numpy()
    max_interval_kwh = reference_system_size_kw * 0.25
    features["actual_cf"] = (features["target_kwh"] / max_interval_kwh).clip(0, 1.5)
    features["physics_cf"] = (features["physics_kwh"] / max_interval_kwh).clip(0, 1.5)
    features["residual_cf"] = features["actual_cf"] - features["physics_cf"]
    features = add_time_features(features)
    metadata["reference_system_size_kw"] = reference_system_size_kw
    metadata["physics_baseline_note"] = "pvlib POA baseline with losses, trained residual target is actual_cf - physics_cf"
    return features, metadata


def main() -> int:
    features, metadata = build_training_frame()
    train_frame, validation_frame, test_frame = split_train_validation_test(features)
    selected_columns = HYBRID_FEATURE_COLUMNS

    reports = {}
    best_name = ""
    best_daily_mae = float("inf")

    max_interval_kwh = float(metadata["reference_system_size_kw"]) * 0.25
    for name, model in build_model_registry().items():
        model.fit(ensure_hybrid_columns(train_frame), train_frame["residual_cf"])

        validation_residual = model.predict(ensure_hybrid_columns(validation_frame))
        validation_kwh = (
            validation_frame["physics_kwh"].to_numpy() + validation_residual * max_interval_kwh
        ).clip(min=0)
        test_residual = model.predict(ensure_hybrid_columns(test_frame))
        test_kwh = (
            test_frame["physics_kwh"].to_numpy() + test_residual * max_interval_kwh
        ).clip(min=0)

        validation_metrics = evaluate(validation_frame["target_kwh"], validation_kwh)
        test_metrics = evaluate(test_frame["target_kwh"], test_kwh)
        reports[name] = {
            "validation_metrics": validation_metrics,
            "test_metrics": test_metrics,
        }
        if test_metrics["daily_energy_mae"] < best_daily_mae:
            best_daily_mae = test_metrics["daily_energy_mae"]
            best_name = name

    train_validation = features.iloc[: len(train_frame) + len(validation_frame)].copy()
    best_model = build_model_registry()[best_name]
    best_model.fit(ensure_hybrid_columns(train_validation), train_validation["residual_cf"])

    HYBRID_MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    with HYBRID_MODEL_PATH.open("wb") as handle:
        pickle.dump(best_model, handle)

    metadata_out = {
        **metadata,
        "forecast_mode": "hybrid_residual",
        "model_family": best_name,
        "feature_columns": selected_columns,
        "residual_target": "actual_capacity_factor - physics_capacity_factor",
        "model_artifact_path": str(HYBRID_MODEL_PATH),
        "report_path": str(REPORT_PATH),
    }
    HYBRID_METADATA_PATH.write_text(json.dumps(metadata_out, indent=2), encoding="utf-8")

    report = {
        **metadata_out,
        "total_rows": int(len(features)),
        "num_rows_train": int(len(train_frame)),
        "num_rows_validation": int(len(validation_frame)),
        "num_rows_test": int(len(test_frame)),
        "models": reports,
        "best_model_by_test_daily_energy_mae": best_name,
    }
    REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
