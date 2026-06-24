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

    def test_find_event_certificate_format_by_event_id_only(self):
        fmt = SimpleNamespace(id=25, organization_id=3, event_required_id=5)
        mock_ce = MagicMock()
        mock_ce.query.filter_by.return_value.first.return_value = fmt
        found = assets.find_event_certificate_format(mock_ce, SimpleNamespace(id=5), org_id=1)
        self.assertIs(found, fmt)
        mock_ce.query.filter_by.assert_called_once_with(event_required_id=5)

    def test_sync_event_certificate_on_save_ensures_before_template_error(self):
        event = SimpleNamespace(id=9, has_certificate=True)
        mock_db = MagicMock()
        with patch.object(assets, 'ensure_certificate_assets_for_event') as ensure_mock:
            with patch.object(assets, 'resolve_event_certificate_org_id', return_value=3):
                with patch(
                    'nodeone.services.certificate_assets.apply_certificate_template_from_event_form',
                    return_value='Plantilla no encontrada',
                ):
                    ok, warn, _assets = assets.sync_event_certificate_on_save(
                        mock_db,
                        event,
                        has_certificate=True,
                        template_form_value='999',
                        admin_scope_org_id=1,
                    )
        self.assertTrue(ok)
        self.assertIn('Plantilla', warn or '')
        ensure_mock.assert_called_once()

if __name__ == '__main__':
    unittest.main()
