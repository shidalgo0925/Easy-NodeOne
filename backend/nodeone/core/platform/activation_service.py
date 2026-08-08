"""Activación EN1 — ADR-035 v1.4 (Licencia → código de activación → redeem).

Standalone canónico: email + activation_code (6 dígitos).
App Link / activation_ref quedan secundarios. Connected exige ops_ready.
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


def _activation_code_digits() -> str:
    """Código de activación Standalone: 6 dígitos (100000–999999)."""
    return f'{secrets.randbelow(900000) + 100000:06d}'


def _legacy_manual_code() -> str:
    """Formato legado XXXX-XXXX-XXXX (Connected / puentes)."""
    raw = secrets.token_hex(6).upper()
    return f'{raw[0:4]}-{raw[4:8]}-{raw[8:12]}'


def _public_base(public_base: str | None = None) -> str:
    base = (public_base or os.environ.get('NODEONE_EPOSONE_PUBLIC_BASE') or '').strip().rstrip('/')
    if not base:
        base = 'https://eposone.easytech.services'
    return base


def _apk_url(*, public_base: str | None = None) -> str:
    return f'{_public_base(public_base)}/static/apk/eposone/EPosOne.apk'


def _app_link(activation_ref: str, *, public_base: str | None = None) -> str:
    ref = (activation_ref or '').strip()
    return f'{_public_base(public_base)}/activate/{ref}'


def _deep_link(activation_ref: str) -> str:
    ref = (activation_ref or '').strip()
    return f'eposone://activate/{ref}'


def activation_transport(
    *,
    activation_ref: str,
    activation_code: str,
    bound_email: str | None = None,
    public_base: str | None = None,
) -> dict[str, Any]:
    """Contrato de transporte ADR-035 v1.4."""
    ref = (activation_ref or '').strip()
    code = (activation_code or '').strip()
    app_link = _app_link(ref, public_base=public_base)
    return {
        'activation_code': code,
        'bound_email': (bound_email or '').strip().lower() or None,
        'activation_ref': ref,  # secundario / auditoría
        'manual_code': code,  # alias legado
        'token': code,
        'apk_url': _apk_url(public_base=public_base),
        'app_link': app_link,
        'activate_url': app_link,
        'deep_link': _deep_link(ref),
        'qr_url': f'/activate/{ref}/qr.png',
        'commercial_entry': '/start',
        'ux_primary': 'email_activation_code',
    }


def parse_activation_credentials(body: dict[str, Any] | None) -> tuple[str, str, str | None]:
    """Devuelve (kind, value, email_or_none).

    Canónico Standalone: email + activation_code.
    Secundario: activation_ref | manual_code | token (legacy).
    """
    data = body or {}
    email = (data.get('email') or '').strip().lower() or None
    code = (data.get('activation_code') or '').strip()
    ref = (data.get('activation_ref') or '').strip()
    manual = (data.get('manual_code') or '').strip()
    legacy = (data.get('token') or '').strip()

    if code:
        if ref or manual or (legacy and legacy != code):
            raise ActivationError('activation_credential_ambiguous', http_status=400)
        if not email:
            raise ActivationError(
                'activation_credential_missing',
                http_status=400,
                message='email_required_with_activation_code',
            )
        return 'activation_code', code, email

    modes: list[tuple[str, str]] = []
    if ref:
        modes.append(('activation_ref', ref))
    if manual:
        modes.append(('manual_code', manual))
    if legacy:
        if manual and legacy.upper() != manual.upper():
            raise ActivationError('activation_credential_ambiguous', http_status=400)
        if not manual:
            modes.append(('manual_code', legacy))

    if len(modes) > 1:
        raise ActivationError('activation_credential_ambiguous', http_status=400)
    if len(modes) == 1:
        return modes[0][0], modes[0][1], email
    if email:
        raise ActivationError(
            'activation_credential_missing',
            http_status=400,
            message='activation_code_required_with_email',
        )
    raise ActivationError('activation_credential_missing', http_status=400)


def _map_token_error(exc: ActivationError, *, kind: str) -> ActivationError:
    if kind != 'activation_code':
        return exc
    mapping = {
        'activation_token_invalid': 'activation_code_invalid',
        'activation_token_expired': 'activation_code_expired',
        'activation_token_used': 'activation_code_used',
        'activation_token_revoked': 'activation_code_revoked',
    }
    new_code = mapping.get(exc.code)
    if not new_code:
        return exc
    return ActivationError(new_code, http_status=exc.http_status, message=new_code)


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
        public_base: str | None = None,
        bound_email: str | None = None,
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
        standalone = str(lic.modality) == 'standalone'
        if standalone:
            code = _activation_code_digits()
            while EtsActivationToken.query.filter_by(token=code).first() is not None:
                code = _activation_code_digits()
        else:
            code = _legacy_manual_code()
            while EtsActivationToken.query.filter_by(token=code).first() is not None:
                code = _legacy_manual_code()
        jti = secrets.token_hex(16)
        email_bound = (bound_email or '').strip().lower() or None
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
            bound_email=email_bound,
            created_at=now,
            updated_at=now,
        )
        db.session.add(row)
        db.session.commit()
        _audit(
            int(lic.organization_id),
            'activation.token_issued',
            {
                'token_id': row.id,
                'license_id': lic.id,
                'modality': lic.modality,
                'bound_email': email_bound,
            },
        )
        return cls._token_public(row, lic, public_base=public_base)

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
    def reissue_standalone_for_organization(
        cls,
        *,
        organization_id: int,
        bound_email: str,
        user_id: int | None = None,
        public_base: str | None = None,
        send_email: bool = False,
        organization_name: str | None = None,
    ) -> dict[str, Any]:
        """Reemite código Standalone sobre la misma licencia (reinstalación / otra tablet)."""
        lic = cls.ensure_license(
            organization_id=int(organization_id),
            modality='standalone',
            implementation_strategy='self_serve',
            user_id=user_id,
            metadata={'source': 'activation_reissue'},
        )
        issued = cls.reissue_token(
            license_id=int(lic.id),
            bound_email=bound_email,
            user_id=user_id,
            public_base=public_base,
        )
        if send_email:
            try:
                from nodeone.modules.eposone_start.service import ensure_standalone_ready_email_sent
                from models.users import User

                user = None
                if user_id:
                    user = User.query.get(int(user_id))
                if user is None:
                    user = User.query.filter_by(email=(bound_email or '').strip().lower()).first()
                if user is not None:
                    ensure_standalone_ready_email_sent(
                        user=user,
                        organization_name=organization_name or '',
                        activation=issued,
                    )
            except Exception:
                pass
        return issued

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
        token: str | None = None,
        activation_ref: str | None = None,
        manual_code: str | None = None,
        product_code: str | None = None,
        credentials: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Pre-check sin consumir."""
        body = dict(credentials or {})
        if activation_ref is not None:
            body['activation_ref'] = activation_ref
        if manual_code is not None:
            body['manual_code'] = manual_code
        if token is not None:
            body.setdefault('token', token)
        kind, value, email = parse_activation_credentials(body)
        try:
            lic, tok = cls._resolve_credential(
                kind, value, product_code=product_code, bound_email=email
            )
            _license_usable(lic)
            _token_row_usable(tok, consume=False)
        except ActivationError as exc:
            raise _map_token_error(exc, kind=kind) from exc
        claims = _claims_from(lic, tok)
        claims['ok'] = True
        claims['consumable'] = int(tok.uses_count or 0) < int(tok.max_uses or 1)
        return claims

    @classmethod
    def redeem(
        cls,
        *,
        token: str | None = None,
        device_uuid: str,
        activation_ref: str | None = None,
        manual_code: str | None = None,
        product_code: str | None = None,
        credentials: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        from nodeone.core.db import db

        body = dict(credentials or {})
        if activation_ref is not None:
            body['activation_ref'] = activation_ref
        if manual_code is not None:
            body['manual_code'] = manual_code
        if token is not None:
            body.setdefault('token', token)
        kind, value, email = parse_activation_credentials(body)
        try:
            lic, tok = cls._resolve_credential(
                kind, value, product_code=product_code, bound_email=email
            )
            _license_usable(lic)
            _token_row_usable(tok, consume=True)
        except ActivationError as exc:
            raise _map_token_error(exc, kind=kind) from exc
        du = (device_uuid or '').strip()
        if not du:
            err = ActivationError(
                'activation_token_invalid',
                http_status=400,
                message='device_uuid_required',
            )
            raise _map_token_error(err, kind=kind)

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
            {
                'token_id': tok.id,
                'license_id': lic.id,
                'device_uuid': du,
                'modality': lic.modality,
                'credential_kind': kind,
            },
        )
        claims = _claims_from(lic, tok)
        claims['ok'] = True
        claims['redeemed'] = True
        return claims

    @classmethod
    def get_by_activation_ref(cls, activation_ref: str, *, product_code: str | None = None):
        return cls._resolve_credential('activation_ref', activation_ref, product_code=product_code)

    @classmethod
    def _resolve_credential(
        cls,
        kind: str,
        value: str,
        *,
        product_code: str | None,
        bound_email: str | None = None,
    ):
        from models.ets_activation_license import EtsActivationLicense
        from models.ets_activation_token import EtsActivationToken

        raw = (value or '').strip()
        if not raw:
            raise ActivationError(
                'activation_code_invalid' if kind == 'activation_code' else 'activation_token_invalid',
                http_status=401,
            )

        tok = None
        if kind == 'activation_code':
            tok = EtsActivationToken.query.filter_by(token=raw).first()
            if tok is None:
                raise ActivationError('activation_code_invalid', http_status=401)
            bound = (getattr(tok, 'bound_email', None) or '').strip().lower()
            want = (bound_email or '').strip().lower()
            if not bound or not want or bound != want:
                raise ActivationError('email_mismatch', http_status=403)
        elif kind == 'activation_ref':
            tok = EtsActivationToken.query.filter_by(jti=raw).first()
            if tok is None:
                tok = EtsActivationToken.query.filter_by(jti=raw.lower()).first()
        elif kind == 'manual_code':
            code = raw.upper()
            tok = EtsActivationToken.query.filter_by(token=code).first()
            if tok is None:
                tok = EtsActivationToken.query.filter_by(token=raw).first()
        else:
            raise ActivationError('activation_credential_missing', http_status=400)

        if tok is None:
            raise ActivationError('activation_token_invalid', http_status=401)
        lic = EtsActivationLicense.query.get(int(tok.license_id))
        if lic is None:
            raise ActivationError('license_revoked', http_status=403)
        want_pc = (product_code or PRODUCT_CODE).strip().lower()
        if str(lic.product_code).lower() != want_pc:
            raise ActivationError('product_mismatch', http_status=400)
        return lic, tok

    @classmethod
    def _resolve_token(cls, token: str, *, product_code: str | None):
        """Compat: resolve por manual_code (legacy)."""
        return cls._resolve_credential('manual_code', token, product_code=product_code)

    @classmethod
    def _token_public(cls, tok, lic, *, public_base: str | None = None) -> dict[str, Any]:
        ref = str(tok.jti or '')
        code = str(tok.token or '')
        bound = (getattr(tok, 'bound_email', None) or None)
        transport = activation_transport(
            activation_ref=ref,
            activation_code=code,
            bound_email=bound,
            public_base=public_base,
        )
        standalone = str(lic.modality) == 'standalone'
        return {
            'token_id': int(tok.id),
            'activation_code': code if standalone else None,
            'bound_email': transport['bound_email'],
            'activation_ref': ref,
            'manual_code': code,  # alias legado
            'token': code,
            'license_id': int(lic.id),
            'organization_id': int(lic.organization_id),
            'product_code': str(lic.product_code),
            'modality': str(lic.modality),
            'implementation_strategy': str(lic.implementation_strategy),
            'expires_at': tok.expires_at.isoformat() + 'Z' if tok.expires_at else None,
            'max_uses': int(tok.max_uses),
            'register_ref': tok.register_ref,
            'apk_url': transport['apk_url'],
            'app_link': transport['app_link'],
            'activate_url': transport['app_link'],
            'deep_link': transport['deep_link'],
            'qr_path': transport['qr_url'],
            'qr_url': transport['qr_url'],
            'transport': {
                'ux_primary': 'email_activation_code' if standalone else 'app_link',
                'commercial_qr': '/start',
                'apk_url': transport['apk_url'],
                'app_link': transport['app_link'],
                'deep_link': transport['deep_link'],
                'activation_ref': ref,
                'activation_code': code if standalone else None,
            },
            'redeem': {
                'method': 'POST',
                'path': '/api/v1/activation/redeem',
                'validate_path': '/api/v1/activation/validate',
                'credential_fields': (
                    ['email', 'activation_code'] if standalone else ['activation_ref', 'manual_code']
                ),
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
        bound_email: str | None = None,
        ends_at: datetime | None = None,
        public_base: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Helper /start Standalone: licencia + código de activación sin árbol ops."""
        meta = dict(metadata or {})
        meta.setdefault('source', 'eposone_start_assistant')
        email = (bound_email or '').strip().lower() or None
        if not email and user_id:
            try:
                from models.users import User

                u = User.query.get(int(user_id))
                if u is not None:
                    email = (u.email or '').strip().lower() or None
            except Exception:
                pass
        lic = cls.ensure_license(
            organization_id=organization_id,
            modality='standalone',
            implementation_strategy='self_serve',
            contract_id=contract_id,
            subscription_id=subscription_id,
            ends_at=ends_at,
            user_id=user_id,
            metadata=meta,
        )
        # Una sola activación active por licencia Standalone (reemite si ya había).
        return cls.reissue_token(
            license_id=int(lic.id),
            user_id=user_id,
            bound_email=email,
            public_base=public_base,
            ttl_days=int(meta.get('grace_days') or 7),
        )
