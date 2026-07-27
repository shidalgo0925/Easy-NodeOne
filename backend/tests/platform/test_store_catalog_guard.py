"""Tienda /services: sales o appointments."""

from __future__ import annotations

import unittest
from unittest.mock import patch


class StoreCatalogGuardTests(unittest.TestCase):
    def test_org_store_catalog_enabled_sales_or_appointments(self):
        from saas_features import org_store_catalog_enabled

        with patch('app.has_saas_module_enabled') as mock_has:
            mock_has.side_effect = lambda oid, code: code == 'sales'
            self.assertTrue(org_store_catalog_enabled(7))

            mock_has.side_effect = lambda oid, code: code == 'appointments'
            self.assertTrue(org_store_catalog_enabled(7))

            mock_has.side_effect = lambda oid, code: False
            self.assertFalse(org_store_catalog_enabled(7))


if __name__ == '__main__':
    unittest.main()
