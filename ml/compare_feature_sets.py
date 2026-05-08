"""Compare cold-start vs adaptive ML-only feature sets on the OPSD experiment."""

from __future__ import annotations

from pathlib import Path
import json

import pandas as pd

from train_baseline import (
    ARTIFACTS_DIR,
    WEATHER_DATA_PATH,
    build_features,
    build_model_registry,
    evaluate_predictions,
    load_dataset,
    merge_optional_weather,
    persistence_predict,
    split_train_validation_test,
)


REPORT_PATH = ARTIFACTS_DIR / "feature_set_report.json"


def feature_sets(columns: list[str]) -> dict[str, list[str]]:
    lag_columns = [column for column in columns if column.startswith("lag_") or column.startswith("rolling_mean_")]
    cold_start_columns = [column for column in columns if column not in lag_columns]
    return {
        "cold_start_weather_time": cold_start_columns,
        "adaptive_with_lags": columns,
    }


def run() -> int:
    frame, target_column, _ = load_dataset()
    frame = merge_optional_weather(frame)
    features = build_features(frame)

    all_feature_columns = [column for column in features.columns if column not in {"timestamp", "target_kwh"}]
    train_frame, validation_frame, test_frame = split_train_validation_test(features)

    report: dict[str, object] = {
        "dataset_target_column": target_column,
        "weather_features_enabled": WEATHER_DATA_PATH.exists(),
        "feature_sets": {},
    }

    for feature_set_name, selected_columns in feature_sets(all_feature_columns).items():
        model_results: dict[str, object] = {}
        preview_columns = set(selected_columns)
        can_use_persistence = "lag_1" in preview_columns

        for model_name, model in build_model_registry().items():
            model.fit(train_frame[selected_columns], train_frame["target_kwh"])
            validation_predictions = model.predict(validation_frame[selected_columns])
            test_predictions = model.predict(test_frame[selected_columns])
            model_results[model_name] = {
                "validation_metrics": evaluate_predictions(validation_frame["target_kwh"], validation_predictions),
                "test_metrics": evaluate_predictions(test_frame["target_kwh"], test_predictions),
            }

        if can_use_persistence:
            model_results["persistence_baseline"] = {
                "validation_metrics": evaluate_predictions(
                    validation_frame["target_kwh"], persistence_predict(validation_frame)
                ),
                "test_metrics": evaluate_predictions(test_frame["target_kwh"], persistence_predict(test_frame)),
            }

        report["feature_sets"][feature_set_name] = {
            "feature_count": len(selected_columns),
            "includes_target_history": can_use_persistence,
            "models": model_results,
        }

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
