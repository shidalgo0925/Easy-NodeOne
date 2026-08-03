"""Añade variables de fin de vigencia a plantillas MEM/PLAN que solo tienen inicio."""

from __future__ import annotations

import copy
import json
import uuid
from typing import Any

_FIN_NAMES = frozenset(
    {
        'membership_end',
        'dia_membresia_fin',
        'mes_membresia_fin',
        'anio_membresia_fin',
        'membership_period',
    }
)

_MIRROR_START_TO_FIN = {
    'dia_membresia_inicio': ('dia_membresia_fin', 35),
    'mes_membresia_inicio': ('mes_membresia_fin', 35),
    'anio_membresia_inicio': ('anio_membresia_fin', 35),
    'membership_start': ('membership_end', 25),
}


def _element_names(elements: list[dict[str, Any]]) -> set[str]:
    return {
        (e.get('name') or '').strip()
        for e in elements
        if (e.get('type') or '').lower() == 'variable'
    }


def ensure_membership_end_variables_in_layout(layout: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    """
    Copia variables de inicio de membresía como fin (desplazadas en Y).
    Devuelve (layout, changed).
    """
    layout = copy.deepcopy(layout or {})
    elements = list(layout.get('elements') or [])
    names = _element_names(elements)
    if names & _FIN_NAMES:
        return layout, False

    added = False
    for el in elements:
        if (el.get('type') or '').lower() != 'variable':
            continue
        src_name = (el.get('name') or '').strip()
        pair = _MIRROR_START_TO_FIN.get(src_name)
        if not pair:
            continue
        fin_name, y_offset = pair
        if fin_name in names:
            continue
        new_el = copy.deepcopy(el)
        new_el['id'] = f'var_{uuid.uuid4().hex[:8]}'
        new_el['name'] = fin_name
        new_el['y'] = int(el.get('y', 0)) + y_offset
        if 'locked_position' in new_el:
            new_el['locked_position'] = True
        elements.append(new_el)
        names.add(fin_name)
        added = True

    if added:
        layout['elements'] = elements
    return layout, added


def repair_plan_basic_certificate_templates(db, organization_id: int | None = None) -> dict:
    """
    Para cada certificate_event PLAN-BASIC con plantilla visual, añade variables de fin si faltan.
    """
    from app import CertificateEvent, CertificateTemplate

    stats = {'templates_checked': 0, 'templates_updated': 0, 'event_ids': []}
    q = CertificateEvent.query.filter(
        CertificateEvent.is_active.is_(True),
        CertificateEvent.code_prefix.ilike('PLAN-BASIC%'),
        CertificateEvent.template_id.isnot(None),
    )
    if organization_id is not None:
        q = q.filter_by(organization_id=int(organization_id))

    seen_tpl: set[int] = set()
    for ev in q.all():
        tid = int(ev.template_id)
        if tid in seen_tpl:
            continue
        seen_tpl.add(tid)
        tpl = CertificateTemplate.query.get(tid)
        if not tpl or not (tpl.json_layout or '').strip():
            continue
        stats['templates_checked'] += 1
        try:
            layout = json.loads(tpl.json_layout) if isinstance(tpl.json_layout, str) else tpl.json_layout
        except Exception:
            continue
        new_layout, changed = ensure_membership_end_variables_in_layout(layout)
        if not changed:
            continue
        tpl.json_layout = json.dumps(new_layout, ensure_ascii=False)
        db.session.add(tpl)
        stats['templates_updated'] += 1
        stats['event_ids'].append(int(ev.id))

    if stats['templates_updated']:
        db.session.commit()
    return stats
