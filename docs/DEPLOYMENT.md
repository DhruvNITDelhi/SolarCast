# SolarCast Deployment Guide

SolarCast is deployed as two services:

- **Backend API:** FastAPI service on Render.
- **Frontend app:** Vite/React static app on Vercel.

This split keeps the Python forecasting engine separate from the browser application.

## 1. Deploy the Backend on Render

1. Push the latest `main` branch to GitHub.
2. Open Render and create a new **Web Service** from `DhruvNITDelhi/SolarCast`.
3. Use the root-level `render.yaml` blueprint if Render detects it.
4. If configuring manually, use:
   - Runtime: `Python 3`
   - Build command: `pip install -r backend/requirements.txt`
   - Start command: `cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT`
   - Branch: `main`
5. After deploy, test:
   - `https://YOUR-BACKEND.onrender.com/health`
   - `https://YOUR-BACKEND.onrender.com/docs`

Do not set the backend root directory to `backend/` unless the ML artifacts are copied there too. The backend imports model artifacts from `ml/artifacts/`, so the full repository must be available at runtime.

## 2. Deploy the Frontend on Vercel

1. Import the same GitHub repository in Vercel.
2. Set **Root Directory** to `frontend`.
3. Use:
   - Framework preset: `Vite`
   - Install command: `npm install`
   - Build command: `npm run build`
   - Output directory: `dist`
4. Add this environment variable for Production and Preview:
   - `VITE_API_BASE_URL=https://YOUR-BACKEND.onrender.com`
5. Redeploy the frontend after adding the environment variable.

## 3. Final Verification

After both services are live:

1. Open the Vercel frontend URL.
2. Confirm the app loads without console errors.
3. Run a Physics forecast for a known Indian location.
4. Run Hybrid mode.
5. Run Compare mode.
6. Confirm API status shows live and forecast charts render.

## 4. Common Issues

### CORS error

Set `SOLARCAST_CORS_ORIGINS` on Render to the exact frontend URL:

```text
https://YOUR-FRONTEND.vercel.app
```

The backend also allows Vercel preview URLs using `SOLARCAST_CORS_ORIGIN_REGEX`.

### ML or Hybrid mode returns 503

Confirm these files exist in GitHub and are available in the deployed service:

- `ml/artifacts/ml_only_model.pkl`
- `ml/artifacts/ml_only_model_metadata.json`
- `ml/artifacts/hybrid_residual_model.pkl`
- `ml/artifacts/hybrid_residual_model_metadata.json`

### Frontend calls localhost

The frontend uses `VITE_API_BASE_URL`. Add the environment variable on Vercel and redeploy.
