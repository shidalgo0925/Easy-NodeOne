"""Contactos / terceros comerciales (tenant_crm_contact) para facturación."""

from __future__ import annotations

from typing import Any

from sqlalchemy import or_

from models.saas import TenantCrmContact
from models.users import User
from nodeone.core.db import db


def display_name(contact: TenantCrmContact) -> str:
    return (
        (contact.legal_name or '').strip()
        or (contact.trade_name or '').strip()
        or (contact.name or '').strip()
        or (contact.company or '').strip()
        or f'Contacto #{contact.id}'
    )


def fiscal_email(contact: TenantCrmContact) -> str:
    return ((contact.fiscal_email or contact.email or '').strip()).lower()


def search_partners(organization_id: int, q: str = '', *, limit: int = 20, customers_only: bool = True) -> list[TenantCrmContact]:
    query = TenantCrmContact.query.filter_by(organization_id=int(organization_id), is_active=True)
    if customers_only:
        query = query.filter(TenantCrmContact.is_customer.is_(True))
    q = (q or '').strip()
    if q:
        like = f'%{q}%'
        conds = [
            TenantCrmContact.name.ilike(like),
            TenantCrmContact.email.ilike(like),
            TenantCrmContact.company.ilike(like),
            TenantCrmContact.legal_name.ilike(like),
            TenantCrmContact.trade_name.ilike(like),
            TenantCrmContact.tax_id.ilike(like),
            TenantCrmContact.fiscal_email.ilike(like),
        ]
        if q.isdigit():
            conds.append(TenantCrmContact.id == int(q))
        query = query.filter(or_(*conds))
    return query.order_by(TenantCrmContact.name.asc()).limit(max(1, min(limit, 100))).all()


def partner_to_dict(c: TenantCrmContact) -> dict[str, Any]:
    return {
        'id': c.id,
        'name': display_name(c),
        'email': fiscal_email(c) or (c.email or ''),
        'phone': (c.fiscal_phone or c.phone or '').strip(),
        'person_type': c.person_type or 'natural',
        'tax_id': (c.tax_id or '').strip(),
        'is_final_consumer': (c.person_type or '') == 'final_consumer',
        'linked_user_id': c.linked_user_id,
    }


def get_partner(organization_id: int, contact_id: int) -> TenantCrmContact | None:
    return TenantCrmContact.query.filter_by(
        id=int(contact_id), organization_id=int(organization_id), is_active=True
    ).first()


def create_partner(organization_id: int, data: dict[str, Any]) -> TenantCrmContact:
    name = (data.get('name') or data.get('legal_name') or '').strip()
    if not name:
        raise ValueError('El nombre es obligatorio.')
    email = (data.get('fiscal_email') or data.get('email') or '').strip()
    row = TenantCrmContact(
        organization_id=int(organization_id),
        name=name[:200],
        legal_name=(data.get('legal_name') or name)[:300],
        trade_name=(data.get('trade_name') or '')[:300] or None,
        email=email[:200] if email else None,
        fiscal_email=email[:255] if email else None,
        phone=(data.get('phone') or data.get('fiscal_phone') or '')[:50] or None,
        fiscal_phone=(data.get('fiscal_phone') or data.get('phone') or '')[:50] or None,
        company=(data.get('company') or '')[:200] or None,
        person_type=(data.get('person_type') or 'natural')[:30],
        id_type=(data.get('id_type') or '')[:30] or None,
        tax_id=(data.get('tax_id') or '')[:80] or None,
        tax_dv=(data.get('tax_dv') or '')[:10] or None,
        id_number=(data.get('id_number') or '')[:80] or None,
        fiscal_address=(data.get('fiscal_address') or '') or None,
        country_code=(data.get('country_code') or 'PA')[:8],
        province=(data.get('province') or '')[:120] or None,
        district=(data.get('district') or '')[:120] or None,
        corregimiento=(data.get('corregimiento') or '')[:120] or None,
        is_customer=bool(data.get('is_customer', True)),
        is_supplier=bool(data.get('is_supplier', False)),
        itbms_exempt=bool(data.get('itbms_exempt', False)),
        is_active=True,
    )
    db.session.add(row)
    db.session.flush()
    return row


def link_partner_to_user(contact: TenantCrmContact, user: User) -> None:
    contact.linked_user_id = int(user.id)
    if not contact.fiscal_email and user.email:
        contact.fiscal_email = user.email
    if not contact.email and user.email:
        contact.email = user.email


def get_or_create_partner_for_user(organization_id: int, user: User) -> TenantCrmContact:
    oid = int(organization_id)
    uid = int(user.id)
    existing = TenantCrmContact.query.filter_by(organization_id=oid, linked_user_id=uid).first()
    if existing:
        return existing
    name = f'{(user.first_name or "").strip()} {(user.last_name or "").strip()}'.strip() or (user.email or f'Usuario {uid}')
    row = create_partner(
        oid,
        {
            'name': name,
            'legal_name': name,
            'fiscal_email': user.email,
            'email': user.email,
            'fiscal_phone': getattr(user, 'phone', None),
            'person_type': 'natural',
        },
    )
    link_partner_to_user(row, user)
    if getattr(user, 'linked_contact_id', None) is None:
        user.linked_contact_id = row.id
    return row


def resolve_invoice_customer_contact(
    organization_id: int,
    *,
    customer_contact_id: int | None = None,
    customer_id: int | None = None,
) -> tuple[TenantCrmContact, int | None]:
    """
    Devuelve (contacto, user_id legacy).
    Prioridad: customer_contact_id explícito; si no, contacto por user; si no, error.
    """
    oid = int(organization_id)
    if customer_contact_id:
        c = get_partner(oid, int(customer_contact_id))
        if not c:
            raise ValueError('El contacto cliente no existe en esta organización.')
        uid = int(c.linked_user_id) if c.linked_user_id else None
        if uid is None and customer_id:
            uid = int(customer_id)
        if uid is None:
            u = User(
                email=fiscal_email(c) or f'contacto.{c.id}@sin-correo.invalid',
                first_name=(c.name or 'Cliente')[:50],
                last_name='.',
                organization_id=oid,
                is_active=True,
            )
            from werkzeug.security import generate_password_hash
            import secrets

            u.password_hash = generate_password_hash(secrets.token_urlsafe(16))
            db.session.add(u)
            db.session.flush()
            link_partner_to_user(c, u)
            uid = int(u.id)
        return c, uid

    if customer_id:
        u = User.query.get(int(customer_id))
        if not u:
            raise ValueError('Cliente (usuario) no encontrado.')
        c = get_or_create_partner_for_user(oid, u)
        return c, int(u.id)

    raise ValueError('Indique un contacto cliente (customer_contact_id).')
