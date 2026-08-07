"""Tests ADR-035 Fase 1 — ActivationService + HTTP redeem/validate."""

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

    def _standalone_token(self):
        from nodeone.core.platform.activation_service import ActivationService

        with patch('nodeone.core.platform.activation_service._audit'):
            return ActivationService.issue_for_organization_standalone(
                organization_id=self.oid,
                user_id=1,
            )

    def test_standalone_redeem_returns_modality(self):
        from nodeone.core.platform.activation_service import ActivationService

        issued = self._standalone_token()
        self.assertEqual(issued['modality'], 'standalone')
        self.assertEqual(issued['implementation_strategy'], 'self_serve')
        with patch('nodeone.core.platform.activation_service._audit'):
            claims = ActivationService.redeem(
                token=issued['token'],
                device_uuid='device-standalone-1',
            )
        self.assertTrue(claims['ok'])
        self.assertEqual(claims['modality'], 'standalone')
        self.assertEqual(claims['implementation_strategy'], 'self_serve')
        self.assertEqual(claims['organization_id'], self.oid)
        self.assertEqual(claims['provisioning_hint']['next'], 'standalone_assistant')
        self.assertIsNone(claims.get('register_ref'))

    def test_double_redeem_fails(self):
        from nodeone.core.platform.activation_service import ActivationError, ActivationService

        issued = self._standalone_token()
        with patch('nodeone.core.platform.activation_service._audit'):
            ActivationService.redeem(token=issued['token'], device_uuid='d1')
            with self.assertRaises(ActivationError) as ctx:
                ActivationService.redeem(token=issued['token'], device_uuid='d2')
        self.assertEqual(ctx.exception.code, 'activation_token_used')

    def test_expired_token(self):
        from models.ets_activation_token import EtsActivationToken
        from nodeone.core.platform.activation_service import ActivationError, ActivationService

        issued = self._standalone_token()
        row = EtsActivationToken.query.get(int(issued['token_id']))
        row.expires_at = datetime.utcnow() - timedelta(days=1)
        self.db.session.commit()
        with self.assertRaises(ActivationError) as ctx:
            ActivationService.redeem(token=issued['token'], device_uuid='d1')
        self.assertEqual(ctx.exception.code, 'activation_token_expired')

    def test_revoked_token(self):
        from nodeone.core.platform.activation_service import ActivationError, ActivationService

        issued = self._standalone_token()
        with patch('nodeone.core.platform.activation_service._audit'):
            ActivationService.revoke_token(int(issued['token_id']), reason='test')
            with self.assertRaises(ActivationError) as ctx:
                ActivationService.redeem(token=issued['token'], device_uuid='d1')
        self.assertEqual(ctx.exception.code, 'activation_token_revoked')

    def test_revoked_license(self):
        from nodeone.core.platform.activation_service import ActivationError, ActivationService

        issued = self._standalone_token()
        with patch('nodeone.core.platform.activation_service._audit'):
            ActivationService.revoke_license(int(issued['license_id']), reason='test')
            with self.assertRaises(ActivationError) as ctx:
                ActivationService.redeem(token=issued['token'], device_uuid='d1')
        self.assertEqual(ctx.exception.code, 'license_revoked')

    def test_validate_ok_does_not_consume(self):
        from nodeone.core.platform.activation_service import ActivationService

        issued = self._standalone_token()
        with patch('nodeone.core.platform.activation_service._audit'):
            v1 = ActivationService.validate(token=issued['token'])
            v2 = ActivationService.validate(token=issued['token'])
            claims = ActivationService.redeem(token=issued['token'], device_uuid='d1')
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

    def test_reissue_revokes_previous(self):
        from nodeone.core.platform.activation_service import ActivationError, ActivationService

        with patch('nodeone.core.platform.activation_service._audit'):
            first = self._standalone_token()
            second = ActivationService.reissue_token(license_id=int(first['license_id']))
            with self.assertRaises(ActivationError) as ctx:
                ActivationService.redeem(token=first['token'], device_uuid='d1')
            self.assertEqual(ctx.exception.code, 'activation_token_revoked')
            claims = ActivationService.redeem(token=second['token'], device_uuid='d1')
        self.assertEqual(claims['modality'], 'standalone')

    def test_product_mismatch(self):
        from nodeone.core.platform.activation_service import ActivationError, ActivationService

        issued = self._standalone_token()
        with self.assertRaises(ActivationError) as ctx:
            ActivationService.redeem(
                token=issued['token'],
                device_uuid='d1',
                product_code='other',
            )
        self.assertEqual(ctx.exception.code, 'product_mismatch')

    def test_http_redeem(self):
        issued = self._standalone_token()
        with self.app.test_client() as c:
            r = c.post(
                '/api/v1/activation/redeem',
                json={
                    'token': issued['token'],
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
        with self.app.test_client() as c:
            r1 = c.post(
                '/api/v1/activation/redeem',
                json={'token': issued['token'], 'device_uuid': 'd1'},
            )
            r2 = c.post(
                '/api/v1/activation/redeem',
                json={'token': issued['token'], 'device_uuid': 'd2'},
            )
        self.assertEqual(r1.status_code, 200)
        self.assertEqual(r2.status_code, 409)
        self.assertEqual(r2.get_json()['error'], 'activation_token_used')


if __name__ == '__main__':
    unittest.main()
