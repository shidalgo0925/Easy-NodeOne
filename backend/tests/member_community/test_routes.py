"""Smoke: blueprint member_community (foros, grupos)."""
import sys
import unittest
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))


class TestMemberCommunityBlueprint(unittest.TestCase):
    def test_endpoints(self):
        from app import app

        endpoints = {r.endpoint for r in app.url_map.iter_rules()}
        self.assertIn('member_community.foros', endpoints)
        self.assertIn('member_community.grupos', endpoints)

    def test_paths(self):
        from app import app

        by_ep = {r.endpoint: r.rule for r in app.url_map.iter_rules()}
        self.assertEqual(by_ep.get('member_community.foros'), '/foros')
        self.assertEqual(by_ep.get('member_community.grupos'), '/grupos')


if __name__ == '__main__':
    unittest.main()
