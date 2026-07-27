"""Tests unitarios: emisión y utilidades de certificados de evento."""
import os
import sys
import tempfile
import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

from nodeone.modules.events.services import certificates as ev_cert


class TestEventCertificateHelpers(unittest.TestCase):
    def test_participant_eligible_checked_in(self):
        p = SimpleNamespace(attendance_status='checked_in', participant_type='external')
        self.assertTrue(ev_cert.participant_eligible_for_certificate(p))

    def test_participant_eligible_reviewer_without_checkin(self):
        p = SimpleNamespace(attendance_status='registered', participant_type='reviewer')
        self.assertTrue(ev_cert.participant_eligible_for_certificate(p))

    def test_participant_not_eligible(self):
        p = SimpleNamespace(attendance_status='registered', participant_type='external')
        self.assertFalse(ev_cert.participant_eligible_for_certificate(p))

    def test_code_prefix_reviewer(self):
        p = SimpleNamespace(participant_type='reviewer')
        self.assertEqual(ev_cert.code_prefix_for_participant(p), ev_cert.PREFIX_REVIEWER)

    def test_code_prefix_default(self):
        p = SimpleNamespace(participant_type='external')
        self.assertEqual(ev_cert.code_prefix_for_participant(p), ev_cert.PREFIX_DEFAULT)

    def test_mask_document(self):
        self.assertEqual(ev_cert.mask_document('1234567890'), '****7890')
        self.assertEqual(ev_cert.mask_document('12'), '****')
        self.assertIsNone(ev_cert.mask_document(''))

    def test_build_verification_url(self):
        app = SimpleNamespace()
        url = ev_cert.build_verification_url(app, 'EN1-2026-ABC123')
        self.assertIn('/certificates/verify/EN1-2026-ABC123', url)

    def test_generate_bulk_empty_ids(self):
        app = SimpleNamespace()
        event = SimpleNamespace(id=1)
        result = ev_cert.generate_bulk_for_event(app, event, 1, [])
        self.assertEqual(result, {'created': 0, 'skipped': 0, 'errors': []})

    def test_generate_bulk_counts_created_and_skipped(self):
        app = SimpleNamespace(root_path=backend_dir)
        event = SimpleNamespace(id=5, created_by=1, creator=None)
        p_ok = SimpleNamespace(id=10, attendance_status='checked_in', participant_type='external')
        p_skip = SimpleNamespace(id=11, attendance_status='registered', participant_type='external')

        with patch('app.EventParticipant') as EP:
            q = MagicMock()
            EP.query.filter_by.return_value = q
            q.filter.return_value = q
            q.order_by.return_value.all.return_value = [p_ok, p_skip]
            with patch.object(ev_cert, 'create_event_certificate') as create_mock:
                create_mock.side_effect = [
                    (SimpleNamespace(id=1), None),
                    (None, 'no elegible'),
                ]
                result = ev_cert.generate_bulk_for_event(app, event, 99, [10, 11])

        self.assertEqual(result['created'], 1)
        self.assertEqual(result['skipped'], 1)
        self.assertTrue(any('no elegible' in e for e in result['errors']))

    def test_write_certificate_pdf_file_fallback(self):
        app = SimpleNamespace(root_path=backend_dir)
        with tempfile.TemporaryDirectory() as tmp:
            legacy = os.path.join(tmp, 'readonly', 'old.pdf')
            os.makedirs(os.path.dirname(legacy), mode=0o755)
            with open(legacy, 'wb') as f:
                f.write(b'%PDF-old')
            os.chmod(os.path.dirname(legacy), 0o555)

            canonical_dir = os.path.join(tmp, 'writable', '3', '5')
            with patch.object(ev_cert, 'certificates_storage_dir', return_value=canonical_dir):
                with patch.object(
                    ev_cert,
                    '_certificate_pdf_paths',
                    return_value=[legacy, os.path.join(canonical_dir, 'EN1-2026-TEST.pdf')],
                ):
                    path, err = ev_cert._write_certificate_pdf_file(
                        app,
                        org_id=3,
                        event_id=5,
                        cert_number='EN1-2026-TEST',
                        pdf_bytes=b'%PDF-new',
                    )
            self.assertIsNone(err)
            self.assertTrue(path and os.path.isfile(path))
            with open(path, 'rb') as f:
                self.assertEqual(f.read(), b'%PDF-new')

    def test_create_event_certificate_rejects_ineligible(self):
        app = SimpleNamespace(root_path=backend_dir)
        event = SimpleNamespace(id=1)
        participant = SimpleNamespace(id=2, attendance_status='registered', participant_type='external')
        cert, err = ev_cert.create_event_certificate(app, event, participant, None)
        self.assertIsNone(cert)
        self.assertIn('condiciones', err or '')

    def test_create_event_certificate_rejects_duplicate(self):
        app = SimpleNamespace(root_path=backend_dir)
        event = SimpleNamespace(id=1, created_by=1, creator=None)
        participant = SimpleNamespace(
            id=2,
            attendance_status='checked_in',
            participant_type='external',
            first_name='Ana',
            middle_name='',
            last_name='Pérez',
            second_last_name='',
            full_name='',
        )
        with patch.object(ev_cert, 'participant_active_certificate', return_value=SimpleNamespace(id=9)):
            cert, err = ev_cert.create_event_certificate(app, event, participant, None)
        self.assertIsNone(cert)
        self.assertIn('activo', err or '')

    def test_regenerate_bulk_skips_revoked(self):
        app = SimpleNamespace(root_path=backend_dir)
        event = SimpleNamespace(id=5)
        active = SimpleNamespace(
            id=1,
            status='generated',
            is_active=True,
            certificate_number='EN1-2026-001',
            participant=SimpleNamespace(id=10, attendance_status='checked_in', participant_type='external'),
        )
        revoked = SimpleNamespace(id=2, status='revoked', is_active=False, certificate_number='EN1-2026-002', participant=None)

        with patch('app.EventCertificate') as EC:
            q = MagicMock()
            EC.query.filter_by.return_value = q
            q.order_by.return_value.all.return_value = [active, revoked]
            with patch.object(ev_cert, 'regenerate_event_certificate') as regen_mock:
                regen_mock.return_value = (active, None)
                result = ev_cert.regenerate_bulk_for_event(app, event, 99)

        self.assertEqual(result['regenerated'], 1)
        self.assertEqual(result['skipped'], 1)
        regen_mock.assert_called_once()


if __name__ == '__main__':
    unittest.main()
