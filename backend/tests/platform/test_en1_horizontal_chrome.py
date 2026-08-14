"""Structural checks — EN1 horizontal chrome chips Pedidos (plan UI unify)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
backend_dir = ROOT / 'backend'
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))


class TestEn1HorizontalChrome(unittest.TestCase):
    def test_subnav_has_no_breadcrumb_title(self):
        html = (ROOT / 'templates' / 'partials' / 'erp_app_subnav.html').read_text(encoding='utf-8')
        self.assertNotIn('erp-module-header__title', html)
        self.assertNotIn('erp-module-header__crumb', html)
        self.assertIn('erp-app-subnav__link', html)
        self.assertIn('is-active', html)

    def test_base_hides_inicio_when_module_bar(self):
        html = (ROOT / 'templates' / 'base.html').read_text(encoding='utf-8')
        self.assertIn('nav_show_module_bar', html)
        self.assertIn('if not (nav_show_module_bar|default(false))', html)
        self.assertIn("elif nav_show_module_bar and nav_area_children", html)

    def test_css_active_uses_action_primary(self):
        css = (ROOT / 'static' / 'css' / 'sidebar-erp-theme.css').read_text(encoding='utf-8')
        self.assertIn('.erp-app-subnav__link.is-active', css)
        self.assertIn('--en1-action', css)
        self.assertNotIn('inset 0 -3px 0 0 #0ea5e9', css)

    def test_inventory_toolbars_no_nav_back_to_existencias(self):
        for name in ('movements.html', 'kardex.html', 'alerts.html'):
            html = (ROOT / 'templates' / 'admin' / 'en1_inventory' / name).read_text(encoding='utf-8')
            self.assertNotIn("inventory_balances')\">Existencias", html, name)

    def test_company_wizard_is_fullwidth(self):
        html = (ROOT / 'templates' / 'admin' / 'company_wizard.html').read_text(encoding='utf-8')
        self.assertIn('en1-company-setup-fullwidth', html)
        self.assertNotIn('col-xl-10', html)
        self.assertNotIn('justify-content-center', html)

    def test_config_zone_hides_module_bar(self):
        from app import app as flask_app
        from nodeone.core.nav_menu import nav_launcher_payload

        kwargs = dict(
            nav_can=lambda _p: True,
            saas_module_enabled=lambda _c: True,
            saas_module_enabled_chain=lambda *_a: True,
            has_view_endpoint=lambda _e: True,
            show_academic_admin_nav=False,
            office365_module_enabled=False,
            show_platform_admin_nav=False,
            is_platform_admin=False,
            is_advisor=False,
            show_tenant_admin_menu=True,
        )
        with flask_app.test_request_context('/admin/company-setup'):
            with patch('nodeone.core.nav_menu._in_config_zone', return_value=True):
                with patch('nodeone.core.nav_menu.resolve_module_bar_area_id', return_value='config'):
                    out = nav_launcher_payload(**kwargs)
        self.assertEqual(out.get('nav_active_area_id'), 'config')
        self.assertFalse(out.get('nav_show_module_bar'))
        self.assertEqual(out.get('nav_area_children') or [], [])

    def test_occ_uses_chip_classes(self):
        html = (ROOT / 'templates' / 'eposone' / '_occ_macros.html').read_text(encoding='utf-8')
        self.assertIn('erp-app-subnav__link', html)
        self.assertIn('occ-subnav-chips', html)
        self.assertNotIn('class="nav nav-pills', html)


if __name__ == '__main__':
    unittest.main()
