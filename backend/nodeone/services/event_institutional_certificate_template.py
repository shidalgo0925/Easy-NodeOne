"""Plantillas visuales (Fabric/Canva) para certificados de evento."""

from __future__ import annotations

import copy
import json
import os
from typing import Any

INSTITUTIONAL_KIND = 'institutional_event'


def parse_event_certificate_config(raw: str | None) -> dict[str, Any]:
    if not raw:
        return {}
    s = raw.strip()
    if not s.startswith('{'):
        return {}
    try:
        data = json.loads(s)
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}


def visual_template_id_for_event(event) -> int | None:
    cfg = parse_event_certificate_config(getattr(event, 'certificate_template', None))
    tid = cfg.get('visual_template_id')
    try:
        return int(tid) if tid else None
    except (TypeError, ValueError):
        return None


def link_visual_template_to_event(event, template_id: int) -> None:
    cfg = parse_event_certificate_config(getattr(event, 'certificate_template', None))
    layout_keys = {
        'header_text', 'convenio_text', 'activity_type', 'issue_city', 'primary_color',
        'secondary_color', 'text_color', 'title_color', 'logo_left_url', 'logo_right_url',
        'seal_url', 'signatory_left_name', 'signatory_left_role', 'signatory_left_org',
        'signatory_left_image', 'signatory_right_name', 'signatory_right_role',
        'signatory_right_org', 'signatory_right_image', 'closing_text', 'academic_hours',
    }
    cfg = {k: v for k, v in cfg.items() if k in layout_keys or k == 'visual_template_id'}
    cfg['visual_template_id'] = int(template_id)
    event.certificate_template = json.dumps(cfg, ensure_ascii=False)


def parse_institutional_meta(json_layout_raw: str | dict | None) -> dict[str, Any] | None:
    if not json_layout_raw:
        return None
    try:
        data = json.loads(json_layout_raw) if isinstance(json_layout_raw, str) else json_layout_raw
    except (TypeError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict) or data.get('kind') != INSTITUTIONAL_KIND:
        return None
    return data


def is_institutional_template(template_model) -> bool:
    return parse_institutional_meta(getattr(template_model, 'json_layout', None)) is not None


def parse_visual_layout(json_layout_raw: str | dict | None) -> dict[str, Any] | None:
    if not json_layout_raw:
        return None
    try:
        data = json.loads(json_layout_raw) if isinstance(json_layout_raw, str) else json_layout_raw
    except (TypeError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict) or parse_institutional_meta(data):
        return None
    if not isinstance(data.get('elements'), list):
        return None
    return data


def is_visual_template(template_model) -> bool:
    return parse_visual_layout(getattr(template_model, 'json_layout', None)) is not None


def event_id_from_visual_template(template_model) -> int | None:
    layout = parse_visual_layout(getattr(template_model, 'json_layout', None)) or {}
    meta = layout.get('meta') if isinstance(layout.get('meta'), dict) else {}
    try:
        eid = meta.get('event_id')
        return int(eid) if eid else None
    except (TypeError, ValueError):
        return None


def build_visual_json_layout(*, event_id: int, canvas: dict, elements: list) -> str:
    payload = {
        'canvas': canvas,
        'elements': elements,
        'meta': {'event_id': int(event_id)},
    }
    return json.dumps(payload, ensure_ascii=False)


def resolve_event_org_id(event) -> int:
    from nodeone.modules.events.services.certificates import organization_id_for_event

    return int(organization_id_for_event(event) or 1)


def _default_visual_base_template(CertificateTemplate, org_id: int):
    for t in CertificateTemplate.query.filter_by(organization_id=org_id).order_by(CertificateTemplate.id.asc()).all():
        if is_visual_template(t) and not event_id_from_visual_template(t):
            return t
    return None


def merged_layout_for_event(event, org_id: int) -> dict[str, Any]:
    from nodeone.services.certificate_institutional_pdf import (
        _load_org_layout_defaults,
        _merge_layout,
        _parse_event_layout_override,
    )

    base = _load_org_layout_defaults(int(org_id or 1))
    cfg = parse_event_certificate_config(getattr(event, 'certificate_template', None))
    cfg.pop('visual_template_id', None)
    override = _parse_event_layout_override(json.dumps(cfg) if cfg else None)
    if not override:
        override = {k: v for k, v in cfg.items() if v not in (None, '')}
    return _merge_layout(base, override)


def build_visual_certificate_data(
    *,
    event,
    participant,
    display_name: str,
    cert_number: str,
    verify_url: str,
    issued_at,
    org_id: int,
    app_root: str | None = None,
) -> dict[str, Any]:
    from nodeone.services.certificate_institutional_pdf import (
        body_text_for_type,
        compute_academic_hours,
        format_event_date_range,
        format_issue_date_legal,
    )

    layout = merged_layout_for_event(event, org_id)
    start = getattr(event, 'start_date', None)
    end = getattr(event, 'end_date', None)
    hours = compute_academic_hours(start, end, layout.get('academic_hours'))
    doc = (getattr(participant, 'document_id', None) or '').strip() or 'No registrado'
    program = (getattr(event, 'title', None) or 'Evento').strip()
    pt = (getattr(participant, 'participant_type', None) or 'external').strip().lower()
    activity = (layout.get('activity_type') or 'Diplomado').strip()
    body = body_text_for_type(participant_type=pt, activity_type=activity)
    date_range = format_event_date_range(start, end) or ''
    hours_line = ''
    if hours:
        hours_line = (
            f'con una duración total de {hours:g} horas'
            if hours == int(hours)
            else f'con una duración total de {hours} horas'
        )
    issue_city = (layout.get('issue_city') or 'Panamá').strip()
    url_short = verify_url if len(verify_url) <= 52 else verify_url[:49] + '...'

    def _fmt_d(d):
        if d and hasattr(d, 'strftime'):
            return d.strftime('%d/%m/%Y')
        return ''

    return {
        'participant_name': (display_name or '—').upper(),
        'document_id': doc,
        'program_name': f'"{program.upper()}"',
        'certificate_name': program,
        'body_text': body,
        'event_dates': date_range,
        'start_date': _fmt_d(start),
        'end_date': _fmt_d(end),
        'hours': str(hours) if hours is not None else '',
        'hours_line': hours_line,
        'duration_hours': str(hours) if hours is not None else '',
        'issue_date': issued_at.strftime('%d/%m/%Y'),
        'issue_date_legal': format_issue_date_legal(issued_at, issue_city),
        'certificate_code': cert_number,
        'verification_url': url_short,
        'institution': (layout.get('header_text') or '').strip(),
        'partner_organization': (layout.get('signatory_right_org') or '').strip(),
        'rector_name': (layout.get('signatory_left_name') or '').strip(),
        'academic_director_name': (layout.get('signatory_right_name') or '').strip(),
        'rector_title': (layout.get('signatory_left_role') or 'Rector').strip(),
        'director_title': (layout.get('signatory_right_role') or 'Directora Académica').strip(),
        'logo_left_url': (layout.get('logo_left_url') or '').strip(),
        'logo_right_url': (layout.get('logo_right_url') or '').strip(),
        'seal_url': (layout.get('seal_url') or '').strip(),
        'background_url': (layout.get('background_url') or '').strip(),
    }


def needs_institutional_visual_layout(template) -> bool:
    layout = parse_visual_layout(getattr(template, 'json_layout', None)) or {}
    meta = layout.get('meta') if isinstance(layout.get('meta'), dict) else {}
    return meta.get('layout_kind') != 'institutional_visual'


def strip_missing_layout_asset_urls(layout: dict[str, Any], app_root: str) -> dict[str, Any]:
    """Omite logos/sello cuya ruta /static/... no existe en disco (evita 404 en PDF)."""
    out = dict(layout)
    root = os.path.abspath(app_root or '.')
    for key in ('logo_left_url', 'logo_right_url', 'seal_url'):
        url = (out.get(key) or '').strip()
        if not url:
            continue
        rel = url.lstrip('/')
        if not os.path.isfile(os.path.join(root, rel)):
            out[key] = ''
    return out


def apply_institutional_visual_layout_to_template(
    template,
    event,
    org_id: int,
    *,
    preserve_background: bool = False,
    app_root: str | None = None,
) -> None:
    from nodeone.services.event_certificate_visual_layout import (
        CANVAS_HEIGHT,
        CANVAS_WIDTH,
        build_institutional_visual_layout,
    )

    prev_bg = getattr(template, 'background_image', None) if preserve_background else None
    root = app_root or os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', '..', '..')
    )
    layout = strip_missing_layout_asset_urls(merged_layout_for_event(event, org_id), root)
    visual = build_institutional_visual_layout(layout, event_id=event.id)
    template.json_layout = json.dumps(visual, ensure_ascii=False)
    template.background_image = prev_bg if preserve_background else None
    template.width = CANVAS_WIDTH
    template.height = CANVAS_HEIGHT
    title = (getattr(event, 'title', None) or f'Evento #{event.id}').strip()
    template.name = title[:200]


def _clone_visual_layout_from_template(base_template, event_id: int) -> tuple[dict, str | None, int, int]:
    layout = copy.deepcopy(parse_visual_layout(base_template.json_layout) or {})
    canvas = layout.get('canvas') or {'width': 1024, 'height': 768}
    elements = layout.get('elements') or []
    width = int(getattr(base_template, 'width', None) or canvas.get('width') or 1024)
    height = int(getattr(base_template, 'height', None) or canvas.get('height') or 768)
    visual = {
        'canvas': {'width': width, 'height': height},
        'elements': elements,
        'meta': {'event_id': int(event_id)},
    }
    return visual, getattr(base_template, 'background_image', None), width, height


def migrate_institutional_template_to_visual(template, event, org_id: int, CertificateTemplate) -> bool:
    """Convierte plantilla institucional (formulario) a visual (lienzo Canva)."""
    if not is_institutional_template(template):
        return False
    base = _default_visual_base_template(CertificateTemplate, org_id)
    if not base:
        return False
    visual, bg, width, height = _clone_visual_layout_from_template(base, event.id)
    template.json_layout = json.dumps(visual, ensure_ascii=False)
    template.background_image = bg
    template.width = width
    template.height = height
    title = (getattr(event, 'title', None) or f'Evento #{event.id}').strip()
    template.name = title[:200]
    link_visual_template_to_event(event, template.id)
    return True


def find_visual_template_for_event(CertificateTemplate, event, org_id: int | None = None):
    oid = int(org_id or resolve_event_org_id(event))
    tid = visual_template_id_for_event(event)
    if tid:
        t = CertificateTemplate.query.filter_by(id=int(tid), organization_id=oid).first()
        if t and is_visual_template(t):
            return t
    candidates = []
    for t in CertificateTemplate.query.filter_by(organization_id=oid).all():
        if event_id_from_visual_template(t) == int(event.id) and is_visual_template(t):
            candidates.append(t)
    if candidates:
        t = max(candidates, key=lambda row: row.updated_at or row.created_at)
        link_visual_template_to_event(event, t.id)
        return t
    for t in CertificateTemplate.query.filter_by(organization_id=oid).all():
        meta = parse_institutional_meta(t.json_layout)
        if meta and int(meta.get('event_id') or 0) == int(event.id):
            return t
    return None


def get_fresh_visual_template_for_render(db, CertificateTemplate, event, org_id: int | None = None):
    """Lee plantilla vigente desde BD (sin cache de sesión ORM)."""
    try:
        db.session.expire_all()
    except Exception:
        pass
    return find_visual_template_for_event(CertificateTemplate, event, org_id)


def sync_event_template_link_from_template(db, template) -> int | None:
    """Al guardar plantilla con meta.event_id, actualiza el vínculo del evento."""
    from app import Event

    layout = parse_visual_layout(getattr(template, 'json_layout', None)) or {}
    meta = layout.get('meta') if isinstance(layout.get('meta'), dict) else {}
    eid = meta.get('event_id')
    if not eid:
        return None
    event = Event.query.get(int(eid))
    if not event:
        return None
    link_visual_template_to_event(event, int(template.id))
    db.session.commit()
    return int(event.id)


def list_event_certificate_formats_for_admin(org_id: int) -> list[dict[str, Any]]:
    """Formatos de certificado ligados a eventos (módulo Eventos) para la pantalla admin unificada."""
    from app import CertificateTemplate, Event, EventCertificate

    oid = int(org_id or 1)
    out: list[dict[str, Any]] = []
    for event in Event.query.order_by(Event.id.asc()).all():
        if int(resolve_event_org_id(event)) != oid:
            continue
        tid = visual_template_id_for_event(event)
        if not tid:
            continue
        tpl = CertificateTemplate.query.filter_by(id=int(tid), organization_id=oid).first()
        if not tpl:
            tpl = CertificateTemplate.query.get(int(tid))
        issued = (
            EventCertificate.query.filter_by(event_id=event.id)
            .filter(EventCertificate.status != 'revoked')
            .count()
        )
        edit_path = f'/admin/certificate-templates/editor/{int(tid)}'
        out.append(
            {
                'kind': 'event_module',
                'event_id': int(event.id),
                'name': (event.title or '').strip() or f'Evento #{event.id}',
                'code_prefix': f'EVT-{event.id}',
                'template_id': int(tid),
                'institution': '',
                'is_active': getattr(event, 'publish_status', 'published') != 'archived',
                'verification_enabled': True,
                'requirement_text': f'Participación · evento #{event.id}',
                'issued_count': int(issued),
                'edit_path': edit_path,
                'certificates_url': f'/admin/events/{event.id}/certificates',
                'participants_url': f'/admin/events/{event.id}/participants',
                'template_name': (getattr(tpl, 'name', None) or '').strip() if tpl else '',
            }
        )
    return out


def apply_certificate_template_from_event_form(
    event,
    raw_template_id,
    org_id: int,
    CertificateTemplate,
) -> str | None:
    """Vincula plantilla elegida en el formulario. None = sin selección (auto al guardar)."""
    raw = (raw_template_id or '').strip()
    if not raw:
        return None
    try:
        tid = int(raw)
    except (TypeError, ValueError):
        return 'Seleccione una plantilla de certificado válida'
    if tid <= 0:
        return None
    t = CertificateTemplate.query.filter_by(id=tid, organization_id=int(org_id)).first()
    if not t:
        return 'Plantilla no encontrada para esta organización'
    link_visual_template_to_event(event, tid)
    return None


def list_certificate_templates_for_event_form(CertificateTemplate, org_id: int) -> list[dict]:
    rows = CertificateTemplate.query.filter_by(organization_id=int(org_id)).order_by(
        CertificateTemplate.name.asc(),
        CertificateTemplate.id.asc(),
    ).all()
    return [
        {'id': int(t.id), 'name': ((t.name or '').strip() or f'Plantilla #{t.id}')}
        for t in rows
    ]


def ensure_certificate_template_for_event(db, event) -> str:
    """
    Crea o repara la plantilla visual de un evento con certificado.
    Retorna: created | migrated | repaired | linked | ok
    """
    from app import CertificateTemplate

    org_id = resolve_event_org_id(event)
    existing = find_visual_template_for_event(CertificateTemplate, event, org_id)

    if existing and is_institutional_template(existing):
        apply_institutional_visual_layout_to_template(existing, event, org_id)
        link_visual_template_to_event(event, existing.id)
        return 'migrated'

    if existing and is_visual_template(existing):
        status = 'ok'
        if int(getattr(existing, 'organization_id', None) or 0) != org_id:
            existing.organization_id = org_id
            status = 'repaired'
        if not visual_template_id_for_event(event):
            link_visual_template_to_event(event, existing.id)
            status = 'linked'
        if needs_institutional_visual_layout(existing):
            apply_institutional_visual_layout_to_template(existing, event, org_id)
            status = 'repaired'
        return status

    title = (getattr(event, 'title', None) or f'Evento #{event.id}').strip()
    t = CertificateTemplate(
        organization_id=org_id,
        name=title[:200],
        width=1056,
        height=816,
        background_image=None,
        json_layout='{}',
    )
    db.session.add(t)
    db.session.flush()
    apply_institutional_visual_layout_to_template(t, event, org_id)
    link_visual_template_to_event(event, t.id)
    return 'created'


def ensure_institutional_event_certificate_templates(db, printfn=print) -> None:
    """Crea o migra plantillas visuales editables (lienzo) para eventos con certificado."""
    from app import CertificateTemplate, Event

    events = Event.query.filter_by(has_certificate=True).order_by(Event.id).all()
    if not events:
        return

    created = 0
    migrated = 0
    repaired = 0

    for event in events:
        result = ensure_certificate_template_for_event(db, event)
        if result == 'created':
            created += 1
        elif result == 'migrated':
            migrated += 1
        elif result in ('repaired', 'linked'):
            repaired += 1

    if created or migrated or repaired:
        db.session.commit()
    if created:
        printfn(f'Plantillas visuales de evento creadas: {created}')
    if migrated:
        printfn(f'Plantillas institucionales migradas a visual: {migrated}')
    if repaired:
        printfn(f'Plantillas de evento reparadas/enlazadas: {repaired}')
