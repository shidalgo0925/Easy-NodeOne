"""Tests Membership Verification API — Sprint A."""

from __future__ import annotations

import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))


class TestMembershipVerificationService(unittest.TestCase):
    def test_type_not_supported(self):
        from nodeone.services.membership_verification import (
            MembershipVerificationError,
            verify,
        )

        with self.assertRaises(MembershipVerificationError) as ctx:
            verify(type='qr', value='x', organization_id=1)
        self.assertEqual(ctx.exception.message, 'type_not_supported')
        self.assertIn('email', ctx.exception.extra.get('supported_types', []))

    def test_validation_empty(self):
        from nodeone.services.membership_verification import (
            MembershipVerificationError,
            verify,
        )

        with self.assertRaises(MembershipVerificationError) as ctx:
            verify(type='email', value='  ', organization_id=1)
        self.assertEqual(ctx.exception.message, 'validation_error')

    @patch('nodeone.services.membership_verification._collect_records')
    @patch('nodeone.services.membership_verification._user_in_org', return_value=True)
    @patch('nodeone.services.membership_verification.User')
    def test_active_member(self, mock_user_cls, _in_org, mock_collect):
        from nodeone.services.membership_verification import verify_by_email

        user = MagicMock()
        user.id = 10
        user.email = 'a@b.com'
        mock_user_cls.query.filter.return_value.first.return_value = user
        mock_collect.return_value = [
            {
                'canon': 'ACTIVE',
                'membership_type': 'premium',
                'end_date': datetime.utcnow() + timedelta(days=30),
                'created_at': datetime.utcnow(),
                'payment_status': 'paid',
            }
        ]
        out = verify_by_email(email='A@B.com', organization_id=1)
        self.assertTrue(out['success'])
        self.assertTrue(out['found'])
        self.assertTrue(out['member']['is_active_member'])
        self.assertEqual(out['member']['membership']['status'], 'ACTIVE')

    @patch('nodeone.services.membership_verification._collect_records', return_value=[])
    @patch('nodeone.services.membership_verification._user_in_org', return_value=True)
    @patch('nodeone.services.membership_verification.User')
    def test_user_never_had_membership(self, mock_user_cls, _in_org, _collect):
        from nodeone.services.membership_verification import verify_by_email

        user = MagicMock()
        user.id = 11
        mock_user_cls.query.filter.return_value.first.return_value = user
        out = verify_by_email(email='x@y.com', organization_id=1)
        self.assertTrue(out['found'])
        self.assertFalse(out['member']['is_active_member'])
        self.assertEqual(out['member']['membership']['status'], 'INACTIVE')

    @patch('nodeone.services.membership_verification._user_in_org', return_value=False)
    @patch('nodeone.services.membership_verification.User')
    def test_not_found(self, mock_user_cls, _in_org):
        from nodeone.services.membership_verification import verify_by_email

        mock_user_cls.query.filter.return_value.first.return_value = None
        out = verify_by_email(email='nobody@x.com', organization_id=1)
        self.assertEqual(out, {'success': True, 'found': False})


class TestMembershipVerificationHTTP(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from app import app as flask_app

        cls.app = flask_app

    def test_unauthorized_without_key(self):
        with self.app.test_client() as c:
            r = c.post(
                '/api/v1/membership/verification',
                json={'type': 'email', 'value': 'a@b.com'},
            )
            self.assertIn(r.status_code, (401, 503))
            data = r.get_json()
            self.assertFalse(data.get('success'))
            self.assertIn(data.get('message'), ('Unauthorized', 'not_configured'))

    def test_rejects_bearer_only(self):
        """Solo X-API-Key; Authorization Bearer no autentica."""
        with self.app.test_client() as c:
            r = c.post(
                '/api/v1/membership/verification',
                headers={'Authorization': 'Bearer totally-invalid'},
                json={'type': 'email', 'value': 'a@b.com'},
            )
            self.assertIn(r.status_code, (401, 503))


if __name__ == '__main__':
    unittest.main()
