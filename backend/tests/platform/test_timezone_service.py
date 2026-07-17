"""Tests unitarios TimeZoneService (política oficial UTC / IANA)."""

import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))


class TestTimeZoneService(unittest.TestCase):
    def test_validate_iana_ok_and_fallback(self):
        from nodeone.core.timezone_service import TimeZoneService

        self.assertEqual(TimeZoneService.validate_iana('America/Panama'), 'America/Panama')
        self.assertEqual(TimeZoneService.validate_iana('Not/AZone'), 'America/Panama')
        self.assertEqual(TimeZoneService.validate_iana(None), 'America/Panama')

    def test_day_bounds_panama(self):
        from nodeone.core.timezone_service import TimeZoneService

        start, end = TimeZoneService.day_bounds_utc_naive('2026-07-17', 'America/Panama')
        self.assertEqual(start, datetime(2026, 7, 17, 5, 0, 0))
        self.assertEqual(end, datetime(2026, 7, 18, 5, 0, 0))

    def test_offset_iso_panama(self):
        from nodeone.core.timezone_service import TimeZoneService

        at = datetime(2026, 7, 17, 12, 0, 0, tzinfo=timezone.utc)
        self.assertEqual(TimeZoneService.offset_iso('America/Panama', at=at), '-05:00')

    def test_to_api_iso(self):
        from nodeone.core.timezone_service import TimeZoneService

        self.assertEqual(
            TimeZoneService.to_api_iso(datetime(2026, 7, 17, 1, 45, 33)),
            '2026-07-17T01:45:33Z',
        )
        self.assertIsNone(TimeZoneService.to_api_iso(None))

    def test_local_roundtrip(self):
        from nodeone.core.timezone_service import TimeZoneService

        local = datetime(2026, 7, 16, 18, 43, 0)
        utc_naive = TimeZoneService.local_to_utc_naive(local, 'America/Panama')
        self.assertEqual(utc_naive, datetime(2026, 7, 16, 23, 43, 0))
        back = TimeZoneService.utc_naive_to_local(utc_naive, 'America/Panama')
        self.assertIsNotNone(back)
        assert back is not None
        self.assertEqual(back.hour, 18)
        self.assertEqual(back.minute, 43)
        self.assertEqual(str(back.tzinfo), 'America/Panama')

    def test_format_local(self):
        from nodeone.core.timezone_service import TimeZoneService

        s = TimeZoneService.format_local(
            datetime(2026, 7, 17, 5, 30, 0),
            ZoneInfo('America/Panama'),
            'DD/MM/YYYY',
            '24h',
        )
        self.assertEqual(s, '17/07/2026 00:30')

    def test_effective_prefers_user_then_org(self):
        from nodeone.core.timezone_service import TimeZoneService

        class Org:
            timezone = 'America/Bogota'

        name = TimeZoneService.effective_timezone_name(
            organization=Org(),
            prefs={'timezone': 'America/New_York'},
        )
        self.assertEqual(name, 'America/New_York')
        name2 = TimeZoneService.effective_timezone_name(organization=Org(), prefs={})
        self.assertEqual(name2, 'America/Bogota')


if __name__ == '__main__':
    unittest.main()
