"""Train and compare baseline ML models on measured OPSD PV generation data."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.base import RegressorMixin
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


RAW_DATA_PATH = Path(__file__).resolve().parent / "data" / "raw" / "household_data_15min_singleindex.csv"
PROCESSED_DIR = Path(__file__).resolve().parent / "data" / "processed"
ARTIFACTS_DIR = Path(__file__).resolve().parent / "artifacts"
WEATHER_DATA_PATH = PROCESSED_DIR / "weather_features.csv"
TARGET_COLUMN_PATH = PROCESSED_DIR / "target_audit.csv"
TARGET_COLUMN_OVERRIDE = None


def list_pv_columns(frame: pd.DataFrame) -> list[str]:
    pv_columns = [column for column in frame.columns if "_pv" in column.lower()]
    if not pv_columns:
        raise ValueError("No PV generation columns were found in the OPSD dataset.")
    return pv_columns


def audit_target_columns(frame: pd.DataFrame) -> pd.DataFrame:
    """Score OPSD PV columns so the training run uses the cleanest measured series."""
    pv_columns = list_pv_columns(frame)
    interpolation = frame["interpolated"].fillna("")
    audit_rows: list[dict[str, float | int | str]] = []

    for column in pv_columns:
        cumulative = frame[column]
        available = cumulative.dropna()
        interpolation_hits = interpolation.str.contains(column, regex=False).sum()

        if available.empty:
            continue

        interval_energy = available.diff().dropna()
        interval_energy = interval_energy[interval_energy >= 0]

        audit_rows.append(
            {
                "target_column": column,
                "available_rows": int(available.shape[0]),
                "coverage_ratio": float(available.shape[0] / frame.shape[0]),
                "interpolated_rows": int(interpolation_hits),
                "interpolated_ratio_of_available": float(interpolation_hits / available.shape[0]),
                "mean_interval_kwh": float(interval_energy.mean()) if not interval_energy.empty else 0.0,
                "max_interval_kwh": float(interval_energy.max()) if not interval_energy.empty else 0.0,
            }
        )

    audit = pd.DataFrame(audit_rows)
    if audit.empty:
        raise ValueError("Unable to build a usable PV target audit from the OPSD dataset.")

    # Favor long, continuous, minimally interpolated measured series.
    audit = audit.sort_values(
        by=["coverage_ratio", "interpolated_ratio_of_available", "mean_interval_kwh"],
        ascending=[False, True, False],
    ).reset_index(drop=True)
    return audit


def select_target_column(audit: pd.DataFrame) -> str:
    if TARGET_COLUMN_OVERRIDE:
        matches = audit.loc[audit["target_column"] == TARGET_COLUMN_OVERRIDE]
        if not matches.empty:
            return str(matches.iloc[0]["target_column"])
        raise ValueError(f"Requested target override {TARGET_COLUMN_OVERRIDE!r} is not present in the audit.")
    return str(audit.iloc[0]["target_column"])


def load_dataset() -> tuple[pd.DataFrame, str, pd.DataFrame]:
    if not RAW_DATA_PATH.exists():
        raise FileNotFoundError(
            f"Dataset not found at {RAW_DATA_PATH}. Run `python ml\\download_opsd.py` first."
        )

    frame = pd.read_csv(RAW_DATA_PATH)
    audit = audit_target_columns(frame)
    target_column = select_target_column(audit)
    frame["timestamp"] = pd.to_datetime(frame["cet_cest_timestamp"], utc=True).dt.tz_localize(None)
    frame = frame[["timestamp", target_column]].rename(columns={target_column: "target_cumulative_kwh"})
    frame = frame.dropna().sort_values("timestamp").reset_index(drop=True)

    # OPSD PV fields are cumulative meter readings, so the ML target must be the per-interval increment.
    frame["target_kwh"] = frame["target_cumulative_kwh"].diff()
    frame = frame.loc[frame["target_kwh"].notna()].copy()
    frame = frame.loc[frame["target_kwh"] >= 0].reset_index(drop=True)
    frame = frame[["timestamp", "target_kwh"]]
    return frame, target_column, audit


def merge_optional_weather(frame: pd.DataFrame) -> pd.DataFrame:
    if not WEATHER_DATA_PATH.exists():
        return frame

    weather = pd.read_csv(WEATHER_DATA_PATH)
    weather["timestamp"] = pd.to_datetime(weather["timestamp"], utc=True).dt.tz_localize(None)
    weather = weather.sort_values("timestamp").reset_index(drop=True)
    if len(weather) > 1:
        median_step = weather["timestamp"].diff().dropna().median()
        if median_step and median_step > pd.Timedelta(minutes=15):
            weather = (
                weather.set_index("timestamp")
                .resample("15min")
                .interpolate(method="time")
                .reset_index()
            )

    merged = frame.merge(weather, on="timestamp", how="left")
    return merged


def build_features(frame: pd.DataFrame) -> pd.DataFrame:
    features = frame.copy()
    timestamp = features["timestamp"]

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

    for lag in (1, 2, 4, 96):
        features[f"lag_{lag}"] = features["target_kwh"].shift(lag)

    features["rolling_mean_4"] = features["target_kwh"].shift(1).rolling(4).mean()
    features["rolling_mean_16"] = features["target_kwh"].shift(1).rolling(16).mean()

    features = features.dropna().reset_index(drop=True)
    return features


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


def persistence_predict(frame: pd.DataFrame) -> np.ndarray:
    return frame["lag_1"].to_numpy()


def build_model_registry() -> dict[str, RegressorMixin]:
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
            n_estimators=150,
            max_depth=16,
            min_samples_leaf=2,
            random_state=42,
            n_jobs=1,
        ),
    }


def save_plots(preview: pd.DataFrame) -> None:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    sample = preview.head(96 * 5).copy()
    plt.figure(figsize=(12, 5))
    plt.plot(sample["timestamp"], sample["target_kwh"], label="Actual", linewidth=1.8)
    if "prediction_hist_gradient_boosting" in sample:
        plt.plot(
            sample["timestamp"],
            sample["prediction_hist_gradient_boosting"],
            label="HistGradientBoosting",
            linewidth=1.5,
        )
    if "prediction_persistence" in sample:
        plt.plot(sample["timestamp"], sample["prediction_persistence"], label="Persistence", linewidth=1.2)
    plt.title("15-minute PV generation preview")
    plt.xlabel("Timestamp")
    plt.ylabel("kWh")
    plt.legend()
    plt.tight_layout()
    plt.savefig(ARTIFACTS_DIR / "prediction_preview.png", dpi=150)
    plt.close()

    daily = preview.copy()
    daily["date"] = pd.to_datetime(daily["timestamp"]).dt.date
    aggregation = {
        "target_kwh": "sum",
    }
    prediction_columns = [column for column in preview.columns if column.startswith("prediction_")]
    for column in prediction_columns:
        aggregation[column] = "sum"
    daily = daily.groupby("date", as_index=False).agg(aggregation).head(14)

    plt.figure(figsize=(12, 5))
    plt.plot(daily["date"], daily["target_kwh"], label="Actual daily total", marker="o")
    for column in prediction_columns:
        plt.plot(daily["date"], daily[column], label=column.replace("prediction_", "").replace("_", " "), marker="o")
    plt.title("Daily energy totals comparison")
    plt.xlabel("Date")
    plt.ylabel("kWh")
    plt.legend()
    plt.tight_layout()
    plt.savefig(ARTIFACTS_DIR / "daily_totals_comparison.png", dpi=150)
    plt.close()


def main() -> int:
    frame, target_column, target_audit = load_dataset()
    frame = merge_optional_weather(frame)
    features = build_features(frame)

    feature_columns = [column for column in features.columns if column not in {"timestamp", "target_kwh"}]
    train_frame, validation_frame, test_frame = split_train_validation_test(features)

    model_registry = build_model_registry()
    model_reports: dict[str, dict[str, dict[str, float]]] = {}
    preview = test_frame[["timestamp", "target_kwh"]].copy()

    for model_name, model in model_registry.items():
        model.fit(train_frame[feature_columns], train_frame["target_kwh"])
        validation_predictions = model.predict(validation_frame[feature_columns])
        test_predictions = model.predict(test_frame[feature_columns])
        preview[f"prediction_{model_name}"] = test_predictions

        model_reports[model_name] = {
            "validation_metrics": evaluate_predictions(validation_frame["target_kwh"], validation_predictions),
            "test_metrics": evaluate_predictions(test_frame["target_kwh"], test_predictions),
        }

    validation_persistence = persistence_predict(validation_frame)
    test_persistence = persistence_predict(test_frame)
    preview["prediction_persistence"] = test_persistence

    report = {
        "dataset_target_column": target_column,
        "target_is_interval_energy": True,
        "target_selection_note": (
            "Selected from OPSD cumulative PV meter series using highest coverage and low interpolation; "
            "training target is the per-15-minute energy increment computed by differencing."
        ),
        "num_rows_train": int(len(train_frame)),
        "num_rows_validation": int(len(validation_frame)),
        "num_rows_test": int(len(test_frame)),
        "feature_count": int(len(feature_columns)),
        "weather_features_enabled": WEATHER_DATA_PATH.exists(),
        "models": model_reports,
        "persistence_baseline": {
            "validation_metrics": evaluate_predictions(validation_frame["target_kwh"], validation_persistence),
            "test_metrics": evaluate_predictions(test_frame["target_kwh"], test_persistence),
        },
    }

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    preview.head(96 * 14).to_csv(PROCESSED_DIR / "model_comparison_preview.csv", index=False)
    target_audit.to_csv(TARGET_COLUMN_PATH, index=False)
    (ARTIFACTS_DIR / "baseline_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    save_plots(preview)

    print("Baseline model comparison complete.")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
