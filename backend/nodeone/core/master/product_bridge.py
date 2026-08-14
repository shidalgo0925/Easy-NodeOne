"""Puente dual Service (catálogo comercial) ↔ core_product (Inventario).

SoR inventario/POS = core_product.
SoR cotizaciones/tienda/agenda = Service.id (int) hasta evolución de líneas.
Sincroniza ambos vía core_product_legacy_service_link.
"""

from __future__ import annotations

from typing import Any

from models.core_master import CoreProduct, CoreProductLegacyServiceLink
from nodeone.core.db import db


LINK_SOURCE_FROM_SERVICE = 'from_service'
LINK_SOURCE_FROM_PRODUCT = 'from_product'
LINK_SOURCE_BACKFILL = 'backfill'


def product_ref_for_service(service_id: int) -> str:
    return f'svc-{int(service_id)}'


def get_link_by_service(organization_id: int, service_id: int) -> CoreProductLegacyServiceLink | None:
    return CoreProductLegacyServiceLink.query.filter_by(
        organization_id=int(organization_id),
        legacy_service_id=int(service_id),
    ).first()


def get_link_by_product_ref(organization_id: int, product_ref: str) -> CoreProductLegacyServiceLink | None:
    ref = (product_ref or '').strip()
    if not ref:
        return None
    return CoreProductLegacyServiceLink.query.filter_by(
        organization_id=int(organization_id),
        product_ref=ref,
    ).first()


def _category_name(service: Any) -> str | None:
    cat = getattr(service, 'category', None)
    if cat is not None and getattr(cat, 'name', None):
        return str(cat.name).strip()[:120] or None
    return None


def _product_type_from_service(service: Any) -> tuple[str, bool]:
    """(product_type, tracks_inventory). Legacy Service → always non-stockable service/good."""
    st = (getattr(service, 'service_type', None) or '').strip().upper()
    if st in ('AGENDABLE', 'CONSULTIVO', 'CV_REGISTRATION', 'COURSE'):
        return 'service', False
    return 'good', False


def _service_type_from_product(product: CoreProduct) -> str:
    if (product.product_type or '').strip().lower() == 'service':
        return 'CONSULTIVO'
    return 'CONSULTIVO'


def ensure_from_service(
    organization_id: int,
    service: Any,
    *,
    link_source: str = LINK_SOURCE_FROM_SERVICE,
    commit: bool = True,
) -> str | None:
    """Crea/actualiza core_product + link para un Service. Devuelve product_ref."""
    if service is None:
        return None
    oid = int(organization_id)
    sid = int(service.id)
    link = get_link_by_service(oid, sid)
    pref = (link.product_ref if link else product_ref_for_service(sid)).strip()
    ptype, tracks = _product_type_from_service(service)
    status = 'active' if bool(getattr(service, 'is_active', True)) else 'inactive'
    name = (getattr(service, 'name', None) or f'Servicio {sid}').strip()[:300]
    desc = (getattr(service, 'description', None) or None)
    if desc is not None:
        desc = str(desc).strip()[:5000] or None
    price = float(getattr(service, 'base_price', 0) or 0)
    image = (getattr(service, 'image_url', None) or None)
    if image is not None:
        image = str(image).strip()[:500] or None
    category = _category_name(service)

    row = CoreProduct.query.filter_by(organization_id=oid, product_ref=pref).first()
    if row is None:
        row = CoreProduct(
            organization_id=oid,
            product_ref=pref,
            name=name,
            description=desc,
            product_type=ptype,
            tracks_inventory=tracks,
            status=status,
            unit_price=price,
            currency='USD',
            source_app_id='catalog.service',
            category=category,
            image_url=image,
            uom='und',
        )
        db.session.add(row)
    else:
        row.name = name
        row.description = desc
        row.product_type = ptype
        row.tracks_inventory = tracks
        row.status = status
        row.unit_price = price
        if category is not None:
            row.category = category
        if image is not None:
            row.image_url = image
        if not row.source_app_id:
            row.source_app_id = 'catalog.service'

    if link is None:
        db.session.add(
            CoreProductLegacyServiceLink(
                organization_id=oid,
                product_ref=pref,
                legacy_service_id=sid,
                link_source=link_source,
            )
        )
    else:
        link.link_source = link_source or link.link_source

    if commit:
        db.session.commit()
    return pref


def ensure_from_product(
    organization_id: int,
    product: CoreProduct | None = None,
    *,
    product_ref: str | None = None,
    link_source: str = LINK_SOURCE_FROM_PRODUCT,
    commit: bool = True,
) -> int | None:
    """Crea/actualiza Service + link para un core_product. Devuelve service_id."""
    from models.catalog import Service

    oid = int(organization_id)
    row = product
    if row is None:
        ref = (product_ref or '').strip()
        if not ref:
            return None
        row = CoreProduct.query.filter_by(organization_id=oid, product_ref=ref).first()
    if row is None:
        return None

    pref = str(row.product_ref).strip()
    link = get_link_by_product_ref(oid, pref)
    service = None
    if link is not None:
        service = Service.query.filter_by(id=int(link.legacy_service_id), organization_id=oid).first()

    name = (row.name or pref).strip()[:200]
    desc = row.description or ''
    price = float(row.unit_price or 0)
    active = (row.status or 'active').strip().lower() == 'active'
    image = row.image_url
    stype = _service_type_from_product(row)

    if service is None:
        service = Service(
            name=name,
            description=desc,
            icon='fas fa-box',
            image_url=image,
            membership_type='basic',
            base_price=price,
            is_active=active,
            display_order=0,
            service_type=stype,
            organization_id=oid,
        )
        db.session.add(service)
        db.session.flush()
    else:
        service.name = name
        service.description = desc
        service.base_price = price
        service.is_active = active
        if image is not None:
            service.image_url = image

    if link is None:
        db.session.add(
            CoreProductLegacyServiceLink(
                organization_id=oid,
                product_ref=pref,
                legacy_service_id=int(service.id),
                link_source=link_source,
            )
        )
    else:
        link.legacy_service_id = int(service.id)
        link.link_source = link_source or link.link_source

    if commit:
        db.session.commit()
    return int(service.id)


def backfill_org(organization_id: int, *, limit: int = 200) -> dict[str, int]:
    """Migra Services sin link → core_product y Products sin link → Service."""
    from models.catalog import Service

    oid = int(organization_id)
    created_from_service = 0
    created_from_product = 0

    linked_sids = {
        int(r.legacy_service_id)
        for r in CoreProductLegacyServiceLink.query.filter_by(organization_id=oid).all()
    }
    services = (
        Service.query.filter_by(organization_id=oid)
        .order_by(Service.id.asc())
        .limit(max(1, int(limit)))
        .all()
    )
    for svc in services:
        if int(svc.id) in linked_sids:
            continue
        if ensure_from_service(oid, svc, link_source=LINK_SOURCE_BACKFILL, commit=False):
            created_from_service += 1
            linked_sids.add(int(svc.id))

    linked_refs = {
        str(r.product_ref)
        for r in CoreProductLegacyServiceLink.query.filter_by(organization_id=oid).all()
    }
    products = (
        CoreProduct.query.filter_by(organization_id=oid)
        .order_by(CoreProduct.id.asc())
        .limit(max(1, int(limit)))
        .all()
    )
    for prod in products:
        if str(prod.product_ref) in linked_refs:
            continue
        sid = ensure_from_product(oid, prod, link_source=LINK_SOURCE_BACKFILL, commit=False)
        if sid:
            created_from_product += 1
            linked_refs.add(str(prod.product_ref))

    db.session.commit()
    images = sync_missing_product_images(oid, commit=True)
    return {
        'from_service': created_from_service,
        'from_product': created_from_product,
        'images': images,
    }


# Cards oficiales login / catálogo ETS (paths públicos bajo /static/…).
_BRAND_IMAGE_BY_KEY: dict[str, str] = {
    'eposone': '/static/images/auth/card-eposone.png',
    'epayroll': '/static/images/auth/card-epayroll.png',
    'eclassone': '/static/images/auth/card-easyclassone.png',
    'easyclassone': '/static/images/auth/card-easyclassone.png',
    'easy thesis': '/static/images/auth/card-easythesis.png',
    'easythesis': '/static/images/auth/card-easythesis.png',
    'ethesis': '/static/images/auth/card-easythesis.png',
    'easyia': '/static/images/auth/card-easyia.png',
    'em+accion': '/static/images/auth/card-em.png',
    'em+acción': '/static/images/auth/card-em.png',
    'em accion': '/static/images/auth/card-em.png',
    'esecurebroker': '/static/images/products/product-confirma.png',
    'e secure broker': '/static/images/products/product-confirma.png',
}


def _norm_key(value: str | None) -> str:
    import re
    import unicodedata

    raw = (value or '').strip().lower()
    raw = unicodedata.normalize('NFKD', raw)
    raw = ''.join(ch for ch in raw if not unicodedata.combining(ch))
    raw = re.sub(r'[^a-z0-9+]+', ' ', raw)
    return ' '.join(raw.split())


def brand_image_for_product(*, name: str | None, product_ref: str | None = None) -> str | None:
    """Resuelve card de marca ETS por nombre o SKU."""
    candidates = [_norm_key(name), _norm_key(product_ref)]
    for key in candidates:
        if not key:
            continue
        if key in _BRAND_IMAGE_BY_KEY:
            return _BRAND_IMAGE_BY_KEY[key]
        compact = key.replace(' ', '')
        for brand, url in _BRAND_IMAGE_BY_KEY.items():
            b = brand.replace(' ', '')
            if compact == b or compact.startswith(b) or b in compact:
                return url
    return None


def _static_file_exists(image_url: str | None) -> bool:
    import os

    url = (image_url or '').strip()
    if not url.startswith('/static/'):
        return False
    rel = url[len('/static/') :]
    roots = (
        '/opt/easynodeone/dev/app/static',
        os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'static'),
    )
    try:
        from flask import current_app, has_app_context

        if has_app_context() and current_app.static_folder:
            roots = (current_app.static_folder,) + roots
    except Exception:
        pass
    for root in roots:
        path = os.path.normpath(os.path.join(root, rel))
        if os.path.isfile(path):
            return True
    return False


def sync_missing_product_images(
    organization_id: int | None = None,
    *,
    fix_broken: bool = True,
    commit: bool = True,
) -> dict[str, int]:
    """Rellena image_url faltante (o rota) desde Service o cards de marca ETS.

    - Copia Service → Product si el Service tiene imagen.
    - Si sigue vacío o el archivo no existe: aplica mapa de marca por nombre.
    - Escribe también en Service vinculado para Tienda/cotizaciones.
    """
    from models.catalog import Service

    q = CoreProduct.query
    if organization_id is not None:
        q = q.filter_by(organization_id=int(organization_id))
    products = q.order_by(CoreProduct.organization_id.asc(), CoreProduct.id.asc()).all()

    filled_from_service = 0
    filled_from_brand = 0
    fixed_broken = 0
    synced_service = 0

    for prod in products:
        oid = int(prod.organization_id)
        current = (prod.image_url or '').strip() or None
        broken = bool(current) and not _static_file_exists(current)
        needs = (not current) or (fix_broken and broken)

        link = get_link_by_product_ref(oid, str(prod.product_ref))
        service = None
        if link is not None:
            service = Service.query.filter_by(
                id=int(link.legacy_service_id), organization_id=oid
            ).first()

        new_url = None
        source = None
        if needs and service is not None:
            svc_img = (getattr(service, 'image_url', None) or '').strip() or None
            if svc_img and (not current or broken) and (
                _static_file_exists(svc_img) or not broken
            ):
                # Prefer service URL if file exists; if product empty take service even if remote-ish.
                if _static_file_exists(svc_img) or not current:
                    if _static_file_exists(svc_img) or not broken:
                        new_url = svc_img
                        source = 'service'

        if needs and not new_url:
            brand = brand_image_for_product(name=prod.name, product_ref=prod.product_ref)
            if brand and _static_file_exists(brand):
                new_url = brand
                source = 'brand'

        if new_url and new_url != current:
            prod.image_url = new_url
            if source == 'service':
                filled_from_service += 1
            elif broken:
                fixed_broken += 1
            else:
                filled_from_brand += 1
            if service is not None:
                service.image_url = new_url
                synced_service += 1
        elif current and service is not None and not (getattr(service, 'image_url', None) or '').strip():
            service.image_url = current
            synced_service += 1

    if commit:
        db.session.commit()
    return {
        'from_service': filled_from_service,
        'from_brand': filled_from_brand,
        'fixed_broken': fixed_broken,
        'synced_service': synced_service,
    }

