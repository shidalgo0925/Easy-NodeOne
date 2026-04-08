"""Smoke: blueprint crm_api registrado y rutas base disponibles."""
import sys
import unittest
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))


class TestCrmApiBlueprint(unittest.TestCase):
    def test_endpoints_registered(self):
        from app import app

        endpoints = {r.endpoint for r in app.url_map.iter_rules()}
        required = {
            'crm_api.crm_leads_get',
            'crm_api.crm_leads_post',
            'crm_api.crm_lead_get',
            'crm_api.crm_lead_patch',
            'crm_api.crm_lead_delete',
            'crm_api.crm_lead_lost',
            'crm_api.crm_lead_activities_post',
            'crm_api.crm_activities_alerts_get',
            'crm_api.crm_lead_log_post',
            'crm_api.crm_stages_get',
            'crm_api.crm_stages_post',
            'crm_api.crm_reports_get',
        }
        missing = required - endpoints
        self.assertFalse(missing, f'Faltan endpoints CRM: {sorted(missing)}')

    def test_paths(self):
        from app import app

        by_ep = {r.endpoint: str(r.rule) for r in app.url_map.iter_rules()}
        self.assertEqual(by_ep.get('crm_api.crm_leads_get'), '/crm/leads')
        self.assertEqual(by_ep.get('crm_api.crm_lead_lost'), '/crm/leads/<int:lead_id>/lost')
        self.assertEqual(by_ep.get('crm_api.crm_reports_get'), '/crm/reports')

    def test_requires_auth(self):
        from app import app

        with app.test_client() as c:
            resp = c.get('/crm/leads')
            self.assertIn(resp.status_code, (302, 401))


if __name__ == '__main__':
    unittest.main()
