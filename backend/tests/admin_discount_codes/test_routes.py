"""Smoke: blueprint promos por producto."""
import sys
import unittest
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))


class TestAdminDiscountCodesBlueprint(unittest.TestCase):
    def test_product_promo_endpoints(self):
        from app import app

        endpoints = {r.endpoint for r in app.url_map.iter_rules()}
        required = {
            'admin_product_discount_codes.index',
            'admin_product_discount_codes.create',
            'admin_product_discount_codes.get_one',
            'admin_product_discount_codes.update',
            'admin_product_discount_codes.delete',
            'admin_product_discount_codes.api_generate',
            'admin_product_discount_codes.legacy_discount_codes_redirect',
        }
        self.assertFalse(required - endpoints, f'Faltan: {sorted(required - endpoints)}')

    def test_product_promo_paths(self):
        from app import app

        by_ep = {r.endpoint: r.rule for r in app.url_map.iter_rules()}
        self.assertEqual(
            by_ep.get('admin_product_discount_codes.index'),
            '/admin/commercial/product-discount-codes',
        )
        self.assertEqual(
            by_ep.get('admin_product_discount_codes.legacy_discount_codes_redirect'),
            '/admin/discount-codes',
        )


if __name__ == '__main__':
    unittest.main()
