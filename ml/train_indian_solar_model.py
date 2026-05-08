"""Train SolarCast ML models on the Indian solar plant dataset."""

from __future__ import annotations

import argparse
import json
import pickle

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from indian_solar_dataset import (
    ARTIFACTS_DIR,
    PROCESSED_DIR,
    add_lag_features,
    available_plants,
    cold_start_feature_columns,
    load_indian_solar_dataset,
    split_train_validation_test,
)
from ml_only_model import MODEL_ARTIFACT_PATH, save_model_metadata


REPORT_PATH = ARTIFACTS_DIR / "indian_solar_training_report.json"
METADATA_PATH = ARTIFACTS_DIR / "ml_only_model_metadata.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train SolarCast on Indian solar plant data.")
    parser.add_argument("--plant", choices=available_plants(), default="plant_1")
    parser.add_argument("--aggregation", choices=["plant", "inverter"], default="plant")
    parser.add_argument(
        "--export",
        action="store_true",
        help="Export the best cold-start model to ml_only_model.pkl for the web app.",
    )
    return parser.parse_args()


def evaluate_predictions(actual: pd.Series, predicted: np.ndarray) -> dict[str, float]:
    daily = (
        pd.DataFrame({"actual": actual.values, "predicted": predicted})
        .assign(day=np.arange(len(actual)) // 96)
        .groupby("day")
        .sum()
    )
    return {
        "mae": float(mean_absolute_error(actual, predicted)),
        "rmse": float(np.sqrt(mean_squared_error(actual, predicted))),
        "daily_energy_mae": float(mean_absolute_error(daily["actual"], daily["predicted"])),
    }


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
            max_depth=6,
            max_iter=300,
            random_state=42,
        ),
        "random_forest": RandomForestRegressor(
            n_estimators=250,
            max_depth=18,
            min_samples_leaf=2,
            random_state=42,
            n_jobs=1,
        ),
    }


def add_persistence_metrics(report: dict, validation_frame: pd.DataFrame, test_frame: pd.DataFrame) -> None:
    if "lag_1" not in validation_frame.columns:
        return
    report["persistence_baseline"] = {
        "validation_metrics": evaluate_predictions(validation_frame["target_kwh"], validation_frame["lag_1"].to_numpy()),
        "test_metrics": evaluate_predictions(test_frame["target_kwh"], test_frame["lag_1"].to_numpy()),
    }


def save_preview_plot(preview: pd.DataFrame) -> None:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    sample = preview.head(96 * 7).copy()
    plt.figure(figsize=(12, 5))
    plt.plot(sample["timestamp"], sample["target_kwh"], label="Actual", linewidth=1.8)
    for column in [c for c in sample.columns if c.startswith("prediction_")]:
        plt.plot(sample["timestamp"], sample[column], label=column.replace("prediction_", ""), linewidth=1.2)
    plt.title("Indian solar plant 15-minute generation forecast preview")
    plt.xlabel("Timestamp")
    plt.ylabel("kWh")
    plt.legend()
    plt.tight_layout()
    plt.savefig(ARTIFACTS_DIR / "indian_solar_prediction_preview.png", dpi=150)
    plt.close()


def train_feature_set(
    feature_set_name: str,
    features: pd.DataFrame,
    selected_columns: list[str],
) -> tuple[dict[str, object], pd.DataFrame, str]:
    train_frame, validation_frame, test_frame = split_train_validation_test(features)
    model_reports: dict[str, object] = {}
    preview = test_frame[["timestamp", "target_kwh"]].copy()

    best_model_name = ""
    best_daily_mae = float("inf")

    for model_name, model in build_model_registry().items():
        model.fit(train_frame[selected_columns], train_frame["target_kwh"])
        validation_predictions = model.predict(validation_frame[selected_columns]).clip(min=0)
        test_predictions = model.predict(test_frame[selected_columns]).clip(min=0)
        preview[f"prediction_{feature_set_name}_{model_name}"] = test_predictions

        validation_metrics = evaluate_predictions(validation_frame["target_kwh"], validation_predictions)
        test_metrics = evaluate_predictions(test_frame["target_kwh"], test_predictions)
        model_reports[model_name] = {
            "validation_metrics": validation_metrics,
            "test_metrics": test_metrics,
        }
        if test_metrics["daily_energy_mae"] < best_daily_mae:
            best_daily_mae = test_metrics["daily_energy_mae"]
            best_model_name = model_name

    report = {
        "feature_count": len(selected_columns),
        "feature_columns": selected_columns,
        "num_rows_train": int(len(train_frame)),
        "num_rows_validation": int(len(validation_frame)),
        "num_rows_test": int(len(test_frame)),
        "models": model_reports,
    }
    add_persistence_metrics(report, validation_frame, test_frame)
    return report, preview, best_model_name


def export_web_model(
    features: pd.DataFrame,
    selected_columns: list[str],
    metadata: dict[str, object],
    model_name: str,
) -> None:
    train_frame, validation_frame, _ = split_train_validation_test(features)
    train_validation = features.iloc[: len(train_frame) + len(validation_frame)].copy()
    model = build_model_registry()[model_name]
    model.fit(train_validation[selected_columns], train_validation["target_kwh"])

    reference_system_size_kw = max(
        1.0,
        round(float(train_validation["target_kw"].quantile(0.995)), 2),
    )

    MODEL_ARTIFACT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with MODEL_ARTIFACT_PATH.open("wb") as handle:
        pickle.dump(model, handle)

    save_model_metadata(
        {
            "forecast_mode": "ml_only_cold_start",
            "model_family": model_name,
            "dataset": metadata["dataset"],
            "dataset_slug": metadata["dataset_slug"],
            "dataset_target_column": f"{metadata['plant']}_plant_ac_power",
            "plant": metadata["plant"],
            "latitude": metadata["latitude"],
            "longitude": metadata["longitude"],
            "timezone": metadata["timezone"],
            "feature_columns": selected_columns,
            "reference_system_size_kw": reference_system_size_kw,
            "report_path": str(REPORT_PATH),
            "model_artifact_path": str(MODEL_ARTIFACT_PATH),
        }
    )


def main() -> int:
    args = parse_args()
    frame, metadata = load_indian_solar_dataset(args.plant, aggregation=args.aggregation)
    frame = frame.dropna().reset_index(drop=True)

    cold_columns = cold_start_feature_columns(frame)
    adaptive_frame = add_lag_features(frame)
    adaptive_columns = cold_columns + [
        column for column in adaptive_frame.columns if column.startswith("lag_") or column.startswith("rolling_mean_")
    ]

    cold_report, cold_preview, cold_best = train_feature_set("cold_start", frame, cold_columns)
    adaptive_report, adaptive_preview, adaptive_best = train_feature_set("adaptive", adaptive_frame, adaptive_columns)

    preview = cold_preview.merge(adaptive_preview, on=["timestamp", "target_kwh"], how="outer")
    save_preview_plot(preview)

    report = {
        **metadata,
        "target_is_interval_energy": True,
        "target_note": "target_kwh is AC_POWER converted to 15-minute energy using AC_POWER * 0.25",
        "total_rows": int(len(frame)),
        "feature_sets": {
            "cold_start_weather_time": {
                **cold_report,
                "best_model_by_test_daily_energy_mae": cold_best,
                "includes_target_history": False,
            },
            "adaptive_with_lags": {
                **adaptive_report,
                "best_model_by_test_daily_energy_mae": adaptive_best,
                "includes_target_history": True,
            },
        },
    }

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    preview.to_csv(PROCESSED_DIR / "indian_solar_model_preview.csv", index=False)
    REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")

    if args.export:
        export_web_model(frame, cold_columns, metadata, cold_best)
        report["exported_model_metadata_path"] = str(METADATA_PATH)
        REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
