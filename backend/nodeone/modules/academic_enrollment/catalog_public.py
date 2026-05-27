"""Catálogo público de programas de inscripción (AcademicProgram) para API y vitrina HTML."""

from __future__ import annotations

from typing import Any

# Orden de bloques alineado con cursos-detalle (WP) + diplomados.
CATEGORY_DISPLAY_ORDER: tuple[str, ...] = (
    'Diplomados',
    'Cursos de Negocios',
    'Cursos en Ciencia',
    'Cursos en Espiritualidad',
    'Cursos de Arte',
    'Talleres',
)

# Categoría en Apps y slug canónico (mismo patrón que Cursos en Espiritualidad: curso-en-…).
ARTE_CATEGORY = 'Cursos de Arte'
ARTE_SLUGS: tuple[str, ...] = (
    'curso-en-aprendizaje-practico',
    'curso-en-liderazgo-y-comunicacion',
    'curso-en-creatividad-y-expresion-artistica-aplicada',
    'curso-en-desarrollo-humano',
)
# Títulos posibles en Elementor (WP) → se normalizan a ARTE_CATEGORY en pull/push.
ARTE_WP_SECTION_TITLES: frozenset[str] = frozenset(('Cursos de Arte', 'Cursos en Arte'))
ARTE_WP_CONTAINER_IDS: frozenset[str] = frozenset(
    ('cursos_arte', 'curso_arte', 'cursos_de_arte', 'curso_de_arte')
)

# Orden en vitrina /cursos-detalle/ — bloque Talleres (slugs canónicos taller-de-*).
TALLERES_DISPLAY_ORDER: tuple[str, ...] = (
    'taller-de-aprendizaje-practico',
    'taller-de-creatividad-e-innovacion',
    'taller-de-desarrollo-humano',
    'taller-de-liderazgo-y-comunicacion',
)


def _sort_talleres_programs(programs: list) -> list:
    order = {s: i for i, s in enumerate(TALLERES_DISPLAY_ORDER)}
    return sorted(
        programs,
        key=lambda p: (
            order.get((p.slug or '').strip().lower(), 99),
            int(getattr(p, 'catalog_sort_order', 0) or 0),
            (p.name or '').lower(),
        ),
    )


def _published_talleres_programs(rows: list) -> list:
    """Sección Talleres: 4 slugs del catálogo (aunque en BD sean program_type=curso en Arte)."""
    by_slug = {
        (p.slug or '').strip().lower(): p
        for p in rows
        if (p.status or '').strip().lower() == 'published'
    }
    out: list = []
    for i, slug in enumerate(TALLERES_DISPLAY_ORDER, 1):
        p = by_slug.get(slug)
        if p is not None:
            out.append(p)
    return out


def catalog_can_manage_programs() -> bool:
    """True si el usuario puede abrir el CRUD admin (misma regla que @admin_required)."""
    try:
        from flask_login import current_user

        if not getattr(current_user, 'is_authenticated', False):
            return False
        if getattr(current_user, 'is_admin', False):
            return True
        from app import _user_has_any_admin_permission

        return bool(_user_has_any_admin_permission(current_user))
    except Exception:
        return False


def resolve_catalog_organization_id() -> int | None:
    from flask import has_request_context, request
    from utils.organization import resolve_current_organization

    if not has_request_context():
        return None
    oid = resolve_current_organization()
    if oid is not None:
        return int(oid)
    from app import _organization_id_from_request_host

    host_oid = _organization_id_from_request_host(request)
    return int(host_oid) if host_oid is not None else None


def serialize_public_program(program, *, external_base: str | None = None) -> dict[str, Any]:
    from flask import url_for

    from nodeone.modules.academic_enrollment.uploads import absolute_public_asset_url

    slug = (program.slug or '').strip().lower()
    inscripcion_path = url_for('payments.diplomado_landing', slug=slug)
    inscripcion_url = (
        f'{external_base.rstrip("/")}{inscripcion_path}'
        if external_base
        else url_for('payments.diplomado_landing', slug=slug, _external=True)
    )
    checkout_plans: list[dict[str, Any]] = []
    for pl in sorted(
        (p for p in (program.pricing_plans or []) if getattr(p, 'is_active', False)),
        key=lambda x: (int(getattr(x, 'sort_order', 0) or 0), int(getattr(x, 'id', 0) or 0)),
    ):
        path = url_for('payments.checkout_programa_shortcut', slug=slug, plan_code=pl.code)
        checkout_plans.append(
            {
                'code': (pl.code or '').strip(),
                'name': pl.name or '',
                'total_usd': int(pl.total_amount_cents or 0) / 100.0,
                'currency': (pl.currency or 'USD').strip().upper(),
                'checkout_path': path,
                'checkout_url': (
                    f'{external_base.rstrip("/")}{path}' if external_base else url_for(
                        'payments.checkout_programa_shortcut', slug=slug, plan_code=pl.code, _external=True
                    )
                ),
            }
        )
    from nodeone.modules.academic_enrollment.program_display_media import (
        catalog_media_path,
        enrollment_media_path,
        resolve_catalog_card_image_absolute,
        resolve_enrollment_media_absolute,
    )

    catalog_card = catalog_media_path(program)
    enrollment_media = enrollment_media_path(program)
    image_abs = resolve_catalog_card_image_absolute(program, external_base=external_base)
    flyer_abs = resolve_enrollment_media_absolute(program, external_base=external_base)
    return {
        'id': int(program.id),
        'slug': slug,
        'name': program.name or '',
        'program_type': (program.program_type or '').strip().lower(),
        'program_type_label': program.display_type_label(),
        'category': (program.category or '').strip() or None,
        'marketing_tag': (program.marketing_tag or '').strip() or None,
        'key_focuses': (program.key_focuses or '').strip() or None,
        'ideal_for': (program.ideal_for or '').strip() or None,
        'cta_label': (program.cta_label or '').strip() or None,
        'cta_action': (getattr(program, 'cta_action', None) or 'scroll_pricing').strip().lower(),
        'catalog_sort_order': int(getattr(program, 'catalog_sort_order', 0) or 0),
        'long_description': (program.long_description or '').strip() or None,
        'start_date': program.start_date.isoformat() if program.start_date else None,
        'start_date_label': program.start_date_display(),
        'short_description': (program.short_description or '').strip() or None,
        'modality': (program.modality or '').strip() or None,
        'duration_text': (program.duration_text or '').strip() or None,
        'hours': (program.hours or '').strip() or None,
        'language': (program.language or '').strip() or None,
        'price_from': float(program.price_from) if program.price_from is not None else None,
        'currency': (program.currency or 'USD').strip().upper()[:8],
        'image_url': catalog_card,
        'image_url_absolute': image_abs,
        'flyer_url': enrollment_media,
        'flyer_url_absolute': flyer_abs,
        'media_position': (getattr(program, 'media_position', None) or 'left').strip().lower(),
        'published': (program.status or '').strip().lower() == 'published',
        'inscripcion_path': inscripcion_path,
        'inscripcion_url': inscripcion_url,
        'checkout_plans': checkout_plans,
    }


def list_published_programs_payload(organization_id: int) -> dict[str, Any]:
    from models.academic_program import AcademicProgram

    rows = (
        AcademicProgram.query.filter_by(organization_id=int(organization_id), status='published')
        .order_by(
            AcademicProgram.category.asc(),
            AcademicProgram.catalog_sort_order.asc(),
            AcademicProgram.name.asc(),
        )
        .all()
    )
    from flask import request

    base = (request.url_root or '').rstrip('/') if request else ''
    programs = [serialize_public_program(p, external_base=base or None) for p in rows]
    by_category: dict[str, list[dict[str, Any]]] = {}
    for item in programs:
        cat = item.get('category') or 'Otros'
        by_category.setdefault(cat, []).append(item)
    talleres_rows = _published_talleres_programs(rows)
    if talleres_rows:
        by_category['Talleres'] = [
            serialize_public_program(p, external_base=base or None) for p in talleres_rows
        ]
    categories = [c for c in CATEGORY_DISPLAY_ORDER if c in by_category]
    for cat in sorted(by_category.keys()):
        if cat not in categories:
            categories.append(cat)
    return {
        'organization_id': int(organization_id),
        'programs': programs,
        'by_category': by_category,
        'categories': categories,
        'count': len(programs),
    }


def active_plans_for_program(program) -> list:
    """Planes activos ordenados (relación ``pricing_plans`` es lazy=dynamic)."""
    return (
        program.pricing_plans.filter_by(is_active=True)
        .order_by('sort_order', 'id')
        .all()
    )


def distinct_program_categories(organization_id: int, *, published_only: bool = False) -> list[str]:
    """Categorías distintas en la org (para filtros admin y vitrina)."""
    from models.academic_program import AcademicProgram

    q = AcademicProgram.query.filter_by(organization_id=int(organization_id))
    if published_only:
        q = q.filter_by(status='published')
    rows = q.with_entities(AcademicProgram.category).distinct().all()
    cats = sorted({(r[0] or '').strip() for r in rows if (r[0] or '').strip()})
    ordered = [c for c in CATEGORY_DISPLAY_ORDER if c in cats]
    for c in cats:
        if c not in ordered:
            ordered.append(c)
    return ordered


def apply_program_list_filters(
    query,
    *,
    q: str = '',
    category: str = '',
    program_type: str = '',
    status: str = 'all',
):
    """Filtros compartidos: listado admin y vitrina /programas."""
    from sqlalchemy import or_

    from models.academic_program import AcademicProgram

    status = (status or 'all').strip().lower()
    if status and status != 'all':
        query = query.filter(AcademicProgram.status == status)
    ptype = (program_type or '').strip().lower()
    if ptype and ptype != 'all':
        query = query.filter(AcademicProgram.program_type == ptype)
    cat = (category or '').strip()
    if cat and cat != 'all':
        query = query.filter(AcademicProgram.category == cat)
    term = (q or '').strip()
    if term:
        like = f'%{term}%'
        query = query.filter(
            or_(
                AcademicProgram.name.ilike(like),
                AcademicProgram.slug.ilike(like),
                AcademicProgram.short_description.ilike(like),
                AcademicProgram.category.ilike(like),
            )
        )
    return query


def group_programs_for_template(
    organization_id: int,
    *,
    q: str = '',
    category: str = '',
    program_type: str = '',
) -> list[tuple[str, list]]:
    """Lista (título_sección, programas ORM) para plantilla HTML."""
    from models.academic_program import AcademicProgram

    base = AcademicProgram.query.filter_by(organization_id=int(organization_id), status='published')
    base = apply_program_list_filters(
        base, q=q, category=category, program_type=program_type, status='published'
    )
    rows = base.order_by(AcademicProgram.catalog_sort_order.asc(), AcademicProgram.name.asc()).all()
    buckets: dict[str, list] = {}
    for p in rows:
        cat = (p.category or '').strip() or 'Otros programas'
        buckets.setdefault(cat, []).append(p)
    for cat in buckets:
        buckets[cat].sort(
            key=lambda x: (int(getattr(x, 'catalog_sort_order', 0) or 0), (x.name or '').lower())
        )
    talleres_rows = _published_talleres_programs(rows)
    if talleres_rows:
        buckets['Talleres'] = talleres_rows

    ordered: list[tuple[str, list]] = []
    seen: set[str] = set()
    for cat in CATEGORY_DISPLAY_ORDER:
        if cat in buckets:
            ordered.append((cat, buckets[cat]))
            seen.add(cat)
    for cat in sorted(buckets.keys()):
        if cat not in seen:
            ordered.append((cat, buckets[cat]))
    return ordered


def _programs_in_catalog_order(programs: list) -> list:
    """Ordena filas ORM por categoría (catálogo) y nombre."""
    buckets: dict[str, list] = {}
    for p in programs:
        cat = (p.category or '').strip() or 'Otros programas'
        buckets.setdefault(cat, []).append(p)
    for cat in buckets:
        buckets[cat].sort(
            key=lambda x: (int(getattr(x, 'catalog_sort_order', 0) or 0), (x.name or '').lower())
        )
    flat: list = []
    seen: set[str] = set()
    for cat in CATEGORY_DISPLAY_ORDER:
        if cat in buckets:
            flat.extend(buckets[cat])
            seen.add(cat)
    for cat in sorted(buckets.keys()):
        if cat not in seen:
            flat.extend(buckets[cat])
    return flat


def list_published_programs_ordered(organization_id: int) -> list:
    """Programas publicados en orden de catálogo (categoría + nombre)."""
    flat: list = []
    for _title, programs in group_programs_for_template(int(organization_id)):
        flat.extend(programs)
    return flat


def list_all_programs_ordered(organization_id: int) -> list:
    """Todos los programas de la org (admin), mismo orden que catálogo."""
    from models.academic_program import AcademicProgram

    rows = AcademicProgram.query.filter_by(organization_id=int(organization_id)).all()
    return _programs_in_catalog_order(rows)


def adjacent_published_programs(organization_id: int, slug: str) -> tuple[object | None, object | None]:
    """(anterior, siguiente). Talleres: solo vecinos del bloque Talleres (orden visual WP)."""
    key = (slug or '').strip().lower()
    rows = list_published_programs_ordered(int(organization_id))
    if key in TALLERES_DISPLAY_ORDER:
        by_slug = {(p.slug or '').strip().lower(): p for p in rows}
        talleres = [by_slug[s] for s in TALLERES_DISPLAY_ORDER if s in by_slug]
        idx = next((i for i, p in enumerate(talleres) if (p.slug or '').strip().lower() == key), None)
        if idx is None:
            return None, None
        return (
            talleres[idx - 1] if idx > 0 else None,
            talleres[idx + 1] if idx < len(talleres) - 1 else None,
        )
    idx = next((i for i, p in enumerate(rows) if (p.slug or '').strip().lower() == key), None)
    if idx is None:
        return None, None
    return (rows[idx - 1] if idx > 0 else None, rows[idx + 1] if idx < len(rows) - 1 else None)


def adjacent_programs_by_id(organization_id: int, program_id: int) -> tuple[object | None, object | None]:
    """(anterior, siguiente) por id de programa — incluye draft/archived (admin)."""
    rows = list_all_programs_ordered(int(organization_id))
    pid = int(program_id)
    idx = next((i for i, p in enumerate(rows) if int(p.id) == pid), None)
    if idx is None:
        return None, None
    prev_p = rows[idx - 1] if idx > 0 else None
    next_p = rows[idx + 1] if idx < len(rows) - 1 else None
    return prev_p, next_p
