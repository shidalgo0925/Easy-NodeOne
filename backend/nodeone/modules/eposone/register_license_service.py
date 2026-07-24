"""Licencia comercial por Caja — License Engine V1.0 (contrato bootstrap/sync)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from models.eposone_register_license import EposoneRegisterLicense

LICENSE_SCHEMA_VERSION = 1
TRIAL_DURATION_DAYS = 15  # contrato oficial Prog1↔Prog2

# Persistencia interna (lowercase)
LICENSE_TYPE_UNLICENSED = 'unlicensed'
LICENSE_TYPE_TRIAL = 'trial'
LICENSE_TYPE_MONTHLY = 'monthly'
LICENSE_TYPE_ANNUAL = 'annual'
LICENSE_TYPE_SUBSCRIPTION = 'subscription'  # legacy → MONTHLY al emitir
LICENSE_TYPE_COURTESY = 'courtesy'
LICENSE_TYPE_PROMOTION = 'promotion'
LICENSE_TYPE_DEMO = 'demo'
LICENSE_TYPE_PERPETUAL = 'perpetual'
LICENSE_TYPE_PARTNER = 'partner'
LICENSE_TYPE_OEM = 'oem'
LICENSE_TYPE_INTERNAL = 'internal'
LICENSE_TYPE_EDUCATIONAL = 'educational'
LICENSE_TYPE_SUSPENDED = 'suspended'  # legacy type; prefer status=suspended

LICENSE_STATUS_PENDING = 'pending'
LICENSE_STATUS_ACTIVE = 'active'
LICENSE_STATUS_GRACE = 'grace'
LICENSE_STATUS_EXPIRED = 'expired'
LICENSE_STATUS_SUSPENDED = 'suspended'
LICENSE_STATUS_REVOKED = 'revoked'
LICENSE_STATUS_CANCELLED = 'cancelled'

ACTIVATION_EN1 = 'EN1'

TRIAL_START_ON_CREATE = 'on_create'
TRIAL_START_ON_ACTIVATE = 'on_activate'
TRIAL_START_ON_FIRST_PROVISION = 'on_first_provision'

# Features canónicas (booleanas vía presencia en lista)
DEFAULT_TRIAL_FEATURES: tuple[str, ...] = (
    'sales',
    'payments',
    'cash_shifts',
    'customers',
    'reports',
)

DEFAULT_FEATURES_BY_TYPE: dict[str, tuple[str, ...]] = {
    LICENSE_TYPE_TRIAL: DEFAULT_TRIAL_FEATURES,
    LICENSE_TYPE_MONTHLY: DEFAULT_TRIAL_FEATURES + ('mixed_payments', 'tips', 'taxes'),
    LICENSE_TYPE_ANNUAL: DEFAULT_TRIAL_FEATURES + ('mixed_payments', 'tips', 'taxes', 'dashboard'),
    LICENSE_TYPE_SUBSCRIPTION: DEFAULT_TRIAL_FEATURES + ('mixed_payments', 'tips', 'taxes'),
    LICENSE_TYPE_PERPETUAL: DEFAULT_TRIAL_FEATURES
    + ('mixed_payments', 'tips', 'taxes', 'dashboard', 'multi_pos'),
    LICENSE_TYPE_COURTESY: DEFAULT_TRIAL_FEATURES,
    LICENSE_TYPE_DEMO: DEFAULT_TRIAL_FEATURES,
    LICENSE_TYPE_PROMOTION: DEFAULT_TRIAL_FEATURES,
    LICENSE_TYPE_PARTNER: DEFAULT_TRIAL_FEATURES + ('multi_pos', 'multi_branch'),
    LICENSE_TYPE_OEM: DEFAULT_TRIAL_FEATURES,
    LICENSE_TYPE_INTERNAL: DEFAULT_TRIAL_FEATURES
    + ('mixed_payments', 'tips', 'taxes', 'dashboard', 'api'),
    LICENSE_TYPE_EDUCATIONAL: DEFAULT_TRIAL_FEATURES,
}

DEFAULT_LIMITS_BY_TYPE: dict[str, dict[str, Any]] = {
    LICENSE_TYPE_TRIAL: {'max_devices': 1, 'max_cashiers': None, 'max_products': None},
    LICENSE_TYPE_MONTHLY: {'max_devices': 1, 'max_cashiers': None, 'max_products': None},
    LICENSE_TYPE_ANNUAL: {'max_devices': 2, 'max_cashiers': None, 'max_products': None},
    LICENSE_TYPE_SUBSCRIPTION: {'max_devices': 1, 'max_cashiers': None, 'max_products': None},
    LICENSE_TYPE_PERPETUAL: {'max_devices': None, 'max_cashiers': None, 'max_products': None},
}

# Grace comercial por tipo (días después de expires_at). Trial=0; resto configurable vía settings.
GRACE_DAYS_BY_TYPE: dict[str, int | None] = {
    LICENSE_TYPE_TRIAL: 0,
    LICENSE_TYPE_PERPETUAL: None,  # no vence
}

COMMERCIAL_UI = {
    'unlicensed': 'Sin licencia',
    'trial': 'Trial',
    'active': 'Activa',
    'grace': 'Gracia',
    'courtesy': 'Cortesía',
    'promotion': 'Promoción',
    'demo': 'Demo',
    'perpetual': 'Permanente',
    'monthly': 'Mensual',
    'annual': 'Anual',
    'expired': 'Vencida',
    'suspended': 'Suspendida',
    'revoked': 'Revocada',
    'pending': 'Pendiente',
    'partner': 'Partner',
    'oem': 'OEM',
    'internal': 'Interna',
    'educational': 'Educativa',
}

_TYPE_EMIT = {
    LICENSE_TYPE_TRIAL: 'TRIAL',
    LICENSE_TYPE_MONTHLY: 'MONTHLY',
    LICENSE_TYPE_ANNUAL: 'ANNUAL',
    LICENSE_TYPE_SUBSCRIPTION: 'MONTHLY',
    LICENSE_TYPE_PERPETUAL: 'PERPETUAL',
    LICENSE_TYPE_PARTNER: 'PARTNER',
    LICENSE_TYPE_OEM: 'OEM',
    LICENSE_TYPE_INTERNAL: 'INTERNAL',
    LICENSE_TYPE_EDUCATIONAL: 'EDUCATIONAL',
    LICENSE_TYPE_COURTESY: 'INTERNAL',
    LICENSE_TYPE_DEMO: 'EDUCATIONAL',
    LICENSE_TYPE_PROMOTION: 'PARTNER',
    LICENSE_TYPE_UNLICENSED: 'TRIAL',  # no se emite operativo; status PENDING
}

_STATUS_EMIT = {
    LICENSE_STATUS_PENDING: 'PENDING',
    LICENSE_STATUS_ACTIVE: 'ACTIVE',
    LICENSE_STATUS_GRACE: 'GRACE',
    LICENSE_STATUS_EXPIRED: 'EXPIRED',
    LICENSE_STATUS_SUSPENDED: 'SUSPENDED',
    LICENSE_STATUS_REVOKED: 'REVOKED',
    LICENSE_STATUS_CANCELLED: 'REVOKED',
}


def _audit(organization_id: int, event_type: str, payload: dict[str, Any]) -> None:
    try:
        from nodeone.core.services.audit import AuditService

        AuditService.publish_domain_event(
            int(organization_id),
            event_type,
            payload,
            source_app_id='eposone',
        )
    except Exception:
        pass


def _loads_json(raw: str | None, default: Any) -> Any:
    if not raw:
        return default
    try:
        return json.loads(raw)
    except (TypeError, ValueError, json.JSONDecodeError):
        return default


def _dumps_json(value: Any) -> str | None:
    if value is None:
        return None
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'))


def _api_iso(dt: datetime | None, *, organization_id: int | None = None) -> str | None:
    """ISO-8601 con zona de la org (fallback Z)."""
    if dt is None:
        return None
    try:
        from nodeone.core.timezone_service import TimeZoneService

        org = None
        if organization_id is not None:
            org = TimeZoneService.resolve_organization(organization_id=int(organization_id))
        zone = TimeZoneService.business_zoneinfo(org)
        local = TimeZoneService.utc_naive_to_local(dt, zone)
        if local is None:
            return TimeZoneService.to_api_iso(dt)
        return local.isoformat(timespec='seconds')
    except Exception:
        naive = dt.replace(tzinfo=None) if dt.tzinfo else dt
        return naive.strftime('%Y-%m-%dT%H:%M:%S') + 'Z'


@dataclass
class RegisterLicenseSnapshot:
    register_ref: str
    license_type: str
    status: str
    plan_code: str
    starts_at: datetime | None
    expires_at: datetime | None
    trial_used: bool
    days_remaining: int | None
    can_operate: bool
    commercial_ui: str
    reason: str | None
    # V1 contract fields
    license_id: str | None = None
    activation_method: str = ACTIVATION_EN1
    issued_at: datetime | None = None
    grace_until: datetime | None = None
    last_validation: datetime | None = None
    updated_at: datetime | None = None
    features: list[str] = field(default_factory=list)
    limits: dict[str, Any] = field(default_factory=dict)
    organization_id: int | None = None

    def to_device_payload(self) -> dict[str, Any]:
        """Contrato oficial License Engine V1 — bloque bootstrap/sync `license`."""
        oid = self.organization_id
        ltype_key = str(self.license_type or '').strip().lower()
        status_key = str(self.status or '').strip().lower()
        emit_type = _TYPE_EMIT.get(ltype_key, ltype_key.upper() or 'TRIAL')
        if ltype_key in (LICENSE_TYPE_UNLICENSED, ''):
            emit_type = 'TRIAL'
            status_key = LICENSE_STATUS_PENDING
        emit_status = _STATUS_EMIT.get(status_key, status_key.upper() or 'PENDING')
        plan = str(self.plan_code or 'eposone')
        if ltype_key == LICENSE_TYPE_TRIAL and plan in ('eposone', ''):
            plan = 'trial'
        return {
            'schema_version': LICENSE_SCHEMA_VERSION,
            'license_id': self.license_id or None,
            'license_type': emit_type,
            'status': emit_status,
            'plan_code': plan,
            'activation_method': (self.activation_method or ACTIVATION_EN1).upper(),
            'issued_at': _api_iso(self.issued_at or self.starts_at, organization_id=oid),
            'starts_at': _api_iso(self.starts_at, organization_id=oid),
            'expires_at': _api_iso(self.expires_at, organization_id=oid),
            'grace_until': _api_iso(self.grace_until, organization_id=oid),
            'last_validation': _api_iso(self.last_validation, organization_id=oid),
            'features': list(self.features or []),
            'limits': dict(self.limits or {}),
            'updated_at': _api_iso(self.updated_at or self.last_validation, organization_id=oid),
        }

    def commercial_ui_key(self) -> str:
        if self.status == LICENSE_STATUS_SUSPENDED or self.license_type == LICENSE_TYPE_SUSPENDED:
            return 'suspended'
        if self.status == LICENSE_STATUS_REVOKED:
            return 'revoked'
        if self.status == LICENSE_STATUS_GRACE:
            return 'grace'
        if self.status == LICENSE_STATUS_EXPIRED or (
            self.expires_at is not None
            and self.expires_at < datetime.utcnow()
            and self.license_type != LICENSE_TYPE_PERPETUAL
            and self.status not in (LICENSE_STATUS_GRACE,)
        ):
            return 'expired'
        if self.license_type in (LICENSE_TYPE_UNLICENSED, '') or self.status == LICENSE_STATUS_PENDING:
            if self.license_type == LICENSE_TYPE_UNLICENSED or not self.license_type:
                return 'unlicensed'
            if self.status == LICENSE_STATUS_PENDING:
                return 'pending'
        if self.license_type == LICENSE_TYPE_TRIAL:
            return 'trial'
        if self.license_type == LICENSE_TYPE_COURTESY:
            return 'courtesy'
        if self.license_type == LICENSE_TYPE_PROMOTION:
            return 'promotion'
        if self.license_type == LICENSE_TYPE_DEMO:
            return 'demo'
        if self.license_type == LICENSE_TYPE_PERPETUAL:
            return 'perpetual'
        if self.license_type in (LICENSE_TYPE_MONTHLY, LICENSE_TYPE_SUBSCRIPTION):
            return 'monthly' if self.status == LICENSE_STATUS_ACTIVE else self.license_type
        if self.license_type == LICENSE_TYPE_ANNUAL:
            return 'annual'
        return self.license_type or 'unlicensed'


class RegisterLicenseService:
    @staticmethod
    def _policy(organization_id: int) -> dict[str, Any]:
        from nodeone.modules.eposone.settings_service import EposoneSettingsService

        s = EposoneSettingsService.runtime_for(int(organization_id))
        return {
            'trial_days_default': int(
                getattr(s, 'trial_days_default', TRIAL_DURATION_DAYS) or TRIAL_DURATION_DAYS
            ),
            'trial_start_policy': str(
                getattr(s, 'trial_start_policy', TRIAL_START_ON_FIRST_PROVISION)
                or TRIAL_START_ON_FIRST_PROVISION
            ),
            'provisioning_code_ttl_minutes': int(getattr(s, 'provisioning_code_ttl_minutes', 30) or 30),
            'offline_grace_days': int(getattr(s, 'offline_grace_days', 7) or 7),
        }

    @staticmethod
    def _default_features(license_type: str) -> list[str]:
        return list(DEFAULT_FEATURES_BY_TYPE.get(license_type, DEFAULT_TRIAL_FEATURES))

    @staticmethod
    def _default_limits(license_type: str) -> dict[str, Any]:
        return dict(DEFAULT_LIMITS_BY_TYPE.get(license_type, DEFAULT_LIMITS_BY_TYPE[LICENSE_TYPE_TRIAL]))

    @staticmethod
    def _grace_days_for(license_type: str, organization_id: int) -> int | None:
        if license_type in GRACE_DAYS_BY_TYPE:
            return GRACE_DAYS_BY_TYPE[license_type]
        if license_type == LICENSE_TYPE_PERPETUAL:
            return None
        # monthly / annual / subscription / etc. — configurable, no hardcode 30
        policy = RegisterLicenseService._policy(organization_id)
        return int(policy['offline_grace_days'])

    @staticmethod
    def get_or_create(organization_id: int, register_ref: str) -> EposoneRegisterLicense:
        from app import db

        oid = int(organization_id)
        ref = (register_ref or '').strip()
        row = EposoneRegisterLicense.query.filter_by(organization_id=oid, register_ref=ref).first()
        if row is None:
            now = datetime.utcnow()
            row = EposoneRegisterLicense(
                organization_id=oid,
                register_ref=ref,
                license_type=LICENSE_TYPE_UNLICENSED,
                status=LICENSE_STATUS_PENDING,
                activation_method=ACTIVATION_EN1,
                issued_at=now,
            )
            db.session.add(row)
            db.session.flush()
            _audit(
                oid,
                'license.created',
                {'register_ref': ref, 'license_id': f'lic_{row.id}', 'status': LICENSE_STATUS_PENDING},
            )
        return row

    @staticmethod
    def _compute_effective(row: EposoneRegisterLicense) -> tuple[str, bool, int | None, str | None]:
        """Devuelve (status_efectivo, can_operate, days_remaining, reason)."""
        now = datetime.utcnow()
        expires = row.expires_at
        grace_until = getattr(row, 'grace_until', None)
        status = str(row.status or LICENSE_STATUS_PENDING)
        ltype = str(row.license_type or LICENSE_TYPE_UNLICENSED)

        if status == LICENSE_STATUS_REVOKED or status == LICENSE_STATUS_CANCELLED:
            return LICENSE_STATUS_REVOKED, False, None, 'revoked'
        if status == LICENSE_STATUS_SUSPENDED or ltype == LICENSE_TYPE_SUSPENDED:
            return LICENSE_STATUS_SUSPENDED, False, None, 'suspended'
        if ltype == LICENSE_TYPE_UNLICENSED or status == LICENSE_STATUS_PENDING:
            return LICENSE_STATUS_PENDING, False, None, 'unlicensed'
        if ltype == LICENSE_TYPE_PERPETUAL and status == LICENSE_STATUS_ACTIVE:
            return LICENSE_STATUS_ACTIVE, True, None, None

        if expires is not None and expires < now:
            if grace_until is not None and grace_until >= now:
                days = max(0, (grace_until.date() - now.date()).days)
                return LICENSE_STATUS_GRACE, True, days, 'grace'
            return LICENSE_STATUS_EXPIRED, False, 0, 'expired'

        days = max(0, (expires.date() - now.date()).days) if expires is not None else None
        if status == LICENSE_STATUS_ACTIVE:
            return LICENSE_STATUS_ACTIVE, True, days, None
        if status == LICENSE_STATUS_GRACE:
            return LICENSE_STATUS_GRACE, True, days, 'grace'
        return status, False, days, status

    @staticmethod
    def snapshot(organization_id: int, register_ref: str) -> RegisterLicenseSnapshot:
        oid = int(organization_id)
        ref = (register_ref or '').strip()
        row = EposoneRegisterLicense.query.filter_by(organization_id=oid, register_ref=ref).first()
        if row is None:
            return RegisterLicenseSnapshot(
                register_ref=ref,
                license_type=LICENSE_TYPE_UNLICENSED,
                status=LICENSE_STATUS_PENDING,
                plan_code='eposone',
                starts_at=None,
                expires_at=None,
                trial_used=False,
                days_remaining=None,
                can_operate=False,
                commercial_ui=COMMERCIAL_UI['unlicensed'],
                reason='unlicensed',
                features=[],
                limits={},
                organization_id=oid,
            )

        eff_status, can, days, reason = RegisterLicenseService._compute_effective(row)
        # Persistir status calculado si cambió por fecha (expired/grace)
        if eff_status in (LICENSE_STATUS_EXPIRED, LICENSE_STATUS_GRACE) and str(row.status) != eff_status:
            prev = str(row.status)
            row.status = eff_status
            try:
                from app import db

                db.session.commit()
            except Exception:
                pass
            if eff_status == LICENSE_STATUS_EXPIRED and prev != LICENSE_STATUS_EXPIRED:
                _audit(
                    oid,
                    'license.expired',
                    {
                        'register_ref': ref,
                        'license_id': f'lic_{row.id}',
                        'expires_at': row.expires_at.isoformat() if row.expires_at else None,
                    },
                )

        ltype = str(row.license_type or LICENSE_TYPE_UNLICENSED)
        features = _loads_json(getattr(row, 'features_json', None), None)
        if not isinstance(features, list) or not features:
            features = RegisterLicenseService._default_features(ltype)
        limits = _loads_json(getattr(row, 'limits_json', None), None)
        if not isinstance(limits, dict) or not limits:
            limits = RegisterLicenseService._default_limits(ltype)

        snap = RegisterLicenseSnapshot(
            register_ref=ref,
            license_type=ltype,
            status=eff_status,
            plan_code=str(row.plan_code or 'eposone'),
            starts_at=row.starts_at,
            expires_at=row.expires_at,
            trial_used=bool(row.trial_used),
            days_remaining=days,
            can_operate=can,
            commercial_ui='',
            reason=reason,
            license_id=f'lic_{int(row.id)}',
            activation_method=str(getattr(row, 'activation_method', None) or ACTIVATION_EN1),
            issued_at=getattr(row, 'issued_at', None) or row.created_at or row.starts_at,
            grace_until=getattr(row, 'grace_until', None),
            last_validation=row.last_validated_at,
            updated_at=row.updated_at,
            features=list(features),
            limits=dict(limits),
            organization_id=oid,
        )
        snap.commercial_ui = COMMERCIAL_UI.get(snap.commercial_ui_key(), snap.commercial_ui_key())
        return snap

    @staticmethod
    def serve_for_device(
        organization_id: int,
        register_ref: str,
        *,
        touch_validation: bool = True,
        event: str = 'license.bootstrap_served',
    ) -> dict[str, Any]:
        """Recalcula, actualiza last_validation y devuelve payload contrato V1."""
        from app import db

        oid = int(organization_id)
        ref = (register_ref or '').strip()
        snap = RegisterLicenseService.snapshot(oid, ref)
        if touch_validation:
            row = EposoneRegisterLicense.query.filter_by(organization_id=oid, register_ref=ref).first()
            if row is not None:
                now = datetime.utcnow()
                row.last_validated_at = now
                row.updated_at = now
                try:
                    db.session.commit()
                except Exception:
                    db.session.rollback()
                snap = RegisterLicenseService.snapshot(oid, ref)
                snap.last_validation = now
        payload = snap.to_device_payload()
        _audit(
            oid,
            event,
            {
                'register_ref': ref,
                'license_id': payload.get('license_id'),
                'status': payload.get('status'),
                'license_type': payload.get('license_type'),
            },
        )
        return payload

    @staticmethod
    def activate(
        organization_id: int,
        register_ref: str,
        *,
        license_type: str,
        duration_days: int | None = None,
        expires_at: datetime | None = None,
        starts_at: datetime | None = None,
        plan_code: str = 'eposone',
        notes: str | None = None,
        reason: str | None = None,
        user_id: int | None = None,
        mark_trial_used: bool | None = None,
        features: list[str] | None = None,
        limits: dict[str, Any] | None = None,
        activation_method: str = ACTIVATION_EN1,
    ) -> RegisterLicenseSnapshot:
        from app import db

        row = RegisterLicenseService.get_or_create(organization_id, register_ref)
        was_new = row.license_type in (LICENSE_TYPE_UNLICENSED, '') and not row.starts_at
        now = starts_at or datetime.utcnow()
        ltype = (license_type or LICENSE_TYPE_MONTHLY).strip().lower()
        if ltype == 'subscription':
            ltype = LICENSE_TYPE_MONTHLY
        row.license_type = ltype
        row.status = LICENSE_STATUS_ACTIVE
        row.plan_code = (plan_code or 'eposone').strip() or 'eposone'
        if ltype == LICENSE_TYPE_TRIAL and row.plan_code in ('eposone', ''):
            row.plan_code = 'trial'
        row.starts_at = now
        row.issued_at = getattr(row, 'issued_at', None) or now
        row.activation_method = (activation_method or ACTIVATION_EN1).strip() or ACTIVATION_EN1
        row.notes = (notes or '').strip() or None
        row.reason = (reason or '').strip() or None
        row.activated_by_user_id = int(user_id) if user_id is not None else None
        row.updated_at = now

        if ltype == LICENSE_TYPE_PERPETUAL:
            row.expires_at = None
            row.grace_until = None
        elif expires_at is not None:
            row.expires_at = expires_at
        elif duration_days is not None:
            row.expires_at = now + timedelta(days=max(0, int(duration_days)))
        elif ltype == LICENSE_TYPE_COURTESY:
            row.expires_at = None
            row.grace_until = None
        else:
            policy = RegisterLicenseService._policy(organization_id)
            days = (
                TRIAL_DURATION_DAYS
                if ltype == LICENSE_TYPE_TRIAL
                else int(policy['trial_days_default'])
            )
            row.expires_at = now + timedelta(days=days)

        grace_days = RegisterLicenseService._grace_days_for(ltype, int(organization_id))
        if row.expires_at is not None and grace_days is not None and grace_days > 0:
            row.grace_until = row.expires_at + timedelta(days=int(grace_days))
        elif ltype == LICENSE_TYPE_TRIAL or grace_days == 0:
            row.grace_until = None

        feats = features if features is not None else RegisterLicenseService._default_features(ltype)
        lims = limits if limits is not None else RegisterLicenseService._default_limits(ltype)
        row.features_json = _dumps_json(list(feats))
        row.limits_json = _dumps_json(dict(lims))

        if ltype == LICENSE_TYPE_TRIAL or mark_trial_used:
            row.trial_used = True
            row.trial_started_at = row.trial_started_at or now
            row.trial_expires_at = row.expires_at

        db.session.commit()
        event = 'license.created' if was_new else 'license.renewed'
        if reason == 'trial_auto':
            event = 'license.created'
        _audit(
            int(organization_id),
            event,
            {
                'register_ref': (register_ref or '').strip(),
                'license_id': f'lic_{row.id}',
                'license_type': ltype,
                'status': LICENSE_STATUS_ACTIVE,
                'expires_at': row.expires_at.isoformat() if row.expires_at else None,
            },
        )
        _audit(
            int(organization_id),
            'license.updated',
            {'register_ref': (register_ref or '').strip(), 'license_id': f'lic_{row.id}'},
        )
        return RegisterLicenseService.snapshot(organization_id, register_ref)

    @staticmethod
    def start_trial_if_eligible(
        organization_id: int, register_ref: str, *, user_id: int | None = None
    ) -> RegisterLicenseSnapshot | None:
        """Trial 15 días una sola vez por Caja (trial_used). No reinicia al reprovisionar."""
        row = RegisterLicenseService.get_or_create(organization_id, register_ref)
        if row.trial_used:
            return None
        if str(row.license_type) not in (LICENSE_TYPE_UNLICENSED, LICENSE_TYPE_TRIAL, ''):
            if row.status == LICENSE_STATUS_ACTIVE:
                return None
        return RegisterLicenseService.activate(
            organization_id,
            register_ref,
            license_type=LICENSE_TYPE_TRIAL,
            duration_days=TRIAL_DURATION_DAYS,
            plan_code='trial',
            reason='trial_auto',
            user_id=user_id,
            mark_trial_used=True,
            activation_method=ACTIVATION_EN1,
        )

    @staticmethod
    def on_first_device_provisioned(organization_id: int, register_ref: str) -> None:
        policy = RegisterLicenseService._policy(organization_id)
        if policy['trial_start_policy'] != TRIAL_START_ON_FIRST_PROVISION:
            return
        RegisterLicenseService.start_trial_if_eligible(organization_id, register_ref)

    @staticmethod
    def suspend(
        organization_id: int,
        register_ref: str,
        *,
        reason: str | None = None,
        user_id: int | None = None,
    ) -> RegisterLicenseSnapshot:
        from app import db

        row = RegisterLicenseService.get_or_create(organization_id, register_ref)
        row.status = LICENSE_STATUS_SUSPENDED
        row.reason = (reason or 'suspended').strip() or 'suspended'
        row.updated_at = datetime.utcnow()
        if user_id is not None:
            row.activated_by_user_id = int(user_id)
        db.session.commit()
        _audit(
            int(organization_id),
            'license.suspended',
            {
                'register_ref': (register_ref or '').strip(),
                'license_id': f'lic_{row.id}',
                'reason': row.reason,
            },
        )
        return RegisterLicenseService.snapshot(organization_id, register_ref)

    @staticmethod
    def reactivate(
        organization_id: int,
        register_ref: str,
        *,
        user_id: int | None = None,
    ) -> RegisterLicenseSnapshot:
        from app import db

        row = RegisterLicenseService.get_or_create(organization_id, register_ref)
        now = datetime.utcnow()
        if row.license_type in (LICENSE_TYPE_UNLICENSED, LICENSE_TYPE_SUSPENDED, ''):
            row.license_type = LICENSE_TYPE_MONTHLY
        # Si ya venció sin grace → expired; si aún válida → active
        if row.expires_at is not None and row.expires_at < now:
            grace = getattr(row, 'grace_until', None)
            row.status = (
                LICENSE_STATUS_GRACE if grace is not None and grace >= now else LICENSE_STATUS_EXPIRED
            )
        else:
            row.status = LICENSE_STATUS_ACTIVE
        row.reason = None
        row.updated_at = now
        if user_id is not None:
            row.activated_by_user_id = int(user_id)
        db.session.commit()
        _audit(
            int(organization_id),
            'license.reactivated',
            {
                'register_ref': (register_ref or '').strip(),
                'license_id': f'lic_{row.id}',
                'status': row.status,
            },
        )
        return RegisterLicenseService.snapshot(organization_id, register_ref)

    @staticmethod
    def revoke(
        organization_id: int,
        register_ref: str,
        *,
        reason: str | None = None,
        user_id: int | None = None,
    ) -> RegisterLicenseSnapshot:
        from app import db

        row = RegisterLicenseService.get_or_create(organization_id, register_ref)
        row.status = LICENSE_STATUS_REVOKED
        row.reason = (reason or 'revoked').strip() or 'revoked'
        row.updated_at = datetime.utcnow()
        if user_id is not None:
            row.activated_by_user_id = int(user_id)
        db.session.commit()
        _audit(
            int(organization_id),
            'license.revoked',
            {
                'register_ref': (register_ref or '').strip(),
                'license_id': f'lic_{row.id}',
                'reason': row.reason,
            },
        )
        return RegisterLicenseService.snapshot(organization_id, register_ref)

    @staticmethod
    def extend(
        organization_id: int,
        register_ref: str,
        *,
        days: int,
        notes: str | None = None,
        user_id: int | None = None,
    ) -> RegisterLicenseSnapshot:
        from app import db

        row = RegisterLicenseService.get_or_create(organization_id, register_ref)
        now = datetime.utcnow()
        base = row.expires_at if row.expires_at and row.expires_at > now else now
        row.expires_at = base + timedelta(days=max(1, int(days)))
        grace_days = RegisterLicenseService._grace_days_for(
            str(row.license_type or ''), int(organization_id)
        )
        if grace_days is not None and grace_days > 0:
            row.grace_until = row.expires_at + timedelta(days=int(grace_days))
        if row.status in (
            LICENSE_STATUS_EXPIRED,
            LICENSE_STATUS_PENDING,
            LICENSE_STATUS_GRACE,
            LICENSE_STATUS_SUSPENDED,
        ):
            row.status = LICENSE_STATUS_ACTIVE
        if row.license_type == LICENSE_TYPE_UNLICENSED:
            row.license_type = LICENSE_TYPE_MONTHLY
        if notes:
            row.notes = ((row.notes or '') + ' | ' + notes.strip()).strip(' |')
        row.activated_by_user_id = int(user_id) if user_id is not None else row.activated_by_user_id
        row.updated_at = now
        db.session.commit()
        _audit(
            int(organization_id),
            'license.renewed',
            {
                'register_ref': (register_ref or '').strip(),
                'license_id': f'lic_{row.id}',
                'expires_at': row.expires_at.isoformat() if row.expires_at else None,
                'days': int(days),
            },
        )
        return RegisterLicenseService.snapshot(organization_id, register_ref)

    @staticmethod
    def map_for_registers(
        organization_id: int, register_refs: list[str]
    ) -> dict[str, RegisterLicenseSnapshot]:
        out: dict[str, RegisterLicenseSnapshot] = {}
        for ref in register_refs:
            out[ref] = RegisterLicenseService.snapshot(organization_id, ref)
        return out
