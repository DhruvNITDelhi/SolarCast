# SolarCast Report Benchmark Summary

## Live Delhi 24-hour Engine Comparison

| Engine | Total kWh | Peak kWh per 15 min | Confidence |
|---|---:|---:|---|
| Physics | 9.27 | 0.329 | High |
| Hybrid residual | 11.0 | 0.368 | High |
| ML-only cold start | 58.85 | 2.214 | High |

## Delta Metrics

| Comparison | Total Delta kWh | Delta % | Hourly MAE | Intervals |
|---|---:|---:|---:|---:|
| Physics vs ML-only | 44.93 | 597.87 | 0.5106 | 88 |
| Physics vs Hybrid | 1.729 | 18.65 | 0.018 | 96 |

## Training Evidence

- ML-only model: RandomForestRegressor, test MAE 0.0543, test RMSE 0.1012.
- Hybrid residual model: hist_gradient_boosting, best model by test daily energy MAE: hist_gradient_boosting.
- Adaptive random forest test MAE: 0.0251.
