# ML Forecast Track

This worktree is the isolated ML experimentation track for SolarCast.

Goal:
- train and evaluate a data-driven solar generation predictor
- use freely available measured PV generation data
- keep the production physics model untouched until the ML path proves value

Current public dataset choice:
- Open Power System Data household data
- official source: https://data.open-power-system-data.org/household_data
- measured residential and small-business PV generation
- available in 15-minute resolution, which matches SolarCast well

Why this dataset:
- real measured PV output, not synthetic labels
- openly downloadable
- small enough to iterate with locally
- structured enough to build a baseline pipeline quickly
- official OPSD documentation states these PV fields are measured cumulative energy readings,
  so the ML target must be derived as per-interval energy by differencing the meter series

Planned ML approach:
1. Download 15-minute OPSD PV data.
2. Extract a single PV generation series as the prediction target.
3. Optionally enrich with historical weather features if site coordinates are known.
4. Build time-based and lag-based features.
5. Train a baseline regression model.
6. Evaluate train, validation, and test performance.
7. Compare against a naive persistence baseline.

## Data quality status

Current verdict on the downloaded OPSD dataset:
- yes, it is a standard and credible research dataset, not a random dump
- source is the official OPSD household data package
- timestamps are regular 15-minute intervals
- PV columns are cumulative meter readings, so raw values are not valid ML labels by themselves
- target columns differ in coverage and interpolation rate, so the pipeline now audits PV columns before training

The current training run automatically writes a target audit to:
- `ml\data\processed\target_audit.csv`

For the latest detailed findings and metrics, see:
- `ml\RESULTS.md`

This branch is intentionally separate from the product branch so we can:
- test different feature engineering ideas
- try multiple model families
- work with real data
- avoid destabilizing the production app

## Suggested Setup

From this worktree root:

```powershell
cd "C:\Users\Lenovo\OneDrive\Desktop\SolarCast\ML forecast"
python -m venv .venv
.venv\Scripts\activate
pip install -r ml\requirements.txt
```

## First Commands

Download data:

```powershell
python ml\download_opsd.py
```

Train and compare baseline models:

```powershell
python ml\train_baseline.py
```

Compare cold-start versus adaptive feature sets:

```powershell
python ml\compare_feature_sets.py
```

Train and export the ML-only cold-start model artifact:

```powershell
python ml\train_ml_only_model.py
```

Run ML-only inference from a local weather CSV:

```powershell
python ml\predict_ml_only.py --weather-csv ml\data\processed\weather_features.csv --forecast-hours 24
```

Run ML-only inference from live Open-Meteo forecast weather:

```powershell
python ml\predict_ml_only.py --latitude 28.6139 --longitude 77.2090 --forecast-hours 24 --timezone auto
```

Benchmark ML-only directly against the physics engine using local weather features:

```powershell
python ml\benchmark_vs_physics.py --latitude 47.6947 --longitude 9.1900 --system-size-kw 10 --timezone Europe/Berlin --weather-csv ml\data\processed\weather_features.csv
```

Backend API routes in this worktree:

```text
POST /forecast
POST /forecast/ml
POST /forecast/compare
```

Optional weather enrichment:

```powershell
copy ml\site_config.example.json ml\site_config.json
python ml\enrich_weather.py
```

## Outputs

The pipeline writes to:
- `ml\data\raw\`
- `ml\data\processed\`
- `ml\artifacts\`
- `ml\OPTIONAL_INTEGRATION.md`

## Optional ML Layer Design

This branch is building an optional ML layer, not a replacement for the current SolarCast model.

Intended production shape later:
- current physics model remains primary
- ML path becomes a correction layer or alternate experiment mode
- rollout stays opt-in until metrics justify promotion

That keeps the production system safe while giving us room to test whether ML adds real forecasting value.

## Current experiment outputs

After training, the branch should produce:
- model comparison metrics JSON
- preview CSV with multiple model predictions
- forecast preview plot
- daily totals comparison plot
- target audit CSV

Latest artifacts:
- `ml\artifacts\baseline_report.json`
- `ml\artifacts\feature_set_report.json`
- `ml\artifacts\ml_only_training_report.json`
- `ml\artifacts\ml_only_model.pkl`
- `ml\artifacts\ml_only_model_metadata.json`
- `ml\artifacts\physics_vs_ml_benchmark.json`
- `ml\artifacts\prediction_preview.png`
- `ml\artifacts\daily_totals_comparison.png`
- `ml\data\processed\model_comparison_preview.csv`
- `ml\data\processed\target_audit.csv`

## Next Intended Upgrades

- try site-specific vs cross-site training
- add direct benchmarking against the SolarCast physics baseline
- build a cold-start ML-only model that does not rely on lagged actual generation
- build a first residual correction model
- test promotion criteria for optional deployment
