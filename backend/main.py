"""
SolarCast — FastAPI Backend
Hourly solar energy generation forecast API.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from cache import TTLCache, build_forecast_cache_key
from models import ForecastRequest, ForecastResponse
from settings import (
    get_cors_origin_regex,
    get_cors_origins,
    get_forecast_cache_max_entries,
    get_forecast_cache_ttl_seconds,
)
from solar_engine import generate_forecast

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("solarcast")

forecast_cache = TTLCache(
    ttl_seconds=get_forecast_cache_ttl_seconds(),
    max_entries=get_forecast_cache_max_entries(),
)


# ─── App ──────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="SolarCast API",
    description="Hourly solar energy generation forecast using real irradiance data and pvlib.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_origin_regex=get_cors_origin_regex(),
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
        cache_key = build_forecast_cache_key(
            lat=req.lat,
            lon=req.lon,
            system_size_kw=req.system_size_kw,
            tilt=req.tilt,
            azimuth=req.azimuth,
            losses=req.losses,
            efficiency=req.efficiency,
        )
        cached_result = forecast_cache.get(cache_key)
        if cached_result is not None:
            logger.info(
                f"Forecast cache hit: lat={req.lat}, lon={req.lon}, size={req.system_size_kw}kW"
            )
            return cached_result

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

        forecast_cache.set(cache_key, result)
        return result

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Forecast error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Forecast calculation failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
