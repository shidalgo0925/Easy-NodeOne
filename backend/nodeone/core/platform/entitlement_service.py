"""ADR-016 — Entitlement Engine V1: ¿qué puede hacer este tenant con este producto?

  ProductRegistry        → qué productos existen
  SubscriptionRegistry   → qué productos tiene el tenant (ADR-014)
  EntitlementService     → cupos, features y excepciones comerciales (este módulo)

Los recursos consumen capacidad; nunca poseen derechos.
Paso 1: modelo + servicio + hooks. Enforcement (gating) = Paso 2.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from nodeone.core.platform.entitlement_plans import (
    get_plan_template,
    merge_limits_with_overrides,
    normalize_plan_code,
)
from nodeone.core.platform.subscription_registry import SubscriptionRegistry, SubscriptionStatus


class EntitlementEffectiveState(str, Enum):
    TRIAL = 'trial'
    ACTIVE = 'active'
    PAST_DUE = 'past_due'
    GRACE = 'grace'
    SUSPENDED = 'suspended'
    CANCELLED = 'cancelled'
    EXPIRED = 'expired'


_OPERABLE_STATES = frozenset(
    {
        EntitlementEffectiveState.TRIAL.value,
        EntitlementEffectiveState.ACTIVE.value,
        EntitlementEffectiveState.PAST_DUE.value,
        EntitlementEffectiveState.GRACE.value,
    }
)

_SUB_TO_EFFECTIVE = {
    SubscriptionStatus.TRIAL.value: EntitlementEffectiveState.TRIAL.value,
    SubscriptionStatus.ACTIVE.value: EntitlementEffectiveState.ACTIVE.value,
    SubscriptionStatus.PAST_DUE.value: EntitlementEffectiveState.PAST_DUE.value,
    SubscriptionStatus.SUSPENDED.value: EntitlementEffectiveState.SUSPENDED.value,
    SubscriptionStatus.CANCELLED.value: EntitlementEffectiveState.CANCELLED.value,
    SubscriptionStatus.EXPIRED.value: EntitlementEffectiveState.EXPIRED.value,
    SubscriptionStatus.PENDING.value: EntitlementEffectiveState.TRIAL.value,
}


class EntitlementError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


@dataclass(frozen=True)
class EntitlementRecord:
    id: int
    subscription_id: int
    organization_id: int
    product_code: str
    plan_code: str
    resource_limits: dict[str, Any]
    features: dict[str, Any]
    overrides: dict[str, Any]
    effective_limits: dict[str, Any]
    effective_state: str
    starts_at: datetime | None
    ends_at: datetime | None
    created_at: datetime | None
    updated_at: datetime | None
    updated_by_user_id: int | None

    @property
    def is_operable(self) -> bool:
        return self.effective_state in _OPERABLE_STATES

    def to_dict(self) -> dict[str, Any]:
        return {
            'id': self.id,
            'subscription_id': self.subscription_id,
            'organization_id': self.organization_id,
            'product_code': self.product_code,
            'plan_code': self.plan_code,
            'resource_limits': dict(self.resource_limits),
            'features': dict(self.features),
            'overrides': dict(self.overrides),
            'effective_limits': dict(self.effective_limits),
            'effective_state': self.effective_state,
            'starts_at': self.starts_at.isoformat() + 'Z' if self.starts_at else None,
            'ends_at': self.ends_at.isoformat() + 'Z' if self.ends_at else None,
            'created_at': self.created_at.isoformat() + 'Z' if self.created_at else None,
            'updated_at': self.updated_at.isoformat() + 'Z' if self.updated_at else None,
            'updated_by_user_id': self.updated_by_user_id,
            'is_operable': self.is_operable,
        }


def _now() -> datetime:
    return datetime.utcnow()


def _parse_json(raw: str | None) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}


def _dump_json(data: dict[str, Any] | None) -> str | None:
    if not data:
        return None
    return json.dumps(data, ensure_ascii=False, sort_keys=True)


def _norm_org(organization_id: int | None) -> int:
    try:
        oid = int(organization_id)
    except (TypeError, ValueError):
        raise EntitlementError('invalid_organization', 'organization_id inválido') from None
    if oid < 1:
        raise EntitlementError('invalid_organization', 'organization_id inválido')
    return oid


def _norm_product(product_code: str | None) -> str:
    code = (product_code or '').strip().lower()
    if not code:
        raise EntitlementError('invalid_product', 'product_code vacío')
    return code


def _assert_tenant_scope(organization_id: int, *, expected_organization_id: int | None) -> None:
    if expected_organization_id is None:
        return
    if int(expected_organization_id) != int(organization_id):
        raise EntitlementError('tenant_isolation', 'No se puede acceder a entitlements de otro tenant')


def effective_state_from_subscription(status: str) -> str:
    return _SUB_TO_EFFECTIVE.get((status or '').strip().lower(), EntitlementEffectiveState.SUSPENDED.value)


def _row_to_record(row) -> EntitlementRecord:
    limits = _parse_json(row.resource_limits_json)
    features = _parse_json(row.features_json)
    overrides = _parse_json(row.overrides_json)
    return EntitlementRecord(
        id=int(row.id),
        subscription_id=int(row.subscription_id),
        organization_id=int(row.organization_id),
        product_code=str(row.product_code),
        plan_code=str(row.plan_code),
        resource_limits=limits,
        features=features,
        overrides=overrides,
        effective_limits=merge_limits_with_overrides(limits, overrides),
        effective_state=str(row.effective_state),
        starts_at=row.starts_at,
        ends_at=row.ends_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
        updated_by_user_id=row.updated_by_user_id,
    )


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
            details=payload,
        )
    except Exception:
        pass


class EntitlementService:
    """API estable del Entitlement Engine (Paso 1)."""

    @classmethod
    def get(cls, entitlement_id: int) -> EntitlementRecord | None:
        from models.ets_product_entitlement import EtsProductEntitlement

        row = EtsProductEntitlement.query.get(int(entitlement_id))
        return _row_to_record(row) if row else None

    @classmethod
    def get_for_tenant_product(
        cls,
        organization_id: int,
        product_code: str,
        *,
        scope_organization_id: int | None = None,
    ) -> EntitlementRecord | None:
        from models.ets_product_entitlement import EtsProductEntitlement

        oid = _norm_org(organization_id)
        code = _norm_product(product_code)
        _assert_tenant_scope(oid, expected_organization_id=scope_organization_id)
        row = EtsProductEntitlement.query.filter_by(
            organization_id=oid, product_code=code
        ).first()
        return _row_to_record(row) if row else None

    @classmethod
    def get_by_subscription(cls, subscription_id: int) -> EntitlementRecord | None:
        from models.ets_product_entitlement import EtsProductEntitlement

        row = EtsProductEntitlement.query.filter_by(subscription_id=int(subscription_id)).first()
        return _row_to_record(row) if row else None

    @classmethod
    def list_for_tenant(
        cls,
        organization_id: int,
        *,
        scope_organization_id: int | None = None,
    ) -> list[EntitlementRecord]:
        from models.ets_product_entitlement import EtsProductEntitlement

        oid = _norm_org(organization_id)
        _assert_tenant_scope(oid, expected_organization_id=scope_organization_id)
        rows = (
            EtsProductEntitlement.query.filter_by(organization_id=oid)
            .order_by(EtsProductEntitlement.product_code.asc())
            .all()
        )
        return [_row_to_record(r) for r in rows]

    @classmethod
    def create_from_subscription(
        cls,
        organization_id: int,
        product_code: str,
        *,
        plan_code: str = 'starter',
        overrides: dict[str, Any] | None = None,
        user_id: int | None = None,
        scope_organization_id: int | None = None,
    ) -> EntitlementRecord:
        """Crea entitlement a partir de la suscripción existente (ADR-014)."""
        from models.ets_product_entitlement import EtsProductEntitlement
        from nodeone.core.db import db

        oid = _norm_org(organization_id)
        code = _norm_product(product_code)
        _assert_tenant_scope(oid, expected_organization_id=scope_organization_id)

        sub = SubscriptionRegistry.get_for_tenant_product(
            oid, code, scope_organization_id=scope_organization_id
        )
        if sub is None:
            raise EntitlementError(
                'subscription_required',
                f'No hay suscripción {code} para org {oid}',
            )

        existing = EtsProductEntitlement.query.filter_by(
            organization_id=oid, product_code=code
        ).first()
        if existing is not None:
            raise EntitlementError('duplicate_entitlement', 'Ya existe entitlement para este producto')

        plan = normalize_plan_code(plan_code)
        template = get_plan_template(code, plan)
        now = _now()
        row = EtsProductEntitlement(
            subscription_id=sub.id,
            organization_id=oid,
            product_code=code,
            plan_code=plan,
            resource_limits_json=_dump_json(template.get('resource_limits') or {}),
            features_json=_dump_json(template.get('features') or {}),
            overrides_json=_dump_json(overrides or {}),
            effective_state=effective_state_from_subscription(sub.status),
            starts_at=sub.starts_at or now,
            ends_at=sub.ends_at,
            updated_by_user_id=user_id,
            created_at=now,
            updated_at=now,
        )
        db.session.add(row)
        db.session.commit()
        rec = _row_to_record(row)
        _audit(
            oid,
            'entitlement.created',
            {
                'entitlement_id': rec.id,
                'subscription_id': rec.subscription_id,
                'product_code': code,
                'plan_code': plan,
            },
        )
        return rec

    @classmethod
    def ensure_for_subscription(
        cls,
        organization_id: int,
        product_code: str,
        *,
        plan_code: str = 'starter',
        user_id: int | None = None,
        scope_organization_id: int | None = None,
    ) -> EntitlementRecord:
        """Idempotente: crea si falta; si existe, sincroniza effective_state desde suscripción."""
        existing = cls.get_for_tenant_product(
            organization_id,
            product_code,
            scope_organization_id=scope_organization_id,
        )
        if existing is not None:
            return cls.sync_state_from_subscription(
                organization_id,
                product_code,
                user_id=user_id,
                scope_organization_id=scope_organization_id,
            )
        return cls.create_from_subscription(
            organization_id,
            product_code,
            plan_code=plan_code,
            user_id=user_id,
            scope_organization_id=scope_organization_id,
        )

    @classmethod
    def set_overrides(
        cls,
        organization_id: int,
        product_code: str,
        overrides: dict[str, Any],
        *,
        user_id: int | None = None,
        scope_organization_id: int | None = None,
    ) -> EntitlementRecord:
        """Excepciones comerciales sin cambiar de plan."""
        from models.ets_product_entitlement import EtsProductEntitlement
        from nodeone.core.db import db

        oid = _norm_org(organization_id)
        code = _norm_product(product_code)
        _assert_tenant_scope(oid, expected_organization_id=scope_organization_id)
        if not isinstance(overrides, dict):
            raise EntitlementError('invalid_overrides', 'overrides debe ser un objeto')

        row = EtsProductEntitlement.query.filter_by(
            organization_id=oid, product_code=code
        ).first()
        if row is None:
            raise EntitlementError('not_found', 'Entitlement no encontrado')

        row.overrides_json = _dump_json(overrides)
        row.updated_by_user_id = user_id
        row.updated_at = _now()
        db.session.commit()
        rec = _row_to_record(row)
        _audit(
            oid,
            'entitlement.overrides_updated',
            {'entitlement_id': rec.id, 'product_code': code, 'overrides': overrides},
        )
        return rec

    @classmethod
    def set_plan(
        cls,
        organization_id: int,
        product_code: str,
        plan_code: str,
        *,
        keep_overrides: bool = True,
        user_id: int | None = None,
        scope_organization_id: int | None = None,
    ) -> EntitlementRecord:
        from models.ets_product_entitlement import EtsProductEntitlement
        from nodeone.core.db import db

        oid = _norm_org(organization_id)
        code = _norm_product(product_code)
        _assert_tenant_scope(oid, expected_organization_id=scope_organization_id)
        plan = normalize_plan_code(plan_code)
        template = get_plan_template(code, plan)

        row = EtsProductEntitlement.query.filter_by(
            organization_id=oid, product_code=code
        ).first()
        if row is None:
            raise EntitlementError('not_found', 'Entitlement no encontrado')

        row.plan_code = plan
        row.resource_limits_json = _dump_json(template.get('resource_limits') or {})
        row.features_json = _dump_json(template.get('features') or {})
        if not keep_overrides:
            row.overrides_json = None
        row.updated_by_user_id = user_id
        row.updated_at = _now()
        db.session.commit()
        rec = _row_to_record(row)
        _audit(
            oid,
            'entitlement.plan_changed',
            {'entitlement_id': rec.id, 'product_code': code, 'plan_code': plan},
        )
        return rec

    @classmethod
    def set_effective_state(
        cls,
        organization_id: int,
        product_code: str,
        effective_state: str,
        *,
        user_id: int | None = None,
        scope_organization_id: int | None = None,
    ) -> EntitlementRecord:
        from models.ets_product_entitlement import EtsProductEntitlement
        from nodeone.core.db import db

        oid = _norm_org(organization_id)
        code = _norm_product(product_code)
        _assert_tenant_scope(oid, expected_organization_id=scope_organization_id)
        state = (effective_state or '').strip().lower()
        valid = {s.value for s in EntitlementEffectiveState}
        if state not in valid:
            raise EntitlementError('invalid_state', f'effective_state inválido: {state}')

        row = EtsProductEntitlement.query.filter_by(
            organization_id=oid, product_code=code
        ).first()
        if row is None:
            raise EntitlementError('not_found', 'Entitlement no encontrado')

        prev = row.effective_state
        row.effective_state = state
        row.updated_by_user_id = user_id
        row.updated_at = _now()
        db.session.commit()
        rec = _row_to_record(row)
        _audit(
            oid,
            'entitlement.state_changed',
            {
                'entitlement_id': rec.id,
                'product_code': code,
                'from': prev,
                'to': state,
            },
        )
        return rec

    @classmethod
    def sync_state_from_subscription(
        cls,
        organization_id: int,
        product_code: str,
        *,
        user_id: int | None = None,
        scope_organization_id: int | None = None,
    ) -> EntitlementRecord:
        """Actualiza effective_state (y fechas) desde subscription.status.

        No degrada GRACE automáticamente (decisión comercial explícita).
        """
        from models.ets_product_entitlement import EtsProductEntitlement
        from nodeone.core.db import db

        oid = _norm_org(organization_id)
        code = _norm_product(product_code)
        _assert_tenant_scope(oid, expected_organization_id=scope_organization_id)

        sub = SubscriptionRegistry.get_for_tenant_product(
            oid, code, scope_organization_id=scope_organization_id
        )
        if sub is None:
            raise EntitlementError('subscription_required', 'Suscripción no encontrada')

        row = EtsProductEntitlement.query.filter_by(
            organization_id=oid, product_code=code
        ).first()
        if row is None:
            raise EntitlementError('not_found', 'Entitlement no encontrado')

        mapped = effective_state_from_subscription(sub.status)
        # Si ya está en grace, no bajar a past_due automáticamente
        if (
            row.effective_state == EntitlementEffectiveState.GRACE.value
            and mapped == EntitlementEffectiveState.PAST_DUE.value
        ):
            mapped = EntitlementEffectiveState.GRACE.value

        row.effective_state = mapped
        row.starts_at = sub.starts_at or row.starts_at
        row.ends_at = sub.ends_at
        row.updated_by_user_id = user_id
        row.updated_at = _now()
        db.session.commit()
        return _row_to_record(row)

    @classmethod
    def has_capacity(
        cls,
        organization_id: int,
        product_code: str,
        resource_type: str,
        *,
        current_count: int = 0,
        scope_organization_id: int | None = None,
    ) -> bool:
        """Hook Paso 1: ¿hay cupo para ``resource_type`` dado ``current_count``?

        ``-1`` = ilimitado. Sin entitlement operable → False.
        """
        rec = cls.get_for_tenant_product(
            organization_id,
            product_code,
            scope_organization_id=scope_organization_id,
        )
        if rec is None or not rec.is_operable:
            return False
        key = (resource_type or '').strip().lower()
        if not key:
            return False
        limit = rec.effective_limits.get(key)
        if limit is None:
            # Recurso no definido en el plan → sin cupo explícito
            return False
        try:
            lim = int(limit)
        except (TypeError, ValueError):
            return False
        if lim < 0:
            return True
        try:
            used = int(current_count)
        except (TypeError, ValueError):
            used = 0
        return used < lim

    @classmethod
    def has_feature(
        cls,
        organization_id: int,
        product_code: str,
        feature: str,
        *,
        scope_organization_id: int | None = None,
    ) -> bool:
        rec = cls.get_for_tenant_product(
            organization_id,
            product_code,
            scope_organization_id=scope_organization_id,
        )
        if rec is None or not rec.is_operable:
            return False
        key = (feature or '').strip().lower()
        if not key:
            return False
        # Overrides pueden habilitar/deshabilitar features booleanas
        if key in rec.overrides:
            val = rec.overrides[key]
            if isinstance(val, bool):
                return val
        val = rec.features.get(key)
        if isinstance(val, bool):
            return val
        if val in (None, False, 0, '', 'basic', 'none', 'no'):
            return bool(val) if isinstance(val, bool) else False
        # Features no booleanas (ej. dashboard=full) cuentan como habilitadas si truthy
        return bool(val)

    @classmethod
    def capacity_denial_message(cls, resource_type: str, limit: int) -> str:
        labels = {
            'pos': 'puntos de venta',
            'registers': 'cajas',
            'tablets': 'tablets',
            'cashiers': 'cajeros',
        }
        label = labels.get((resource_type or '').strip().lower(), resource_type or 'recursos')
        return (
            f'Su plan permite {limit} {label}. Ha alcanzado el límite. '
            'Contacte a su proveedor para ampliar.'
        )
