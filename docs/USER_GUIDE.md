# SolarCast User Guide

## Purpose

SolarCast estimates short-term solar photovoltaic energy generation from location, weather, and system parameters. It is designed as an interactive dashboard for studying physics-based, ML-only, and hybrid forecasting.

## Basic Workflow

1. Open the frontend dashboard.
2. Select a location using search, map click, or auto-detect.
3. Review or adjust the system parameters.
4. Select a 24-hour or 72-hour forecast horizon.
5. Select a forecast engine:
   - Physics
   - Hybrid
   - ML-only
   - Compare
6. Click Generate Forecast.
7. Review the chart, summary cards, confidence score, daily outlook, and hourly table.
8. Export CSV if tabular forecast values are needed.

## Forecast Engine Selection

### Physics

Use this mode when interpretability and physical consistency are most important. It is the safest baseline for a new location because it does not depend on user-specific historical generation.

### ML-only

Use this mode for experimentation and comparison. It is a cold-start machine learning forecast and should not be treated as the production baseline.

### Hybrid

Use this mode when the goal is to combine physical modelling with data-driven residual correction. It is the preferred research direction because correction is bounded and physically guarded.

### Compare

Use this mode to compare all engines. It shows matched totals, yield delta, delta percentage, hourly MAE, and interval counts.

## Interpreting Confidence

High confidence means the daylight irradiance and cloud conditions are relatively stable. Medium or low confidence indicates greater weather variability and therefore greater forecast risk.

## Interpreting Maintenance Insight

The maintenance card compares expected output with clear-sky potential. Persistent underperformance during clear conditions may suggest dust, shading, soiling, equipment faults, or system degradation.

## Limitations

SolarCast estimates generation from public weather forecasts and model assumptions. Actual generation may differ due to local shading, inverter behaviour, panel temperature, soiling, wiring losses, and forecast weather error.
