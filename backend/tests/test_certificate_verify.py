"""Tests: verificación pública /verify y alias /certificates/verify."""
import os
import sys
import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

import certificate_routes as routes


class TestCertificateVerify(unittest.TestCase):
    def setUp(self):
        self.app = MagicMock()
        self.ctx = MagicMock()
        self.ctx.__enter__ = MagicMock(return_value=None)
        self.ctx.__exit__ = MagicMock(return_value=False)

    def test_verify_membership_certificate_found(self):
        user = SimpleNamespace(first_name='Ana', last_name='García')
        ev = SimpleNamespace(name='Certificado MEM', start_date=None, end_date=None)
        cert = SimpleNamespace(
            certificate_code='MEM-2026-001',
            user=user,
            certificate_event=ev,
            generated_at=datetime(2026, 1, 15),
        )
        with patch('app.Certificate') as Cert:
            Cert.query.filter_by.return_value.first.return_value = cert
            with patch.object(routes, 'render_template_string', return_value='OK') as render:
                with patch.object(routes, '_verify_date_range_display', return_value=''):
                    with patch.object(routes, '_verify_issuer_membership', return_value='Relatic'):
                        resp, status = routes.verify('MEM-2026-001')
        self.assertEqual(status, 200)
        self.assertEqual(resp, 'OK')
        kwargs = render.call_args.kwargs or render.call_args[1]
        self.assertTrue(kwargs['valid'])
        self.assertEqual(kwargs['full_name'], 'Ana García')
        self.assertEqual(kwargs['certificate_type'], 'membership')

    def test_verify_event_certificate_by_number(self):
        part = SimpleNamespace(
            full_name='Carlos Pérez',
            first_name='Carlos',
            middle_name='',
            last_name='Pérez',
            second_last_name='',
            document_id='8-123-4567',
        )
        ev = SimpleNamespace(title='Seminario X', start_date=None, end_date=None)
        ec = SimpleNamespace(
            certificate_number='EN1-2026-ABC',
            verification_token='tok123',
            participant_id=1,
            event_id=2,
            status='generated',
            is_active=True,
            expires_at=None,
            issued_date=datetime(2026, 2, 1),
            title='Certificado de participación',
            certificate_type='participation',
        )
        with patch('app.Certificate') as Cert:
            Cert.query.filter_by.return_value.first.return_value = None
            with patch('app.EventCertificate') as EC:
                EC.query.filter.return_value.first.return_value = ec
                with patch('app.EventParticipant') as EP:
                    EP.query.get.return_value = part
                    with patch('app.Event') as Event:
                        Event.query.get.return_value = ev
                        with patch.object(routes, 'render_template_string', return_value='OK') as render:
                            with patch.object(routes, '_verify_date_range_display', return_value=''):
                                with patch.object(routes, '_verify_issuer_event', return_value='Relatic'):
                                    with patch.object(routes, '_verify_expired_cert', return_value=False):
                                        resp, status = routes.verify('EN1-2026-ABC')
        self.assertEqual(status, 200)
        kwargs = render.call_args.kwargs or render.call_args[1]
        self.assertTrue(kwargs['valid'])
        self.assertEqual(kwargs['full_name'], 'Carlos Pérez')
        self.assertEqual(kwargs['event_name'], 'Seminario X')

    def test_verify_event_certificate_revoked(self):
        ec = SimpleNamespace(
            certificate_number='EN1-2026-REV',
            participant_id=1,
            event_id=2,
            status='revoked',
            is_active=False,
            expires_at=None,
            issued_date=None,
            title='',
            certificate_type='participation',
        )
        with patch('app.Certificate') as Cert:
            Cert.query.filter_by.return_value.first.return_value = None
            with patch('app.EventCertificate') as EC:
                EC.query.filter.return_value.first.return_value = ec
                with patch('app.EventParticipant') as EP:
                    EP.query.get.return_value = None
                    with patch('app.Event') as Event:
                        Event.query.get.return_value = SimpleNamespace(title='E')
                        with patch.object(routes, 'render_template_string', return_value='OK') as render:
                            with patch.object(routes, '_verify_date_range_display', return_value=''):
                                with patch.object(routes, '_verify_issuer_event', return_value=''):
                                    with patch.object(routes, '_verify_expired_cert', return_value=False):
                                        _, status = routes.verify('EN1-2026-REV')
        self.assertEqual(status, 200)
        kwargs = render.call_args.kwargs or render.call_args[1]
        self.assertFalse(kwargs['valid'])
        self.assertTrue(kwargs['revoked'])

    def test_verify_not_found(self):
        with patch('app.Certificate') as Cert:
            Cert.query.filter_by.return_value.first.return_value = None
            with patch('app.EventCertificate') as EC:
                EC.query.filter.return_value.first.return_value = None
                with patch.object(routes, 'render_template_string', return_value='NF') as render:
                    resp, status = routes.verify('NO-EXISTE')
        self.assertEqual(status, 404)
        kwargs = render.call_args.kwargs or render.call_args[1]
        self.assertFalse(kwargs['valid'])

    def test_verify_alias_delegates(self):
        with patch.object(routes, 'verify', return_value=('ALIAS', 200)) as verify_mock:
            resp, status = routes.verify_event_certificate_alias('CODE-1')
        verify_mock.assert_called_once_with('CODE-1')
        self.assertEqual((resp, status), ('ALIAS', 200))


if __name__ == '__main__':
    unittest.main()
