# SolarCast Deployment Guide

SolarCast is deployed as two services:

- **Backend API:** FastAPI service on Hugging Face Spaces or Render.
- **Frontend app:** Vite/React static app on Vercel.

This split keeps the Python forecasting engine separate from the browser application.

## Recommended No-Card Deployment

Use Hugging Face Spaces for the backend and Vercel for the frontend. This avoids Render's credit-card requirement.

## 1. Update the Backend on Hugging Face Spaces

Use the existing SolarCast backend Space if you already created one.

1. Open the Hugging Face Space.
2. Confirm the Space SDK is **Docker**.
3. Upload/sync the current repository files from GitHub or with the Hugging Face CLI.
4. Make sure the Space contains these root-level files/folders:
   - `Dockerfile`
   - `backend/`
   - `ml/`
5. If the Space README needs Docker metadata, use `deploy/huggingface/README.md` as the Space `README.md`.
6. Wait for the Space rebuild to finish.
7. Test:
   - `https://YOUR-USERNAME-solarcast-backend.hf.space/health`
   - `https://YOUR-USERNAME-solarcast-backend.hf.space/docs`

The backend listens on `0.0.0.0:7860`, which is the default public port for Docker Spaces.

If using the Hugging Face CLI:

```powershell
hf auth login
hf upload YOUR-USERNAME/solarcast-backend . --repo-type space --commit-message "Update SolarCast backend"
hf upload YOUR-USERNAME/solarcast-backend deploy/huggingface/README.md README.md --repo-type space --commit-message "Update Space metadata"
```

Replace `YOUR-USERNAME/solarcast-backend` with the actual Space id.

## 2. Optional: Deploy the Backend on Render

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

## 3. Deploy or Update the Frontend on Vercel

1. Import the same GitHub repository in Vercel.
2. Set **Root Directory** to `frontend`.
3. Use:
   - Framework preset: `Vite`
   - Install command: `npm install`
   - Build command: `npm run build`
   - Output directory: `dist`
4. Add this environment variable for Production and Preview:
   - `VITE_API_BASE_URL=https://YOUR-USERNAME-solarcast-backend.hf.space`
5. Redeploy the frontend after adding the environment variable.

## 4. Final Verification

After both services are live:

1. Open the Vercel frontend URL.
2. Confirm the app loads without console errors.
3. Run a Physics forecast for a known Indian location.
4. Run Hybrid mode.
5. Run Compare mode.
6. Confirm API status shows live and forecast charts render.

## 5. Common Issues

### CORS error

Set `SOLARCAST_CORS_ORIGINS` on the backend host to the exact frontend URL:

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
