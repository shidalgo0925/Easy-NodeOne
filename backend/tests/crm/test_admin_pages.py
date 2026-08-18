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
            'admin_crm_settings',
            'admin_crm_calendar',
            'admin_crm_table',
            'admin_crm_activities',
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
        self.assertEqual(by_ep.get('admin_crm_settings'), '/admin/crm/settings')
        self.assertEqual(by_ep.get('admin_crm_calendar'), '/admin/crm/calendar')
        self.assertEqual(by_ep.get('admin_crm_table'), '/admin/crm/table')
        self.assertEqual(by_ep.get('admin_crm_activities'), '/admin/crm/activities')

    def test_admin_crm_dashboard_redirects_to_leads(self):
        from unittest.mock import MagicMock, patch

        from app import app

        mock_user = MagicMock()
        mock_user.is_authenticated = True
        mock_user.is_admin = True
        mock_user.must_change_password = False

        with app.test_client() as client:
            with patch('flask_login.utils._get_user', return_value=mock_user):
                resp = client.get('/admin/crm', follow_redirects=False)
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/admin/crm/leads', resp.headers.get('Location', ''))

    def test_crm_list_toolbar_matches_contacts_pattern(self):
        html = (Path(__file__).resolve().parents[3] / 'templates' / 'admin' / 'crm_dashboard.html').read_text(encoding='utf-8')
        self.assertIn('>Nuevo</button>', html)
        self.assertIn('>Filtrar</button>', html)
        self.assertIn('>Limpiar</button>', html)
        self.assertIn('id="crmSearch"', html)
        self.assertNotIn('Nuevo lead', html)
        self.assertNotIn('Crear el primero', html)
        self.assertNotIn('crm-view-toolbar', html)
        self.assertNotIn('crmReloadBtn', html)


if __name__ == '__main__':
    unittest.main()
