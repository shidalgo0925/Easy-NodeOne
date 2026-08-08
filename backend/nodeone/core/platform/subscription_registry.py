"""ADR-014 — Subscription Registry V1: ¿qué productos tiene habilitados este tenant?

Producto ≠ Suscripción ≠ Licencia.

  ProductRegistry   → catálogo ETS (qué existe)
  SubscriptionRegistry → organization_id + product_code + estado comercial
  License Engine    → autorización operativa (caja/dispositivo)

V1: una fila por (organization_id, product_code); el historial es transición de status
en la misma fila (no múltiples abiertas).

No copia metadatos del producto. No controla App Registry.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Sequence

from nodeone.core.platform.product_registry import ProductRegistry

# --- Estados (enum explícito; persistencia = value lowercase) ---


class SubscriptionStatus(str, Enum):
    PENDING = 'pending'
    TRIAL = 'trial'
    ACTIVE = 'active'
    PAST_DUE = 'past_due'
    SUSPENDED = 'suspended'
    CANCELLED = 'cancelled'
    EXPIRED = 'expired'


# Estados que cuentan como “habilitado comercialmente” para list_active / has_product
_ENTITLED_STATUSES = frozenset(
    {
        SubscriptionStatus.TRIAL.value,
        SubscriptionStatus.ACTIVE.value,
        SubscriptionStatus.PAST_DUE.value,
    }
)

_OPEN_FOR_CREATE = frozenset(
    {
        SubscriptionStatus.PENDING.value,
        SubscriptionStatus.TRIAL.value,
        SubscriptionStatus.ACTIVE.value,
        SubscriptionStatus.PAST_DUE.value,
        SubscriptionStatus.SUSPENDED.value,
    }
)


class SubscriptionError(Exception):
    """Error de negocio del Subscription Registry."""

    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


@dataclass(frozen=True)
class SubscriptionRecord:
    """Vista inmutable de una suscripción (contrato estable)."""

    id: int
    organization_id: int
    product_code: str
    status: str
    starts_at: datetime | None
    ends_at: datetime | None
    trial_ends_at: datetime | None
    reason: str | None
    metadata: dict[str, Any]
    created_at: datetime | None
    updated_at: datetime | None
    created_by_user_id: int | None
    updated_by_user_id: int | None

    @property
    def is_entitled(self) -> bool:
        return self.status in _ENTITLED_STATUSES

    def to_dict(self) -> dict[str, Any]:
        return {
            'id': self.id,
            'organization_id': self.organization_id,
            'product_code': self.product_code,
            'status': self.status,
            'starts_at': self.starts_at.isoformat() + 'Z' if self.starts_at else None,
            'ends_at': self.ends_at.isoformat() + 'Z' if self.ends_at else None,
            'trial_ends_at': self.trial_ends_at.isoformat() + 'Z' if self.trial_ends_at else None,
            'reason': self.reason,
            'metadata': dict(self.metadata),
            'created_at': self.created_at.isoformat() + 'Z' if self.created_at else None,
            'updated_at': self.updated_at.isoformat() + 'Z' if self.updated_at else None,
            'created_by_user_id': self.created_by_user_id,
            'updated_by_user_id': self.updated_by_user_id,
            'is_entitled': self.is_entitled,
        }


def _now() -> datetime:
    return datetime.utcnow()


def _parse_metadata(raw: str | None) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}


def _dump_metadata(data: dict[str, Any] | None) -> str | None:
    if not data:
        return None
    return json.dumps(data, ensure_ascii=False, sort_keys=True)


def _row_to_record(row) -> SubscriptionRecord:
    return SubscriptionRecord(
        id=int(row.id),
        organization_id=int(row.organization_id),
        product_code=str(row.product_code),
        status=str(row.status),
        starts_at=row.starts_at,
        ends_at=row.ends_at,
        trial_ends_at=row.trial_ends_at,
        reason=row.reason,
        metadata=_parse_metadata(row.metadata_json),
        created_at=row.created_at,
        updated_at=row.updated_at,
        created_by_user_id=row.created_by_user_id,
        updated_by_user_id=row.updated_by_user_id,
    )


def _norm_product(code: str | None) -> str:
    return (code or '').strip().lower()


def _norm_org(organization_id: int | None) -> int:
    try:
        oid = int(organization_id)
    except (TypeError, ValueError):
        raise SubscriptionError('invalid_organization', 'organization_id inválido') from None
    if oid < 1:
        raise SubscriptionError('invalid_organization', 'organization_id inválido')
    return oid


def _require_product(product_code: str) -> str:
    code = _norm_product(product_code)
    if not code:
        raise SubscriptionError('invalid_product', 'product_code vacío')
    if ProductRegistry.get(code) is None:
        raise SubscriptionError('unknown_product', f'Producto no registrado: {code}')
    # Plataforma/portal no se “contratan” como productos de marketplace
    definition = ProductRegistry.get(code)
    if definition and definition.surface == 'platform':
        raise SubscriptionError('not_subscribable', f'El producto {code} no es suscribible')
    return code


def _assert_org_exists(organization_id: int) -> None:
    from models.saas import SaasOrganization

    org = SaasOrganization.query.get(organization_id)
    if org is None:
        raise SubscriptionError('unknown_organization', f'Organización no encontrada: {organization_id}')


def _assert_tenant_scope(organization_id: int, *, expected_organization_id: int | None) -> None:
    """Aislamiento: si el caller declara un scope, debe coincidir."""
    if expected_organization_id is None:
        return
    if int(expected_organization_id) != int(organization_id):
        raise SubscriptionError('tenant_isolation', 'No se puede acceder a suscripciones de otro tenant')


def _audit(organization_id: int, event_type: str, payload: dict[str, Any]) -> None:
    try:
        from nodeone.core.services.audit import AuditService

        AuditService.publish_domain_event(
            int(organization_id),
            event_type,
            payload,
            source_app_id='platform',
        )
        AuditService.log_system_action(
            event_type,
            organization_id=int(organization_id),
            context=payload,
        )
    except Exception:
        pass


def _sync_licenses_minimal(
    organization_id: int,
    product_code: str,
    *,
    action: str,
    reason: str | None,
) -> None:
    """Integración unidireccional mínima con License Engine (solo eposone).

    No duplica grace/heartbeat/offline. Solo propaga suspend comercial a cajas
    cuando la suscripción del producto eposone se suspende o cancela.
    """
    if product_code != 'eposone':
        return
    if action not in ('suspend', 'cancel'):
        return
    try:
        from models.eposone_register_license import EposoneRegisterLicense
        from nodeone.modules.eposone.register_license_service import (
            LICENSE_STATUS_SUSPENDED,
            RegisterLicenseService,
        )

        rows = EposoneRegisterLicense.query.filter_by(organization_id=int(organization_id)).all()
        skip = {
            LICENSE_STATUS_SUSPENDED,
            'revoked',
            'cancelled',
            'expired',
        }
        for row in rows:
            if str(row.status) in skip:
                continue
            RegisterLicenseService.suspend(
                int(organization_id),
                str(row.register_ref),
                reason=reason or f'subscription_{action}',
            )
    except Exception:
        # No tumbar la suscripción si la capa de licencia falla
        pass


class SubscriptionRegistry:
    """API estable del Subscription Registry (V1)."""

    @classmethod
    def get(cls, subscription_id: int) -> SubscriptionRecord | None:
        from models.ets_product_subscription import EtsProductSubscription

        try:
            sid = int(subscription_id)
        except (TypeError, ValueError):
            return None
        row = EtsProductSubscription.query.get(sid)
        return _row_to_record(row) if row else None

    @classmethod
    def get_for_tenant_product(
        cls,
        organization_id: int,
        product_code: str,
        *,
        scope_organization_id: int | None = None,
    ) -> SubscriptionRecord | None:
        from models.ets_product_subscription import EtsProductSubscription

        oid = _norm_org(organization_id)
        _assert_tenant_scope(oid, expected_organization_id=scope_organization_id)
        code = _norm_product(product_code)
        row = EtsProductSubscription.query.filter_by(organization_id=oid, product_code=code).first()
        return _row_to_record(row) if row else None

    @classmethod
    def list_for_tenant(
        cls,
        organization_id: int,
        *,
        scope_organization_id: int | None = None,
    ) -> Sequence[SubscriptionRecord]:
        from models.ets_product_subscription import EtsProductSubscription

        oid = _norm_org(organization_id)
        _assert_tenant_scope(oid, expected_organization_id=scope_organization_id)
        rows = (
            EtsProductSubscription.query.filter_by(organization_id=oid)
            .order_by(EtsProductSubscription.product_code.asc())
            .all()
        )
        return tuple(_row_to_record(r) for r in rows)

    @classmethod
    def list_active_for_tenant(
        cls,
        organization_id: int,
        *,
        scope_organization_id: int | None = None,
    ) -> Sequence[SubscriptionRecord]:
        return tuple(
            r
            for r in cls.list_for_tenant(organization_id, scope_organization_id=scope_organization_id)
            if r.is_entitled
        )

    @classmethod
    def has_product(
        cls,
        organization_id: int,
        product_code: str,
        *,
        scope_organization_id: int | None = None,
    ) -> bool:
        rec = cls.get_for_tenant_product(
            organization_id, product_code, scope_organization_id=scope_organization_id
        )
        return bool(rec and rec.is_entitled)

    @classmethod
    def create_trial(
        cls,
        organization_id: int,
        product_code: str,
        trial_ends_at: datetime,
        *,
        starts_at: datetime | None = None,
        user_id: int | None = None,
        metadata: dict[str, Any] | None = None,
        scope_organization_id: int | None = None,
        sync_licenses: bool = False,
        customer_id: int | None = None,
    ) -> SubscriptionRecord:
        """Crea/reabre suscripción en TRIAL. El Trial lo origina EN1 (no la APK)."""
        from app import db
        from models.ets_product_subscription import EtsProductSubscription

        oid = _norm_org(organization_id)
        _assert_tenant_scope(oid, expected_organization_id=scope_organization_id)
        _assert_org_exists(oid)
        code = _require_product(product_code)
        if trial_ends_at is None:
            raise SubscriptionError('invalid_trial', 'trial_ends_at requerido')

        now = _now()
        start = starts_at or now
        cid = int(customer_id) if customer_id else None
        if cid:
            row = EtsProductSubscription.query.filter_by(customer_id=cid, product_code=code).first()
        else:
            row = EtsProductSubscription.query.filter_by(
                organization_id=oid, product_code=code, customer_id=None
            ).first()
            if row is None:
                row = (
                    EtsProductSubscription.query.filter_by(organization_id=oid, product_code=code)
                    .filter(EtsProductSubscription.customer_id.is_(None))
                    .first()
                )
        if row is not None and str(row.status) in _OPEN_FOR_CREATE and str(row.status) != SubscriptionStatus.SUSPENDED.value:
            if str(row.status) in (
                SubscriptionStatus.TRIAL.value,
                SubscriptionStatus.ACTIVE.value,
                SubscriptionStatus.PAST_DUE.value,
                SubscriptionStatus.PENDING.value,
            ):
                raise SubscriptionError(
                    'duplicate_active',
                    f'Ya existe suscripción vigente {row.status} para {code}',
                )

        created = False
        if row is None:
            row = EtsProductSubscription(
                organization_id=oid,
                customer_id=cid,
                product_code=code,
                status=SubscriptionStatus.TRIAL.value,
                starts_at=start,
                ends_at=None,
                trial_ends_at=trial_ends_at,
                reason=None,
                metadata_json=_dump_metadata(metadata),
                created_by_user_id=user_id,
                updated_by_user_id=user_id,
                created_at=now,
                updated_at=now,
            )
            db.session.add(row)
            created = True
        else:
            row.status = SubscriptionStatus.TRIAL.value
            row.starts_at = start
            row.ends_at = None
            row.trial_ends_at = trial_ends_at
            row.reason = None
            if cid:
                row.customer_id = cid
            if metadata is not None:
                row.metadata_json = _dump_metadata(metadata)
            row.updated_by_user_id = user_id
            row.updated_at = now

        db.session.commit()
        rec = _row_to_record(row)
        _audit(
            oid,
            'subscription.created' if created else 'subscription.trial_started',
            {
                'subscription_id': rec.id,
                'product_code': code,
                'status': rec.status,
                'customer_id': cid,
            },
        )
        if not created:
            _audit(
                oid,
                'subscription.trial_started',
                {
                    'subscription_id': rec.id,
                    'product_code': code,
                    'trial_ends_at': trial_ends_at.isoformat(),
                    'customer_id': cid,
                },
            )
        return rec

    @classmethod
    def activate(
        cls,
        organization_id: int,
        product_code: str,
        *,
        ends_at: datetime | None = None,
        user_id: int | None = None,
        scope_organization_id: int | None = None,
    ) -> SubscriptionRecord:
        from app import db
        from models.ets_product_subscription import EtsProductSubscription

        oid = _norm_org(organization_id)
        _assert_tenant_scope(oid, expected_organization_id=scope_organization_id)
        _assert_org_exists(oid)
        code = _require_product(product_code)
        now = _now()
        row = EtsProductSubscription.query.filter_by(organization_id=oid, product_code=code).first()
        if row is None:
            row = EtsProductSubscription(
                organization_id=oid,
                product_code=code,
                status=SubscriptionStatus.ACTIVE.value,
                starts_at=now,
                ends_at=ends_at,
                trial_ends_at=None,
                created_by_user_id=user_id,
                updated_by_user_id=user_id,
                created_at=now,
                updated_at=now,
            )
            db.session.add(row)
            event = 'subscription.created'
        else:
            if str(row.status) == SubscriptionStatus.CANCELLED.value:
                row.starts_at = now
            row.status = SubscriptionStatus.ACTIVE.value
            row.ends_at = ends_at
            row.reason = None
            row.updated_by_user_id = user_id
            row.updated_at = now
            event = 'subscription.activated'
        db.session.commit()
        rec = _row_to_record(row)
        _audit(oid, event, {'subscription_id': rec.id, 'product_code': code, 'status': rec.status})
        if event == 'subscription.created':
            _audit(oid, 'subscription.activated', {'subscription_id': rec.id, 'product_code': code})
        return rec

    @classmethod
    def suspend(
        cls,
        organization_id: int,
        product_code: str,
        *,
        reason: str | None = None,
        user_id: int | None = None,
        scope_organization_id: int | None = None,
        sync_licenses: bool = True,
    ) -> SubscriptionRecord:
        from app import db
        from models.ets_product_subscription import EtsProductSubscription

        oid = _norm_org(organization_id)
        _assert_tenant_scope(oid, expected_organization_id=scope_organization_id)
        code = _require_product(product_code)
        row = EtsProductSubscription.query.filter_by(organization_id=oid, product_code=code).first()
        if row is None:
            raise SubscriptionError('not_found', f'Sin suscripción para {code}')
        row.status = SubscriptionStatus.SUSPENDED.value
        row.reason = (reason or 'suspended').strip() or 'suspended'
        row.updated_by_user_id = user_id
        row.updated_at = _now()
        db.session.commit()
        rec = _row_to_record(row)
        _audit(
            oid,
            'subscription.suspended',
            {'subscription_id': rec.id, 'product_code': code, 'reason': rec.reason},
        )
        if sync_licenses:
            _sync_licenses_minimal(oid, code, action='suspend', reason=rec.reason)
        return rec

    @classmethod
    def cancel(
        cls,
        organization_id: int,
        product_code: str,
        *,
        reason: str | None = None,
        user_id: int | None = None,
        scope_organization_id: int | None = None,
        sync_licenses: bool = True,
    ) -> SubscriptionRecord:
        from app import db
        from models.ets_product_subscription import EtsProductSubscription

        oid = _norm_org(organization_id)
        _assert_tenant_scope(oid, expected_organization_id=scope_organization_id)
        code = _require_product(product_code)
        row = EtsProductSubscription.query.filter_by(organization_id=oid, product_code=code).first()
        if row is None:
            raise SubscriptionError('not_found', f'Sin suscripción para {code}')
        now = _now()
        row.status = SubscriptionStatus.CANCELLED.value
        row.ends_at = now
        row.reason = (reason or 'cancelled').strip() or 'cancelled'
        row.updated_by_user_id = user_id
        row.updated_at = now
        db.session.commit()
        rec = _row_to_record(row)
        _audit(
            oid,
            'subscription.cancelled',
            {'subscription_id': rec.id, 'product_code': code, 'reason': rec.reason},
        )
        if sync_licenses:
            _sync_licenses_minimal(oid, code, action='cancel', reason=rec.reason)
        return rec

    @classmethod
    def mark_expired(
        cls,
        organization_id: int,
        product_code: str,
        *,
        user_id: int | None = None,
        scope_organization_id: int | None = None,
    ) -> SubscriptionRecord:
        from app import db
        from models.ets_product_subscription import EtsProductSubscription

        oid = _norm_org(organization_id)
        _assert_tenant_scope(oid, expected_organization_id=scope_organization_id)
        code = _require_product(product_code)
        row = EtsProductSubscription.query.filter_by(organization_id=oid, product_code=code).first()
        if row is None:
            raise SubscriptionError('not_found', f'Sin suscripción para {code}')
        now = _now()
        row.status = SubscriptionStatus.EXPIRED.value
        row.ends_at = row.ends_at or now
        row.updated_by_user_id = user_id
        row.updated_at = now
        db.session.commit()
        rec = _row_to_record(row)
        _audit(oid, 'subscription.expired', {'subscription_id': rec.id, 'product_code': code})
        return rec

    @classmethod
    def list_tenant_products(
        cls,
        organization_id: int,
        *,
        scope_organization_id: int | None = None,
        entitled_only: bool = False,
    ) -> list[dict[str, Any]]:
        """DTO para Portal ETS «Mis productos» (suscripción + catálogo, sin duplicar producto en BD)."""
        rows = cls.list_for_tenant(organization_id, scope_organization_id=scope_organization_id)
        if entitled_only:
            rows = tuple(r for r in rows if r.is_entitled)
        out: list[dict[str, Any]] = []
        for rec in rows:
            definition = ProductRegistry.get(rec.product_code)
            product_payload = None
            if definition is not None:
                product_payload = {
                    'name': definition.name,
                    'primary_domain': definition.primary_domain,
                    'icon': definition.icon,
                    'surface': definition.surface,
                    'status': definition.status,
                }
            out.append(
                {
                    'product_code': rec.product_code,
                    'subscription_status': rec.status,
                    'starts_at': rec.starts_at.isoformat() + 'Z' if rec.starts_at else None,
                    'ends_at': rec.ends_at.isoformat() + 'Z' if rec.ends_at else None,
                    'trial_ends_at': rec.trial_ends_at.isoformat() + 'Z' if rec.trial_ends_at else None,
                    'is_entitled': rec.is_entitled,
                    'product': product_payload,
                }
            )
        return out
