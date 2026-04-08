"""Smoke: blueprint admin_discount_codes."""
import sys
import unittest
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))


class TestAdminDiscountCodesBlueprint(unittest.TestCase):
    def test_discount_endpoints(self):
        from app import app

        endpoints = {r.endpoint for r in app.url_map.iter_rules()}
        required = {
            'admin_discount_codes.admin_discount_codes',
            'admin_discount_codes.admin_discount_code_create',
            'admin_discount_codes.admin_discount_code_get',
            'admin_discount_codes.admin_discount_code_update',
            'admin_discount_codes.admin_discount_code_delete',
            'admin_discount_codes.api_generate_discount_code',
        }
        self.assertFalse(required - endpoints, f'Faltan: {sorted(required - endpoints)}')

    def test_discount_paths(self):
        from app import app

        by_ep = {r.endpoint: r.rule for r in app.url_map.iter_rules()}
        self.assertEqual(by_ep.get('admin_discount_codes.admin_discount_codes'), '/admin/discount-codes')


if __name__ == '__main__':
    unittest.main()
