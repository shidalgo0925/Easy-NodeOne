"""Garantiza formato (certificate_events) y plantilla visual para eventos y planes."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from nodeone.services.certificate_membership_rules import (
    _SKIP_PLAN_SLUGS,
    _plan_code_prefix,
    _purge_orphan_certificate_event_formats,
)

STATUS_CREATED = 'CREATED'
STATUS_REUSED = 'REUSED'
STATUS_REPAIRED = 'REPAIRED'
STATUS_DEACTIVATED = 'DEACTIVATED'


def _org_layout_defaults(org_id: int) -> dict[str, Any]:
    from nodeone.services.certificate_institutional_pdf import _load_org_layout_defaults

    return _load_org_layout_defaults(int(org_id or 1))


def _org_name(org_id: int) -> str:
    try:
        from app import SaasOrganization

        org = SaasOrganization.query.get(int(org_id))
        return (org.name or '').strip() if org else ''
    except Exception:
        return ''


def find_event_certificate_format(CertificateEvent, event, org_id: int | None = None):
    """Busca formato por event_required_id (vínculo canónico evento ↔ formato)."""
    row = CertificateEvent.query.filter_by(event_required_id=int(event.id)).first()
    if row:
        return row
    if org_id is not None:
        return CertificateEvent.query.filter_by(
            organization_id=int(org_id),
            event_required_id=int(event.id),
        ).first()
    return None


def _fill_empty_format_fields(fmt, event, org_id: int) -> bool:
    """Completa solo campos vacíos del formato institucional."""
    changed = False
    layout = _org_layout_defaults(org_id)
    title = (getattr(event, 'title', None) or f'Evento #{event.id}').strip()

    if not (fmt.name or '').strip():
        fmt.name = title[:200]
        changed = True
    if not (fmt.code_prefix or '').strip():
        fmt.code_prefix = 'EVT'
        changed = True
    if not fmt.institution:
        inst = (layout.get('header_text') or _org_name(org_id) or '').strip()
        if inst:
            fmt.institution = inst[:200]
            changed = True
    if not fmt.partner_organization and layout.get('signatory_right_org'):
        fmt.partner_organization = str(layout['signatory_right_org'])[:200]
        changed = True
    if not fmt.rector_name and layout.get('signatory_left_name'):
        fmt.rector_name = str(layout['signatory_left_name'])[:200]
        changed = True
    if not fmt.academic_director_name and layout.get('signatory_right_name'):
        fmt.academic_director_name = str(layout['signatory_right_name'])[:200]
        changed = True
    for attr, key in (
        ('logo_left_url', 'logo_left_url'),
        ('logo_right_url', 'logo_right_url'),
        ('seal_url', 'seal_url'),
    ):
        if not getattr(fmt, attr, None) and layout.get(key):
            setattr(fmt, attr, str(layout[key])[:500])
            changed = True
    if fmt.start_date is None and getattr(event, 'start_date', None):
        fmt.start_date = event.start_date
        changed = True
    if fmt.end_date is None and getattr(event, 'end_date', None):
        fmt.end_date = event.end_date
        changed = True
    if fmt.duration_hours is None and getattr(event, 'start_date', None) and getattr(event, 'end_date', None):
        from nodeone.services.certificate_institutional_pdf import compute_academic_hours

        fmt.duration_hours = compute_academic_hours(event.start_date, event.end_date, None)
        changed = True
    if not fmt.is_active:
        fmt.is_active = True
        changed = True
    return changed


def ensure_event_certificate_format(db, event, org_id: int) -> tuple[Any, str]:
    from app import CertificateEvent

    existing = find_event_certificate_format(CertificateEvent, event, org_id)
    if existing:
        if _fill_empty_format_fields(existing, event, org_id):
            return existing, STATUS_REPAIRED
        return existing, STATUS_REUSED

    layout = _org_layout_defaults(org_id)
    title = (getattr(event, 'title', None) or f'Evento #{event.id}').strip()
    fmt = CertificateEvent(
        organization_id=int(org_id),
        name=title[:200],
        event_required_id=int(event.id),
        membership_required_id=None,
        code_prefix='EVT',
        is_active=True,
        verification_enabled=True,
        institution=(layout.get('header_text') or _org_name(org_id) or '')[:200] or None,
        partner_organization=(layout.get('signatory_right_org') or '')[:200] or None,
        rector_name=(layout.get('signatory_left_name') or '')[:200] or None,
        academic_director_name=(layout.get('signatory_right_name') or '')[:200] or None,
        logo_left_url=(layout.get('logo_left_url') or '')[:500] or None,
        logo_right_url=(layout.get('logo_right_url') or '')[:500] or None,
        seal_url=(layout.get('seal_url') or '')[:500] or None,
        start_date=getattr(event, 'start_date', None),
        end_date=getattr(event, 'end_date', None),
    )
    if fmt.start_date and fmt.end_date:
        from nodeone.services.certificate_institutional_pdf import compute_academic_hours

        fmt.duration_hours = compute_academic_hours(fmt.start_date, fmt.end_date, None)
    db.session.add(fmt)
    db.session.flush()
    return fmt, STATUS_CREATED


def _template_has_user_content(template) -> bool:
    from nodeone.services.event_institutional_certificate_template import (
        is_institutional_template,
        is_visual_template,
        parse_visual_layout,
    )

    if is_institutional_template(template):
        return True
    if not is_visual_template(template):
        return bool((getattr(template, 'json_layout', None) or '').strip() not in ('', '{}'))
    layout = parse_visual_layout(template.json_layout) or {}
    elements = layout.get('elements') or []
    return len(elements) > 0


def ensure_event_visual_template(db, event, org_id: int) -> tuple[Any | None, str]:
    """
    Garantiza plantilla visual. Nunca sobrescribe json_layout de plantilla existente con contenido.
    """
    from app import CertificateTemplate

    from nodeone.services.event_institutional_certificate_template import (
        apply_institutional_visual_layout_to_template,
        find_visual_template_for_event,
        is_institutional_template,
        is_visual_template,
        link_visual_template_to_event,
        migrate_institutional_template_to_visual,
        visual_template_id_for_event,
    )

    existing = find_visual_template_for_event(CertificateTemplate, event, org_id)
    if existing:
        status = STATUS_REUSED
        if int(getattr(existing, 'organization_id', None) or 0) != int(org_id):
            existing.organization_id = int(org_id)
            status = STATUS_REPAIRED
        if not visual_template_id_for_event(event):
            link_visual_template_to_event(event, existing.id)
            status = STATUS_REPAIRED
        if is_institutional_template(existing) and not _template_has_user_content(existing):
            if migrate_institutional_template_to_visual(existing, event, org_id, CertificateTemplate):
                status = STATUS_REPAIRED
        return existing, status

    title = (getattr(event, 'title', None) or f'Evento #{event.id}').strip()
    t = CertificateTemplate(
        organization_id=int(org_id),
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
    return t, STATUS_CREATED


def _link_format_to_template(fmt, template) -> bool:
    if template is None:
        return False
    tid = int(template.id)
    if getattr(fmt, 'template_id', None) == tid:
        return False
    if getattr(fmt, 'template_id', None) in (None, 0):
        fmt.template_id = tid
        return True
    return False


def ensure_certificate_assets_for_event(db, event, *, commit: bool = False) -> dict[str, Any]:
    """Garantiza formato + plantilla para un evento con has_certificate=true."""
    from nodeone.services.event_institutional_certificate_template import resolve_event_org_id

    org_id = resolve_event_org_id(event)
    result: dict[str, Any] = {
        'event_id': int(event.id),
        'format_status': None,
        'template_status': None,
        'certificate_event_id': None,
        'template_id': None,
    }

    if not getattr(event, 'has_certificate', False):
        deactivated = deactivate_certificate_assets_for_event(db, event, commit=False)
        result['format_status'] = deactivated
        return result

    fmt, fmt_status = ensure_event_certificate_format(db, event, org_id)
    tpl, tpl_status = ensure_event_visual_template(db, event, org_id)
    if _link_format_to_template(fmt, tpl):
        if fmt_status == STATUS_REUSED:
            fmt_status = STATUS_REPAIRED

    result.update(
        {
            'format_status': fmt_status,
            'template_status': tpl_status,
            'certificate_event_id': int(fmt.id),
            'template_id': int(tpl.id) if tpl else None,
        }
    )
    if commit:
        db.session.commit()
    return result


def resolve_event_certificate_org_id(event, *, admin_scope_org_id: int) -> int:
    """Org canónica del evento (creador); fallback al scope admin en altas sin id."""
    if event and getattr(event, 'id', None):
        from nodeone.services.event_institutional_certificate_template import resolve_event_org_id

        return int(resolve_event_org_id(event))
    return int(admin_scope_org_id or 1)


def sync_event_certificate_on_save(
    db,
    event,
    *,
    has_certificate: bool,
    template_form_value: str | None,
    admin_scope_org_id: int,
) -> tuple[bool, str | None, dict[str, Any]]:
    """
    Único punto al guardar create/edit: desactiva o garantiza formato + plantilla.
    El formato se crea antes de validar la plantilla del formulario (nunca rollback por plantilla).
    """
    from app import CertificateTemplate

    from nodeone.services.event_institutional_certificate_template import (
        apply_certificate_template_from_event_form,
    )

    empty: dict[str, Any] = {}
    if not has_certificate:
        deactivate_certificate_assets_for_event(db, event, commit=False)
        return True, None, empty

    assets = ensure_certificate_assets_for_event(db, event, commit=False)
    org_id = resolve_event_certificate_org_id(event, admin_scope_org_id=admin_scope_org_id)
    err = apply_certificate_template_from_event_form(
        event,
        template_form_value,
        org_id,
        CertificateTemplate,
    )
    return True, err, assets


def ensure_all_event_certificate_formats(db, *, commit: bool = True) -> dict[str, Any]:
    """Crea/repara formatos+plantillas de TODOS los eventos con has_certificate (sin filtro org)."""
    from app import Event

    stats: dict[str, Any] = {
        STATUS_CREATED: 0,
        STATUS_REPAIRED: 0,
        STATUS_REUSED: 0,
        'events': [],
    }
    for event in Event.query.filter_by(has_certificate=True).order_by(Event.id).all():
        r = ensure_certificate_assets_for_event(db, event, commit=False)
        stats['events'].append(r)
        for key in ('format_status', 'template_status'):
            st = r.get(key) or STATUS_REUSED
            if st in stats:
                stats[st] = int(stats.get(st, 0)) + 1
    if commit:
        db.session.commit()
    return stats


def event_certificate_ui_context(
    db,
    CertificateTemplate,
    event=None,
    *,
    admin_scope_org_id: int,
    ensure: bool = False,
) -> dict[str, Any]:
    """Contexto compartido formulario y pantalla certificados (plantillas + id formato)."""
    from app import CertificateEvent

    from nodeone.services.event_institutional_certificate_template import (
        list_certificate_templates_for_event_form,
        visual_template_id_for_event,
    )

    org_id = resolve_event_certificate_org_id(event, admin_scope_org_id=admin_scope_org_id)
    certificate_event_id = None
    if event and getattr(event, 'has_certificate', False) and getattr(event, 'id', None):
        if ensure:
            assets = ensure_certificate_assets_for_event(db, event, commit=True)
            certificate_event_id = assets.get('certificate_event_id')
        if certificate_event_id is None:
            fmt = find_event_certificate_format(CertificateEvent, event, org_id)
            certificate_event_id = int(fmt.id) if fmt else None

    return {
        'certificate_templates': list_certificate_templates_for_event_form(
            CertificateTemplate, org_id
        ),
        'selected_certificate_template_id': (
            visual_template_id_for_event(event) if event else None
        ),
        'certificate_event_id': certificate_event_id,
    }


def deactivate_certificate_assets_for_event(db, event, *, commit: bool = False) -> str:
    """Desactiva formato vinculado; no borra plantilla ni emisiones."""
    from app import CertificateEvent

    from nodeone.services.event_institutional_certificate_template import resolve_event_org_id

    org_id = resolve_event_org_id(event)
    fmt = find_event_certificate_format(CertificateEvent, event, org_id)
    if fmt and fmt.is_active:
        fmt.is_active = False
        if commit:
            db.session.commit()
        return STATUS_DEACTIVATED
    if commit:
        db.session.commit()
    return STATUS_REUSED


def ensure_plan_certificate_format(db, org_id: int, plan) -> str:
    """Un formato PLAN-* por plan comercial activo."""
    from app import CertificateEvent

    oid = int(org_id)
    slug = (plan.slug or '').strip().lower()
    if not slug or slug in _SKIP_PLAN_SLUGS:
        return STATUS_REUSED

    code_prefix = _plan_code_prefix(slug)
    existing = CertificateEvent.query.filter(
        CertificateEvent.organization_id == oid,
        CertificateEvent.membership_required_id == int(plan.id),
    ).first()
    if existing:
        changed = False
        if not existing.is_active:
            existing.is_active = True
            changed = True
        if not (existing.name or '').strip():
            existing.name = f'Certificado de Membresía {plan.name}'
            changed = True
        expected_prefix = _plan_code_prefix(slug)
        if (existing.code_prefix or '').strip().upper() != expected_prefix:
            existing.code_prefix = expected_prefix
            changed = True
        return STATUS_REPAIRED if changed else STATUS_REUSED

    db.session.add(
        CertificateEvent(
            organization_id=oid,
            name=f'Certificado de Membresía {plan.name}',
            is_active=True,
            verification_enabled=True,
            code_prefix=code_prefix,
            membership_required_id=int(plan.id),
            event_required_id=None,
        )
    )
    return STATUS_CREATED


def ensure_certificate_assets_for_org(db, org_id: int, *, commit: bool = True) -> dict[str, Any]:
    """Planes comerciales + eventos con certificado de una organización."""
    from app import Certificate, CertificateEvent, CertificateTemplate, Event, MembershipPlan, SaasOrganization

    oid = int(org_id)
    stats: dict[str, Any] = {
        'organization_id': oid,
        'plans': {STATUS_CREATED: 0, STATUS_REUSED: 0, STATUS_REPAIRED: 0},
        'events': {STATUS_CREATED: 0, STATUS_REUSED: 0, STATUS_REPAIRED: 0, STATUS_DEACTIVATED: 0},
        'orphans': {},
    }
    if SaasOrganization.query.get(oid) is None:
        return stats

    CertificateEvent.__table__.create(db.engine, checkfirst=True)
    Certificate.__table__.create(db.engine, checkfirst=True)
    CertificateTemplate.__table__.create(db.engine, checkfirst=True)

    for plan in MembershipPlan.query.filter_by(organization_id=oid, is_active=True).order_by(
        MembershipPlan.display_order, MembershipPlan.level, MembershipPlan.id
    ):
        st = ensure_plan_certificate_format(db, oid, plan)
        stats['plans'][st] = stats['plans'].get(st, 0) + 1

    legacy = CertificateEvent.query.filter(
        CertificateEvent.organization_id == oid,
        CertificateEvent.membership_required_id.is_(None),
        CertificateEvent.event_required_id.is_(None),
        CertificateEvent.code_prefix.in_(['MEM', 'mem', 'REG', 'reg']),
    ).all()
    for ev in legacy:
        ev.is_active = False

    stats['orphans'] = _purge_orphan_certificate_event_formats(db, oid)

    for event in Event.query.filter_by(has_certificate=True).order_by(Event.id).all():
        from nodeone.services.event_institutional_certificate_template import resolve_event_org_id

        if resolve_event_org_id(event) != oid:
            continue
        r = ensure_certificate_assets_for_event(db, event, commit=False)
        fs = r.get('format_status') or STATUS_REUSED
        ts = r.get('template_status') or STATUS_REUSED
        for st in (fs, ts):
            if st in stats['events']:
                stats['events'][st] = stats['events'].get(st, 0) + 1

    if commit:
        db.session.commit()
    return stats


def repair_certificates_job(db, printfn=print) -> dict[str, Any]:
    """Cron nocturno: repara formatos/plantillas faltantes por org activa."""
    from app import SaasOrganization

    totals: dict[str, Any] = {'organizations': 0, 'details': []}
    for org in SaasOrganization.query.filter_by(is_active=True).order_by(SaasOrganization.id).all():
        oid = int(org.id)
        try:
            stats = ensure_certificate_assets_for_org(db, oid, commit=True)
            totals['organizations'] += 1
            totals['details'].append(stats)
            printfn(
                f'[repair_certificates] org={oid} '
                f"plans_created={stats['plans'].get(STATUS_CREATED, 0)} "
                f"events_created={stats['events'].get(STATUS_CREATED, 0)} "
                f"events_repaired={stats['events'].get(STATUS_REPAIRED, 0)}"
            )
        except Exception as exc:
            printfn(f'[repair_certificates] org={oid} error: {exc}')
            try:
                db.session.rollback()
            except Exception:
                pass
    return totals


def certificate_event_delete_blocked(ev) -> str | None:
    """Bloquea DELETE de formatos vinculados o con emisiones."""
    if ev.membership_required_id is not None or ev.event_required_id is not None:
        return (
            'Este formato está vinculado a un plan o evento. '
            'Desactive primero la opción de certificado antes de eliminarlo.'
        )
    from app import Certificate

    if Certificate.query.filter_by(certificate_event_id=int(ev.id)).count() > 0:
        return (
            'Este formato tiene certificados emitidos. '
            'Desactive el formato en lugar de eliminarlo.'
        )
    return None


def certificate_template_delete_blocked(template) -> str | None:
    """Bloquea DELETE de plantillas en uso."""
    from app import Certificate, CertificateEvent, Event

    from nodeone.services.event_institutional_certificate_template import (
        event_id_from_visual_template,
        parse_event_certificate_config,
        visual_template_id_for_event,
    )

    tid = int(template.id)
    if CertificateEvent.query.filter_by(template_id=tid).count() > 0:
        return 'Esta plantilla está siendo utilizada por un certificado activo.'

    eid = event_id_from_visual_template(template)
    if eid and Event.query.get(int(eid)):
        return 'Esta plantilla está siendo utilizada por un certificado activo.'

    for event in Event.query.filter(Event.certificate_template.isnot(None)).all():
        cfg = parse_event_certificate_config(getattr(event, 'certificate_template', None))
        try:
            if int(cfg.get('visual_template_id') or 0) == tid:
                return 'Esta plantilla está siendo utilizada por un certificado activo.'
        except (TypeError, ValueError):
            continue

    linked_events = CertificateEvent.query.filter(
        CertificateEvent.event_required_id.isnot(None),
        CertificateEvent.template_id == tid,
    ).count()
    if linked_events:
        return 'Esta plantilla está siendo utilizada por un certificado activo.'

    return None
