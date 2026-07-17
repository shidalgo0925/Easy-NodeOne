"""Licencia comercial por Caja — independiente del provisioning de dispositivos."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from models.eposone_register_license import EposoneRegisterLicense

LICENSE_TYPE_UNLICENSED = 'unlicensed'
LICENSE_TYPE_TRIAL = 'trial'
LICENSE_TYPE_SUBSCRIPTION = 'subscription'
LICENSE_TYPE_COURTESY = 'courtesy'
LICENSE_TYPE_PROMOTION = 'promotion'
LICENSE_TYPE_DEMO = 'demo'
LICENSE_TYPE_PERPETUAL = 'perpetual'
LICENSE_TYPE_SUSPENDED = 'suspended'

LICENSE_STATUS_PENDING = 'pending'
LICENSE_STATUS_ACTIVE = 'active'
LICENSE_STATUS_EXPIRED = 'expired'
LICENSE_STATUS_SUSPENDED = 'suspended'
LICENSE_STATUS_CANCELLED = 'cancelled'

# Política de inicio de trial (org)
TRIAL_START_ON_CREATE = 'on_create'
TRIAL_START_ON_ACTIVATE = 'on_activate'
TRIAL_START_ON_FIRST_PROVISION = 'on_first_provision'

COMMERCIAL_UI = {
    'unlicensed': 'Sin licencia',
    'trial': 'Trial',
    'active': 'Activa',
    'courtesy': 'Cortesía',
    'promotion': 'Promoción',
    'demo': 'Demo',
    'perpetual': 'Permanente',
    'expired': 'Vencida',
    'suspended': 'Suspendida',
    'pending': 'Pendiente',
}


@dataclass(frozen=True)
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

    def to_device_payload(self) -> dict[str, Any]:
        return {
            'status': self.commercial_ui_key(),
            'plan': self.plan_code,
            'license_type': self.license_type,
            'starts_at': self.starts_at.isoformat(sep='T', timespec='seconds') if self.starts_at else None,
            'expires_at': self.expires_at.isoformat(sep='T', timespec='seconds') if self.expires_at else None,
            'days_remaining': self.days_remaining,
            'can_operate': self.can_operate,
            'reason': self.reason,
            'trial_used': self.trial_used,
        }

    def commercial_ui_key(self) -> str:
        if self.status == LICENSE_STATUS_SUSPENDED or self.license_type == LICENSE_TYPE_SUSPENDED:
            return 'suspended'
        if self.status == LICENSE_STATUS_EXPIRED or (
            self.expires_at is not None and self.expires_at < datetime.utcnow() and self.license_type != LICENSE_TYPE_PERPETUAL
        ):
            return 'expired'
        if self.license_type in (
            LICENSE_TYPE_UNLICENSED,
            '',
        ) or self.status == LICENSE_STATUS_PENDING:
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
        if self.license_type == LICENSE_TYPE_SUBSCRIPTION and self.status == LICENSE_STATUS_ACTIVE:
            return 'active'
        return self.license_type or 'unlicensed'


class RegisterLicenseService:
    @staticmethod
    def _policy(organization_id: int) -> dict[str, Any]:
        from nodeone.modules.eposone.settings_service import EposoneSettingsService

        s = EposoneSettingsService.runtime_for(int(organization_id))
        return {
            'trial_days_default': int(getattr(s, 'trial_days_default', 45) or 45),
            'trial_start_policy': str(
                getattr(s, 'trial_start_policy', TRIAL_START_ON_FIRST_PROVISION)
                or TRIAL_START_ON_FIRST_PROVISION
            ),
            'provisioning_code_ttl_minutes': int(getattr(s, 'provisioning_code_ttl_minutes', 30) or 30),
            'offline_grace_days': int(getattr(s, 'offline_grace_days', 7) or 7),
        }

    @staticmethod
    def get_or_create(organization_id: int, register_ref: str) -> EposoneRegisterLicense:
        from app import db

        oid = int(organization_id)
        ref = (register_ref or '').strip()
        row = EposoneRegisterLicense.query.filter_by(organization_id=oid, register_ref=ref).first()
        if row is None:
            row = EposoneRegisterLicense(
                organization_id=oid,
                register_ref=ref,
                license_type=LICENSE_TYPE_UNLICENSED,
                status=LICENSE_STATUS_PENDING,
            )
            db.session.add(row)
            db.session.flush()
        return row

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
            )

        now = datetime.utcnow()
        expires = row.expires_at
        status = str(row.status or LICENSE_STATUS_PENDING)
        ltype = str(row.license_type or LICENSE_TYPE_UNLICENSED)

        if ltype == LICENSE_TYPE_PERPETUAL and status == LICENSE_STATUS_ACTIVE:
            can = True
            days = None
            reason = None
        elif status == LICENSE_STATUS_SUSPENDED or ltype == LICENSE_TYPE_SUSPENDED:
            can = False
            days = None
            reason = 'suspended'
        elif ltype == LICENSE_TYPE_UNLICENSED or status == LICENSE_STATUS_PENDING:
            can = False
            days = None
            reason = 'unlicensed'
        elif expires is not None and expires < now:
            can = False
            days = 0
            reason = 'expired'
            if status == LICENSE_STATUS_ACTIVE:
                status = LICENSE_STATUS_EXPIRED
        else:
            can = status == LICENSE_STATUS_ACTIVE
            if expires is not None:
                days = max(0, (expires.date() - now.date()).days)
            else:
                days = None
            reason = None if can else status

        ui_key = RegisterLicenseSnapshot(
            register_ref=ref,
            license_type=ltype,
            status=status,
            plan_code=str(row.plan_code or 'eposone'),
            starts_at=row.starts_at,
            expires_at=expires,
            trial_used=bool(row.trial_used),
            days_remaining=days,
            can_operate=can,
            commercial_ui='',
            reason=reason,
        ).commercial_ui_key()

        return RegisterLicenseSnapshot(
            register_ref=ref,
            license_type=ltype,
            status=status,
            plan_code=str(row.plan_code or 'eposone'),
            starts_at=row.starts_at,
            expires_at=expires,
            trial_used=bool(row.trial_used),
            days_remaining=days,
            can_operate=can,
            commercial_ui=COMMERCIAL_UI.get(ui_key, ui_key),
            reason=reason,
        )

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
    ) -> RegisterLicenseSnapshot:
        from app import db

        row = RegisterLicenseService.get_or_create(organization_id, register_ref)
        now = starts_at or datetime.utcnow()
        ltype = (license_type or LICENSE_TYPE_SUBSCRIPTION).strip().lower()
        row.license_type = ltype
        row.status = LICENSE_STATUS_ACTIVE
        row.plan_code = (plan_code or 'eposone').strip() or 'eposone'
        row.starts_at = now
        row.notes = (notes or '').strip() or None
        row.reason = (reason or '').strip() or None
        row.activated_by_user_id = int(user_id) if user_id is not None else None

        if ltype == LICENSE_TYPE_PERPETUAL:
            row.expires_at = None
        elif expires_at is not None:
            row.expires_at = expires_at
        elif duration_days is not None:
            row.expires_at = now + timedelta(days=max(0, int(duration_days)))
        elif ltype == LICENSE_TYPE_COURTESY:
            row.expires_at = None  # cortesía abierta hasta que admin fije vencimiento
        else:
            policy = RegisterLicenseService._policy(organization_id)
            row.expires_at = now + timedelta(days=int(policy['trial_days_default']))

        if ltype == LICENSE_TYPE_TRIAL or mark_trial_used:
            row.trial_used = True
            row.trial_started_at = row.trial_started_at or now
            row.trial_expires_at = row.expires_at

        db.session.commit()
        return RegisterLicenseService.snapshot(organization_id, register_ref)

    @staticmethod
    def start_trial_if_eligible(organization_id: int, register_ref: str, *, user_id: int | None = None) -> RegisterLicenseSnapshot | None:
        """Inicia trial solo si la política lo permite y la caja no usó trial."""
        policy = RegisterLicenseService._policy(organization_id)
        row = RegisterLicenseService.get_or_create(organization_id, register_ref)
        if row.trial_used:
            return None
        if str(row.license_type) not in (LICENSE_TYPE_UNLICENSED, LICENSE_TYPE_TRIAL, ''):
            if row.status == LICENSE_STATUS_ACTIVE:
                return None
        days = int(policy['trial_days_default'])
        if days <= 0:
            return None
        return RegisterLicenseService.activate(
            organization_id,
            register_ref,
            license_type=LICENSE_TYPE_TRIAL,
            duration_days=days,
            reason='trial_auto',
            user_id=user_id,
            mark_trial_used=True,
        )

    @staticmethod
    def on_first_device_provisioned(organization_id: int, register_ref: str) -> None:
        policy = RegisterLicenseService._policy(organization_id)
        if policy['trial_start_policy'] != TRIAL_START_ON_FIRST_PROVISION:
            return
        RegisterLicenseService.start_trial_if_eligible(organization_id, register_ref)

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
        if row.status in (LICENSE_STATUS_EXPIRED, LICENSE_STATUS_PENDING):
            row.status = LICENSE_STATUS_ACTIVE
        if row.license_type == LICENSE_TYPE_UNLICENSED:
            row.license_type = LICENSE_TYPE_SUBSCRIPTION
        if notes:
            row.notes = ((row.notes or '') + ' | ' + notes.strip()).strip(' |')
        row.activated_by_user_id = int(user_id) if user_id is not None else row.activated_by_user_id
        db.session.commit()
        return RegisterLicenseService.snapshot(organization_id, register_ref)

    @staticmethod
    def map_for_registers(organization_id: int, register_refs: list[str]) -> dict[str, RegisterLicenseSnapshot]:
        out: dict[str, RegisterLicenseSnapshot] = {}
        for ref in register_refs:
            out[ref] = RegisterLicenseService.snapshot(organization_id, ref)
        return out
