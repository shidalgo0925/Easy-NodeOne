"""Fechas y títulos de diplomados publicados (fuente única para calendario WP)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from models.academic_program import AcademicProgram, format_start_date_es
from nodeone.modules.academic_enrollment.program_academic_pdf import is_diplomado_program


def list_diplomado_inicios_payload(organization_id: int) -> dict[str, Any]:
    """JSON para WordPress [iius_diplomados_calendario] y sync admin."""
    rows = (
        AcademicProgram.query.filter_by(organization_id=int(organization_id), status='published')
        .order_by(AcademicProgram.catalog_sort_order.asc(), AcademicProgram.name.asc())
        .all()
    )
    rows = sorted(
        [p for p in rows if is_diplomado_program(p) and p.start_date],
        key=lambda p: (p.start_date, int(getattr(p, 'catalog_sort_order', 0) or 0)),
    )
    by_heading: dict[str, dict[str, str]] = {}
    programs: list[dict[str, str]] = []

    for p in rows:
        slug = (p.slug or '').strip().lower()
        if not slug:
            continue
        iso = p.start_date.strftime('%Y-%m-%d')
        texto = format_start_date_es(p.start_date) or iso
        name = (p.name or '').strip()
        entry = {
            'fecha_iso': iso,
            'fecha_texto': texto,
            'name': name,
            'title': name,
        }
        by_heading[slug] = entry
        programs.append({'slug': slug, **entry})

    return {
        'ok': True,
        'updated': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
        'timezone': 'UTC',
        'organization_id': int(organization_id),
        'by_heading': by_heading,
        'programs': programs,
        'count': len(programs),
    }
