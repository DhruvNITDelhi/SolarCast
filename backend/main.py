"""
SolarCast — FastAPI Backend
Hourly solar energy generation forecast API.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from models import ForecastRequest, ForecastResponse
from solar_engine import generate_forecast

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("solarcast")


# ─── App ──────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="SolarCast API",
    description="Hourly solar energy generation forecast using real irradiance data and pvlib.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Routes ──────────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    return {
        "message": "SolarCast API is running!",
        "docs_url": "/docs",
        "health_check": "/health"
    }

@app.get("/health")
async def health():
    return {"status": "ok", "service": "solarcast"}


@app.post("/forecast", response_model=ForecastResponse)
async def forecast(req: ForecastRequest):
    """
    Generate a 24-hour solar energy forecast.

    Fetches real irradiance data from Open-Meteo and uses pvlib
    for physics-based solar position and power calculations.
    """
    try:
        logger.info(
            f"Forecast request: lat={req.lat}, lon={req.lon}, "
            f"size={req.system_size_kw}kW, tilt={req.tilt}, azimuth={req.azimuth}"
        )

        result = generate_forecast(
            lat=req.lat,
            lon=req.lon,
            system_size_kw=req.system_size_kw,
            tilt=req.tilt,
            azimuth=req.azimuth,
            losses=req.losses,
            efficiency=req.efficiency,
        )

        logger.info(
            f"Forecast complete: total={result['total_kwh']}kWh, "
            f"peak={result['peak_hour']}, confidence={result['confidence']}"
        )

        return result

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Forecast error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Forecast calculation failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
