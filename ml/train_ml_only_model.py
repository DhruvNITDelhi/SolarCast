"""Train and save the SolarCast ML-only cold-start forecast artifact."""

from __future__ import annotations

import json
import pickle

try:
    from .train_baseline import evaluate_predictions, load_dataset, merge_optional_weather, split_train_validation_test
    from .ml_only_model import (
        ARTIFACTS_DIR,
        MODEL_ARTIFACT_PATH,
        build_cold_start_features,
        build_ml_only_model,
        cold_start_feature_columns,
        save_model_metadata,
    )
except ImportError:
    from train_baseline import evaluate_predictions, load_dataset, merge_optional_weather, split_train_validation_test
    from ml_only_model import (
        ARTIFACTS_DIR,
        MODEL_ARTIFACT_PATH,
        build_cold_start_features,
        build_ml_only_model,
        cold_start_feature_columns,
        save_model_metadata,
    )


REPORT_PATH = ARTIFACTS_DIR / "ml_only_training_report.json"


def main() -> int:
    frame, target_column, _ = load_dataset()
    frame = merge_optional_weather(frame)
    features = build_cold_start_features(frame)
    features["target_kwh"] = frame["target_kwh"].to_numpy()

    selected_columns = cold_start_feature_columns(features)
    train_frame, validation_frame, test_frame = split_train_validation_test(features)

    model = build_ml_only_model()
    model.fit(train_frame[selected_columns], train_frame["target_kwh"])

    validation_predictions = model.predict(validation_frame[selected_columns])
    test_predictions = model.predict(test_frame[selected_columns])

    train_validation_frame = features.iloc[: len(train_frame) + len(validation_frame)].copy()
    reference_system_size_kw = max(
        1.0,
        round(float(train_validation_frame["target_kwh"].quantile(0.995) / 0.25), 2),
    )

    report = {
        "model_family": "RandomForestRegressor",
        "forecast_mode": "ml_only_cold_start",
        "dataset_target_column": target_column,
        "feature_columns": selected_columns,
        "feature_count": len(selected_columns),
        "reference_system_size_kw": reference_system_size_kw,
        "num_rows_train": int(len(train_frame)),
        "num_rows_validation": int(len(validation_frame)),
        "num_rows_test": int(len(test_frame)),
        "validation_metrics": evaluate_predictions(validation_frame["target_kwh"], validation_predictions),
        "test_metrics": evaluate_predictions(test_frame["target_kwh"], test_predictions),
    }

    # Refit on train + validation before exporting the artifact for inference use.
    export_model = build_ml_only_model()
    export_model.fit(train_validation_frame[selected_columns], train_validation_frame["target_kwh"])

    MODEL_ARTIFACT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with MODEL_ARTIFACT_PATH.open("wb") as handle:
        pickle.dump(export_model, handle)

    save_model_metadata(
        {
            "forecast_mode": "ml_only_cold_start",
            "dataset_target_column": target_column,
            "feature_columns": selected_columns,
            "reference_system_size_kw": reference_system_size_kw,
            "report_path": str(REPORT_PATH),
            "model_artifact_path": str(MODEL_ARTIFACT_PATH),
        }
    )
    REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(json.dumps(report, indent=2))
    print(f"Saved model artifact to {MODEL_ARTIFACT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
