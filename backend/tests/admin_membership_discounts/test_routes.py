"""Smoke: blueprint admin_membership_discounts."""
import sys
import unittest
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))


class TestAdminMembershipDiscountsBlueprint(unittest.TestCase):
    def test_endpoints(self):
        from app import app

        endpoints = {r.endpoint for r in app.url_map.iter_rules()}
        required = {
            'admin_membership_discounts.admin_membership_discounts',
            'admin_membership_discounts.admin_membership_discounts_create',
            'admin_membership_discounts.admin_membership_discounts_update',
            'admin_membership_discounts.admin_membership_discounts_get',
            'admin_membership_discounts.admin_membership_discounts_delete',
            'admin_membership_discounts.admin_master_discount',
        }
        self.assertFalse(required - endpoints, f'Faltan: {sorted(required - endpoints)}')

    def test_paths(self):
        from app import app

        by_ep = {r.endpoint: r.rule for r in app.url_map.iter_rules()}
        self.assertEqual(by_ep.get('admin_membership_discounts.admin_membership_discounts'), '/admin/membership-discounts')
        self.assertEqual(by_ep.get('admin_membership_discounts.admin_master_discount'), '/admin/master-discount')


if __name__ == '__main__':
    unittest.main()
