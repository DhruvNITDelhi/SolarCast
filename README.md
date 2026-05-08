# SolarCast

SolarCast is a solar generation forecasting application for estimating photovoltaic output from a selected location and system configuration. It combines a production physics model with experimental ML and hybrid residual-correction engines so users can compare forecasting approaches from one interface.

## Current Capabilities

- 24-hour and 72-hour solar generation forecasts at 15-minute resolution.
- Physics-based forecast using Open-Meteo irradiance/weather data and `pvlib`.
- Experimental ML-only cold-start forecast using exported model artifacts.
- Hybrid physics + ML residual correction forecast for patent-track experimentation.
- Compare mode for Physics vs Hybrid vs ML-only output.
- Confidence scoring, cloud-loss diagnostics, daily summaries, smart usage window, and CSV export.
- React dashboard with map/location search, system controls, charts, summary cards, and state ranking.

## Architecture

```text
SolarCast/
  backend/   FastAPI service, forecast engines, API schemas, tests
  frontend/  React + Vite dashboard
  ml/        Training, benchmarking, model artifacts, and ML documentation
```

### Backend

- Framework: FastAPI
- Core libraries: `pvlib`, `pandas`, `numpy`, `requests`, `timezonefinder`
- Data source: Open-Meteo forecast APIs
- Main API routes:
  - `GET /health`
  - `POST /forecast`
  - `POST /forecast/ml`
  - `POST /forecast/hybrid`
  - `POST /forecast/compare`

### Frontend

- Framework: React + Vite
- UI: Tailwind CSS, custom CSS variables, Lucide icons
- Visualization: Recharts
- Maps/geocoding: Leaflet, React-Leaflet, OpenStreetMap/Nominatim

## Forecast Engines

### Physics

The production baseline fetches forecast irradiance and weather, computes solar geometry with `pvlib`, transposes irradiance to plane-of-array, applies system losses, and returns expected AC generation.

### ML-only

The ML-only engine is an experimental cold-start model. It uses weather and time features to generate a data-driven forecast without relying on live inverter history. Treat this mode as a comparison and research tool, not the production baseline.

### Hybrid

The hybrid engine starts with the physics forecast, then applies a bounded ML residual correction trained on Indian solar plant data. This keeps the forecast physically guarded while allowing learned corrections where the data supports them.

## Local Development

### Backend

```powershell
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn main:app --reload --port 8000
```

The API runs at `http://localhost:8000`, with interactive docs at `http://localhost:8000/docs`.

### Frontend

```powershell
cd frontend
npm install
npm run dev
```

The Vite app normally runs at `http://localhost:5173`. API calls are proxied to the backend by `frontend/vite.config.js`.

## Verification

Run these checks before committing:

```powershell
python -m py_compile backend\main.py backend\solar_engine.py backend\hybrid_engine.py backend\ml_engine.py ml\hybrid_residual_model.py ml\train_hybrid_residual_model.py
cd backend
python -m pytest tests -q
cd ..\frontend
npm run lint
npm run build
```

## ML Workflow

The `ml/` directory contains scripts for downloading data, training baseline and ML-only models, training the hybrid residual model, and benchmarking against the physics engine. See `ml/README.md` and `ML_FORECAST_PROJECT_DOCUMENTATION.md` for experiment details, dataset notes, and artifact descriptions.

Key artifact paths:

- `ml/artifacts/ml_only_model.pkl`
- `ml/artifacts/ml_only_model_metadata.json`
- `ml/artifacts/hybrid_residual_model.pkl`
- `ml/artifacts/hybrid_residual_model_metadata.json`

## Deployment Notes

- Backend deployment configuration is in `backend/render.yaml`.
- Frontend builds with `npm run build` into `frontend/dist`.
- Runtime configuration for the frontend API base can be supplied with `VITE_API_BASE_URL`.
- Local raw datasets, processed data, cache directories, and development-only inspection folders are ignored by `.gitignore`.

## Project Status

The current product path is:

1. Keep the physics engine as the stable production baseline.
2. Use ML-only mode for experimentation and benchmarking.
3. Develop the hybrid residual engine as the main patent-track forecasting direction.
4. Compare all engines transparently in the UI before promoting any model behavior.
