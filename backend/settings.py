"""Runtime settings for SolarCast backend."""

from __future__ import annotations

import os


DEFAULT_CORS_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:4173",
    "http://127.0.0.1:4173",
    "https://solar-cast-roan.vercel.app",
]


def _split_csv(raw_value: str | None) -> list[str]:
    if not raw_value:
        return []
    return [item.strip() for item in raw_value.split(",") if item.strip()]


def get_cors_origins() -> list[str]:
    configured = _split_csv(os.getenv("SOLARCAST_CORS_ORIGINS"))
    return configured or DEFAULT_CORS_ORIGINS


def get_cors_origin_regex() -> str:
    return os.getenv("SOLARCAST_CORS_ORIGIN_REGEX", r"https://.*\.vercel\.app")


def get_open_meteo_timeout() -> float:
    return float(os.getenv("OPEN_METEO_TIMEOUT_SECONDS", "30"))


def get_open_meteo_user_agent() -> str:
    return os.getenv("OPEN_METEO_USER_AGENT", "SolarCast/1.0")


def get_forecast_cache_ttl_seconds() -> int:
    return int(os.getenv("FORECAST_CACHE_TTL_SECONDS", "300"))


def get_forecast_cache_max_entries() -> int:
    return int(os.getenv("FORECAST_CACHE_MAX_ENTRIES", "256"))
