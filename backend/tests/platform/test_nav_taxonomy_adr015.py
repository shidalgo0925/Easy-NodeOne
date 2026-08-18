"""ADR-015 — taxonomía de navegación v1/v2."""

from __future__ import annotations

import os
import unittest


class NavTaxonomyTests(unittest.TestCase):
    def setUp(self):
        self._prev = os.environ.get('NODEONE_NAV_TAXONOMY')
        os.environ.pop('NODEONE_NAV_TAXONOMY_V1_ORG_IDS', None)
        os.environ.pop('NODEONE_NAV_TAXONOMY_V2_ORG_IDS', None)

    def tearDown(self):
        if self._prev is None:
            os.environ.pop('NODEONE_NAV_TAXONOMY', None)
        else:
            os.environ['NODEONE_NAV_TAXONOMY'] = self._prev

    def _ctx(self):
        from nodeone.core.nav_menu import build_nav_context

        return build_nav_context(
            nav_can=lambda _p: True,
            saas_module_enabled=lambda _c: True,
            saas_module_enabled_chain=lambda *_a: True,
            has_view_endpoint=lambda _e: True,
            show_academic_admin_nav=True,
            office365_module_enabled=True,
            show_platform_admin_nav=True,
            is_platform_admin=True,
            is_advisor=False,
            show_tenant_admin_menu=True,
        )

    def test_v2_flat_launcher_no_legacy_groups(self):
        from nodeone.core.nav_menu import (
            _SIDEBAR_V2_FLAT_AREA_IDS,
            current_nav_taxonomy,
            visible_sidebar_launcher,
        )

        os.environ['NODEONE_NAV_TAXONOMY'] = 'v2'
        self.assertEqual(current_nav_taxonomy(), 'v2')
        top, groups = visible_sidebar_launcher(self._ctx())
        self.assertEqual(groups, [])
        labels = {a['label'] for a in top}
        ids = {a['id'] for a in top}
        self.assertNotIn('Comercial', labels)
        self.assertIn('facturacion', ids)
        self.assertIn('cobros', ids)
        self.assertIn('Marketing', labels)
        self.assertIn('tienda', ids)
        # Contador = «Conteo físico»; Inventario EN1 (ADR-039 + unificación A+B+C) sí va en v2.
        self.assertIn('Inventario', labels)
        self.assertIn('inventario', ids)
        self.assertNotIn('Taller', labels)
        self.assertNotIn('Eventos', labels)
        flat_ids = [a['id'] for a in top]
        # Orden relativo según lista canónica (solo ids presentes/visibles)
        expected = [aid for aid in _SIDEBAR_V2_FLAT_AREA_IDS if aid in ids]
        self.assertEqual(flat_ids, expected)
        self.assertEqual(
            list(_SIDEBAR_V2_FLAT_AREA_IDS),
            [
                'contactos',
                'crm',
                'ventas',
                'facturacion',
                'cobros',
                'inventario',
                'tienda',
                'marketing_email',
                'eposone',
                'agenda',
                'membresias',
                'educacion',
                'certificados',
                'analitica',
                'epayroll',
                'plataforma',
            ],
        )

    def test_tienda_visible_with_sales_without_appointments(self):
        from nodeone.core.nav_menu import _v_tienda, build_nav_context

        ctx = build_nav_context(
            nav_can=lambda _p: True,
            saas_module_enabled=lambda c: c == 'sales',
            saas_module_enabled_chain=lambda *_a: False,
            has_view_endpoint=lambda e: e == 'services.list',
            show_academic_admin_nav=False,
            office365_module_enabled=False,
            show_platform_admin_nav=False,
            is_platform_admin=False,
            is_advisor=False,
            show_tenant_admin_menu=True,
        )
        self.assertTrue(_v_tienda(ctx))

    def test_v1_keeps_legacy_groups(self):
        from nodeone.core.nav_menu import current_nav_taxonomy, visible_sidebar_launcher

        os.environ['NODEONE_NAV_TAXONOMY'] = 'v1'
        self.assertEqual(current_nav_taxonomy(), 'v1')
        _top, groups = visible_sidebar_launcher(self._ctx())
        glabels = {g['label'] for g in groups}
        self.assertIn('Comercial', glabels)
        self.assertIn('Finanzas', glabels)


if __name__ == '__main__':
    unittest.main()
