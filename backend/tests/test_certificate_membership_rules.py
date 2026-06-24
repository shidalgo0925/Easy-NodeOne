"""Tests: elegibilidad de certificados por plan de membresía."""
import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from nodeone.services import certificate_membership_rules as rules


class _Plan:
    def __init__(self, pid, slug='basic', name='Básico'):
        self.id = pid
        self.slug = slug
        self.name = name
        self.is_active = True


class _CertEvent:
    def __init__(self, *, prefix='PLAN-BASIC', membership_required_id=1, event_required_id=None):
        self.code_prefix = prefix
        self.membership_required_id = membership_required_id
        self.event_required_id = event_required_id
        self.membership_plan = _Plan(membership_required_id) if membership_required_id else None
        self.event_required = None

class TestCertificateMembershipRules(unittest.TestCase):
    def test_reg_always_qualified(self):
        user = MagicMock(id=1, is_admin=False)
        ev = _CertEvent(prefix='REG', membership_required_id=None)
        self.assertTrue(rules.user_qualified_for_certificate_event(user, ev, org_id=1))

    @patch.object(rules, 'user_active_membership_plan_id', return_value=1)
    def test_plan_cert_qualified_when_plan_matches(self, _mock):
        user = MagicMock(id=1, is_admin=False)
        ev = _CertEvent(membership_required_id=1)
        self.assertTrue(rules.user_qualified_for_certificate_event(user, ev, org_id=1))

    @patch.object(rules, 'user_active_membership_plan_id', return_value=1)
    def test_plan_cert_not_qualified_for_other_plan(self, _mock):
        user = MagicMock(id=1, is_admin=False)
        ev = _CertEvent(membership_required_id=2)
        self.assertFalse(rules.user_qualified_for_certificate_event(user, ev, org_id=1))

    @patch.object(rules, 'user_active_membership_plan_id', return_value=None)
    def test_plan_cert_not_qualified_without_membership(self, _mock):
        user = MagicMock(id=1, is_admin=False)
        ev = _CertEvent(membership_required_id=1)
        self.assertFalse(rules.user_qualified_for_certificate_event(user, ev, org_id=1))

    def test_requirement_text_plan(self):
        ev = _CertEvent(membership_required_id=1)
        self.assertIn('Básico', rules.requirement_text_for_certificate_event(ev))

    @patch.object(rules, 'user_participated_in_event', return_value=False)
    def test_event_linked_cert_requires_participation(self, _mock):
        user = MagicMock(id=1, is_admin=False, email='a@b.com')
        ev = _CertEvent(prefix='PLAN-X', membership_required_id=None, event_required_id=99)
        ev.event_required = MagicMock(title='Seminario')
        self.assertFalse(rules.user_qualified_for_certificate_event(user, ev, org_id=1))

    @patch.object(rules, 'user_participated_in_event', return_value=True)
    def test_event_linked_cert_qualified_with_participation(self, _mock):
        user = MagicMock(id=1, is_admin=False, email='a@b.com')
        ev = _CertEvent(prefix='PLAN-X', membership_required_id=None, event_required_id=99)
        self.assertTrue(rules.user_qualified_for_certificate_event(user, ev, org_id=1))

    def test_plan_code_prefix(self):
        self.assertEqual(rules._plan_code_prefix('basic'), 'PLAN-BASIC')
        self.assertTrue(rules._plan_code_prefix('pro').startswith('PLAN-'))

    @patch.object(rules, 'get_user_currently_active_membership_record')
    def test_orphan_rel_seminar_not_qualified(self, mock_mem):
        mock_mem.return_value = MagicMock(membership_type='basic')
        user = MagicMock(id=1, is_admin=False)
        ev = _CertEvent(prefix='REL', membership_required_id=None, event_required_id=None)
        ev.name = 'Seminario de ejemplo'
        self.assertFalse(rules.user_qualified_for_certificate_event(user, ev, org_id=1))

    @patch('nodeone.services.certificate_assets.ensure_certificate_assets_for_org')
    def test_seed_runs_orphan_purge(self, mock_ensure):
        mock_ensure.return_value = {'orphans': {'deleted': 0}}
        mock_db = MagicMock()
        rules.seed_membership_certificate_events_for_org(mock_db, 1)
        mock_ensure.assert_called_once_with(mock_db, 1, commit=True)

    def test_purge_deletes_zero_issued_orphans(self):
        orphan = MagicMock(id=6, is_active=True, code_prefix='REL')
        mock_db = MagicMock()
        with patch('app.CertificateEvent') as CE, patch('app.Certificate') as Cert, patch(
            'app.MembershipPlan'
        ) as MP:
            CE.query.filter.return_value.all.return_value = [orphan]
            Cert.query.filter_by.return_value.count.return_value = 0
            MP.query.filter_by.return_value.all.return_value = []
            stats = rules._purge_orphan_certificate_event_formats(mock_db, 1)
        mock_db.session.delete.assert_called_once_with(orphan)
        self.assertEqual(stats['deleted'], 1)


if __name__ == '__main__':
    unittest.main()
