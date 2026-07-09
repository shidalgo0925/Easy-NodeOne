"""Tests regeneración masiva certificados de membresía."""
import json
import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from nodeone.services import certificate_membership_bulk as bulk


class TestMembershipCertificateBulk(unittest.TestCase):
    def test_is_membership_certificate_format(self):
        mem = SimpleNamespace(membership_required_id=2, event_required_id=None)
        evt = SimpleNamespace(membership_required_id=2, event_required_id=5)
        self.assertTrue(bulk.is_membership_certificate_format(mem))
        self.assertFalse(bulk.is_membership_certificate_format(evt))

    def test_build_emission_snapshot_freezes_membership(self):
        user = SimpleNamespace(
            first_name='Ana',
            last_name='López',
            email='a@x.com',
            document_id=None,
            cedula_or_passport='8-888',
            cedula=None,
        )
        membership = SimpleNamespace(
            membership_type='pro',
            start_date=datetime(2026, 1, 1),
            end_date=datetime(2027, 1, 1),
        )
        user.get_active_membership = MagicMock(return_value=membership)
        ev = SimpleNamespace(membership_plan=None)
        snap = bulk.build_emission_snapshot(user, ev)
        self.assertEqual(snap['participant_name'], 'Ana López')
        self.assertEqual(snap['document_id'], '8-888')
        self.assertEqual(snap['membership_type'], 'pro')
        self.assertEqual(snap['membership_start'], '2026-01-01')
        self.assertEqual(snap['membership_end'], '2027-01-01')
        self.assertIn('issue_date', snap)

    def test_user_document_id_prefers_cedula_or_passport(self):
        user = SimpleNamespace(document_id=None, cedula_or_passport='08-382-686', cedula=None)
        self.assertEqual(bulk.user_document_id(user), '08-382-686')
        user2 = SimpleNamespace(document_id='DOC-1', cedula_or_passport='08-382-686', cedula=None)
        self.assertEqual(bulk.user_document_id(user2), 'DOC-1')

    def test_refresh_snapshot_document_id(self):
        user = SimpleNamespace(document_id=None, cedula_or_passport='08-382-686', cedula=None)
        snap = {'participant_name': 'Raul', 'document_id': ''}
        out = bulk.refresh_snapshot_document_id(snap, user)
        self.assertEqual(out['document_id'], '08-382-686')
        self.assertEqual(snap['document_id'], '')  # no muta el original

    def test_legacy_snapshot_uses_generated_at(self):
        cert = SimpleNamespace(
            generated_at=datetime(2025, 6, 15, 10, 0, 0),
        )
        user = SimpleNamespace(
            first_name='Bo',
            last_name='Li',
            email='b@x.com',
            document_id='',
            cedula_or_passport='1-2-3',
            cedula=None,
        )
        plan = SimpleNamespace(slug='pro')
        ev = SimpleNamespace(membership_plan=plan)
        snap = bulk.legacy_emission_snapshot(cert, user, ev)
        self.assertEqual(snap['issue_date'], '2025-06-15')
        self.assertEqual(snap['membership_type'], 'pro')
        self.assertEqual(snap['document_id'], '1-2-3')
        self.assertTrue(snap.get('legacy_inferred'))

    def test_ensure_emission_snapshot_persists_legacy(self):
        cert = SimpleNamespace(
            emission_snapshot=None,
            generated_at=datetime(2025, 3, 1),
        )
        user = SimpleNamespace(
            first_name='X',
            last_name='Y',
            email='x@y.com',
            document_id='',
            cedula_or_passport=None,
            cedula=None,
        )
        ev = SimpleNamespace(membership_plan=SimpleNamespace(slug='basic'))
        snap = bulk.ensure_emission_snapshot(cert, user, ev, persist=True)
        self.assertIsNotNone(cert.emission_snapshot)
        loaded = json.loads(cert.emission_snapshot)
        self.assertEqual(loaded['issue_date'], '2025-03-01')

    @patch('nodeone.services.certificate_membership_bulk.regenerate_one_membership_certificate')
    @patch('app.db')
    @patch('app.User')
    @patch('app.Certificate')
    def test_regenerate_bulk_stats(self, mock_cert_cls, mock_user_cls, mock_db, mock_regen):
        ev = SimpleNamespace(id=9, membership_required_id=1, event_required_id=None)
        c1 = SimpleNamespace(id=1, user_id=10, certificate_code='PLAN-BASIC-O1-2026-0001')
        mock_cert_cls.query.filter_by.return_value.order_by.return_value.all.return_value = [c1]
        mock_user_cls.query.get.return_value = SimpleNamespace(id=10)
        mock_regen.return_value = (True, None)

        stats = bulk.regenerate_membership_certificates_for_format(ev, issued_by_user_id=1)

        self.assertEqual(stats['found'], 1)
        self.assertEqual(stats['regenerated'], 1)
        self.assertEqual(stats['skipped'], 0)
        mock_db.session.commit.assert_called()


if __name__ == '__main__':
    unittest.main()
