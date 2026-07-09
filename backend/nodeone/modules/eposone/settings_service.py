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

    def to_dict(self) -> dict[str, Any]:
        return {
            'organization_id': self.organization_id,
            'default_currency': self.default_currency,
            'kds_auto_enqueue': self.kds_auto_enqueue,
            'delivery_auto_create': self.delivery_auto_create,
            'fiscal_on_payment': self.fiscal_on_payment,
            'supervisor_approval_required': self.supervisor_approval_required,
        }


def _to_dto(row: EposoneSettings) -> EposoneSettingsDTO:
    return EposoneSettingsDTO(
        organization_id=int(row.organization_id),
        default_currency=str(row.default_currency or 'USD').upper(),
        kds_auto_enqueue=bool(row.kds_auto_enqueue),
        delivery_auto_create=bool(row.delivery_auto_create),
        fiscal_on_payment=bool(row.fiscal_on_payment),
        supervisor_approval_required=bool(row.supervisor_approval_required),
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
            )
        return _to_dto(row)

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
