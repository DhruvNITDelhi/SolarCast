# ML Experiment Results

This document records what we have actually tested in the `ML forecast` worktree, what data we used, what issues we found, and what the current results mean.

## 1. Objective

Build a credible ML-only forecasting track for SolarCast using freely available real PV data, while keeping the production physics model separate and untouched.

## 2. Data sources used

### Measured PV generation
- Dataset: Open Power System Data Household Data
- Source: https://data.open-power-system-data.org/household_data
- File used: `household_data_15min_singleindex.csv`
- Type: measured household and small-business energy generation / consumption time series
- Resolution: 15 minutes

Why this source is acceptable:
- official OPSD research dataset
- documented publicly
- structured tabular format
- real measured PV data, not simulated labels

### Weather features
- Source: Open-Meteo historical archive output saved locally in `ml\data\processed\weather_features.csv`
- Purpose: enrich the ML-only model with cloud cover, temperature, and solar radiation features

## 3. Data audit findings

The downloaded OPSD file is useful and standard, but there was an important modeling trap:

- the PV fields are cumulative meter readings, not direct per-interval generation labels
- if we train directly on raw cumulative values, the model learns the wrong target
- the correct target is the 15-minute energy increment computed by differencing the cumulative meter series

We fixed the training pipeline to do that automatically.

The training script now also audits all PV columns and writes the summary to:
- `ml\data\processed\target_audit.csv`

Latest selected target:
- `DE_KN_residential3_pv`

Why it was selected:
- highest coverage among available PV columns
- low interpolation rate relative to available rows
- continuous 15-minute series after cleaning

## 4. Important issues discovered and fixed

### Issue A: wrong label interpretation
Original problem:
- the pipeline treated cumulative PV meter readings as direct forecast targets

Fix:
- convert cumulative readings into per-interval `target_kwh` using first differences
- drop the initial undefined row and any negative deltas

Why this matters:
- this was the biggest reason the first ML results were misleading

### Issue B: weather alignment was too strict
Original problem:
- weather data was hourly
- PV data was 15-minute
- exact timestamp merge caused most rows to be dropped

Fix:
- resample weather features to 15-minute intervals before merging

Why this matters:
- the training set grew from a small hourly-overlap subset to the full usable 15-minute series

## 5. Current pipeline shape

Current feature groups:
- time features: hour, minute, weekday, month, day-of-year
- cyclical encodings: sin/cos hour and day-of-year
- lag features: recent target history
- rolling mean features
- weather features when available:
  - temperature_2m
  - cloud_cover
  - shortwave_radiation
  - direct_radiation
  - diffuse_radiation

Current models:
- Ridge Regression
- HistGradientBoostingRegressor
- RandomForestRegressor
- persistence baseline for comparison

Additional comparison now available:
- `cold_start_weather_time`: no lagged actual generation features
- `adaptive_with_lags`: includes recent target history and rolling means

## 6. Latest metrics

Latest report file:
- `ml\artifacts\baseline_report.json`
- `ml\artifacts\feature_set_report.json`

Current run summary:
- selected target: `DE_KN_residential3_pv`
- train rows: `63084`
- validation rows: `13518`
- test rows: `13519`
- weather features enabled: `true`

### Validation

| Model | MAE | RMSE | Daily Energy MAE |
|---|---:|---:|---:|
| Ridge | 0.0563 | 0.0841 | 2.7323 |
| HistGradientBoosting | 0.0297 | 0.1137 | 1.3330 |
| RandomForest | 0.0226 | 0.2797 | 1.1219 |
| Persistence baseline | 0.0151 | 0.0379 | 0.0025 |

### Test

| Model | MAE | RMSE | Daily Energy MAE |
|---|---:|---:|---:|
| Ridge | 0.0745 | 0.1188 | 3.2689 |
| HistGradientBoosting | 0.0417 | 0.1370 | 1.2932 |
| RandomForest | 0.0251 | 0.0564 | 0.5071 |
| Persistence baseline | 0.0302 | 0.0627 | 0.1170 |

## 7. What these results mean

Main takeaways:
- the official OPSD dataset is usable and worth continuing with
- fixing the target definition and weather alignment made the ML results much more realistic
- the ML-only models are now meaningful, not broken
- persistence is still very strong, which is common in short-horizon PV forecasting
- Random Forest is now competitive on test MAE and RMSE, but persistence remains stronger on daily energy error

Interpretation:
- we do not yet have a publishable claim that "ML-only clearly beats simple baselines"
- we do have a valuable research result that proper data handling matters more than blindly increasing model complexity
- we also now have a clean base to continue toward stronger models

## 7A. Cold-start vs adaptive ML-only comparison

This is an important distinction for SolarCast:

- `cold-start` means the model only uses time + weather features and can forecast without needing recent actual PV output
- `adaptive` means the model also uses recent plant history through lag features

For a web app that should work immediately for a new user, the cold-start behavior matters more.
For a repeat user with historical readings, adaptive behavior can be stronger.

Latest feature-set comparison file:
- `ml\artifacts\feature_set_report.json`

Summary of best test MAE by feature set:

| Feature set | Best model | Test MAE | Comment |
|---|---|---:|---|
| Cold-start weather + time | Random Forest | 0.0539 | usable baseline, no target history required |
| Adaptive with lags | Random Forest | 0.0251 | much stronger, but depends on recent actual generation |
| Persistence | Persistence baseline | 0.0302 | still a very strong short-horizon baseline |

Key takeaway:
- the current ML-only branch works much better when recent actual generation is available
- the cold-start variant is weaker, which means it is not yet a drop-in universal replacement for the physics model
- this is exactly why the hybrid direction remains strong

## 8. Current limitations

- this is still effectively a site-specific experiment, not yet a general multi-site deployment model
- lag features make the current ML setup adaptive, but not a true cold-start replacement for the current physics model
- the present ML-only pipeline is not yet ready to drop into the web app as a universal forecasting engine

## 9. Recommended next steps

In order of importance:

1. Build a `cold-start` ML-only variant without lagged actual generation
2. Compare `weather-only/time-only` vs `weather + lag` feature sets
3. Add a second dataset or additional PV sites for stronger generalization evidence
4. Benchmark the ML-only branch directly against the current SolarCast physics baseline
5. If ML-only stays weaker, prioritize hybrid `physics + ML correction` rather than replacement

## 9A. ML-only inference layer status

We now have a first usable ML-only inference path:

- trainer: `ml\train_ml_only_model.py`
- shared feature logic: `ml\ml_only_model.py`
- predictor: `ml\predict_ml_only.py`

What it does:
- trains a cold-start ML-only model using time + weather features
- exports a reusable model artifact and metadata
- produces 15-minute forecast output in a SolarCast-like JSON shape
- can run from a local weather CSV or from live Open-Meteo forecast weather

Current exported artifact files:
- `ml\artifacts\ml_only_model.pkl`
- `ml\artifacts\ml_only_model_metadata.json`
- `ml\artifacts\ml_only_training_report.json`

Important limitation:
- this is the first usable ML-only path, not the final publishable model
- it is intended for continued experimentation and interface design
- it is not yet proven to beat the current physics model

## 9B. Physics vs ML benchmark route

We now also have two comparison paths:

- API route: `POST /forecast/compare`
- offline benchmark script: `ml\benchmark_vs_physics.py`

Current verified offline benchmark artifact:
- `ml\artifacts\physics_vs_ml_benchmark.json`

This gives us a reproducible way to compare:
- total predicted daily yield
- peak interval generation
- hourly MAE between the two engines
- interval alignment and overlap

This is useful for:
- thesis screenshots and benchmark tables
- deciding when ML-only is too unstable
- documenting why a hybrid approach may still be preferable

## 10. Repro commands

Install dependencies:

```powershell
C:\Python312\python.exe -m pip install --user -r ml\requirements.txt
```

Download OPSD data:

```powershell
C:\Python312\python.exe ml\download_opsd.py
```

Train the current baseline:

```powershell
C:\Python312\python.exe ml\train_baseline.py
```

Optional weather enrichment if you need to regenerate the weather file:

```powershell
copy ml\site_config.example.json ml\site_config.json
C:\Python312\python.exe ml\enrich_weather.py
```
