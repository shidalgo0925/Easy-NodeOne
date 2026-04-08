"""Smoke: blueprint admin_export registrado."""
import sys
import unittest
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))


class TestAdminExportBlueprint(unittest.TestCase):
    def test_export_endpoints_registered(self):
        from app import app

        endpoints = {r.endpoint for r in app.url_map.iter_rules()}
        required = {
            'admin_export.admin_export_page',
            'admin_export.api_export_fields',
            'admin_export.api_export_xls',
            'admin_export.api_export_pdf',
            'admin_export.api_export_preview',
            'admin_export.api_export_templates',
            'admin_export.api_export_template_get',
        }
        missing = required - endpoints
        self.assertFalse(missing, f'Faltan endpoints: {sorted(missing)}')

    def test_export_paths_unchanged(self):
        from app import app

        by_ep = {r.endpoint: r.rule for r in app.url_map.iter_rules()}
        self.assertEqual(by_ep.get('admin_export.admin_export_page'), '/admin/export')
        self.assertEqual(by_ep.get('admin_export.api_export_fields'), '/api/admin/export/fields')


if __name__ == '__main__':
    unittest.main()
