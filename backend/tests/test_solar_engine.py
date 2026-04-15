"""Unit tests for backend forecast helpers."""

import unittest

import pandas as pd

from solar_engine import assess_confidence, build_forecast_dataframe, compute_confidence, localize_index


class SolarEngineTests(unittest.TestCase):
    def test_compute_confidence_thresholds(self):
        self.assertEqual(compute_confidence(pd.Series([5, 10, 15])), "High")
        self.assertEqual(compute_confidence(pd.Series([20, 40, 60])), "Medium")
        self.assertEqual(compute_confidence(pd.Series([70, 80, 90])), "Low")

    def test_localize_index_handles_naive_index(self):
        index = pd.to_datetime(["2026-04-15 06:00:00"])
        localized = localize_index(index, "Asia/Kolkata")
        self.assertEqual(str(localized.tz), "Asia/Kolkata")

    def test_build_forecast_dataframe_validates_required_fields(self):
        with self.assertRaisesRegex(ValueError, "missing required fields"):
            build_forecast_dataframe(
                {
                    "minutely_15": {
                        "time": ["2026-04-15T06:00"],
                        "shortwave_radiation": [10],
                    },
                    "hourly": {
                        "time": ["2026-04-15T06:00"],
                        "cloudcover": [20],
                        "temperature_2m": [28],
                    },
                },
                "Asia/Kolkata",
            )

    def test_build_forecast_dataframe_returns_expected_columns(self):
        frame = build_forecast_dataframe(
            {
                "minutely_15": {
                    "time": [
                        "2026-04-15T06:00",
                        "2026-04-15T06:15",
                        "2026-04-15T06:30",
                        "2026-04-15T06:45",
                    ],
                    "shortwave_radiation": [10, 20, 30, 40],
                    "direct_normal_irradiance": [5, 10, 15, 20],
                    "diffuse_radiation": [3, 4, 5, 6],
                },
                "hourly": {
                    "time": ["2026-04-15T06:00", "2026-04-15T07:00"],
                    "cloudcover": [20, 40],
                    "temperature_2m": [28, 30],
                },
            },
            "Asia/Kolkata",
        )

        self.assertListEqual(
            list(frame.columns),
            ["ghi", "dni", "dhi", "cloud_cover", "temperature"],
        )
        self.assertEqual(len(frame), 4)

    def test_assess_confidence_returns_high_for_stable_conditions(self):
        daylight = pd.DataFrame(
            {
                "cloud_cover": [5, 8, 10, 12],
                "ghi": [650, 670, 680, 690],
            }
        )

        result = assess_confidence(daylight)
        self.assertEqual(result["confidence"], "High")
        self.assertGreaterEqual(result["confidence_score"], 75)

    def test_assess_confidence_returns_low_for_unstable_conditions(self):
        daylight = pd.DataFrame(
            {
                "cloud_cover": [20, 90, 30, 95],
                "ghi": [700, 250, 660, 180],
            }
        )

        result = assess_confidence(daylight)
        self.assertEqual(result["confidence"], "Low")
        self.assertLess(result["confidence_score"], 45)


if __name__ == "__main__":
    unittest.main()
