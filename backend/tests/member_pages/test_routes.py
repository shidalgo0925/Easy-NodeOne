"""Smoke: blueprint member_pages (settings, help)."""
import sys
import unittest
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))


class TestMemberPagesBlueprint(unittest.TestCase):
    def test_endpoints(self):
        from app import app

        endpoints = {r.endpoint for r in app.url_map.iter_rules()}
        self.assertIn('member_pages.settings', endpoints)
        self.assertIn('member_pages.help_page', endpoints)

    def test_paths(self):
        from app import app

        by_ep = {r.endpoint: r.rule for r in app.url_map.iter_rules()}
        self.assertEqual(by_ep.get('member_pages.settings'), '/settings')
        self.assertEqual(by_ep.get('member_pages.help_page'), '/help')


if __name__ == '__main__':
    unittest.main()
