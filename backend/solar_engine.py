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
from pvlib.irradiance import get_total_irradiance, get_extra_radiation, clearsky_index
from pvlib.clearsky import ineichen


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
    Fetch 15-minute irradiance and weather forecast from Open-Meteo.
    Returns DataFrame with columns: ghi, dni, dhi, cloud_cover, temperature
    """
    params = {
        "latitude": lat,
        "longitude": lon,
        "minutely_15": ",".join([
            "shortwave_radiation",         # GHI (W/m²)
            "direct_normal_irradiance",    # DNI (W/m²)
            "diffuse_radiation",           # DHI (W/m²)
        ]),
        "hourly": ",".join([
            "cloudcover",                  # Cloud cover (%)
            "temperature_2m",             # Temperature (°C)
        ]),
        "timezone": timezone,
        "forecast_days": 2,
        "past_days": 1,
    }

    response = requests.get(OPEN_METEO_BASE, params=params, timeout=30)
    response.raise_for_status()
    data = response.json()

    # ── Process 15-min data (Radiation) ──
    m15 = data["minutely_15"]
    df_15 = pd.DataFrame({
        "time": pd.to_datetime(m15["time"]),
        "ghi": m15["shortwave_radiation"],
        "dni": m15["direct_normal_irradiance"],
        "dhi": m15["diffuse_radiation"],
    }).set_index("time")

    # ── Process Hourly data (Cloud/Temp) and upsample to 15-min ──
    hr = data["hourly"]
    df_hr = pd.DataFrame({
        "time": pd.to_datetime(hr["time"]),
        "cloud_cover": hr["cloudcover"],
        "temperature": hr["temperature_2m"],
    }).set_index("time")

    # Resample hourly to 15-min and interpolate
    df_hr = df_hr.resample("15min").interpolate(method="linear")

    # Join both
    df = df_15.join(df_hr, how="inner")

    # Localize to detected timezone
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

    # Power (kW) = (POA / 1000) * system_size * efficiency_factor * loss_factor
    # Each row is 15 mins (0.25 hours), so kWh = Power * 0.25
    df["kwh"] = (
        (df["poa_global"] / 1000.0)
        * system_size_kw
        * eff
        * loss_factor
        * 0.25 # Convert kW to 15-min kWh
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

    # ── Compute actual POA and generation first ──
    df = compute_poa_irradiance(df, lat, lon, tilt, azimuth)
    df = compute_hourly_generation(df, system_size_kw, efficiency, losses)

    # ── Clear Sky Potential (Diagnostic) ──
    # We compute what the generation WOULD have been if ghi/dni were clear sky
    location = Location(latitude=lat, longitude=lon)
    clearsky = location.get_clearsky(df.index) # Ineichen/Solis clear sky
    
    # Transpose clear sky to POA
    dni_extra = get_extra_radiation(df.index)
    poa_clear = get_total_irradiance(
        surface_tilt=tilt,
        surface_azimuth=azimuth,
        dni=clearsky["dni"],
        ghi=clearsky["ghi"],
        dhi=clearsky["dhi"],
        dni_extra=dni_extra,
        solar_zenith=df["solar_zenith"],
        solar_azimuth=df["solar_azimuth"],
        model="haydavies",
    )
    
    eff = efficiency / 100.0
    loss_factor = 1.0 - (losses / 100.0)
    df["kwh_potential"] = (
        (poa_clear["poa_global"].clip(lower=0) / 1000.0)
        * system_size_kw
        * eff
        * loss_factor
        * 0.25
    )
    df.loc[df["solar_zenith"] >= 90, "kwh_potential"] = 0.0

    now = pd.Timestamp.now(tz=timezone)

    # ── Extract Yesterday's Diagnostics (Actual vs Potential) ──
    yesterday_start = now.normalize() - pd.Timedelta(days=1)
    yesterday_end = now.normalize() - pd.Timedelta(minutes=15)
    yesterday_df = df.loc[yesterday_start:yesterday_end]
    
    yesterday_actual = round(yesterday_df["kwh"].sum(), 2) if not yesterday_df.empty else 0.0
    yesterday_potential = round(yesterday_df["kwh_potential"].sum(), 2) if not yesterday_df.empty else 0.0
    
    loss_pct = 0.0
    if yesterday_potential > 0:
        loss_pct = round(((yesterday_potential - yesterday_actual) / yesterday_potential) * 100, 1)

    # ── Filter to next 24 hours from current time for future forecast ──
    start = now.ceil("15min")
    end = start + pd.Timedelta(hours=24)
    df_f = df.loc[start:end].head(96)

    # ── Confidence & Maintenance Alerts ──
    daylight = df_f[df_f["solar_zenith"] < 90]
    avg_cloud = daylight["cloud_cover"].mean() if not daylight.empty else 100
    confidence = compute_confidence(daylight["cloud_cover"]) if not daylight.empty else "Low"

    maintenance_alert = None
    if avg_cloud < 15:
        maintenance_alert = "Perfect clear skies! High ROI window to wash your solar panels today."

    # ── Sunrise / Sunset ──
    sunrise, sunset = get_sunrise_sunset(lat, lon, timezone)

    # ── Build response ──
    hourly = []
    for ts, row in df_f.iterrows():
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
    
    # ── Smart Window (Best 3-hour usage) ──
    # 3 hours = 12 steps of 15 mins
    best_3h_sum = -1.0
    smart_start = None
    smart_end = None
    
    for i in range(len(hourly) - 11):
        three_hour_sum = sum(h["kwh"] for h in hourly[i:i+12])
        if three_hour_sum > best_3h_sum:
            best_3h_sum = three_hour_sum
            smart_start = hourly[i]["hour"]
            smart_end = (pd.Timestamp(hourly[i+11]["hour"]) + pd.Timedelta(minutes=15)).isoformat()

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
        "smart_window_start": smart_start,
        "smart_window_end": smart_end,
        "yesterday_kwh": yesterday_actual,
        "yesterday_potential": yesterday_potential,
        "yesterday_loss_percent": loss_pct,
        "maintenance_alert": maintenance_alert,
    }
