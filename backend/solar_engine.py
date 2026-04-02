"""
Solar Forecast Calculation Engine
Uses Open-Meteo API for irradiance forecast data and pvlib for solar modeling.
"""

import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Any, Tuple, Optional
from timezonefinder import TimezoneFinder
import pvlib
from pvlib.location import Location
from pvlib.irradiance import get_total_irradiance, get_extra_radiation


# ─── Constants ────────────────────────────────────────────────────────────────

OPEN_METEO_BASE = "https://api.open-meteo.com/v1/forecast"
DEFAULT_AZIMUTH = 180.0  # South-facing (India)
DEFAULT_LOSSES = 14.0
DEFAULT_EFFICIENCY = 18.0

tf = TimezoneFinder()


# ─── Timezone Detection ──────────────────────────────────────────────────────

def get_timezone(lat: float, lon: float) -> str:
    """Detect timezone from coordinates."""
    tz = tf.timezone_at(lat=lat, lng=lon)
    return tz if tz else "UTC"


# ─── Open-Meteo Data Fetch ───────────────────────────────────────────────────

def fetch_irradiance_forecast(lat: float, lon: float, timezone: str) -> pd.DataFrame:
    """
    Fetch hourly irradiance and weather forecast from Open-Meteo.
    Returns DataFrame with columns: ghi, dni, dhi, cloud_cover, temperature
    """
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": ",".join([
            "shortwave_radiation",         # GHI (W/m²)
            "direct_normal_irradiance",    # DNI (W/m²)
            "diffuse_radiation",           # DHI (W/m²)
            "cloudcover",                  # Cloud cover (%)
            "temperature_2m",             # Temperature (°C)
        ]),
        "timezone": timezone,
        "forecast_days": 2,  # Get 2 days to ensure full 24h coverage
    }

    response = requests.get(OPEN_METEO_BASE, params=params, timeout=30)
    response.raise_for_status()
    data = response.json()

    hourly = data["hourly"]
    times = pd.to_datetime(hourly["time"])

    df = pd.DataFrame({
        "time": times,
        "ghi": hourly["shortwave_radiation"],
        "dni": hourly["direct_normal_irradiance"],
        "dhi": hourly["diffuse_radiation"],
        "cloud_cover": hourly["cloudcover"],
        "temperature": hourly["temperature_2m"],
    })

    df = df.set_index("time")

    # Localize to the detected timezone
    df.index = df.index.tz_localize(timezone)

    return df


# ─── Solar Position & Irradiance Transposition ───────────────────────────────

def compute_poa_irradiance(
    df: pd.DataFrame,
    lat: float,
    lon: float,
    tilt: float,
    azimuth: float,
    altitude: float = 0,
) -> pd.DataFrame:
    """
    Compute Plane-of-Array irradiance using pvlib.
    Transposes horizontal irradiance (GHI, DNI, DHI) to tilted surface.
    """
    location = Location(latitude=lat, longitude=lon, altitude=altitude)

    # Solar position for each timestamp
    solpos = location.get_solarposition(df.index)

    # Extra-terrestrial radiation for transposition model
    dni_extra = get_extra_radiation(df.index)

    # Transpose to plane of array using Haydavies model
    poa = get_total_irradiance(
        surface_tilt=tilt,
        surface_azimuth=azimuth,
        dni=df["dni"],
        ghi=df["ghi"],
        dhi=df["dhi"],
        dni_extra=dni_extra,
        solar_zenith=solpos["apparent_zenith"],
        solar_azimuth=solpos["azimuth"],
        model="haydavies",
    )

    df["poa_global"] = poa["poa_global"].clip(lower=0)
    df["solar_zenith"] = solpos["apparent_zenith"]
    df["solar_azimuth"] = solpos["azimuth"]

    return df


# ─── Power Calculation ───────────────────────────────────────────────────────

def compute_hourly_generation(
    df: pd.DataFrame,
    system_size_kw: float,
    efficiency: float,
    losses: float,
) -> pd.DataFrame:
    """
    Convert POA irradiance to hourly energy generation (kWh).

    Power (kW) = POA (W/m²) × System_Size (kW) × Efficiency / 1000 W/kW
    Then apply losses, and since each row is 1 hour, kW = kWh for that hour.
    """
    # efficiency as fraction
    eff = efficiency / 100.0
    loss_factor = 1.0 - (losses / 100.0)

    # STC irradiance is 1000 W/m², so normalize
    # Power = (POA / 1000) * system_size * efficiency_factor * loss_factor
    df["kwh"] = (
        (df["poa_global"] / 1000.0)
        * system_size_kw
        * eff
        * loss_factor
    )

    # Zero out nighttime (solar zenith >= 90 means sun is below horizon)
    df.loc[df["solar_zenith"] >= 90, "kwh"] = 0.0

    # Ensure no negative values
    df["kwh"] = df["kwh"].clip(lower=0)

    # Round to 3 decimal places
    df["kwh"] = df["kwh"].round(3)

    return df


# ─── Confidence Calculation ──────────────────────────────────────────────────

def compute_confidence(cloud_data: pd.Series) -> str:
    """
    Determine forecast confidence based on cloud cover variability.
    - High: avg cloud < 20%
    - Medium: avg cloud 20-60%
    - Low: avg cloud > 60%
    """
    avg_cloud = cloud_data.mean()

    if avg_cloud < 20:
        return "High"
    elif avg_cloud <= 60:
        return "Medium"
    else:
        return "Low"


# ─── Sunrise / Sunset Detection ──────────────────────────────────────────────

def get_sunrise_sunset(lat: float, lon: float, tz: str) -> Tuple[Optional[str], Optional[str]]:
    """Get sunrise and sunset times for today using pvlib."""
    location = Location(latitude=lat, longitude=lon, tz=tz)
    today = pd.Timestamp.now(tz=tz).normalize()

    # Get sun rise/set for today
    try:
        sun_times = location.get_sun_rise_set_transit(
            pd.DatetimeIndex([today]),
            method="geometric",
        )
        sunrise = sun_times["sunrise"].iloc[0]
        sunset = sun_times["sunset"].iloc[0]

        return (
            sunrise.strftime("%H:%M") if pd.notna(sunrise) else None,
            sunset.strftime("%H:%M") if pd.notna(sunset) else None,
        )
    except Exception:
        return None, None


# ─── Main Forecast Function ──────────────────────────────────────────────────

def generate_forecast(
    lat: float,
    lon: float,
    system_size_kw: float,
    tilt: Optional[float] = None,
    azimuth: Optional[float] = None,
    losses: float = DEFAULT_LOSSES,
    efficiency: float = DEFAULT_EFFICIENCY,
) -> Dict[str, Any]:
    """
    Generate a complete 24-hour solar forecast.

    Returns dict matching ForecastResponse schema.
    """
    # ── Defaults ──
    if tilt is None:
        tilt = abs(lat)  # Rule of thumb: tilt ≈ latitude
    if azimuth is None:
        azimuth = DEFAULT_AZIMUTH  # South-facing for India

    # ── Timezone ──
    timezone = get_timezone(lat, lon)

    # ── Fetch irradiance data ──
    df = fetch_irradiance_forecast(lat, lon, timezone)

    # ── Filter to next 24 hours from current time ──
    now = pd.Timestamp.now(tz=timezone)
    # Start from the next full hour
    start = now.ceil("h")
    end = start + timedelta(hours=24)
    df = df.loc[start:end].head(24)

    if df.empty:
        raise ValueError("No forecast data available for the requested location and time range.")

    # ── Compute POA irradiance ──
    df = compute_poa_irradiance(df, lat, lon, tilt, azimuth)

    # ── Compute generation ──
    df = compute_hourly_generation(df, system_size_kw, efficiency, losses)

    # ── Confidence ──
    # Only consider daylight hours for confidence
    daylight = df[df["solar_zenith"] < 90]
    confidence = compute_confidence(daylight["cloud_cover"]) if not daylight.empty else "Low"

    # ── Sunrise / Sunset ──
    sunrise, sunset = get_sunrise_sunset(lat, lon, timezone)

    # ── Build response ──
    hourly = []
    for ts, row in df.iterrows():
        hourly.append({
            "hour": ts.isoformat(),
            "kwh": round(row["kwh"], 3),
            "irradiance": round(row["poa_global"], 1),
            "ghi": round(row["ghi"], 1),
            "temperature": round(row["temperature"], 1),
            "cloud_cover": round(row["cloud_cover"], 1),
        })

    total_kwh = round(sum(h["kwh"] for h in hourly), 2)

    # Peak hour
    if hourly:
        peak = max(hourly, key=lambda h: h["kwh"])
        peak_hour = peak["hour"]
        peak_kwh = peak["kwh"]
    else:
        peak_hour = ""
        peak_kwh = 0.0

    return {
        "hourly": hourly,
        "total_kwh": total_kwh,
        "peak_hour": peak_hour,
        "peak_kwh": peak_kwh,
        "confidence": confidence,
        "location_info": {
            "latitude": lat,
            "longitude": lon,
            "timezone": timezone,
        },
        "system_params": {
            "system_size_kw": system_size_kw,
            "tilt": tilt,
            "azimuth": azimuth,
            "losses": losses,
            "efficiency": efficiency,
        },
        "sunrise": sunrise,
        "sunset": sunset,
    }
