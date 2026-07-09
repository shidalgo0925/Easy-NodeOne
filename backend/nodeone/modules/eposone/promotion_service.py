"""Promociones POS EPosOne — scaffold v1."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from models.eposone_promotion import PROMO_TYPES, PROMO_TYPE_PERCENT, EposonePromotion
from nodeone.core.commerce.order import OrderValidationError


@dataclass(frozen=True)
class PromotionDTO:
    id: int
    organization_id: int
    promo_ref: str
    name: str
    promo_type: str
    value: float
    code: str | None
    active: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            'id': self.id,
            'organization_id': self.organization_id,
            'promo_ref': self.promo_ref,
            'name': self.name,
            'promo_type': self.promo_type,
            'value': self.value,
            'code': self.code,
            'active': self.active,
        }


def _to_dto(row: EposonePromotion) -> PromotionDTO:
    return PromotionDTO(
        id=int(row.id),
        organization_id=int(row.organization_id),
        promo_ref=str(row.promo_ref),
        name=str(row.name),
        promo_type=str(row.promo_type or PROMO_TYPE_PERCENT),
        value=float(row.value or 0),
        code=(str(row.code).strip() if row.code else None),
        active=bool(row.active),
    )


class PromotionService:
    @staticmethod
    def _next_promo_ref(organization_id: int) -> str:
        prefix = 'PROMO'
        rx = re.compile(rf'^{re.escape(prefix)}-(\d{{1,12}})\Z')
        max_seq = 0
        for (ref,) in (
            EposonePromotion.query.filter_by(organization_id=int(organization_id))
            .with_entities(EposonePromotion.promo_ref)
            .all()
        ):
            m = rx.match(str(ref or '').strip())
            if m:
                max_seq = max(max_seq, int(m.group(1)))
        return f'{prefix}-{max_seq + 1:04d}'

    @staticmethod
    def list_promotions(organization_id: int, *, limit: int = 50) -> list[PromotionDTO]:
        rows = (
            EposonePromotion.query.filter_by(organization_id=int(organization_id))
            .order_by(EposonePromotion.id.desc())
            .limit(max(1, min(int(limit), 200)))
            .all()
        )
        return [_to_dto(row) for row in rows]

    @staticmethod
    def create_promotion(
        organization_id: int,
        *,
        name: str,
        promo_type: str,
        value: float,
        code: str | None = None,
    ) -> PromotionDTO:
        from app import db

        label = (name or '').strip()
        if not label:
            raise OrderValidationError('promo_name_required')
        ptype = (promo_type or '').strip().lower()
        if ptype not in PROMO_TYPES:
            raise OrderValidationError('promo_type_invalid')
        amount = float(value or 0)
        if amount <= 0:
            raise OrderValidationError('promo_value_required')
        if ptype == PROMO_TYPE_PERCENT and amount > 100:
            raise OrderValidationError('promo_percent_max_100')
        code_norm = (code or '').strip().upper() or None
        if code_norm:
            existing = EposonePromotion.query.filter_by(
                organization_id=int(organization_id),
                code=code_norm,
            ).first()
            if existing is not None:
                raise OrderValidationError('promo_code_exists')
        row = EposonePromotion(
            organization_id=int(organization_id),
            promo_ref=PromotionService._next_promo_ref(int(organization_id)),
            name=label[:200],
            promo_type=ptype,
            value=amount,
            code=code_norm,
            active=True,
        )
        db.session.add(row)
        db.session.commit()
        return _to_dto(row)

    @staticmethod
    def set_active(organization_id: int, promotion_id: int, *, active: bool) -> PromotionDTO:
        from app import db

        row = EposonePromotion.query.filter_by(
            organization_id=int(organization_id),
            id=int(promotion_id),
        ).first()
        if row is None:
            raise OrderValidationError('promo_not_found')
        row.active = bool(active)
        db.session.commit()
        return _to_dto(row)
