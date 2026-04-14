"""Smoke: blueprint admin_services_catalog (servicios + categorías admin)."""
import sys
import unittest
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))


class TestAdminServicesCatalogBlueprint(unittest.TestCase):
    def test_endpoints(self):
        from app import app

        endpoints = {r.endpoint for r in app.url_map.iter_rules()}
        self.assertIn('admin_services_catalog.admin_services', endpoints)
        self.assertIn('admin_services_catalog.admin_service_categories', endpoints)
        self.assertIn('admin_services_catalog.admin_services_create', endpoints)
        self.assertIn('admin_services_catalog.admin_service_categories_list', endpoints)
        self.assertIn('admin_services_catalog.admin_services_export_csv', endpoints)
        self.assertIn('admin_services_catalog.admin_services_export_xlsx', endpoints)
        self.assertIn('admin_services_catalog.admin_services_import_template_csv', endpoints)
        self.assertIn('admin_services_catalog.admin_services_import', endpoints)

    def test_paths(self):
        from app import app

        by_ep = {r.endpoint: str(r.rule) for r in app.url_map.iter_rules()}
        self.assertEqual(by_ep.get('admin_services_catalog.admin_services'), '/admin/services')
        self.assertEqual(by_ep.get('admin_services_catalog.admin_service_categories'), '/admin/service-categories')
        self.assertEqual(by_ep.get('admin_services_catalog.admin_services_export_csv'), '/api/admin/services/export.csv')
        self.assertEqual(by_ep.get('admin_services_catalog.admin_services_import'), '/api/admin/services/import')


if __name__ == '__main__':
    unittest.main()
