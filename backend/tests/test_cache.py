"""Unit tests for backend cache helpers."""

import time
import unittest

from cache import TTLCache, build_forecast_cache_key


class CacheTests(unittest.TestCase):
    def test_cache_key_rounds_equivalent_requests(self):
        key_a = build_forecast_cache_key(28.6139123, 77.2090234, 10.0001, None, 180.004, 14.0, 18.0)
        key_b = build_forecast_cache_key(28.6139499, 77.2090499, 10.0002, None, 180.003, 14.0, 18.0)
        self.assertEqual(key_a, key_b)

    def test_ttl_cache_expires_values(self):
        cache = TTLCache(ttl_seconds=1, max_entries=2)
        cache.set("forecast", {"ok": True})
        self.assertEqual(cache.get("forecast"), {"ok": True})
        time.sleep(1.1)
        self.assertIsNone(cache.get("forecast"))


if __name__ == "__main__":
    unittest.main()
