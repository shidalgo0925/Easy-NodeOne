"""Activación EN1 — ADR-035 v1.2 (Licencia → Token → redeem).

No crea árbol ops Standalone. Connected exige ops_ready (register_ref + unidad).
"""

from __future__ import annotations

import json
import os
import secrets
from datetime import datetime, timedelta
from typing import Any

DEFAULT_TTL_DAYS = 14
PRODUCT_CODE = 'eposone'
MODALITIES = frozenset({'standalone', 'connected'})
STRATEGIES = frozenset({'self_serve', 'assisted'})
SKEW_SECONDS = 300


class ActivationError(Exception):
    def __init__(self, code: str, *, http_status: int = 400, message: str | None = None) -> None:
        super().__init__(message or code)
        self.code = code
        self.http_status = http_status
        self.message = message or code


def _now() -> datetime:
    return datetime.utcnow()


def _norm_modality(raw: str | None) -> str:
    v = (raw or '').strip().lower()
    if v in ('local',):
        v = 'standalone'
    if v not in MODALITIES:
        raise ActivationError('modality_mismatch', http_status=409, message='modality inválida')
    return v


def _norm_strategy(raw: str | None, *, modality: str) -> str:
    v = (raw or '').strip().lower()
    if not v:
        v = 'self_serve' if modality == 'standalone' else 'assisted'
    if v not in STRATEGIES:
        raise ActivationError('modality_mismatch', http_status=409, message='strategy inválida')
    return v


def _token_string() -> str:
    # Formato legible: XXXX-XXXX-XXXX (hex)
    raw = secrets.token_hex(6).upper()
    return f'{raw[0:4]}-{raw[4:8]}-{raw[8:12]}'


def _activate_url(token: str) -> str:
    base = (os.environ.get('NODEONE_EPOSONE_PUBLIC_BASE') or '').strip().rstrip('/')
    if not base:
        base = 'https://eposone.easytech.services'
    return f'{base}/activate?token={token}'


def _audit(organization_id: int | None, event_type: str, payload: dict[str, Any]) -> None:
    try:
        from nodeone.core.platform.subscription_registry import _audit as sub_audit

        if organization_id is not None:
            sub_audit(int(organization_id), event_type, payload)
    except Exception:
        pass


def _ops_ready_for_connected(*, organization_id: int, register_ref: str | None) -> bool:
    """ADR-034 mínimo: existe unidad register en la org (sin implementar casos ADR-034)."""
    ref = (register_ref or '').strip()
    if not ref:
        return False
    try:
        from models.core_master import CoreOrgUnit
        from nodeone.core.master.constants import ORG_UNIT_TYPE_REGISTER

        row = CoreOrgUnit.query.filter_by(
            organization_id=int(organization_id),
            unit_ref=ref,
        ).first()
        if row is None:
            return False
        return str(getattr(row, 'unit_type', '') or '').lower() == ORG_UNIT_TYPE_REGISTER
    except Exception:
        return False


def _license_usable(lic) -> None:
    now = _now()
    status = str(lic.status or '')
    if status == 'revoked':
        raise ActivationError('license_revoked', http_status=403)
    if status == 'suspended':
        raise ActivationError('license_revoked', http_status=403, message='license_suspended')
    if status == 'expired':
        raise ActivationError('license_expired', http_status=403)
    if lic.ends_at is not None and lic.ends_at + timedelta(seconds=SKEW_SECONDS) < now:
        raise ActivationError('license_expired', http_status=403)
    if status not in ('issued', 'active', 'renewed'):
        raise ActivationError('license_revoked', http_status=403, message='license_not_usable')


def _token_row_usable(tok, *, consume: bool) -> None:
    now = _now()
    status = str(tok.status or '')
    if status == 'revoked':
        raise ActivationError('activation_token_revoked', http_status=403)
    if status == 'consumed' or (
        int(tok.uses_count or 0) >= int(tok.max_uses or 1) and status != 'active'
    ):
        raise ActivationError('activation_token_used', http_status=409)
    if status == 'expired' or (
        tok.expires_at is not None and tok.expires_at + timedelta(seconds=SKEW_SECONDS) < now
    ):
        if status == 'active':
            tok.status = 'expired'
            from nodeone.core.db import db

            db.session.commit()
        raise ActivationError('activation_token_expired', http_status=400)
    if status != 'active':
        raise ActivationError('activation_token_invalid', http_status=401)
    if consume and int(tok.uses_count or 0) >= int(tok.max_uses or 1):
        raise ActivationError('activation_token_used', http_status=409)


def _claims_from(lic, tok) -> dict[str, Any]:
    hint = None
    if str(lic.modality) == 'connected':
        hint = {
            'next': 'devices_register',
            'header': 'X-EN1-Activation-Token',
            'legacy_header': 'X-EN1-Provisioning-Code',
        }
    else:
        hint = {
            'next': 'standalone_assistant',
            'adr': 'ADR-033',
        }
    ends = lic.ends_at.isoformat() + 'Z' if lic.ends_at else None
    return {
        'license_id': int(lic.id),
        'organization_id': int(lic.organization_id),
        'product_code': str(lic.product_code),
        'modality': str(lic.modality),
        'implementation_strategy': str(lic.implementation_strategy),
        'register_ref': tok.register_ref,
        'license_expires_at': ends,
        'contract_id': int(lic.contract_id) if lic.contract_id else None,
        'subscription_id': int(lic.subscription_id) if lic.subscription_id else None,
        'provisioning_hint': hint,
        'token_id': int(tok.id),
        'token_expires_at': tok.expires_at.isoformat() + 'Z' if tok.expires_at else None,
    }


class ActivationService:
    """API estable ADR-035 Fase 1."""

    @classmethod
    def ensure_license(
        cls,
        *,
        organization_id: int,
        modality: str,
        implementation_strategy: str | None = None,
        product_code: str = PRODUCT_CODE,
        contract_id: int | None = None,
        subscription_id: int | None = None,
        starts_at: datetime | None = None,
        ends_at: datetime | None = None,
        user_id: int | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        from models.ets_activation_license import EtsActivationLicense
        from nodeone.core.db import db

        mod = _norm_modality(modality)
        strat = _norm_strategy(implementation_strategy, modality=mod)
        now = _now()
        row = (
            EtsActivationLicense.query.filter_by(
                organization_id=int(organization_id),
                product_code=product_code,
                modality=mod,
            )
            .filter(EtsActivationLicense.status.in_(('issued', 'active')))
            .order_by(EtsActivationLicense.id.desc())
            .first()
        )
        if row is None:
            row = EtsActivationLicense(
                organization_id=int(organization_id),
                contract_id=contract_id,
                subscription_id=subscription_id,
                product_code=product_code,
                modality=mod,
                implementation_strategy=strat,
                status='issued',
                starts_at=starts_at or now,
                ends_at=ends_at,
                metadata_json=json.dumps(metadata, ensure_ascii=False) if metadata else None,
                created_by_user_id=user_id,
                created_at=now,
                updated_at=now,
            )
            db.session.add(row)
            db.session.commit()
            _audit(organization_id, 'activation.license_issued', {'license_id': row.id, 'modality': mod})
        return row

    @classmethod
    def issue_token(
        cls,
        *,
        license_id: int,
        ttl_days: int | None = None,
        max_uses: int = 1,
        register_ref: str | None = None,
        user_id: int | None = None,
        ops_ready: bool | None = None,
    ) -> dict[str, Any]:
        from models.ets_activation_license import EtsActivationLicense
        from models.ets_activation_token import EtsActivationToken
        from nodeone.core.db import db

        lic = EtsActivationLicense.query.get(int(license_id))
        if lic is None:
            raise ActivationError('license_revoked', http_status=403, message='license_not_found')
        _license_usable(lic)

        if str(lic.modality) == 'connected':
            ready = ops_ready if ops_ready is not None else _ops_ready_for_connected(
                organization_id=int(lic.organization_id),
                register_ref=register_ref,
            )
            if not ready:
                raise ActivationError('ops_not_ready', http_status=409)
            if not (register_ref or '').strip():
                raise ActivationError('ops_not_ready', http_status=409, message='register_ref_required')

        ttl = int(ttl_days if ttl_days is not None else DEFAULT_TTL_DAYS)
        ttl = max(7, min(30, ttl))
        now = _now()
        code = _token_string()
        while EtsActivationToken.query.filter_by(token=code).first() is not None:
            code = _token_string()
        jti = secrets.token_hex(16)
        row = EtsActivationToken(
            license_id=int(lic.id),
            organization_id=int(lic.organization_id),
            token=code,
            status='active',
            expires_at=now + timedelta(days=ttl),
            max_uses=max(1, int(max_uses)),
            uses_count=0,
            register_ref=(register_ref or '').strip() or None,
            jti=jti,
            created_by_user_id=user_id,
            created_at=now,
            updated_at=now,
        )
        db.session.add(row)
        db.session.commit()
        _audit(
            int(lic.organization_id),
            'activation.token_issued',
            {'token_id': row.id, 'license_id': lic.id, 'modality': lic.modality},
        )
        return cls._token_public(row, lic)

    @classmethod
    def reissue_token(cls, *, license_id: int, revoke_previous_active: bool = True, **kwargs) -> dict[str, Any]:
        from models.ets_activation_token import EtsActivationToken
        from nodeone.core.db import db

        if revoke_previous_active:
            now = _now()
            q = EtsActivationToken.query.filter_by(license_id=int(license_id), status='active')
            for t in q.all():
                t.status = 'revoked'
                t.revoked_at = now
                t.revoke_reason = 'reissued'
                t.updated_at = now
            db.session.commit()
        return cls.issue_token(license_id=license_id, **kwargs)

    @classmethod
    def revoke_token(cls, token_id: int, *, reason: str | None = None) -> None:
        from models.ets_activation_token import EtsActivationToken
        from nodeone.core.db import db

        row = EtsActivationToken.query.get(int(token_id))
        if row is None:
            raise ActivationError('activation_token_invalid', http_status=404)
        now = _now()
        row.status = 'revoked'
        row.revoked_at = now
        row.revoke_reason = (reason or 'revoked')[:200]
        row.updated_at = now
        db.session.commit()
        _audit(int(row.organization_id), 'activation.token_revoked', {'token_id': row.id})

    @classmethod
    def revoke_license(cls, license_id: int, *, reason: str | None = None) -> None:
        from models.ets_activation_license import EtsActivationLicense
        from models.ets_activation_token import EtsActivationToken
        from nodeone.core.db import db

        lic = EtsActivationLicense.query.get(int(license_id))
        if lic is None:
            raise ActivationError('license_revoked', http_status=404, message='license_not_found')
        now = _now()
        lic.status = 'revoked'
        lic.revoked_at = now
        lic.revoke_reason = (reason or 'revoked')[:200]
        lic.updated_at = now
        for t in EtsActivationToken.query.filter_by(license_id=int(lic.id)).filter(
            EtsActivationToken.status.in_(('active',))
        ).all():
            t.status = 'revoked'
            t.revoked_at = now
            t.revoke_reason = 'license_revoked'
            t.updated_at = now
        db.session.commit()
        _audit(int(lic.organization_id), 'activation.license_revoked', {'license_id': lic.id})

    @classmethod
    def validate(
        cls,
        *,
        token: str,
        product_code: str | None = None,
    ) -> dict[str, Any]:
        """Pre-check sin consumir."""
        lic, tok = cls._resolve_token(token, product_code=product_code)
        _license_usable(lic)
        _token_row_usable(tok, consume=False)
        claims = _claims_from(lic, tok)
        claims['ok'] = True
        claims['consumable'] = int(tok.uses_count or 0) < int(tok.max_uses or 1)
        return claims

    @classmethod
    def redeem(
        cls,
        *,
        token: str,
        device_uuid: str,
        product_code: str | None = None,
    ) -> dict[str, Any]:
        from nodeone.core.db import db

        lic, tok = cls._resolve_token(token, product_code=product_code)
        _license_usable(lic)
        _token_row_usable(tok, consume=True)
        du = (device_uuid or '').strip()
        if not du:
            raise ActivationError('activation_token_invalid', http_status=400, message='device_uuid_required')

        now = _now()
        tok.uses_count = int(tok.uses_count or 0) + 1
        tok.consumed_at = now
        tok.consumed_device_uuid = du[:128]
        tok.updated_at = now
        if tok.uses_count >= int(tok.max_uses or 1):
            tok.status = 'consumed'
        if str(lic.status) == 'issued':
            lic.status = 'active'
            lic.updated_at = now
        db.session.commit()
        _audit(
            int(lic.organization_id),
            'activation.token_redeemed',
            {'token_id': tok.id, 'license_id': lic.id, 'device_uuid': du, 'modality': lic.modality},
        )
        claims = _claims_from(lic, tok)
        claims['ok'] = True
        claims['redeemed'] = True
        return claims

    @classmethod
    def _resolve_token(cls, token: str, *, product_code: str | None):
        from models.ets_activation_license import EtsActivationLicense
        from models.ets_activation_token import EtsActivationToken

        code = (token or '').strip().upper()
        if not code:
            raise ActivationError('activation_token_invalid', http_status=401)
        tok = EtsActivationToken.query.filter_by(token=code).first()
        if tok is None:
            # intentar sin normalizar por si guardamos mixed
            tok = EtsActivationToken.query.filter_by(token=(token or '').strip()).first()
        if tok is None:
            raise ActivationError('activation_token_invalid', http_status=401)
        lic = EtsActivationLicense.query.get(int(tok.license_id))
        if lic is None:
            raise ActivationError('license_revoked', http_status=403)
        want = (product_code or PRODUCT_CODE).strip().lower()
        if str(lic.product_code).lower() != want:
            raise ActivationError('product_mismatch', http_status=400)
        return lic, tok

    @classmethod
    def _token_public(cls, tok, lic) -> dict[str, Any]:
        return {
            'token_id': int(tok.id),
            'token': tok.token,
            'license_id': int(lic.id),
            'organization_id': int(lic.organization_id),
            'product_code': str(lic.product_code),
            'modality': str(lic.modality),
            'implementation_strategy': str(lic.implementation_strategy),
            'expires_at': tok.expires_at.isoformat() + 'Z' if tok.expires_at else None,
            'max_uses': int(tok.max_uses),
            'register_ref': tok.register_ref,
            'activate_url': _activate_url(tok.token),
            'qr_path': f'/api/v1/activation/tokens/{int(tok.id)}/qr.png',
            'transport': {
                'commercial_qr': '/start',
                'technical_qr': 'token_only',
            },
        }

    @classmethod
    def issue_for_organization_standalone(
        cls,
        *,
        organization_id: int,
        contract_id: int | None = None,
        subscription_id: int | None = None,
        user_id: int | None = None,
        ends_at: datetime | None = None,
    ) -> dict[str, Any]:
        """Helper /start Standalone: licencia + token sin árbol ops."""
        lic = cls.ensure_license(
            organization_id=organization_id,
            modality='standalone',
            implementation_strategy='self_serve',
            contract_id=contract_id,
            subscription_id=subscription_id,
            ends_at=ends_at,
            user_id=user_id,
            metadata={'source': 'eposone_start_assistant'},
        )
        return cls.issue_token(license_id=int(lic.id), user_id=user_id)
