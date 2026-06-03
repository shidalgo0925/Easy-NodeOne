"""Lógica de negocio — Contactos."""

from __future__ import annotations

import re
from typing import Any

from sqlalchemy import or_

from models.contact import Contact
from nodeone.core.db import db

_EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')

CONTACT_TYPES = ('person', 'company', 'consumer_final')
ID_TYPES = ('ruc', 'cedula', 'passport', 'consumer_final')


class ContactValidationError(ValueError):
    pass


def _norm(s: str | None) -> str:
    return (s or '').strip()


def validate_contact_payload(data: dict[str, Any], *, organization_id: int, exclude_id: int | None = None) -> dict[str, Any]:
    contact_type = _norm(data.get('contact_type')) or 'person'
    if contact_type not in CONTACT_TYPES:
        raise ContactValidationError('Tipo de contacto no válido.')

    identification_type = _norm(data.get('identification_type')) or 'consumer_final'
    if identification_type not in ID_TYPES:
        raise ContactValidationError('Tipo de identificación no válido.')

    display_name = _norm(data.get('display_name'))
    company_name = _norm(data.get('company_name'))
    first_name = _norm(data.get('first_name'))
    last_name = _norm(data.get('last_name'))

    if not display_name:
        if contact_type == 'company':
            display_name = company_name or _norm(data.get('commercial_name'))
        else:
            display_name = f'{first_name} {last_name}'.strip() or _norm(data.get('email'))
    if not display_name:
        raise ContactValidationError('El nombre para mostrar es obligatorio.')

    if contact_type == 'company' and not company_name:
        raise ContactValidationError('Para empresa, la razón social (company_name) es obligatoria.')

    tax_id = _norm(data.get('tax_id')) or None
    dv = _norm(data.get('dv')) or None
    email = _norm(data.get('email')).lower() or None

    if email and not _EMAIL_RE.match(email):
        raise ContactValidationError('El correo electrónico no tiene un formato válido.')

    if identification_type == 'ruc' and not tax_id:
        raise ContactValidationError('El RUC es obligatorio para identificación tipo RUC.')

    if identification_type == 'consumer_final':
        tax_id = None
        dv = None
        if contact_type != 'consumer_final':
            contact_type = 'consumer_final'

    if tax_id and identification_type != 'consumer_final':
        dup = find_fiscal_duplicate(organization_id, identification_type, tax_id, dv, exclude_id=exclude_id)
        if dup:
            raise ContactValidationError(
                f'Ya existe un contacto con la misma identificación fiscal (#{dup.id} — {dup.display_name}).'
            )

    payload = {
        'contact_type': contact_type,
        'display_name': display_name[:300],
        'first_name': first_name[:120] or None,
        'last_name': last_name[:120] or None,
        'company_name': company_name[:300] or None,
        'commercial_name': _norm(data.get('commercial_name'))[:300] or None,
        'email': email[:255] if email else None,
        'phone': _norm(data.get('phone'))[:50] or None,
        'mobile': _norm(data.get('mobile'))[:50] or None,
        'country': (_norm(data.get('country')) or 'PA')[:8],
        'province': _norm(data.get('province'))[:120] or None,
        'district': _norm(data.get('district'))[:120] or None,
        'township': _norm(data.get('township'))[:120] or None,
        'fiscal_address': _norm(data.get('fiscal_address')) or None,
        'identification_type': identification_type,
        'tax_id': tax_id[:80] if tax_id else None,
        'dv': dv[:10] if dv else None,
        'is_customer': bool(data.get('is_customer')),
        'is_supplier': bool(data.get('is_supplier')),
        'is_member': bool(data.get('is_member')),
        'is_student': bool(data.get('is_student')),
        'is_participant': bool(data.get('is_participant')),
        'is_instructor': bool(data.get('is_instructor')),
        'is_donor': bool(data.get('is_donor')),
        'is_employee': bool(data.get('is_employee')),
        'is_tax_exempt': bool(data.get('is_tax_exempt')),
        'active': bool(data.get('active', True)),
    }
    # Foto: solo vía subida en rutas admin (_apply_contact_photo), no borrar en updates de texto.
    if 'image_url' in data:
        payload['image_url'] = _norm_image_url(data.get('image_url'))
    return payload


def _norm_image_url(value: Any) -> str | None:
    url = _norm(str(value) if value is not None else None)
    if not url:
        return None
    if len(url) > 500:
        url = url[:500]
    if url.startswith('/static/') or url.startswith('http://') or url.startswith('https://'):
        return url
    raise ContactValidationError('URL de imagen no válida.')


def find_fiscal_duplicate(
    organization_id: int,
    identification_type: str,
    tax_id: str,
    dv: str | None,
    *,
    exclude_id: int | None = None,
) -> Contact | None:
    if identification_type == 'consumer_final' or not (tax_id or '').strip():
        return None
    q = Contact.query.filter_by(
        organization_id=int(organization_id),
        identification_type=identification_type,
        tax_id=tax_id.strip(),
    )
    dv_norm = (dv or '').strip()
    if dv_norm:
        q = q.filter(Contact.dv == dv_norm)
    else:
        q = q.filter(or_(Contact.dv.is_(None), Contact.dv == ''))
    if exclude_id:
        q = q.filter(Contact.id != int(exclude_id))
    return q.first()


def apply_payload(contact: Contact, payload: dict[str, Any]) -> None:
    for key, value in payload.items():
        setattr(contact, key, value)


def search_contacts(
    organization_id: int,
    *,
    q: str = '',
    role: str = '',
    active_only: bool | None = None,
    contact_type: str = '',
    limit: int = 100,
    offset: int = 0,
) -> tuple[list[Contact], int]:
    query = Contact.query.filter_by(organization_id=int(organization_id))
    if active_only is True:
        query = query.filter(Contact.active.is_(True))
    elif active_only is False:
        query = query.filter(Contact.active.is_(False))
    if contact_type and contact_type in CONTACT_TYPES:
        query = query.filter(Contact.contact_type == contact_type)
    role = (role or '').strip().lower()
    role_map = {
        'customer': Contact.is_customer.is_(True),
        'supplier': Contact.is_supplier.is_(True),
        'member': Contact.is_member.is_(True),
        'student': Contact.is_student.is_(True),
        'participant': Contact.is_participant.is_(True),
        'instructor': Contact.is_instructor.is_(True),
        'donor': Contact.is_donor.is_(True),
        'employee': Contact.is_employee.is_(True),
        'consumer_final': Contact.identification_type == 'consumer_final',
    }
    if role in role_map:
        query = query.filter(role_map[role])
    q = (q or '').strip()
    if q:
        like = f'%{q}%'
        conds = [
            Contact.display_name.ilike(like),
            Contact.email.ilike(like),
            Contact.phone.ilike(like),
            Contact.mobile.ilike(like),
            Contact.tax_id.ilike(like),
            Contact.company_name.ilike(like),
            Contact.commercial_name.ilike(like),
        ]
        if q.isdigit():
            conds.append(Contact.id == int(q))
        query = query.filter(or_(*conds))
    total = query.count()
    rows = (
        query.order_by(Contact.display_name.asc(), Contact.id.asc())
        .offset(max(0, offset))
        .limit(max(1, min(limit, 500)))
        .all()
    )
    return rows, total


def get_contact(organization_id: int, contact_id: int) -> Contact | None:
    return Contact.query.filter_by(organization_id=int(organization_id), id=int(contact_id)).first()


def create_contact(organization_id: int, data: dict[str, Any]) -> Contact:
    payload = validate_contact_payload(data, organization_id=int(organization_id))
    row = Contact(organization_id=int(organization_id), **payload)
    db.session.add(row)
    db.session.flush()
    return row


def update_contact(organization_id: int, contact_id: int, data: dict[str, Any]) -> Contact:
    row = get_contact(organization_id, contact_id)
    if not row:
        raise ContactValidationError('Contacto no encontrado.')
    payload = validate_contact_payload(data, organization_id=int(organization_id), exclude_id=row.id)
    apply_payload(row, payload)
    db.session.flush()
    return row
