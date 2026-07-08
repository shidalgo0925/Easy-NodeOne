"""Catálogo de productos EasyTech para ECalendar V1 (lista oficial aprobada)."""

from __future__ import annotations

import json
from typing import Any

DEFAULT_PRODUCTS: list[dict[str, str]] = [
    {'id': 'easy_odoo', 'name': 'Easy Odoo'},
    {'id': 'facturacion_electronica_panama', 'name': 'Facturación Electrónica Panamá'},
    {'id': 'easy_converso', 'name': 'Easy Converso'},
    {'id': 'easynodeone', 'name': 'EasyNodeOne (EN1)'},
    {'id': 'eclassone', 'name': 'EClassOne'},
    {'id': 'ethesisone', 'name': 'EThesisOne'},
    {'id': 'eposone', 'name': 'EPOSOne'},
    {'id': 'epayroll', 'name': 'EPayRoll'},
    {'id': 'iius', 'name': 'IIUS'},
    {'id': 'consultoria_ti', 'name': 'Consultoría TI'},
    {'id': 'desarrollo_software', 'name': 'Desarrollo de Software'},
]


def load_products(products_json: str | None = None) -> list[dict[str, str]]:
    raw = (products_json or '').strip()
    if raw:
        try:
            data = json.loads(raw)
            if isinstance(data, list):
                out = []
                for item in data:
                    if not isinstance(item, dict):
                        continue
                    pid = (item.get('id') or '').strip()
                    name = (item.get('name') or '').strip()
                    if pid and name:
                        out.append({'id': pid, 'name': name})
                if out:
                    return out
        except json.JSONDecodeError:
            pass
    return list(DEFAULT_PRODUCTS)


def product_by_id(product_id: str, products_json: str | None = None) -> dict[str, str] | None:
    pid = (product_id or '').strip().lower()
    for p in load_products(products_json):
        if p['id'] == pid:
            return p
    return None


def products_payload(products_json: str | None = None) -> dict[str, Any]:
    products = load_products(products_json)
    return {'ok': True, 'products': products}
