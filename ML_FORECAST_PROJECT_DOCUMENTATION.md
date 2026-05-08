# SolarCast ML Forecast Project Documentation

Last updated: 2026-05-08

## 1. Project Summary

SolarCast currently has three forecasting tracks:

1. **Physics-based forecast**
   - Uses solar geometry, irradiance transposition, and system parameters.
   - Implemented mainly in `ML forecast/backend/solar_engine.py`.
   - Uses `pvlib` to compute plane-of-array irradiance from GHI/DNI/DHI.

2. **Experimental ML-only forecast**
   - Uses a trained cold-start machine learning model.
   - The current exported model has been retrained on the Indian Kaggle solar plant dataset.
   - Implemented mainly in `ML forecast/ml/train_indian_solar_model.py`, `ML forecast/ml/indian_solar_dataset.py`, `ML forecast/ml/ml_only_model.py`, and `ML forecast/backend/ml_engine.py`.
   - Exposed in the app through:
     - `POST /forecast/ml`
     - `POST /forecast/compare`

3. **Patent-track hybrid forecast**
   - Uses the physics forecast as the baseline and an ML model only to predict the residual error.
   - Implemented mainly in `ML forecast/backend/hybrid_engine.py`, `ML forecast/ml/hybrid_residual_model.py`, and `ML forecast/ml/train_hybrid_residual_model.py`.
   - Exposed through:
     - `POST /forecast/hybrid`
     - `POST /forecast/compare`

Important: the ML-only model is useful for experimentation, but the stronger patent-level direction is now the hybrid residual engine: **physics first, ML correction second, with physical guardrails**.

## 2. Relevant External Links

- Open Power System Data Household Data: https://data.open-power-system-data.org/household_data
- Kaggle Solar Power Generation Data: https://www.kaggle.com/datasets/anikannal/solar-power-generation-data
- Open-Meteo Forecast API / historical forecast docs: https://open-meteo.com/en/docs/historical-forecast-api
- Open-Meteo Historical Weather API: https://open-meteo.com/en/docs/historical-weather-api
- pvlib Python documentation: https://pvlib-python.readthedocs.io/
- pvlib `get_total_irradiance`: https://pvlib-python.readthedocs.io/en/stable/reference/irradiance/class-methods.html
- scikit-learn `RandomForestRegressor`: https://sklearn.org/stable/modules/generated/sklearn.ensemble.RandomForestRegressor.html
- FastAPI documentation: https://fastapi.tiangolo.com/
- Vite documentation: https://vite.dev/
- React documentation: https://react.dev/
- Recharts documentation: https://recharts.org/

## 3. Dataset Used For ML

### Current Main PV Dataset: Indian Solar Plant Data

We now use:

```text
Kaggle Solar Power Generation Data
```

Local raw files:

```text
ML forecast/ml/data/raw/indian_solar/Plant_1_Generation_Data.csv
ML forecast/ml/data/raw/indian_solar/Plant_1_Weather_Sensor_Data.csv
ML forecast/ml/data/raw/indian_solar/Plant_2_Generation_Data.csv
ML forecast/ml/data/raw/indian_solar/Plant_2_Weather_Sensor_Data.csv
```

Official source:

```text
https://www.kaggle.com/datasets/anikannal/solar-power-generation-data
```

Why this dataset is now preferred:

- It is India-based.
- It contains measured solar plant generation.
- It has inverter/generation and weather sensor data.
- It has 15-minute resolution.
- It is much closer to SolarCast's India use case than the earlier German OPSD dataset.

Current exported ML model uses:

```text
plant_1
approximate location: Gandikotta, Andhra Pradesh region
approximate coordinates: 14.8141, 78.1984
timezone: Asia/Kolkata
```

Important columns:

```text
DATE_TIME
DC_POWER
AC_POWER
DAILY_YIELD
TOTAL_YIELD
AMBIENT_TEMPERATURE
MODULE_TEMPERATURE
IRRADIATION
```

Target used:

```text
target_kwh = AC_POWER * 0.25
```

because the data interval is 15 minutes.

Training script:

```text
ML forecast/ml/train_indian_solar_model.py
```

Dataset loader:

```text
ML forecast/ml/indian_solar_dataset.py
```

Download helper:

```text
ML forecast/ml/download_indian_solar.py
```

### Previous Experimental PV Dataset

We used:

```text
Open Power System Data Household Data
```

Local file:

```text
ML forecast/ml/data/raw/household_data_15min_singleindex.csv
```

Official source:

```text
https://data.open-power-system-data.org/household_data
```

Why this dataset was originally chosen:

- It is a public and credible research dataset.
- It contains measured household / small-business PV generation data.
- It has 15-minute resolution, which matches our SolarCast chart and forecast interval design.
- It is small enough for local experimentation.

This dataset is no longer the preferred production-facing ML dataset because it is Germany/Konstanz area data, not Indian solar plant data.

### Previous OPSD target PV column selected

The previous OPSD selected target column was:

```text
DE_KN_residential3_pv
```

This was selected automatically by the old audit logic in:

```text
ML forecast/ml/train_baseline.py
```

The audit checks PV columns for:

- available rows
- coverage ratio
- interpolated row count
- interpolation ratio
- mean interval energy
- max interval energy

Audit output:

```text
ML forecast/ml/data/processed/target_audit.csv
```

## 4. Important Dataset Correction

The OPSD PV columns are cumulative meter readings, not direct 15-minute generation labels.

Wrong interpretation:

```text
raw cumulative meter value = target
```

Correct interpretation:

```text
target_kwh = current cumulative reading - previous cumulative reading
```

So our training pipeline converts cumulative PV data into per-interval generation using `.diff()`.

Implemented in:

```text
ML forecast/ml/train_baseline.py
```

Relevant code behavior:

- read selected cumulative PV column
- sort by timestamp
- compute `target_kwh` using first difference
- drop missing first row
- remove negative deltas

This was a major fix. Without it, the ML model would learn the wrong target.

## 5. Weather Data Used

The ML training pipeline optionally uses local weather features:

```text
ML forecast/ml/data/processed/weather_features.csv
```

Weather feature columns used by the ML-only model:

```text
temperature_2m
cloud_cover
shortwave_radiation
direct_radiation
diffuse_radiation
```

These features are aligned with the PV target by timestamp.

Important correction:

- Weather data can be hourly.
- PV target is 15-minute.
- We resample/interpolate weather to 15-minute intervals before merging.

Implemented in:

```text
ML forecast/ml/train_baseline.py
ML forecast/ml/ml_only_model.py
ML forecast/backend/ml_engine.py
```

## 6. Train / Validation / Test Split

Yes, we did split the data into train, validation, and test sets.

The split is **time-based**, not random.

Implemented in:

```text
ML forecast/ml/train_baseline.py
```

Function:

```python
split_train_validation_test(frame)
```

Current split logic:

```text
first 70%  -> training
next 15%   -> validation
last 15%   -> test
```

Why this is correct for forecasting:

- Solar forecasting is a time-series problem.
- Random splitting would leak future patterns into training.
- Time-based splitting gives a more honest estimate of future forecasting performance.

## 7. Baseline ML Models Tested

The baseline experiment tested:

1. Ridge Regression
2. HistGradientBoostingRegressor
3. RandomForestRegressor
4. Persistence baseline

Implemented in:

```text
ML forecast/ml/train_baseline.py
```

The persistence baseline predicts using recent actual generation, especially lag-1. It is a very strong baseline for short-horizon PV forecasting.

## 8. Adaptive vs Cold-Start Feature Sets

We tested two feature styles:

### A. Cold-start weather + time

Used by current exported ML-only app model.

Features:

```text
temperature_2m
cloud_cover
shortwave_radiation
direct_radiation
diffuse_radiation
hour
minute
dayofweek
month
dayofyear
is_weekend
sin_hour
cos_hour
sin_dayofyear
cos_dayofyear
```

This does **not** use recent actual generation.

Pros:

- Can work for a new user/site immediately.
- Suitable for web-app demo mode.

Cons:

- Weaker than adaptive models.
- Cannot learn site-specific inverter, dust, shading, or panel behavior without history.

### B. Adaptive with lags

Features include cold-start features plus target history:

```text
lag_1
lag_2
lag_4
lag_96
rolling_mean_4
rolling_mean_16
```

Pros:

- Much stronger when recent actual generation exists.
- Better for deployed plants with historical meter/inverter data.

Cons:

- Not truly cold-start.
- Cannot be used for a brand-new site unless actual generation history is available.

## 9. Current Exported ML-Only Model

The current app uses a cold-start ML-only model trained on the Indian Kaggle plant data.

Trainer:

```text
ML forecast/ml/train_indian_solar_model.py
```

Shared feature logic:

```text
ML forecast/ml/ml_only_model.py
```

Saved artifact:

```text
ML forecast/ml/artifacts/ml_only_model.pkl
```

Metadata:

```text
ML forecast/ml/artifacts/ml_only_model_metadata.json
```

Training report:

```text
ML forecast/ml/artifacts/ml_only_training_report.json
```

Model family:

```text
HistGradientBoostingRegressor
```

Reference training system size:

```text
27595.01 kW
```

In the app, predictions are scaled from the large plant reference size to the user-selected system size.

Example:

```text
if user selects 10 kW:
scale_factor = 10 / 27595.01
```

This is a practical approximation, not a final scientific model.

## 10. Current Indian ML Training Metrics

From:

```text
ML forecast/ml/artifacts/indian_solar_training_report.json
```

Dataset:

```text
Kaggle Solar Power Generation Data
```

Current plant:

```text
plant_1
```

Rows:

| Split | Rows |
|---|---:|
| Train | 2209 |
| Validation | 474 |
| Test | 474 |

Cold-start feature columns:

```text
temperature_2m
cloud_cover
shortwave_radiation
direct_radiation
diffuse_radiation
hour
minute
dayofweek
month
dayofyear
is_weekend
sin_hour
cos_hour
sin_dayofyear
cos_dayofyear
```

Note: Kaggle `IRRADIATION` is scaled to the live Open-Meteo convention by multiplying by 1000 before being used as `shortwave_radiation`.

### Cold-start test metrics

| Model | MAE | RMSE | Daily Energy MAE |
|---|---:|---:|---:|
| Ridge | 100.0999 | 177.3670 | 4970.4132 |
| HistGradientBoosting | 81.4719 | 180.2051 | 4204.7676 |
| RandomForest | 82.5427 | 181.8159 | 4600.6158 |

Current exported model:

```text
HistGradientBoostingRegressor
```

because it produced the lowest cold-start test daily energy MAE in the current run.

## 10A. Previous OPSD ML-Only Training Metrics

From:

```text
ML forecast/ml/artifacts/ml_only_training_report.json
```

Model:

```text
RandomForestRegressor
```

Forecast mode:

```text
ml_only_cold_start
```

Rows:

| Split | Rows |
|---|---:|
| Train | 63151 |
| Validation | 13533 |
| Test | 13533 |

Validation metrics:

| Metric | Value |
|---|---:|
| MAE | 0.0832 |
| RMSE | 0.6001 |
| Daily energy MAE | 6.3546 |

Test metrics:

| Metric | Value |
|---|---:|
| MAE | 0.0543 |
| RMSE | 0.1012 |
| Daily energy MAE | 2.6827 |

Interpretation:

- The cold-start ML model works, but it is not yet strong enough to be considered final.
- Daily energy error is still meaningful.
- The model is useful for experimentation, UI comparison, and as a base for a future hybrid model.

## 11. Baseline Experiment Metrics

From:

```text
ML forecast/ml/artifacts/baseline_report.json
```

Rows:

| Split | Rows |
|---|---:|
| Train | 63084 |
| Validation | 13518 |
| Test | 13519 |

### Test metrics

| Model | MAE | RMSE | Daily Energy MAE |
|---|---:|---:|---:|
| Ridge | 0.0745 | 0.1188 | 3.2689 |
| HistGradientBoosting | 0.0417 | 0.1370 | 1.2932 |
| RandomForest | 0.0251 | 0.0564 | 0.5071 |
| Persistence baseline | 0.0302 | 0.0627 | 0.1170 |

Important observation:

- RandomForest has strong point-wise test performance.
- Persistence baseline is still very strong for daily energy error.
- This means ML-only is not yet clearly superior to simple time-series baselines.

## 12. Cold-Start vs Adaptive Results

From:

```text
ML forecast/ml/artifacts/feature_set_report.json
```

| Feature Set | Best Model | Test MAE | Includes Target History |
|---|---|---:|---|
| Cold-start weather + time | RandomForest | 0.0539 | No |
| Adaptive with lags | RandomForest | 0.0251 | Yes |
| Persistence baseline | Persistence | 0.0302 | Yes |

Meaning:

- Adaptive models perform better because they know recent actual generation.
- Cold-start is weaker but easier to deploy for new users.
- For a serious product or patent-level system, ML should probably become a correction/adaptation layer rather than a full replacement for physics.

## 13. Web App Integration

Frontend:

```text
ML forecast/frontend/src/App.jsx
ML forecast/frontend/src/components/ForecastChart.jsx
ML forecast/frontend/src/components/ComparisonPanel.jsx
```

Backend:

```text
ML forecast/backend/main.py
ML forecast/backend/ml_engine.py
ML forecast/backend/compare_engine.py
ML forecast/backend/solar_engine.py
```

Routes:

```text
POST /forecast
POST /forecast/ml
POST /forecast/compare
```

Meaning of modes:

- `Physics`: physics-based pvlib forecast
- `ML-only`: cold-start ML model forecast
- `Compare`: returns both physics and ML-only forecast plus comparison metrics

## 14. Recent Bugs Fixed

### A. ML cache key tuple bug

Problem:

```text
can only concatenate str (not "tuple") to str
```

Cause:

```python
"ml:" + build_forecast_cache_key(...)
```

But `build_forecast_cache_key()` returns a tuple.

Fix:

```python
cache_key = ("ml", base_cache_key)
```

File:

```text
ML forecast/backend/main.py
```

### B. Open-Meteo blocked by Windows/network

Problem:

```text
WinError 10013
```

Fix:

- ML forecast now falls back to local clear-sky weather.
- Physics forecast also falls back to local clear-sky weather.

Files:

```text
ML forecast/backend/ml_engine.py
ML forecast/backend/solar_engine.py
```

### C. NaN JSON serialization bug

Problem:

```text
ValueError: Out of range float values are not JSON compliant: nan
```

Cause:

- Some hourly weather rows became 15-minute rows with missing values after merge.

Fix:

- Interpolate weather to 15-minute intervals.
- Fill remaining gaps.
- Sanitize non-finite floats before JSON response.

File:

```text
ML forecast/backend/ml_engine.py
```

### D. Misleading comparison graph / totals

Problems:

- Physics timestamps had timezone offsets.
- ML timestamps were local/naive.
- Chart matched exact timestamp strings, so comparison line could be misleading.
- Backend compared full totals even when only partial intervals matched.
- Physics model was underpredicting because panel efficiency was being double-counted.

Fixes:

- Normalize timestamps to local wall-clock keys.
- Compare matched intervals.
- Show matched totals.
- Remove efficiency double-counting from physics kWh formula.

Files:

```text
ML forecast/backend/compare_engine.py
ML forecast/backend/solar_engine.py
ML forecast/frontend/src/App.jsx
ML forecast/frontend/src/components/ForecastChart.jsx
ML forecast/frontend/src/components/ComparisonPanel.jsx
```

Current comparison smoke-test after fixes:

```text
HTTP 200
Intervals compared: 96
Physics full total: about 61.09 kWh
ML-only full total: about 77.86 kWh
Matched physics total: about 61.09 kWh
Matched ML total: about 77.86 kWh
```

## 15. How To Reproduce The ML Pipeline

From:

```powershell
cd "C:\Users\Lenovo\OneDrive\Desktop\SolarCast\ML forecast"
```

Install dependencies:

```powershell
python -m pip install -r ml\requirements.txt
```

Download the Indian solar plant dataset:

```powershell
python ml\download_indian_solar.py
```

Train the Indian ML-only model:

```powershell
python ml\train_indian_solar_model.py
```

Train the hybrid residual model:

```powershell
python ml\train_hybrid_residual_model.py
```

Legacy OPSD workflow, kept only for reference:

```powershell
python ml\download_opsd.py
```

Run baseline training:

```powershell
python ml\train_baseline.py
```

Compare feature sets:

```powershell
python ml\compare_feature_sets.py
```

Train the exported ML-only model:

```powershell
python ml\train_ml_only_model.py
```

Run local ML-only prediction:

```powershell
python ml\predict_ml_only.py --weather-csv ml\data\processed\weather_features.csv --forecast-hours 24
```

Run backend:

```powershell
cd "C:\Users\Lenovo\OneDrive\Desktop\SolarCast\ML forecast\backend"
python main.py
```

Run frontend:

```powershell
cd "C:\Users\Lenovo\OneDrive\Desktop\SolarCast\ML forecast\frontend"
npm run dev
```

## 16. What We Have Actually Achieved

We have:

- integrated a working ML-only forecast mode into the web app
- integrated a Hybrid forecast mode into the web app
- trained a real ML model using measured PV data
- retrained the main exported model on India-based solar plant data
- trained a physics-residual ML model using the same Indian plant data
- used a chronological train/validation/test split
- corrected cumulative-meter target handling
- added weather feature enrichment
- compared cold-start and adaptive feature sets
- benchmarked multiple regressors and persistence baseline
- added physics-vs-ML comparison UI
- added physics-vs-hybrid-vs-ML comparison UI
- added physical guardrails so the residual model cannot overpower the physics baseline
- fixed major backend and chart comparison bugs

## 17. What We Have Not Yet Achieved

We have **not yet** built a final production-grade or patent-level ML model.

Current limitations:

- dataset is effectively site-specific
- Indian dataset is Plant 1 / Plant 2 data, not actual Gurgaon rooftop or plant data
- cold-start ML does not yet prove superiority over a well-calibrated physics model for every location
- adaptive ML needs recent actual generation history
- current hybrid residual model is still trained offline, not continuously adapted from the user's inverter data
- no uncertainty bands yet for ML-only output
- residual correction exists now, but needs validation against live actual generation
- no DSM penalty-aware schedule optimizer yet
- no live inverter/meter feedback loop yet

## 18. Best Technical Direction From Here

The strongest next direction is not pure ML-only replacement.

Recommended architecture:

```text
Physics forecast
        +
ML residual correction
        +
recent actual generation feedback
        +
uncertainty estimation
        +
DSM/risk-aware schedule recommendation
```

Instead of:

```text
weather -> ML -> kWh
```

Use:

```text
weather + solar geometry -> physics forecast
physics forecast + recent error + weather features -> ML correction
correction + uncertainty -> final forecast band
forecast band + DSM/tariff logic -> recommended commitment
```

## 19. Patent-Level Development Ideas

Potential patent-worthy direction:

```text
Adaptive Hybrid Solar Forecasting and DSM-Aware Dispatch Optimization System
for Distributed Renewable Energy Assets
```

Potential novelty areas:

1. **Hybrid physics + ML residual correction**
   - ML predicts the error of the physics model instead of replacing physics.

2. **Self-correcting site bias engine**
   - Learns recurring forecast bias by time, weather class, season, and recent actual generation.

3. **Uncertainty-aware forecast commitment**
   - Outputs P10/P50/P90 style generation bands.

4. **DSM penalty-aware scheduling**
   - Chooses a schedule that minimizes expected grid penalty, not only forecast error.

5. **Soiling / shading / degradation inference**
   - Detects persistent underperformance under clear-sky conditions.

6. **Regional transfer learning**
   - Initializes forecasts for new sites using similar nearby sites, then personalizes over time.

## 20. Recommended Next Implementation Steps

Best immediate steps:

1. Add actual Gurgaon/site generation feedback:

```text
forecast timestamp
physics forecast
hybrid forecast
actual inverter / meter generation
forecast error
```

2. Add forecast history storage:

```text
forecast timestamp
weather
physics forecast
ML forecast
actual generation
forecast error
```

3. Add uncertainty bands:

```text
P10 / P50 / P90
```

4. Add adaptive correction:

```text
last 7 days bias by time-of-day and weather class
```

5. Add DSM-aware recommended commitment:

```text
recommended_kwh = risk-adjusted forecast commitment
```

## 21. Bottom Line

Yes, we used real measured PV data and yes, we used a proper chronological train/validation/test split.

But the current ML-only model should be treated as an experimental comparison model, not the final invention.

The strongest future version of this project should be:

```text
Physics baseline + ML correction + uncertainty + adaptive learning + DSM-aware dispatch
```

That direction is much more useful, much more defensible, and much closer to patent-level work than a standalone ML-only solar predictor.
