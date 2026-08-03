"""Tests centro legal ETS (/legal)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

from flask import Flask

backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))


class TestEtsLegalPages(unittest.TestCase):
    def test_catalog_has_required_slugs(self):
        from nodeone.modules.ets_legal.pages import LEGAL_PAGES, get_legal_page

        slugs = {p.slug for p in LEGAL_PAGES}
        for needed in (
            'terms',
            'privacy',
            'cookies',
            'eula',
            'refunds',
            'ip',
            'data-deletion',
            'support',
        ):
            self.assertIn(needed, slugs)
        self.assertIsNotNone(get_legal_page('eula'))
        self.assertIsNone(get_legal_page('nope'))

    def test_routes_render(self):
        from nodeone.modules.ets_legal.register import register_ets_legal

        app = Flask(
            __name__,
            template_folder=str(backend_dir.parent / 'templates'),
            static_folder=str(backend_dir.parent / 'static'),
        )
        register_ets_legal(app)
        with app.test_client() as c:
            r = c.get('/legal/')
            self.assertEqual(r.status_code, 200)
            self.assertIn(b'Centro legal', r.data)
            self.assertEqual(c.get('/legal/privacy').status_code, 200)
            self.assertEqual(c.get('/legal/eula').status_code, 200)
            self.assertEqual(c.get('/legal/missing').status_code, 404)


if __name__ == '__main__':
    unittest.main()
