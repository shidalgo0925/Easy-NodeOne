"""Configuración operativa EPosOne — scaffold v1."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from models.eposone_settings import EposoneSettings
from nodeone.core.commerce.order import OrderValidationError

ALLOWED_CURRENCIES: frozenset[str] = frozenset({'USD', 'PAB', 'EUR'})


@dataclass(frozen=True)
class EposoneSettingsDTO:
    organization_id: int
    default_currency: str
    kds_auto_enqueue: bool
    delivery_auto_create: bool
    fiscal_on_payment: bool
    supervisor_approval_required: bool
    trial_days_default: int = 15
    trial_start_policy: str = 'on_first_provision'
    provisioning_code_ttl_minutes: int = 30
    offline_grace_days: int = 7

    def to_dict(self) -> dict[str, Any]:
        return {
            'organization_id': self.organization_id,
            'default_currency': self.default_currency,
            'kds_auto_enqueue': self.kds_auto_enqueue,
            'delivery_auto_create': self.delivery_auto_create,
            'fiscal_on_payment': self.fiscal_on_payment,
            'supervisor_approval_required': self.supervisor_approval_required,
            'trial_days_default': self.trial_days_default,
            'trial_start_policy': self.trial_start_policy,
            'provisioning_code_ttl_minutes': self.provisioning_code_ttl_minutes,
            'offline_grace_days': self.offline_grace_days,
        }


def _to_dto(row: EposoneSettings) -> EposoneSettingsDTO:
    return EposoneSettingsDTO(
        organization_id=int(row.organization_id),
        default_currency=str(row.default_currency or 'USD').upper(),
        kds_auto_enqueue=bool(row.kds_auto_enqueue),
        delivery_auto_create=bool(row.delivery_auto_create),
        fiscal_on_payment=bool(row.fiscal_on_payment),
        supervisor_approval_required=bool(row.supervisor_approval_required),
        trial_days_default=int(getattr(row, 'trial_days_default', 15) or 15),
        trial_start_policy=str(
            getattr(row, 'trial_start_policy', 'on_first_provision') or 'on_first_provision'
        ),
        provisioning_code_ttl_minutes=int(getattr(row, 'provisioning_code_ttl_minutes', 30) or 30),
        offline_grace_days=int(getattr(row, 'offline_grace_days', 7) or 7),
    )


def _default_row(organization_id: int) -> EposoneSettings:
    return EposoneSettings(organization_id=int(organization_id))


class EposoneSettingsService:
    @staticmethod
    def get_settings(organization_id: int) -> EposoneSettingsDTO:
        row = EposoneSettings.query.filter_by(organization_id=int(organization_id)).first()
        if row is None:
            oid = int(organization_id)
            return EposoneSettingsDTO(
                organization_id=oid,
                default_currency='USD',
                kds_auto_enqueue=True,
                delivery_auto_create=True,
                fiscal_on_payment=False,
                supervisor_approval_required=True,
                trial_days_default=15,
                trial_start_policy='on_first_provision',
                provisioning_code_ttl_minutes=30,
                offline_grace_days=7,
            )
        return _to_dto(row)

    @staticmethod
    def runtime_for(organization_id: int) -> EposoneSettingsDTO:
        """Configuración operativa efectiva (defaults si no hay fila en BD)."""
        return EposoneSettingsService.get_settings(int(organization_id))

    @staticmethod
    def get_or_create(organization_id: int) -> EposoneSettingsDTO:
        from app import db

        oid = int(organization_id)
        row = EposoneSettings.query.filter_by(organization_id=oid).first()
        if row is None:
            row = _default_row(oid)
            db.session.add(row)
            db.session.commit()
        return _to_dto(row)

    @staticmethod
    def update_settings(
        organization_id: int,
        *,
        default_currency: str | None = None,
        kds_auto_enqueue: bool | None = None,
        delivery_auto_create: bool | None = None,
        fiscal_on_payment: bool | None = None,
        supervisor_approval_required: bool | None = None,
    ) -> EposoneSettingsDTO:
        from app import db

        oid = int(organization_id)
        row = EposoneSettings.query.filter_by(organization_id=oid).first()
        if row is None:
            row = _default_row(oid)
            db.session.add(row)
        if default_currency is not None:
            currency = (default_currency or '').strip().upper()
            if currency not in ALLOWED_CURRENCIES:
                raise OrderValidationError('currency_invalid')
            row.default_currency = currency
        if kds_auto_enqueue is not None:
            row.kds_auto_enqueue = bool(kds_auto_enqueue)
        if delivery_auto_create is not None:
            row.delivery_auto_create = bool(delivery_auto_create)
        if fiscal_on_payment is not None:
            row.fiscal_on_payment = bool(fiscal_on_payment)
        if supervisor_approval_required is not None:
            row.supervisor_approval_required = bool(supervisor_approval_required)
        db.session.commit()
        return _to_dto(row)
