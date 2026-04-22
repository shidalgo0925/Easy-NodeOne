"""Tests unitarios: parsing y auth de la API pública del landing (sin BD)."""

import sys
import unittest
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))


class TestLandingParsePreferred(unittest.TestCase):
    def test_date_only_defaults_9am(self):
        from nodeone.modules.public_api import landing_pure

        dt = landing_pure.parse_preferred_start_utc('2030-06-15', '')
        self.assertIsNotNone(dt)
        self.assertEqual(dt.year, 2030)
        self.assertEqual(dt.month, 6)
        self.assertEqual(dt.day, 15)
        self.assertEqual(dt.hour, 9)
        self.assertEqual(dt.minute, 0)

    def test_date_and_time(self):
        from nodeone.modules.public_api import landing_pure

        dt = landing_pure.parse_preferred_start_utc('2030-01-20', '14:30')
        self.assertIsNotNone(dt)
        self.assertEqual(dt.hour, 14)
        self.assertEqual(dt.minute, 30)

    def test_invalid_date(self):
        from nodeone.modules.public_api import landing_pure

        self.assertIsNone(landing_pure.parse_preferred_start_utc('', '12:00'))
        self.assertIsNone(landing_pure.parse_preferred_start_utc('not-a-date', ''))


class TestLandingApiKey(unittest.TestCase):
    def test_compare_digest(self):
        from nodeone.modules.public_api import landing_pure

        self.assertTrue(
            landing_pure.verify_landing_api_key('secret', 'secret')
        )
        self.assertFalse(
            landing_pure.verify_landing_api_key('wrong', 'secret')
        )
        self.assertFalse(landing_pure.verify_landing_api_key('', 'secret'))
        self.assertFalse(landing_pure.verify_landing_api_key('x', ''))


class TestIdempotencyKeyNormalize(unittest.TestCase):
    def test_trim_and_cap(self):
        from nodeone.modules.public_api import landing_pure

        self.assertIsNone(landing_pure.normalize_idempotency_key(None))
        self.assertIsNone(landing_pure.normalize_idempotency_key('   '))
        long_k = 'a' * 200
        self.assertEqual(
            len(landing_pure.normalize_idempotency_key(long_k) or ''),
            128,
        )


if __name__ == '__main__':
    unittest.main()
