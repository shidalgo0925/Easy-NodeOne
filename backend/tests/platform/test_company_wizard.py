"""Tests wizard unificado de empresa."""

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))


class TestCompanyWizardService(unittest.TestCase):
    def test_resolve_initial_step_slug(self):
        from nodeone.services.company_wizard import resolve_initial_wizard_step, wizard_max_step

        self.assertEqual(resolve_initial_wizard_step(mode='tenant', step_arg='branding'), 3)
        self.assertEqual(resolve_initial_wizard_step(mode='tenant', step_arg='fiscal'), 2)
        self.assertEqual(resolve_initial_wizard_step(mode='tenant', step_arg='acceso'), 3)
        self.assertEqual(resolve_initial_wizard_step(mode='tenant', step_arg='opciones'), 4)
        self.assertEqual(resolve_initial_wizard_step(mode='platform', step_arg='opciones'), 5)
        self.assertEqual(wizard_max_step(mode='tenant'), 4)
        self.assertEqual(wizard_max_step(mode='platform'), 5)

    def test_identity_preset_choices(self):
        from nodeone.services.company_wizard import (
            IDENTITY_PRESETS,
            identity_preset_choices_for_wizard,
        )

        keys = [k for k, _ in identity_preset_choices_for_wizard()]
        self.assertIn('en1', keys)
        self.assertIn('custom', keys)
        self.assertIn('esmeralda', keys)
        self.assertIn('asador', keys)
        self.assertEqual(
            IDENTITY_PRESETS['asador'],
            {
                'primary_color': '#9B1C1C',
                'primary_color_dark': '#1A1412',
                'accent_color': '#F0B429',
            },
        )

    def test_validate_hex_color(self):
        from nodeone.services.company_wizard import validate_hex_color

        self.assertTrue(validate_hex_color('#FF6B35'))
        self.assertFalse(validate_hex_color('FF6B35'))

    @patch('app.db')
    @patch('models.saas.OrganizationSettings')
    def test_save_identity_preset(self, mock_settings_cls, mock_db):
        from nodeone.services.company_wizard import save_identity_from_form

        row = MagicMock()
        mock_settings_cls.query.filter_by.return_value.first.return_value = row
        err = save_identity_from_form({'identity_preset': 'en1'}, 1)
        self.assertIsNone(err)
        self.assertEqual(row.preset, 'en1')

    def test_fiscal_payload_from_form(self):
        from nodeone.services.company_wizard import fiscal_payload_from_form

        payload = fiscal_payload_from_form({'legal_name': ' ACME ', 'tax_id': '123'})
        self.assertEqual(payload['legal_name'], 'ACME')
        self.assertEqual(payload['tax_id'], '123')

    @patch('flask.url_for', side_effect=lambda ep, **kw: f'/{ep}')
    def test_tenant_quick_links_exclude_saas(self, _url_for):
        from nodeone.services.company_wizard import build_wizard_quick_links

        labels = [
            x['label']
            for x in build_wizard_quick_links(
                wizard_mode='tenant', org_id=1, has_view_endpoint=lambda _e: True
            )
        ]
        self.assertNotIn('Módulos SaaS', labels)
        self.assertNotIn('Guía de productos', labels)
        self.assertNotIn('Catálogo módulos', labels)
        self.assertIn('Impuestos', labels)
        self.assertIn('Usuarios', labels)

    @patch('flask.url_for', side_effect=lambda ep, **kw: f'/{ep}')
    def test_platform_quick_links_include_saas(self, _url_for):
        from nodeone.services.company_wizard import build_wizard_quick_links

        labels = [
            x['label']
            for x in build_wizard_quick_links(
                wizard_mode='edit', org_id=1, has_view_endpoint=lambda _e: True
            )
        ]
        self.assertIn('Módulos SaaS', labels)
        self.assertIn('Catálogo módulos', labels)


class TestCompanyWizardRoutes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from app import app as flask_app

        cls.app = flask_app

    def test_company_wizard_routes_registered(self):
        rules = {r.rule for r in self.app.url_map.iter_rules()}
        self.assertIn('/admin/company', rules)
        self.assertIn('/admin/organizations/new', rules)

    def test_identity_redirects_to_company(self):
        with self.app.test_client() as client:
            resp = client.get('/admin/identity', follow_redirects=False)
            self.assertIn(resp.status_code, (302, 401))


if __name__ == '__main__':
    unittest.main()
