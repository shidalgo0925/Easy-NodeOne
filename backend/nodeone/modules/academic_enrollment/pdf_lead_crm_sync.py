"""Sincroniza leads confirmados de PDF académico al CRM (crm_lead)."""

from __future__ import annotations

from datetime import datetime


def sync_confirmed_pdf_lead_to_crm(lead, program=None) -> int | None:
    """Crea o actualiza un CrmLead tras confirmar el correo. Retorna crm_lead.id."""
    if lead is None:
        return None
    if getattr(lead, 'crm_lead_id', None):
        return int(lead.crm_lead_id)

    from nodeone.core.db import db
    from nodeone.modules.crm_api.models import CrmLead, CrmStage
    from nodeone.modules.crm_api.routes import _ensure_default_stages, _ensure_tables

    org_id = int(lead.organization_id)
    _ensure_tables()
    _ensure_default_stages(org_id)

    stage = (
        CrmStage.query.filter_by(organization_id=org_id, is_won=False, is_lost=False)
        .order_by(CrmStage.sequence.asc())
        .first()
    )
    if stage is None:
        return None

    program_name = (getattr(program, 'name', None) or lead.program_slug or 'Programa').strip()
    slug = (lead.program_slug or '').strip()
    lines = [
        f'PDF programa académico confirmado ({datetime.utcnow().strftime("%Y-%m-%d %H:%M")} UTC).',
        f'Programa: {program_name}',
    ]
    if slug:
        lines.append(f'Slug: {slug}')
    if lead.country:
        lines.append(f'País: {lead.country}')
    if lead.company:
        lines.append(f'Empresa: {lead.company}')
    if lead.message:
        lines.append(f'Mensaje: {lead.message}')
    utm = '/'.join(
        x for x in (lead.utm_source, lead.utm_medium, lead.utm_campaign) if x
    )
    if utm:
        lines.append(f'UTM: {utm}')
    note = '\n'.join(lines)

    email_norm = (lead.email or '').strip().lower()
    existing = None
    if email_norm:
        existing = (
            CrmLead.query.filter_by(organization_id=org_id, email=email_norm, active=True)
            .order_by(CrmLead.id.desc())
            .first()
        )

    if existing is not None:
        prev = (existing.description or '').strip()
        if note not in prev:
            existing.description = f'{prev}\n\n---\n{note}'.strip() if prev else note
        if lead.phone and not (existing.phone or '').strip():
            existing.phone = lead.phone
        if lead.company and not (existing.company_name or '').strip():
            existing.company_name = lead.company
        crm_id = existing.id
    else:
        row = CrmLead(
            organization_id=org_id,
            lead_type='lead',
            name=(lead.name or email_norm or 'Lead PDF')[:255],
            contact_name=(lead.name or '')[:255] or None,
            company_name=(lead.company or '')[:255] or None,
            email=email_norm or None,
            phone=(lead.phone or '')[:80] or None,
            stage_id=stage.id,
            user_id=None,
            expected_revenue=0.0,
            probability=float(stage.probability_default or 10),
            priority='medium',
            source=((lead.source or 'wp_landing_pdf')[:80]),
            description=note,
        )
        db.session.add(row)
        db.session.flush()
        crm_id = row.id

    lead.crm_lead_id = int(crm_id)
    db.session.commit()
    return int(crm_id)
