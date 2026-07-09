"""Menú digital + pedidos QR — Etapa 17."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from models.eposone_digital_menu import EposoneDigitalMenu, EposoneDigitalMenuItem
from nodeone.core.commerce.order import OrderService, OrderValidationError


@dataclass(frozen=True)
class DigitalMenuItemDTO:
    id: int
    name: str
    description: str | None
    category: str | None
    price: float
    available: bool
    sort_order: int

    def to_dict(self) -> dict[str, Any]:
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'category': self.category,
            'price': self.price,
            'available': self.available,
            'sort_order': self.sort_order,
        }


@dataclass(frozen=True)
class DigitalMenuDTO:
    id: int
    organization_id: int
    menu_ref: str
    name: str
    public_token: str
    active: bool
    items: tuple[DigitalMenuItemDTO, ...]

    def to_dict(self, *, include_token: bool = True) -> dict[str, Any]:
        data = {
            'id': self.id,
            'organization_id': self.organization_id,
            'menu_ref': self.menu_ref,
            'name': self.name,
            'active': self.active,
            'items': [i.to_dict() for i in self.items],
        }
        if include_token:
            data['public_token'] = self.public_token
        return data


def _menu_to_dto(row: EposoneDigitalMenu, *, public_only: bool = False) -> DigitalMenuDTO:
    items_list: list[DigitalMenuItemDTO] = []
    for item in row.items or []:
        if public_only and not bool(item.available):
            continue
        items_list.append(
            DigitalMenuItemDTO(
                id=int(item.id),
                name=str(item.name),
                description=(item.description or None),
                category=(item.category or None),
                price=float(item.price or 0),
                available=bool(item.available),
                sort_order=int(item.sort_order or 0),
            )
        )
    return DigitalMenuDTO(
        id=int(row.id),
        organization_id=int(row.organization_id),
        menu_ref=str(row.menu_ref),
        name=str(row.name),
        public_token=str(row.public_token),
        active=bool(row.active),
        items=tuple(items_list),
    )


class DigitalMenuService:
    @staticmethod
    def _next_menu_ref(organization_id: int) -> str:
        prefix = 'MENU'
        rx = re.compile(rf'^{re.escape(prefix)}-(\d{{1,12}})\Z')
        max_seq = 0
        for (ref,) in (
            EposoneDigitalMenu.query.filter_by(organization_id=int(organization_id))
            .with_entities(EposoneDigitalMenu.menu_ref)
            .all()
        ):
            m = rx.match(str(ref or '').strip())
            if m:
                max_seq = max(max_seq, int(m.group(1)))
        return f'{prefix}-{max_seq + 1:04d}'

    @staticmethod
    def list_menus(organization_id: int) -> list[DigitalMenuDTO]:
        rows = (
            EposoneDigitalMenu.query.filter_by(organization_id=int(organization_id))
            .order_by(EposoneDigitalMenu.id.desc())
            .all()
        )
        return [_menu_to_dto(r) for r in rows]

    @staticmethod
    def get_menu(organization_id: int, menu_id: int) -> DigitalMenuDTO | None:
        row = EposoneDigitalMenu.query.filter_by(
            organization_id=int(organization_id),
            id=int(menu_id),
        ).first()
        return _menu_to_dto(row) if row is not None else None

    @staticmethod
    def set_active(organization_id: int, menu_id: int, *, active: bool) -> DigitalMenuDTO:
        from app import db

        row = EposoneDigitalMenu.query.filter_by(
            organization_id=int(organization_id),
            id=int(menu_id),
        ).first()
        if row is None:
            raise OrderValidationError('menu_not_found')
        row.active = bool(active)
        db.session.commit()
        return _menu_to_dto(row)

    @staticmethod
    def create_menu(organization_id: int, *, name: str, items: list[dict[str, Any]] | None = None) -> DigitalMenuDTO:
        from app import db

        label = (name or '').strip()
        if not label:
            raise OrderValidationError('menu_name_required')
        row = EposoneDigitalMenu(
            organization_id=int(organization_id),
            menu_ref=DigitalMenuService._next_menu_ref(int(organization_id)),
            name=label[:200],
            active=True,
        )
        row.items = DigitalMenuService._build_items(items or [])
        db.session.add(row)
        db.session.commit()
        return _menu_to_dto(row)

    @staticmethod
    def _build_items(raw_items: list[dict[str, Any]]) -> list[EposoneDigitalMenuItem]:
        out: list[EposoneDigitalMenuItem] = []
        for idx, raw in enumerate(raw_items):
            if not isinstance(raw, dict):
                continue
            name = (raw.get('name') or '').strip()
            if not name:
                continue
            out.append(
                EposoneDigitalMenuItem(
                    name=name[:200],
                    description=(str(raw.get('description')).strip()[:500] if raw.get('description') else None),
                    category=(str(raw.get('category')).strip()[:120] if raw.get('category') else None),
                    price=float(raw.get('price') or 0),
                    available=bool(raw.get('available', True)),
                    sort_order=int(raw.get('sort_order', idx)),
                )
            )
        return out

    @staticmethod
    def get_by_token(public_token: str) -> DigitalMenuDTO | None:
        token = (public_token or '').strip()
        if not token:
            return None
        row = EposoneDigitalMenu.query.filter_by(public_token=token, active=True).first()
        return _menu_to_dto(row, public_only=True) if row is not None else None

    @staticmethod
    def public_menu_url(public_token: str) -> str:
        from flask import url_for

        return url_for('eposone_public.public_menu_page', token=public_token, _external=True)

    @staticmethod
    def place_order_from_token(
        public_token: str,
        cart_lines: list[dict[str, Any]],
        *,
        notes: str | None = None,
    ):
        menu = DigitalMenuService.get_by_token(public_token)
        if menu is None:
            raise OrderValidationError('menu_not_found')
        item_map = {i.id: i for i in menu.items}
        lines: list[dict[str, Any]] = []
        for raw in cart_lines:
            if not isinstance(raw, dict):
                continue
            item_id = raw.get('item_id')
            qty = float(raw.get('quantity') or 1)
            if qty <= 0:
                continue
            item = item_map.get(int(item_id)) if item_id is not None else None
            if item is None:
                raise OrderValidationError(f'item_not_found:{item_id}')
            lines.append(
                {
                    'description': item.name,
                    'quantity': qty,
                    'unit_price': item.price,
                    'product_ref': f'menu-item:{item.id}',
                }
            )
        if not lines:
            raise OrderValidationError('cart_empty')
        payload: dict[str, Any] = {
            'lines': lines,
            'notes': notes,
            'source': 'digital_menu',
            'menu_ref': menu.menu_ref,
        }
        return OrderService.create(int(menu.organization_id), payload, source_app_id='eposone')
