"""Datos unificados para plantillas visuales de certificado (editor Canva → HTML/PDF)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

# Variables cuyo valor es URL de imagen (render como <img>, no texto).
IMAGE_CERT_VARIABLES = frozenset(
    {
        'background_url',
        'logo_left_url',
        'logo_right_url',
        'seal_url',
    }
)


def _fmt_date(val) -> str:
    if val is None or val == '':
        return ''
    if isinstance(val, str):
        s = val.strip()
        if not s:
            return ''
        for fmt in ('%Y-%m-%d', '%d/%m/%Y'):
            try:
                return datetime.strptime(s[:10], fmt).strftime('%d/%m/%Y')
            except ValueError:
                continue
        return s[:10]
    if hasattr(val, 'strftime'):
        return val.strftime('%d/%m/%Y')
    return str(val)


def _membership_plan_label(event_like) -> str:
    mid = getattr(event_like, 'membership_required_id', None)
    if not mid:
        return ''
    try:
        from app import MembershipPlan

        plan = MembershipPlan.query.get(int(mid))
        if not plan:
            return ''
        return (getattr(plan, 'name', None) or getattr(plan, 'slug', None) or '').strip()
    except Exception:
        return ''


def _hours_line(hours) -> str:
    if hours is None or hours == '':
        return ''
    try:
        h = float(hours)
    except (TypeError, ValueError):
        return ''
    if h <= 0:
        return ''
    if h == int(h):
        return f'con una duración total de {int(h):g} horas'
    return f'con una duración total de {h:g} horas'


def build_certificate_template_data(
    event_like,
    *,
    participant_name: str = '',
    document_id: str = '',
    program_name: str | None = None,
    certificate_code: str = '',
    verification_url: str = '',
    issue_date: datetime | str | None = None,
    membership_type: str = '',
    membership_start: str = '',
    membership_end: str = '',
    body_text: str = '',
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Mapa completo de variables del editor ↔ carátula (CertificateEvent) + titular.

    Campos de carátula: institution, partner_organization, rector_name,
    academic_director_name, duration_hours, start_date, end_date, logos, sello, fondo,
    code_prefix, membership_required (como membership_plan_required).
    """
    from nodeone.services.certificate_institutional_pdf import (
        format_event_date_range,
        format_issue_date_legal,
    )

    name = (program_name or getattr(event_like, 'name', None) or 'Certificado').strip()
    institution = (getattr(event_like, 'institution', None) or '').strip()
    partner = (getattr(event_like, 'partner_organization', None) or '').strip()
    rector = (getattr(event_like, 'rector_name', None) or '').strip()
    director = (getattr(event_like, 'academic_director_name', None) or '').strip()
    prefix = (getattr(event_like, 'code_prefix', None) or '').strip()

    start_raw = getattr(event_like, 'start_date', None)
    end_raw = getattr(event_like, 'end_date', None)
    start_fmt = _fmt_date(start_raw)
    end_fmt = _fmt_date(end_raw)

    hours_val = getattr(event_like, 'duration_hours', None)
    if hours_val is None or hours_val == '':
        hours_val = ''

    if issue_date is None:
        issued = datetime.utcnow()
    elif isinstance(issue_date, str):
        try:
            issued = datetime.strptime(issue_date[:10], '%Y-%m-%d')
        except ValueError:
            issued = datetime.utcnow()
    else:
        issued = issue_date

    issue_str = issued.strftime('%d/%m/%Y')
    issue_legal = format_issue_date_legal(issued, 'Panamá')

    event_range = format_event_date_range(start_raw, end_raw) or ''
    if not event_range and start_fmt and end_fmt:
        event_range = f'del {start_fmt} al {end_fmt}'
    elif not event_range and start_fmt:
        event_range = start_fmt

    m_start = _fmt_date(membership_start) if membership_start else ''
    m_end = _fmt_date(membership_end) if membership_end else ''
    m_period = ''
    if m_start and m_end:
        m_period = f'desde el {m_start} hasta el {m_end}'
    elif m_start:
        m_period = f'desde el {m_start}'
    elif m_end:
        m_period = f'hasta el {m_end}'

    data: dict[str, Any] = {
        # Titular / emisión
        'participant_name': (participant_name or 'Nombre de Ejemplo').strip(),
        'document_id': (document_id or 'No registrado').strip(),
        'certificate_code': certificate_code or 'PREVIEW-0000',
        'verification_url': verification_url or '',
        'issue_date': issue_str,
        'issue_date_legal': issue_legal,
        # Carátula — textos
        'certificate_name': name,
        'program_name': name,
        'code_prefix': prefix,
        'institution': institution,
        'partner_organization': partner,
        'rector_name': rector,
        'academic_director_name': director,
        'rector_title': 'Rector',
        'director_title': 'Directora Académica',
        'duration_hours': str(hours_val) if hours_val != '' else '',
        'hours': str(hours_val) if hours_val != '' else '',
        'hours_line': _hours_line(hours_val),
        'start_date': start_fmt,
        'end_date': end_fmt,
        'event_dates': event_range,
        'membership_plan_required': _membership_plan_label(event_like),
        'body_text': (body_text or '').strip(),
        # Membresía del titular (no carátula; necesario plantillas MEM)
        'membership_type': (membership_type or '').strip(),
        'membership_start': m_start,
        'membership_end': m_end,
        'membership_period': m_period,
        # Carátula — imágenes (URLs relativas /static/...)
        'background_url': (getattr(event_like, 'background_url', None) or '').strip(),
        'logo_left_url': (getattr(event_like, 'logo_left_url', None) or '').strip(),
        'logo_right_url': (getattr(event_like, 'logo_right_url', None) or '').strip(),
        'seal_url': (getattr(event_like, 'seal_url', None) or '').strip(),
    }
    if extra:
        for k, v in extra.items():
            if v is not None:
                data[k] = v
    return data
