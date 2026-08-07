"""Tests ADR-035 v1.4 — ActivationService + HTTP redeem/validate/reissue."""

from __future__ import annotations

import sys
import unittest
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))


class TestActivationService(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from app import app, db
        from nodeone.services.ets_activation_schema import ensure_ets_activation_schema
        from nodeone.services.ets_commercial_schema import ensure_ets_commercial_schema

        cls.app = app
        cls.db = db
        with app.app_context():
            ensure_ets_commercial_schema(db, db.engine)
            ensure_ets_activation_schema(db, db.engine)

    def setUp(self):
        from models.saas import SaasOrganization

        self.ctx = self.app.app_context()
        self.ctx.push()
        suffix = uuid.uuid4().hex[:10]
        self.email = f'act{suffix}@example.com'
        self.org = SaasOrganization(name=f'ActTest {suffix}', subdomain=f'act{suffix}')
        self.db.session.add(self.org)
        self.db.session.commit()
        self.oid = int(self.org.id)

    def tearDown(self):
        from models.ets_activation_license import EtsActivationLicense
        from models.ets_activation_token import EtsActivationToken
        from models.saas import SaasOrganization

        try:
            lids = [
                r.id
                for r in EtsActivationLicense.query.filter_by(organization_id=self.oid).all()
            ]
            if lids:
                EtsActivationToken.query.filter(
                    EtsActivationToken.license_id.in_(lids)
                ).delete(synchronize_session=False)
            EtsActivationLicense.query.filter_by(organization_id=self.oid).delete(
                synchronize_session=False
            )
            SaasOrganization.query.filter_by(id=self.oid).delete(synchronize_session=False)
            self.db.session.commit()
        except Exception:
            self.db.session.rollback()
        self.ctx.pop()

    def _standalone_token(self, *, email: str | None = None):
        from nodeone.core.platform.activation_service import ActivationService

        with patch('nodeone.core.platform.activation_service._audit'):
            return ActivationService.issue_for_organization_standalone(
                organization_id=self.oid,
                user_id=1,
                bound_email=email or self.email,
            )

    def test_standalone_issues_six_digit_code(self):
        issued = self._standalone_token()
        self.assertEqual(issued['modality'], 'standalone')
        code = issued['activation_code']
        self.assertTrue(code and code.isdigit() and len(code) == 6)
        self.assertEqual(issued['bound_email'], self.email)
        self.assertEqual(issued['redeem']['credential_fields'], ['email', 'activation_code'])
        self.assertEqual(issued['transport']['ux_primary'], 'email_activation_code')
        self.assertIn('apk_url', issued)

    def test_standalone_redeem_email_code(self):
        from nodeone.core.platform.activation_service import ActivationService

        issued = self._standalone_token()
        with patch('nodeone.core.platform.activation_service._audit'):
            claims = ActivationService.redeem(
                credentials={
                    'email': self.email,
                    'activation_code': issued['activation_code'],
                },
                device_uuid='device-standalone-1',
            )
        self.assertTrue(claims['ok'])
        self.assertEqual(claims['modality'], 'standalone')
        self.assertEqual(claims['implementation_strategy'], 'self_serve')
        self.assertEqual(claims['organization_id'], self.oid)
        self.assertEqual(claims['provisioning_hint']['next'], 'standalone_assistant')

    def test_email_mismatch(self):
        from nodeone.core.platform.activation_service import ActivationError, ActivationService

        issued = self._standalone_token()
        with self.assertRaises(ActivationError) as ctx:
            ActivationService.redeem(
                credentials={
                    'email': 'other@example.com',
                    'activation_code': issued['activation_code'],
                },
                device_uuid='d',
            )
        self.assertEqual(ctx.exception.code, 'email_mismatch')
        self.assertEqual(ctx.exception.http_status, 403)

    def test_redeem_by_manual_code_legacy(self):
        from nodeone.core.platform.activation_service import ActivationService

        issued = self._standalone_token()
        with patch('nodeone.core.platform.activation_service._audit'):
            claims = ActivationService.redeem(
                manual_code=issued['manual_code'],
                device_uuid='device-manual-1',
            )
        self.assertTrue(claims['ok'])
        self.assertEqual(claims['modality'], 'standalone')

    def test_redeem_by_activation_ref_secondary(self):
        from nodeone.core.platform.activation_service import ActivationService

        issued = self._standalone_token()
        with patch('nodeone.core.platform.activation_service._audit'):
            claims = ActivationService.redeem(
                activation_ref=issued['activation_ref'],
                device_uuid='device-ref-1',
            )
        self.assertTrue(claims['ok'])
        self.assertEqual(claims['modality'], 'standalone')

    def test_credential_ambiguous(self):
        from nodeone.core.platform.activation_service import ActivationError, ActivationService

        issued = self._standalone_token()
        with self.assertRaises(ActivationError) as ctx:
            ActivationService.redeem(
                credentials={
                    'activation_ref': issued['activation_ref'],
                    'manual_code': issued['manual_code'],
                },
                device_uuid='d',
            )
        self.assertEqual(ctx.exception.code, 'activation_credential_ambiguous')

    def test_activation_code_ambiguous_with_ref(self):
        from nodeone.core.platform.activation_service import ActivationError, ActivationService

        issued = self._standalone_token()
        with self.assertRaises(ActivationError) as ctx:
            ActivationService.redeem(
                credentials={
                    'email': self.email,
                    'activation_code': issued['activation_code'],
                    'activation_ref': issued['activation_ref'],
                },
                device_uuid='d',
            )
        self.assertEqual(ctx.exception.code, 'activation_credential_ambiguous')

    def test_credential_missing(self):
        from nodeone.core.platform.activation_service import ActivationError, ActivationService

        with self.assertRaises(ActivationError) as ctx:
            ActivationService.validate(credentials={})
        self.assertEqual(ctx.exception.code, 'activation_credential_missing')

    def test_email_without_code_missing(self):
        from nodeone.core.platform.activation_service import ActivationError, ActivationService

        with self.assertRaises(ActivationError) as ctx:
            ActivationService.validate(credentials={'email': self.email})
        self.assertEqual(ctx.exception.code, 'activation_credential_missing')

    def test_double_redeem_code_used(self):
        from nodeone.core.platform.activation_service import ActivationError, ActivationService

        issued = self._standalone_token()
        with patch('nodeone.core.platform.activation_service._audit'):
            ActivationService.redeem(
                credentials={
                    'email': self.email,
                    'activation_code': issued['activation_code'],
                },
                device_uuid='d1',
            )
            with self.assertRaises(ActivationError) as ctx:
                ActivationService.redeem(
                    credentials={
                        'email': self.email,
                        'activation_code': issued['activation_code'],
                    },
                    device_uuid='d2',
                )
        self.assertEqual(ctx.exception.code, 'activation_code_used')

    def test_expired_code(self):
        from models.ets_activation_token import EtsActivationToken
        from nodeone.core.platform.activation_service import ActivationError, ActivationService

        issued = self._standalone_token()
        row = EtsActivationToken.query.get(int(issued['token_id']))
        row.expires_at = datetime.utcnow() - timedelta(days=1)
        self.db.session.commit()
        with self.assertRaises(ActivationError) as ctx:
            ActivationService.redeem(
                credentials={
                    'email': self.email,
                    'activation_code': issued['activation_code'],
                },
                device_uuid='d1',
            )
        self.assertEqual(ctx.exception.code, 'activation_code_expired')

    def test_revoked_code(self):
        from nodeone.core.platform.activation_service import ActivationError, ActivationService

        issued = self._standalone_token()
        with patch('nodeone.core.platform.activation_service._audit'):
            ActivationService.revoke_token(int(issued['token_id']), reason='test')
            with self.assertRaises(ActivationError) as ctx:
                ActivationService.redeem(
                    credentials={
                        'email': self.email,
                        'activation_code': issued['activation_code'],
                    },
                    device_uuid='d1',
                )
        self.assertEqual(ctx.exception.code, 'activation_code_revoked')

    def test_revoked_license(self):
        from nodeone.core.platform.activation_service import ActivationError, ActivationService

        issued = self._standalone_token()
        with patch('nodeone.core.platform.activation_service._audit'):
            ActivationService.revoke_license(int(issued['license_id']), reason='test')
            with self.assertRaises(ActivationError) as ctx:
                ActivationService.redeem(
                    credentials={
                        'email': self.email,
                        'activation_code': issued['activation_code'],
                    },
                    device_uuid='d1',
                )
        self.assertEqual(ctx.exception.code, 'license_revoked')

    def test_validate_ok_does_not_consume(self):
        from nodeone.core.platform.activation_service import ActivationService

        issued = self._standalone_token()
        with patch('nodeone.core.platform.activation_service._audit'):
            v1 = ActivationService.validate(
                credentials={'email': self.email, 'activation_code': issued['activation_code']}
            )
            v2 = ActivationService.validate(
                credentials={'email': self.email, 'activation_code': issued['activation_code']}
            )
            claims = ActivationService.redeem(
                credentials={'email': self.email, 'activation_code': issued['activation_code']},
                device_uuid='d1',
            )
        self.assertTrue(v1['ok'])
        self.assertTrue(v2['ok'])
        self.assertEqual(claims['modality'], 'standalone')

    def test_connected_requires_ops_ready(self):
        from nodeone.core.platform.activation_service import ActivationError, ActivationService

        with patch('nodeone.core.platform.activation_service._audit'):
            lic = ActivationService.ensure_license(
                organization_id=self.oid,
                modality='connected',
                implementation_strategy='assisted',
            )
            with self.assertRaises(ActivationError) as ctx:
                ActivationService.issue_token(license_id=int(lic.id), register_ref=None)
        self.assertEqual(ctx.exception.code, 'ops_not_ready')

    def test_connected_with_ops_ready_flag(self):
        from nodeone.core.platform.activation_service import ActivationService

        with patch('nodeone.core.platform.activation_service._audit'):
            lic = ActivationService.ensure_license(
                organization_id=self.oid,
                modality='CONNECTED',
                implementation_strategy='assisted',
            )
            issued = ActivationService.issue_token(
                license_id=int(lic.id),
                register_ref='reg-main',
                ops_ready=True,
            )
            claims = ActivationService.redeem(token=issued['token'], device_uuid='d-conn')
        self.assertEqual(issued['modality'], 'connected')
        self.assertEqual(claims['modality'], 'connected')
        self.assertEqual(claims['register_ref'], 'reg-main')
        self.assertEqual(claims['provisioning_hint']['next'], 'devices_register')
        # Connected sigue formato legado XXXX-XXXX-XXXX
        self.assertIn('-', issued['token'])

    def test_reissue_same_license_revokes_previous(self):
        from nodeone.core.platform.activation_service import ActivationError, ActivationService

        with patch('nodeone.core.platform.activation_service._audit'):
            first = self._standalone_token()
            second = ActivationService.reissue_standalone_for_organization(
                organization_id=self.oid,
                bound_email=self.email,
            )
            self.assertEqual(first['license_id'], second['license_id'])
            self.assertNotEqual(first['activation_code'], second['activation_code'])
            with self.assertRaises(ActivationError) as ctx:
                ActivationService.redeem(
                    credentials={
                        'email': self.email,
                        'activation_code': first['activation_code'],
                    },
                    device_uuid='d1',
                )
            self.assertEqual(ctx.exception.code, 'activation_code_revoked')
            claims = ActivationService.redeem(
                credentials={
                    'email': self.email,
                    'activation_code': second['activation_code'],
                },
                device_uuid='d1',
            )
        self.assertEqual(claims['modality'], 'standalone')

    def test_product_mismatch(self):
        from nodeone.core.platform.activation_service import ActivationError, ActivationService

        issued = self._standalone_token()
        with self.assertRaises(ActivationError) as ctx:
            ActivationService.redeem(
                credentials={
                    'email': self.email,
                    'activation_code': issued['activation_code'],
                },
                device_uuid='d1',
                product_code='other',
            )
        self.assertEqual(ctx.exception.code, 'product_mismatch')

    def test_http_redeem_email_code(self):
        issued = self._standalone_token()
        with self.app.test_client() as c:
            r = c.post(
                '/api/v1/activation/redeem',
                json={
                    'email': self.email,
                    'activation_code': issued['activation_code'],
                    'device_uuid': 'http-device-1',
                    'product_code': 'eposone',
                },
            )
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertEqual(data['modality'], 'standalone')
        self.assertTrue(data['ok'])

    def test_http_double_redeem(self):
        issued = self._standalone_token()
        body = {
            'email': self.email,
            'activation_code': issued['activation_code'],
            'device_uuid': 'd1',
        }
        with self.app.test_client() as c:
            r1 = c.post('/api/v1/activation/redeem', json=body)
            r2 = c.post(
                '/api/v1/activation/redeem',
                json={**body, 'device_uuid': 'd2'},
            )
        self.assertEqual(r1.status_code, 200)
        self.assertEqual(r2.status_code, 409)
        self.assertEqual(r2.get_json()['error'], 'activation_code_used')

    def test_http_email_mismatch(self):
        issued = self._standalone_token()
        with self.app.test_client() as c:
            r = c.post(
                '/api/v1/activation/redeem',
                json={
                    'email': 'wrong@example.com',
                    'activation_code': issued['activation_code'],
                    'device_uuid': 'd1',
                },
            )
        self.assertEqual(r.status_code, 403)
        self.assertEqual(r.get_json()['error'], 'email_mismatch')


if __name__ == '__main__':
    unittest.main()
