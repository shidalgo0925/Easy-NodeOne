"""Tests recuperación de contraseña (hash, un uso, rate limit, política)."""

from __future__ import annotations

import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))


class TestPasswordResetService(unittest.TestCase):
    def test_hash_token_stable(self):
        from nodeone.services.password_reset_service import hash_token

        self.assertEqual(hash_token('abc'), hash_token('abc'))
        self.assertNotEqual(hash_token('abc'), hash_token('abd'))
        self.assertEqual(len(hash_token('x')), 64)

    def test_validate_new_password(self):
        from nodeone.services.password_reset_service import PasswordResetError, validate_new_password

        with self.assertRaises(PasswordResetError):
            validate_new_password('', '')
        with self.assertRaises(PasswordResetError):
            validate_new_password('short', 'short')
        with self.assertRaises(PasswordResetError):
            validate_new_password('longenough', 'different1')
        validate_new_password('longenough', 'longenough')

    def test_generic_message_constant(self):
        from nodeone.services.password_reset_service import GENERIC_REQUEST_MESSAGE

        self.assertIn('Si existe una cuenta asociada', GENERIC_REQUEST_MESSAGE)

    @patch('nodeone.services.password_reset_service.PasswordResetToken')
    @patch('nodeone.services.password_reset_service.User')
    def test_find_valid_token_rejects_used(self, mock_user, mock_token_cls):
        from nodeone.services.password_reset_service import find_valid_token, hash_token

        row = MagicMock()
        row.used_at = datetime.utcnow()
        row.expires_at = datetime.utcnow() + timedelta(minutes=30)
        row.user_id = 1
        mock_token_cls.query.filter_by.return_value.first.return_value = row
        self.assertIsNone(find_valid_token('raw-token'))
        mock_token_cls.query.filter_by.assert_called()
        args = mock_token_cls.query.filter_by.call_args
        self.assertEqual(args.kwargs.get('token_hash') or args[1].get('token_hash'), hash_token('raw-token'))


class TestPasswordResetRoutesRegistered(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from app import app as flask_app

        cls.app = flask_app

    def test_forgot_and_reset_routes_exist(self):
        rules = {r.rule for r in self.app.url_map.iter_rules()}
        self.assertIn('/forgot-password', rules)
        self.assertIn('/reset-password', rules)

    def test_login_has_forgot_link_template(self):
        from pathlib import Path

        login = Path(__file__).resolve().parents[2] / 'templates' / 'login.html'
        # templates live at repo templates/
        login = Path('/opt/easynodeone/dev/app/templates/login.html')
        text = login.read_text(encoding='utf-8')
        self.assertIn('forgot_password', text)


if __name__ == '__main__':
    unittest.main()
