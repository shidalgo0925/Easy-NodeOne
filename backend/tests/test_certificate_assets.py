"""Tests: ensure_certificate_assets (Fase 1 certificados)."""
import os
import sys
import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

from nodeone.services import certificate_assets as assets


class TestCertificateAssets(unittest.TestCase):
    def test_fill_empty_format_fields_only_empty(self):
        fmt = SimpleNamespace(
            name='',
            code_prefix='',
            institution=None,
            partner_organization=None,
            rector_name=None,
            academic_director_name=None,
            logo_left_url=None,
            logo_right_url=None,
            seal_url=None,
            start_date=None,
            end_date=None,
            duration_hours=None,
            is_active=False,
        )
        event = SimpleNamespace(
            id=5,
            title='Seminario Test',
            start_date=datetime(2026, 1, 1),
            end_date=datetime(2026, 1, 3),
        )
        with patch.object(assets, '_org_layout_defaults', return_value={'header_text': 'Relatic'}):
            with patch.object(assets, '_org_name', return_value='Relatic Org'):
                changed = assets._fill_empty_format_fields(fmt, event, 1)
        self.assertTrue(changed)
        self.assertEqual(fmt.name, 'Seminario Test')
        self.assertEqual(fmt.code_prefix, 'EVT')
        self.assertEqual(fmt.institution, 'Relatic')

        fmt.institution = 'Personalizada'
        with patch.object(assets, '_org_layout_defaults', return_value={'header_text': 'Otra'}):
            changed2 = assets._fill_empty_format_fields(fmt, event, 1)
        self.assertFalse(changed2)
        self.assertEqual(fmt.institution, 'Personalizada')

    def test_certificate_event_delete_blocked_linked_event(self):
        ev = SimpleNamespace(membership_required_id=None, event_required_id=3, id=1)
        msg = assets.certificate_event_delete_blocked(ev)
        self.assertIn('vinculado', msg or '')

    def test_certificate_event_delete_blocked_with_issued(self):
        ev = SimpleNamespace(membership_required_id=None, event_required_id=None, id=9)
        with patch('app.Certificate') as Cert:
            Cert.query.filter_by.return_value.count.return_value = 1
            msg = assets.certificate_event_delete_blocked(ev)
        self.assertIn('emitidos', msg or '')

    def test_template_has_user_content_visual_elements(self):
        tpl = SimpleNamespace(
            json_layout='{"canvas":{},"elements":[{"type":"text"}],"meta":{"event_id":1}}'
        )
        self.assertTrue(assets._template_has_user_content(tpl))

    def test_status_constants(self):
        self.assertEqual(assets.STATUS_CREATED, 'CREATED')
        self.assertEqual(assets.STATUS_REUSED, 'REUSED')


if __name__ == '__main__':
    unittest.main()
