"""ADR-019 — jerarquía admin: labels Plataforma (SaaS/Sistema) vs Empresa."""

from __future__ import annotations

import unittest

from nodeone.core.nav_menu import (
    APP_AREAS,
    _PLATAFORMA_SAAS_ITEMS,
    _PLATAFORMA_SISTEMA_ITEMS,
    _v_plataforma,
    build_nav_context,
)


class TestAdr019AdminHierarchyNav(unittest.TestCase):
    def test_plataforma_labels_saas_and_sistema(self):
        area = next(a for a in APP_AREAS if a.id == 'plataforma')
        drop_labels = {it.label for it in area.items if it.dropdown_items}
        self.assertIn('SaaS', drop_labels)
        self.assertIn('Sistema', drop_labels)
        self.assertNotIn('Administración', drop_labels)

        saas_labels = [it.label for it in _PLATAFORMA_SAAS_ITEMS]
        self.assertEqual(saas_labels, ['Organizaciones', 'Catálogo SaaS', 'Módulos SaaS'])

        sistema_labels = [it.label for it in _PLATAFORMA_SISTEMA_ITEMS]
        self.assertIn('Usuarios globales', sistema_labels)
        self.assertIn('Logs', sistema_labels)
        self.assertIn('Respaldos', sistema_labels)

    def test_config_area_label_is_empresa(self):
        area = next(a for a in APP_AREAS if a.id == 'config')
        self.assertEqual(area.label, 'Empresa')
        drop_labels = {it.label for it in area.items if it.dropdown_items}
        self.assertIn('Perfil', drop_labels)
        self.assertIn('Fiscal', drop_labels)
        self.assertIn('Acceso', drop_labels)
        self.assertNotIn('Organización', drop_labels)

    def test_plataforma_only_for_platform_admin(self):
        sa = build_nav_context(
            nav_can=lambda _p: True,
            saas_module_enabled=lambda _c: True,
            saas_module_enabled_chain=lambda *_a: True,
            has_view_endpoint=lambda _e: True,
            show_academic_admin_nav=False,
            office365_module_enabled=False,
            show_platform_admin_nav=True,
            is_platform_admin=True,
            is_advisor=False,
            show_tenant_admin_menu=True,
        )
        tenant = build_nav_context(
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
        self.assertTrue(_v_plataforma(sa))
        self.assertFalse(_v_plataforma(tenant))


if __name__ == '__main__':
    unittest.main()
