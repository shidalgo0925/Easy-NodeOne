"""Impuestos porcentuales estándar (0 %, 7 %) por organización. Idempotente."""

from __future__ import annotations

from datetime import datetime
from typing import Callable, Optional

# Nombres por defecto; si el nombre ya existe para otro tipo de impuesto, se desambigua.
DEFAULT_TAX_PAIRS: tuple[tuple[float, str], ...] = (
    (0.0, '0%'),
    (7.0, '7%'),
)


def _rate_exists(org_id: int, target: float) -> bool:
    from sqlalchemy import func

    from nodeone.modules.accounting.models import Tax

    return (
        Tax.query.filter(
            Tax.organization_id == org_id,
            Tax.computation == 'percent',
            func.abs(Tax.percentage - target) < 0.000001,
        ).first()
        is not None
    )


def _next_free_name(org_id: int, base: str) -> str:
    from nodeone.modules.accounting.models import Tax

    if Tax.query.filter_by(organization_id=org_id, name=base).first() is None:
        return base
    n = 2
    while True:
        cand = f'{base} ({n})'
        if Tax.query.filter_by(organization_id=org_id, name=cand).first() is None:
            return cand
        n += 1


def ensure_default_percent_taxes(
    printfn: Optional[Callable[[str], None]] = None,
    organization_id: Optional[int] = None,
) -> int:
    """
    Asegura impuestos porcentuales 0% y 7% por organización (tabla ``taxes``).
    No duplica si ya existe un impuesto ``percent`` con ese porcentaje.
    Retorna el número de filas nuevas insertadas.
    """
    from app import SaasOrganization, db

    from nodeone.modules.accounting.models import Tax

    Tax.__table__.create(db.engine, checkfirst=True)

    if organization_id is not None:
        orgs = [SaasOrganization.query.get(int(organization_id))]
    else:
        orgs = list(SaasOrganization.query.order_by(SaasOrganization.id.asc()).all())

    created = 0
    for org in orgs:
        if org is None:
            continue
        oid = int(org.id)
        for pct, default_name in DEFAULT_TAX_PAIRS:
            if _rate_exists(oid, pct):
                continue
            name = _next_free_name(oid, default_name)
            t = Tax(
                organization_id=oid,
                name=name,
                percentage=float(pct),
                type='excluded',
                computation='percent',
                amount_fixed=0.0,
                price_included=False,
                active=True,
                created_at=datetime.utcnow(),
            )
            db.session.add(t)
            created += 1
            if printfn:
                printfn(f'+ tax org={oid} {name} ({pct:g}%)')

    if created:
        db.session.commit()
    return created
