"""Tests Onboarding Login API V1 (token + payload shape)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))


class TestOnboardingToken(unittest.TestCase):
    def test_issue_and_parse_roundtrip(self):
        from flask import Flask

        from nodeone.modules.eposone.onboarding_auth_service import (
            authenticate_bearer,
            issue_access_token,
            parse_access_token,
        )

        app = Flask(__name__)
        app.config['SECRET_KEY'] = 'test-secret-onboarding'
        with app.app_context():
            token, expires = issue_access_token(user_id=42, organization_id=5)
            self.assertGreater(expires, 0)
            data = parse_access_token(token)
            self.assertEqual(data['user_id'], 42)
            self.assertEqual(data['organization_id'], 5)
            auth = authenticate_bearer(f'Bearer {token}')
            self.assertEqual(auth['user_id'], 42)

    def test_bearer_required(self):
        from flask import Flask

        from nodeone.modules.eposone.onboarding_auth_service import (
            OnboardingAuthError,
            authenticate_bearer,
        )

        app = Flask(__name__)
        app.config['SECRET_KEY'] = 'test-secret-onboarding'
        with app.app_context():
            with self.assertRaises(OnboardingAuthError) as ctx:
                authenticate_bearer(None)
            self.assertEqual(ctx.exception.code, 'auth_required')


class TestOnboardingLoginErrors(unittest.TestCase):
    def test_invalid_credentials_empty(self):
        from flask import Flask

        from nodeone.modules.eposone.onboarding_auth_service import (
            OnboardingAuthError,
            login_with_password,
        )

        app = Flask(__name__)
        app.config['SECRET_KEY'] = 'x'
        with app.app_context():
            with self.assertRaises(OnboardingAuthError) as ctx:
                login_with_password('', '')
            self.assertEqual(ctx.exception.code, 'invalid_credentials')


class TestOnboardingBlueprint(unittest.TestCase):
    def test_prefix(self):
        from nodeone.modules.eposone.onboarding_v1_routes import eposone_onboarding_v1_bp

        self.assertEqual(eposone_onboarding_v1_bp.url_prefix, '/api/v1/onboarding')


if __name__ == '__main__':
    unittest.main()
