"""Structural checks — EN1 horizontal chrome chips Pedidos (plan UI unify)."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


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
        self.assertIn('subnav-chips-pedidos', html)

    def test_css_active_uses_action_primary(self):
        css = (ROOT / 'static' / 'css' / 'sidebar-erp-theme.css').read_text(encoding='utf-8')
        self.assertIn('.erp-app-subnav__link.is-active', css)
        self.assertIn('--en1-action', css)
        self.assertNotIn('inset 0 -3px 0 0 #0ea5e9', css)

    def test_inventory_toolbars_no_nav_back_to_existencias(self):
        for name in ('movements.html', 'kardex.html', 'alerts.html'):
            html = (ROOT / 'templates' / 'admin' / 'en1_inventory' / name).read_text(encoding='utf-8')
            self.assertNotIn("inventory_balances')\">Existencias", html, name)

    def test_occ_uses_chip_classes(self):
        html = (ROOT / 'templates' / 'eposone' / '_occ_macros.html').read_text(encoding='utf-8')
        self.assertIn('erp-app-subnav__link', html)
        self.assertIn('occ-subnav-chips', html)
        self.assertNotIn('class="nav nav-pills', html)


if __name__ == '__main__':
    unittest.main()
