"""Menú digital + pedidos QR — Etapa 17."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from models.eposone_digital_menu import EposoneDigitalMenu, EposoneDigitalMenuItem
from nodeone.core.commerce.order import OrderService, OrderValidationError


# Orden preferido de categorías (Mexican Food / resto alfabético al final).
_CATEGORY_ORDER = (
    'Entradas',
    'Nachos',
    'Tacos',
    'Burritos',
    'Platos fuertes',
    'Bandejas',
    'Bebidas',
    'Postres',
)


@dataclass(frozen=True)
class DigitalMenuItemDTO:
    id: int
    name: str
    description: str | None
    category: str | None
    price: float
    available: bool
    sort_order: int
    image_url: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'category': self.category,
            'price': self.price,
            'available': self.available,
            'sort_order': self.sort_order,
            'image_url': self.image_url,
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
            'categories': _group_items_by_category(self.items),
        }
        if include_token:
            data['public_token'] = self.public_token
        return data


def _product_image_lookup(organization_id: int) -> dict[str, str]:
    """Mapa nombre|categoría → image_url de productos activos (menú digital no guarda imagen)."""
    try:
        from models.core_master import CoreProduct

        rows = (
            CoreProduct.query.filter_by(organization_id=int(organization_id), status='active')
            .with_entities(CoreProduct.name, CoreProduct.category, CoreProduct.image_url)
            .all()
        )
    except Exception:
        return {}
    out: dict[str, str] = {}
    for name, category, image_url in rows:
        url = (image_url or '').strip()
        if not url:
            continue
        key_name = (name or '').strip().lower()
        if not key_name:
            continue
        cat = (category or '').strip().lower()
        if cat:
            out[f'{key_name}|{cat}'] = url
        out.setdefault(key_name, url)
    return out


def _resolve_item_image(
    lookup: dict[str, str],
    *,
    name: str,
    category: str | None,
) -> str | None:
    key_name = (name or '').strip().lower()
    if not key_name:
        return None
    cat = (category or '').strip().lower()
    if cat:
        hit = lookup.get(f'{key_name}|{cat}')
        if hit:
            return hit
    return lookup.get(key_name)


def _group_items_by_category(items: tuple[DigitalMenuItemDTO, ...]) -> list[dict[str, Any]]:
    buckets: dict[str, list[DigitalMenuItemDTO]] = {}
    for item in items:
        cat = (item.category or '').strip() or 'Otros'
        buckets.setdefault(cat, []).append(item)

    def sort_key(cat: str) -> tuple[int, str]:
        try:
            return (_CATEGORY_ORDER.index(cat), cat.lower())
        except ValueError:
            return (len(_CATEGORY_ORDER), cat.lower())

    grouped: list[dict[str, Any]] = []
    for cat in sorted(buckets.keys(), key=sort_key):
        cat_items = sorted(buckets[cat], key=lambda i: (i.sort_order, i.name.lower()))
        grouped.append(
            {
                'name': cat,
                'slug': re.sub(r'[^a-z0-9]+', '-', cat.lower()).strip('-') or 'otros',
                'items': [i.to_dict() for i in cat_items],
            }
        )
    return grouped


def resolve_public_menu_brand_logo(organization_id: int) -> str | None:
    """Ruta relativa bajo static/ del logo del tenant para menú público."""
    import os

    from nodeone.services.post_login_organization import organization_logo_url_for_picker
    from nodeone.services.tenant_email_logo_storage import TENANT_EMAIL_LOGO_REL_DIR, _static_root_abs

    def _normalize_rel(stored: str | None) -> str | None:
        rel = (stored or '').strip().lstrip('/')
        if not rel or rel.startswith('http'):
            return None
        if rel.startswith('static/'):
            rel = rel[7:]
        path = os.path.join(_static_root_abs(), rel.replace('/', os.sep))
        return rel if os.path.isfile(path) else None

    oid = int(organization_id)
    root = _static_root_abs()

    # Preferencia: logo de marca para menú digital (fondo de página).
    for ext in ('jpg', 'jpeg', 'png', 'svg', 'webp'):
        cand = f'uploads/eposone/brands/org{oid}-logo.{ext}'
        if os.path.isfile(os.path.join(root, cand.replace('/', os.sep))):
            return cand

    rel = _normalize_rel(organization_logo_url_for_picker(oid))
    if rel:
        return rel

    for ext in ('png', 'svg', 'jpg', 'jpeg'):
        cand = f'{TENANT_EMAIL_LOGO_REL_DIR}/logo-email-org{oid}.{ext}'
        path = os.path.join(root, cand.replace('/', os.sep))
        if os.path.isfile(path):
            return cand
    return None


def _menu_to_dto(row: EposoneDigitalMenu, *, public_only: bool = False) -> DigitalMenuDTO:
    image_lookup = _product_image_lookup(int(row.organization_id))
    items_list: list[DigitalMenuItemDTO] = []
    for item in row.items or []:
        if public_only and not bool(item.available):
            continue
        name = str(item.name)
        category = item.category or None
        items_list.append(
            DigitalMenuItemDTO(
                id=int(item.id),
                name=name,
                description=(item.description or None),
                category=category,
                price=float(item.price or 0),
                available=bool(item.available),
                sort_order=int(item.sort_order or 0),
                image_url=_resolve_item_image(image_lookup, name=name, category=category),
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
    def qr_png_bytes(public_url: str, *, size: int = 512) -> bytes:
        """PNG del QR que apunta a la URL pública del menú."""
        from nodeone.modules.qr_generator.services import generate_png_bytes

        url = (public_url or '').strip()
        if not url:
            raise OrderValidationError('public_url_required')
        return generate_png_bytes(url, int(size), 'M', style={'fill': '#0a0e14', 'bg': '#ffffff', 'border': 2})

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
