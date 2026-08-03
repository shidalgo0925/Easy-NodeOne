"""Tests Asistente de Inicio EPosOne (ADR-024) — Dev."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))


class TestRecommendEngine(unittest.TestCase):
    def test_cafe_recommends_business(self):
        from nodeone.modules.eposone_start.recommend import recommend_for_business_type

        r = recommend_for_business_type('Cafetería')
        self.assertEqual(r['plan_code'], 'business')
        self.assertEqual(r['modality'], 'connected')
        self.assertIn('39.95', r['price_label'])

    def test_mini_super_recommends_starter(self):
        from nodeone.modules.eposone_start.recommend import recommend_for_business_type

        r = recommend_for_business_type('Mini súper')
        self.assertEqual(r['plan_code'], 'starter')

    def test_catalog_has_four_plans(self):
        from nodeone.modules.eposone_start.recommend import catalog_payload

        cat = catalog_payload('Restaurante')
        self.assertEqual(len(cat['plans']), 4)
        self.assertEqual(cat['recommendation']['plan_code'], 'business')


class TestStartRoutes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from app import app as flask_app

        cls.app = flask_app
        cls.headers = {'Host': 'eposone.easytech.services'}

    def test_start_page_on_eposone_host(self):
        with self.app.test_client() as c:
            r = c.get('/start', headers=self.headers)
            self.assertEqual(r.status_code, 200)
            body = r.get_data(as_text=True)
            self.assertIn('Empieza con EPosOne', body)
            self.assertIn('eposone_start/start.js', body)

    def test_start_404_on_en1_host(self):
        with self.app.test_client() as c:
            r = c.get('/start', headers={'Host': 'appdev.easynodeone.com'})
            self.assertEqual(r.status_code, 404)

    def test_recommend_api(self):
        with self.app.test_client() as c:
            r = c.get(
                '/api/public/eposone-start/recommend?business_type=Bar',
                headers=self.headers,
            )
            self.assertEqual(r.status_code, 200)
            data = r.get_json()
            self.assertEqual(data['plan_code'], 'business')

    def test_complete_validation(self):
        with self.app.test_client() as c:
            r = c.post(
                '/api/public/eposone-start/complete',
                headers={**self.headers, 'Content-Type': 'application/json'},
                json={
                    'full_name': 'Ana',
                    'email': 'ana@example.test',
                    'password': 'short',
                    'business_name': 'Café',
                    'business_type': 'Cafetería',
                    'plan_code': 'business',
                    'accept_terms': True,
                    'accept_privacy': True,
                    'accept_eula': True,
                },
            )
            self.assertEqual(r.status_code, 400)
            self.assertEqual(r.get_json()['error'], 'validation_error')

    @patch('nodeone.modules.eposone_start.routes.complete_start')
    def test_complete_success_mocked(self, mock_complete):
        mock_complete.return_value = {
            'ok': True,
            'organization_id': 1,
            'installation': {'code': 'ABCD-1234'},
            'wow': {'title': '¡Bienvenido a EPosOne!', 'subtitle': 'x', 'checks': []},
            'play_store_url': 'https://play.google.com',
            'plan': {'plan_code': 'business'},
            'subscription': {'status': 'trial'},
        }
        with self.app.test_client() as c:
            r = c.post(
                '/api/public/eposone-start/complete',
                headers={**self.headers, 'Content-Type': 'application/json'},
                json={
                    'full_name': 'Ana Pérez',
                    'email': 'ana2@example.test',
                    'password': 'password123',
                    'business_name': 'Café Aurora',
                    'business_type': 'Cafetería',
                    'plan_code': 'business',
                    'accept_terms': True,
                    'accept_privacy': True,
                    'accept_eula': True,
                },
            )
            self.assertEqual(r.status_code, 201)
            self.assertTrue(r.get_json()['ok'])


if __name__ == '__main__':
    unittest.main()
