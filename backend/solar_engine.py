"""
Solar Forecast Calculation Engine
Uses Open-Meteo API for irradiance forecast data and pvlib for solar modeling.
"""

import requests
import pandas as pd
import numpy as np
from typing import Dict, Any, Tuple, Optional
from timezonefinder import TimezoneFinder
from pvlib.location import Location
from pvlib.irradiance import get_total_irradiance, get_extra_radiation
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from settings import get_open_meteo_timeout, get_open_meteo_user_agent


OPEN_METEO_BASE = "https://api.open-meteo.com/v1/forecast"
DEFAULT_AZIMUTH = 180.0
DEFAULT_LOSSES = 14.0
DEFAULT_EFFICIENCY = 18.0

tf = TimezoneFinder()


def _build_retry_session() -> requests.Session:
    session = requests.Session()
    retries = Retry(
        total=2,
        read=2,
        connect=2,
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update({"User-Agent": get_open_meteo_user_agent()})
    return session


HTTP_SESSION = _build_retry_session()


def get_timezone(lat: float, lon: float) -> str:
    """Detect timezone from coordinates."""
    tz = tf.timezone_at(lat=lat, lng=lon)
    return tz if tz else "UTC"


def localize_index(index: pd.DatetimeIndex, timezone: str) -> pd.DatetimeIndex:
    """Ensure forecast timestamps are timezone-aware in the detected timezone."""
    if index.tz is None:
        return index.tz_localize(timezone)
    return index.tz_convert(timezone)


def build_forecast_dataframe(data: Dict[str, Any], timezone: str) -> pd.DataFrame:
    """Normalize and validate Open-Meteo forecast payload into a dataframe."""
    try:
        minutely = data["minutely_15"]
        hourly = data["hourly"]
    except KeyError as exc:
        raise ValueError(f"Open-Meteo response missing '{exc.args[0]}' data") from exc

    required_minutely = {
        "time",
        "shortwave_radiation",
        "direct_normal_irradiance",
        "diffuse_radiation",
    }
    required_hourly = {"time", "cloudcover", "temperature_2m"}

    missing_fields = sorted(required_minutely - set(minutely)) + sorted(
        required_hourly - set(hourly)
    )
    if missing_fields:
        raise ValueError(
            f"Open-Meteo response missing required fields: {', '.join(missing_fields)}"
        )

    df_15 = pd.DataFrame(
        {
            "time": pd.to_datetime(minutely["time"]),
            "ghi": minutely["shortwave_radiation"],
            "dni": minutely["direct_normal_irradiance"],
            "dhi": minutely["diffuse_radiation"],
        }
    ).set_index("time")

    df_hr = pd.DataFrame(
        {
            "time": pd.to_datetime(hourly["time"]),
            "cloud_cover": hourly["cloudcover"],
            "temperature": hourly["temperature_2m"],
        }
    ).set_index("time")

    df_hr = df_hr.resample("15min").interpolate(method="linear")
    df = df_15.join(df_hr, how="inner")
    df.index = localize_index(df.index, timezone)
    return df


def fetch_irradiance_forecast(lat: float, lon: float, timezone: str) -> pd.DataFrame:
    """
    Fetch 15-minute irradiance and weather forecast from Open-Meteo.
    Returns DataFrame with columns: ghi, dni, dhi, cloud_cover, temperature
    """
    params = {
        "latitude": lat,
        "longitude": lon,
        "minutely_15": ",".join(
            [
                "shortwave_radiation",
                "direct_normal_irradiance",
                "diffuse_radiation",
            ]
        ),
        "hourly": ",".join(["cloudcover", "temperature_2m"]),
        "timezone": timezone,
        "forecast_days": 2,
        "past_days": 1,
    }

    try:
        response = HTTP_SESSION.get(
            OPEN_METEO_BASE,
            params=params,
            timeout=get_open_meteo_timeout(),
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise ValueError("Unable to fetch forecast data from Open-Meteo right now.") from exc

    try:
        data = response.json()
    except ValueError as exc:
        raise ValueError("Open-Meteo returned an invalid JSON response.") from exc

    return build_forecast_dataframe(data, timezone)


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

    solpos = location.get_solarposition(df.index)
    dni_extra = get_extra_radiation(df.index)

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


def compute_hourly_generation(
    df: pd.DataFrame,
    system_size_kw: float,
    efficiency: float,
    losses: float,
) -> pd.DataFrame:
    """
    Convert POA irradiance to hourly energy generation (kWh).

    Power (kW) = POA (W/m2) x System_Size (kW) x Efficiency / 1000 W/kW
    Then apply losses, and since each row is 15 minutes, kWh = Power * 0.25.
    """
    eff = efficiency / 100.0
    loss_factor = 1.0 - (losses / 100.0)

    df["kwh"] = (
        (df["poa_global"] / 1000.0)
        * system_size_kw
        * eff
        * loss_factor
        * 0.25
    )

    df.loc[df["solar_zenith"] >= 90, "kwh"] = 0.0
    df["kwh"] = df["kwh"].clip(lower=0)
    df["kwh"] = df["kwh"].round(3)

    return df


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
    if avg_cloud <= 60:
        return "Medium"
    return "Low"


def assess_confidence(daylight: pd.DataFrame) -> Dict[str, Any]:
    """Build a more informative confidence assessment from forecast stability."""
    if daylight.empty:
        return {
            "confidence": "Low",
            "confidence_score": 20,
            "confidence_reason": "Very limited daylight forecast data is available for this location right now.",
        }

    avg_cloud = float(daylight["cloud_cover"].mean())
    cloud_std = float(daylight["cloud_cover"].std(ddof=0))
    irradiance_change = daylight["ghi"].diff().abs().fillna(0)
    irradiance_volatility = float(irradiance_change.mean())

    score = 100
    score -= min(45, avg_cloud * 0.55)
    score -= min(25, cloud_std * 0.45)
    score -= min(20, irradiance_volatility / 35)
    score = max(5, min(100, int(round(score))))

    if score >= 75:
        level = "High"
    elif score >= 45:
        level = "Medium"
    else:
        level = "Low"

    if avg_cloud < 20 and cloud_std < 15 and irradiance_volatility < 140:
        reason = "Stable clear-sky conditions are expected, so forecast uncertainty is low."
    elif avg_cloud > 65:
        reason = "Heavy cloud cover is expected for much of the day, which reduces forecast certainty."
    elif cloud_std > 25 or irradiance_volatility > 220:
        reason = "Rapid cloud and irradiance swings are expected, so output may change through the day."
    else:
        reason = "Conditions look mixed but reasonably stable, so the forecast should be directionally reliable."

    return {
        "confidence": level,
        "confidence_score": score,
        "confidence_reason": reason,
    }


def get_sunrise_sunset(lat: float, lon: float, tz: str) -> Tuple[Optional[str], Optional[str]]:
    """Get sunrise and sunset times for today using pvlib."""
    location = Location(latitude=lat, longitude=lon, tz=tz)
    today = pd.Timestamp.now(tz=tz).normalize()

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
    if tilt is None:
        tilt = abs(lat)
    if azimuth is None:
        azimuth = DEFAULT_AZIMUTH

    timezone = get_timezone(lat, lon)
    df = fetch_irradiance_forecast(lat, lon, timezone)
    df = compute_poa_irradiance(df, lat, lon, tilt, azimuth)
    df = compute_hourly_generation(df, system_size_kw, efficiency, losses)

    location = Location(latitude=lat, longitude=lon)
    clearsky = location.get_clearsky(df.index)

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

    yesterday_start = now.normalize() - pd.Timedelta(days=1)
    yesterday_end = now.normalize() - pd.Timedelta(minutes=15)
    yesterday_df = df.loc[yesterday_start:yesterday_end]

    yesterday_actual = round(yesterday_df["kwh"].sum(), 2) if not yesterday_df.empty else 0.0
    yesterday_potential = (
        round(yesterday_df["kwh_potential"].sum(), 2) if not yesterday_df.empty else 0.0
    )

    loss_pct = 0.0
    if yesterday_potential > 0:
        loss_pct = round(
            ((yesterday_potential - yesterday_actual) / yesterday_potential) * 100,
            1,
        )

    start = now.ceil("15min")
    end = start + pd.Timedelta(hours=24)
    df_f = df.loc[start:end].head(96)

    daylight = df_f[df_f["solar_zenith"] < 90]
    avg_cloud = daylight["cloud_cover"].mean() if not daylight.empty else 100
    confidence_data = assess_confidence(daylight)
    confidence = confidence_data["confidence"]

    maintenance_alert = None
    if avg_cloud < 15:
        maintenance_alert = "Perfect clear skies! High ROI window to wash your solar panels today."

    sunrise, sunset = get_sunrise_sunset(lat, lon, timezone)

    hourly = []
    for ts, row in df_f.iterrows():
        hourly.append(
            {
                "hour": ts.isoformat(),
                "kwh": round(row["kwh"], 3),
                "irradiance": round(row["poa_global"], 1),
                "ghi": round(row["ghi"], 1),
                "temperature": round(row["temperature"], 1),
                "cloud_cover": round(row["cloud_cover"], 1),
            }
        )

    total_kwh = round(sum(h["kwh"] for h in hourly), 2)

    if hourly:
        peak = max(hourly, key=lambda h: h["kwh"])
        peak_hour = peak["hour"]
        peak_kwh = peak["kwh"]
    else:
        peak_hour = ""
        peak_kwh = 0.0

    best_3h_sum = -1.0
    smart_start = None
    smart_end = None

    for i in range(len(hourly) - 11):
        three_hour_sum = sum(h["kwh"] for h in hourly[i : i + 12])
        if three_hour_sum > best_3h_sum:
            best_3h_sum = three_hour_sum
            smart_start = hourly[i]["hour"]
            smart_end = (
                pd.Timestamp(hourly[i + 11]["hour"]) + pd.Timedelta(minutes=15)
            ).isoformat()

    return {
        "hourly": hourly,
        "total_kwh": total_kwh,
        "peak_hour": peak_hour,
        "peak_kwh": peak_kwh,
        "confidence": confidence,
        "confidence_score": confidence_data["confidence_score"],
        "confidence_reason": confidence_data["confidence_reason"],
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
