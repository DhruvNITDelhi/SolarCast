"""Pydantic models for the Solar Forecast API."""

from pydantic import BaseModel, Field
from typing import List, Optional


class ForecastRequest(BaseModel):
    """Request body for the /forecast endpoint."""
    lat: float = Field(..., ge=-90, le=90, description="Latitude")
    lon: float = Field(..., ge=-180, le=180, description="Longitude")
    system_size_kw: float = Field(..., gt=0, le=1000, description="System size in kW")
    tilt: Optional[float] = Field(None, ge=0, le=90, description="Panel tilt in degrees (default: latitude)")
    azimuth: Optional[float] = Field(None, ge=0, le=360, description="Panel azimuth in degrees (default: 180 for India)")
    losses: float = Field(14.0, ge=0, le=50, description="System losses percentage")
    efficiency: float = Field(18.0, ge=5, le=30, description="Panel efficiency percentage")


class TimeSeriesData(BaseModel):
    """A single 15-minute time step of forecast data."""
    hour: str = Field(..., description="ISO 8601 timestamp")
    kwh: float = Field(..., description="Estimated generation in kWh")
    irradiance: float = Field(..., description="Plane-of-array irradiance in W/m²")
    ghi: float = Field(..., description="Global Horizontal Irradiance in W/m²")
    temperature: float = Field(..., description="Ambient temperature in °C")
    cloud_cover: float = Field(..., description="Cloud cover percentage")


class SystemParams(BaseModel):
    """Echo of the system parameters used for the calculation."""
    system_size_kw: float
    tilt: float
    azimuth: float
    losses: float
    efficiency: float


class LocationInfo(BaseModel):
    """Location metadata."""
    latitude: float
    longitude: float
    timezone: str


class ForecastResponse(BaseModel):
    """Response body for the /forecast endpoint."""
    hourly: List[TimeSeriesData]
    total_kwh: float
    peak_hour: str
    peak_kwh: float
    confidence: str  # "High", "Medium", "Low"
    confidence_score: Optional[int] = None
    confidence_reason: Optional[str] = None
    location_info: LocationInfo
    system_params: SystemParams
    sunrise: Optional[str] = None
    sunset: Optional[str] = None
    smart_window_start: Optional[str] = None
    smart_window_end: Optional[str] = None
    yesterday_kwh: Optional[float] = None
    yesterday_potential: Optional[float] = None
    yesterday_loss_percent: Optional[float] = None
    maintenance_alert: Optional[str] = None
