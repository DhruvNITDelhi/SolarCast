# Report Assets

This directory contains supporting evidence prepared for the SolarCast Minor Degree project report.

## Benchmark Files

- `delhi_engine_comparison.json`: full live comparison response for a 10 kW Delhi forecast request.
- `delhi_engine_comparison_summary.csv`: report-ready engine summary table.
- `delhi_engine_delta_metrics.csv`: report-ready delta metrics for Physics vs ML-only and Physics vs Hybrid.
- `report_benchmark_summary.json`: consolidated training and live comparison evidence.
- `report_benchmark_summary.md`: human-readable benchmark summary for report drafting.

## Screenshots

Screenshots are stored in `screenshots/` and listed in `screenshot_manifest.md`.
They were captured from the local React dashboard after selecting a representative Indian location and running Compare mode.

## Note

The live comparison values are time-sensitive because Open-Meteo forecasts change. The saved files preserve the exact values used during report preparation.
