"""Tests unificación Inventario A+B+C — nav + puente Service↔core_product."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch


class TestInventarioNavUnify(unittest.TestCase):
    def test_ventas_catalog_productos_servicios_hidden(self):
        from nodeone.core.nav_menu import _v_catalog_productos, _v_catalog_servicios

        ctx = MagicMock()
        self.assertFalse(_v_catalog_productos(ctx))
        self.assertFalse(_v_catalog_servicios(ctx))

    def test_productos_top_level_hidden(self):
        from nodeone.core.nav_menu import APP_AREAS

        area = next(a for a in APP_AREAS if a.id == 'productos')
        self.assertFalse(area.visible(MagicMock()))

    def test_inventario_zone_includes_products(self):
        from nodeone.core.nav_menu import APP_AREAS

        inv = next(a for a in APP_AREAS if a.id == 'inventario')
        self.assertIn('en1_products', inv.zone_blueprints)
        self.assertIn('/admin/products', inv.zone_path_prefixes)


class TestProductBridge(unittest.TestCase):
    def test_product_ref_for_service(self):
        from nodeone.core.master.product_bridge import product_ref_for_service

        self.assertEqual(product_ref_for_service(42), 'svc-42')

    def test_brand_image_for_product(self):
        from nodeone.core.master.product_bridge import brand_image_for_product

        self.assertIn('card-easyclassone', brand_image_for_product(name='EClassOne') or '')
        self.assertIn('card-easythesis', brand_image_for_product(name='EThesis') or '')
        self.assertIn('card-eposone', brand_image_for_product(name='EPosOne') or '')

    @patch('nodeone.core.master.product_bridge.db')
    @patch('nodeone.core.master.product_bridge.CoreProductLegacyServiceLink')
    @patch('nodeone.core.master.product_bridge.CoreProduct')
    def test_ensure_from_service_creates_product(self, mock_cp, mock_link, mock_db):
        from nodeone.core.master.product_bridge import ensure_from_service

        mock_link.query.filter_by.return_value.first.return_value = None
        mock_cp.query.filter_by.return_value.first.return_value = None

        svc = MagicMock()
        svc.id = 7
        svc.name = 'Consulta'
        svc.description = 'Desc'
        svc.is_active = True
        svc.base_price = 25.0
        svc.image_url = None
        svc.service_type = 'AGENDABLE'
        svc.category = None

        pref = ensure_from_service(1, svc, commit=True)
        self.assertEqual(pref, 'svc-7')
        mock_cp.assert_called_once()
        mock_db.session.add.assert_called()
        mock_db.session.commit.assert_called()


if __name__ == '__main__':
    unittest.main()
