"""
SolarCast - FastAPI Backend
Hourly solar energy generation forecast API.
"""

import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from cache import TTLCache, build_forecast_cache_key
from compare_engine import compare_forecasts
from hybrid_engine import generate_hybrid_forecast
from ml_engine import generate_ml_forecast
from models import ForecastRequest, ForecastResponse
from settings import (
    get_cors_origin_regex,
    get_cors_origins,
    get_forecast_cache_max_entries,
    get_forecast_cache_ttl_seconds,
)
from solar_engine import generate_forecast

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("solarcast")

forecast_cache = TTLCache(
    ttl_seconds=get_forecast_cache_ttl_seconds(),
    max_entries=get_forecast_cache_max_entries(),
)

app = FastAPI(
    title="SolarCast API",
    description="Solar energy generation forecast using real irradiance data and pvlib.",
    version="1.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_origin_regex=get_cors_origin_regex(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {
        "message": "SolarCast API is running!",
        "docs_url": "/docs",
        "health_check": "/health",
    }


@app.get("/health")
async def health():
    return {"status": "ok", "service": "solarcast"}


@app.post("/forecast", response_model=ForecastResponse)
async def forecast(req: ForecastRequest):
    """Generate a solar energy forecast for the selected horizon."""
    try:
        cache_key = build_forecast_cache_key(
            lat=req.lat,
            lon=req.lon,
            system_size_kw=req.system_size_kw,
            tilt=req.tilt,
            azimuth=req.azimuth,
            losses=req.losses,
            efficiency=req.efficiency,
            forecast_hours=req.forecast_hours,
        )
        cached_result = forecast_cache.get(cache_key)
        if cached_result is not None:
            logger.info(
                "Forecast cache hit: lat=%s, lon=%s, size=%skW, hours=%s",
                req.lat,
                req.lon,
                req.system_size_kw,
                req.forecast_hours,
            )
            return cached_result

        logger.info(
            "Forecast request: lat=%s, lon=%s, size=%skW, tilt=%s, azimuth=%s, hours=%s",
            req.lat,
            req.lon,
            req.system_size_kw,
            req.tilt,
            req.azimuth,
            req.forecast_hours,
        )

        result = generate_forecast(
            lat=req.lat,
            lon=req.lon,
            system_size_kw=req.system_size_kw,
            tilt=req.tilt,
            azimuth=req.azimuth,
            losses=req.losses,
            efficiency=req.efficiency,
            forecast_hours=req.forecast_hours,
        )

        logger.info(
            "Forecast complete: total=%skWh, peak=%s, confidence=%s",
            result["total_kwh"],
            result["peak_hour"],
            result["confidence"],
        )

        forecast_cache.set(cache_key, result)
        return result

    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("Forecast error: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Forecast calculation failed: {str(exc)}",
        )


@app.post("/forecast/ml", response_model=ForecastResponse)
async def ml_forecast(req: ForecastRequest):
    """Generate an experimental ML-only cold-start forecast."""
    try:
        logger.info(
            "ML forecast request: lat=%s, lon=%s, size=%skW, hours=%s",
            req.lat,
            req.lon,
            req.system_size_kw,
            req.forecast_hours,
        )
        return generate_ml_forecast(
            lat=req.lat,
            lon=req.lon,
            system_size_kw=req.system_size_kw,
            tilt=req.tilt,
            azimuth=req.azimuth,
            losses=req.losses,
            efficiency=req.efficiency,
            forecast_hours=req.forecast_hours,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("ML forecast error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"ML forecast failed: {str(exc)}")


@app.post("/forecast/hybrid", response_model=ForecastResponse)
async def hybrid_forecast(req: ForecastRequest):
    """Generate the patent-track physics + ML residual forecast."""
    try:
        logger.info(
            "Hybrid forecast request: lat=%s, lon=%s, size=%skW, hours=%s",
            req.lat,
            req.lon,
            req.system_size_kw,
            req.forecast_hours,
        )
        return generate_hybrid_forecast(
            lat=req.lat,
            lon=req.lon,
            system_size_kw=req.system_size_kw,
            tilt=req.tilt,
            azimuth=req.azimuth,
            losses=req.losses,
            efficiency=req.efficiency,
            forecast_hours=req.forecast_hours,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("Hybrid forecast error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Hybrid forecast failed: {str(exc)}")


@app.post("/forecast/compare")
async def compare_forecast_modes(req: ForecastRequest):
    """Compare physics, ML-only, and hybrid forecasts for the same request."""
    try:
        logger.info(
            "Forecast comparison request: lat=%s, lon=%s, size=%skW, hours=%s",
            req.lat,
            req.lon,
            req.system_size_kw,
            req.forecast_hours,
        )
        common_args = {
            "lat": req.lat,
            "lon": req.lon,
            "system_size_kw": req.system_size_kw,
            "tilt": req.tilt,
            "azimuth": req.azimuth,
            "losses": req.losses,
            "efficiency": req.efficiency,
            "forecast_hours": req.forecast_hours,
        }
        physics = generate_forecast(**common_args)
        ml_only = generate_ml_forecast(**common_args)
        hybrid = generate_hybrid_forecast(**common_args)

        return {
            "physics": physics,
            "ml_only": ml_only,
            "hybrid": hybrid,
            "comparison": compare_forecasts(physics, ml_only),
            "hybrid_comparison": compare_forecasts(physics, hybrid),
        }
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("Forecast comparison error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Forecast comparison failed: {str(exc)}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
