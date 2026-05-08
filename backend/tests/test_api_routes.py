"""Route-level tests for SolarCast forecast API modes."""

import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from main import app


def sample_forecast(mode="physics", total_kwh=12.5, peak_kwh=1.25):
    """Build a minimal ForecastResponse-compatible payload."""
    return {
        "forecast_mode": mode,
        "engine_name": mode,
        "engine_notes": "test forecast",
        "hourly": [
            {
                "hour": "2026-05-08T12:00:00+05:30",
                "kwh": peak_kwh,
                "irradiance": 850.0,
                "ghi": 900.0,
                "temperature": 32.0,
                "cloud_cover": 20.0,
            }
        ],
        "daily_summaries": [
            {
                "date": "2026-05-08",
                "total_kwh": total_kwh,
                "peak_kwh": peak_kwh,
                "peak_hour": "2026-05-08T12:00:00+05:30",
            }
        ],
        "forecast_hours": 24,
        "total_kwh": total_kwh,
        "peak_hour": "2026-05-08T12:00:00+05:30",
        "peak_kwh": peak_kwh,
        "confidence": "High",
        "confidence_score": 88,
        "confidence_reason": "Stable test irradiance profile.",
        "location_info": {
            "latitude": 28.6139,
            "longitude": 77.2090,
            "timezone": "Asia/Kolkata",
        },
        "system_params": {
            "system_size_kw": 10.0,
            "tilt": 28.6,
            "azimuth": 180.0,
            "losses": 14.0,
            "efficiency": 18.0,
        },
        "sunrise": "05:35",
        "sunset": "18:58",
        "smart_window_start": "2026-05-08T11:15:00+05:30",
        "smart_window_end": "2026-05-08T12:00:00+05:30",
        "yesterday_kwh": None,
        "yesterday_potential": None,
        "yesterday_loss_percent": None,
        "maintenance_alert": "test alert",
    }


class ForecastRouteTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.request_payload = {
            "lat": 28.6139,
            "lon": 77.2090,
            "system_size_kw": 10,
            "losses": 14,
            "efficiency": 18,
            "forecast_hours": 24,
        }

    @patch("main.generate_ml_forecast")
    def test_ml_forecast_route_returns_forecast_response(self, mock_generate_ml):
        mock_generate_ml.return_value = sample_forecast("ml_only", total_kwh=11.2)

        response = self.client.post("/forecast/ml", json=self.request_payload)

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["forecast_hours"], 24)
        self.assertEqual(data["total_kwh"], 11.2)
        self.assertEqual(data["location_info"]["timezone"], "Asia/Kolkata")
        mock_generate_ml.assert_called_once()

    @patch("main.generate_hybrid_forecast")
    def test_hybrid_forecast_route_returns_forecast_response(self, mock_generate_hybrid):
        mock_generate_hybrid.return_value = sample_forecast("hybrid", total_kwh=12.1)

        response = self.client.post("/forecast/hybrid", json=self.request_payload)

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["forecast_hours"], 24)
        self.assertEqual(data["total_kwh"], 12.1)
        self.assertEqual(data["daily_summaries"][0]["date"], "2026-05-08")
        mock_generate_hybrid.assert_called_once()

    @patch("main.generate_hybrid_forecast")
    @patch("main.generate_ml_forecast")
    @patch("main.generate_forecast")
    def test_compare_route_returns_all_engines(
        self,
        mock_generate_physics,
        mock_generate_ml,
        mock_generate_hybrid,
    ):
        mock_generate_physics.return_value = sample_forecast("physics", total_kwh=10.0, peak_kwh=1.0)
        mock_generate_ml.return_value = sample_forecast("ml_only", total_kwh=11.0, peak_kwh=1.1)
        mock_generate_hybrid.return_value = sample_forecast("hybrid", total_kwh=10.5, peak_kwh=1.05)

        response = self.client.post("/forecast/compare", json=self.request_payload)

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("physics", data)
        self.assertIn("ml_only", data)
        self.assertIn("hybrid", data)
        self.assertIn("comparison", data)
        self.assertIn("hybrid_comparison", data)
        self.assertEqual(data["comparison"]["compared_intervals"], 1)
        self.assertEqual(data["hybrid_comparison"]["total_kwh_delta"], 0.05)

    @patch("main.generate_ml_forecast")
    def test_missing_ml_artifact_returns_service_unavailable(self, mock_generate_ml):
        mock_generate_ml.side_effect = FileNotFoundError("missing artifact")

        response = self.client.post("/forecast/ml", json=self.request_payload)

        self.assertEqual(response.status_code, 503)
        self.assertIn("missing artifact", response.json()["detail"])


if __name__ == "__main__":
    unittest.main()
