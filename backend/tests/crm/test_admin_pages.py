"""Smoke: vistas admin CRM registradas y rutas esperadas."""
import sys
import unittest
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))


class TestAdminCrmPages(unittest.TestCase):
    def test_admin_crm_endpoints(self):
        from app import app

        endpoints = {r.endpoint for r in app.url_map.iter_rules()}
        required = {
            'admin_crm_dashboard',
            'admin_crm_kanban',
            'admin_crm_leads',
            'admin_crm_reports',
        }
        missing = required - endpoints
        self.assertFalse(missing, f'Faltan endpoints admin CRM: {sorted(missing)}')

    def test_admin_crm_paths(self):
        from app import app

        by_ep = {r.endpoint: str(r.rule) for r in app.url_map.iter_rules()}
        self.assertEqual(by_ep.get('admin_crm_dashboard'), '/admin/crm')
        self.assertEqual(by_ep.get('admin_crm_kanban'), '/admin/crm/kanban')
        self.assertEqual(by_ep.get('admin_crm_leads'), '/admin/crm/leads')
        self.assertEqual(by_ep.get('admin_crm_reports'), '/admin/crm/reports')


if __name__ == '__main__':
    unittest.main()
