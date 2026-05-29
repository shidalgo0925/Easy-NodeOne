"""Integración facturas comerciales → maestro en1_contact."""

from __future__ import annotations

import secrets
from typing import Any

from models.contact import Contact
from models.users import User
from nodeone.core.db import db
from nodeone.modules.contacts import service as contact_svc
from werkzeug.security import generate_password_hash


def contact_to_api_dict(c: Contact) -> dict[str, Any]:
    is_cf = c.identification_type == 'consumer_final' or c.contact_type == 'consumer_final'
    return {
        'id': c.id,
        'name': c.display_name,
        'email': (c.email or '').strip(),
        'phone': (c.phone or c.mobile or '').strip(),
        'person_type': 'final_consumer' if is_cf else ('juridica' if c.contact_type == 'company' else 'natural'),
        'tax_id': (c.tax_id or '').strip(),
        'tax_dv': (c.dv or '').strip(),
        'is_final_consumer': is_cf,
        'identification_type': c.identification_type,
        'contact_type': c.contact_type,
    }


def fiscal_email(c: Contact) -> str:
    return ((c.email or '').strip()).lower()


def fiscal_display_name(c: Contact) -> str:
    return (c.display_name or '').strip() or f'Contacto #{c.id}'


def _shadow_user_for_contact(organization_id: int, contact: Contact, customer_id: int | None) -> int:
    if customer_id:
        u = User.query.get(int(customer_id))
        if u:
            return int(u.id)
    email = fiscal_email(contact)
    if email:
        u = User.query.filter_by(email=email, organization_id=int(organization_id)).first()
        if u:
            return int(u.id)
    first = (contact.first_name or contact.display_name or 'Cliente')[:50]
    last = (contact.last_name or '.')[:50]
    u = User(
        email=email or f'contacto.{contact.id}@sin-correo.invalid',
        first_name=first,
        last_name=last,
        organization_id=int(organization_id),
        is_active=True,
    )
    u.password_hash = generate_password_hash(secrets.token_urlsafe(16))
    db.session.add(u)
    db.session.flush()
    return int(u.id)


def find_or_create_contact_from_user(organization_id: int, user: User) -> Contact:
    oid = int(organization_id)
    email = (user.email or '').strip().lower()
    if email:
        existing = Contact.query.filter_by(organization_id=oid, email=email).first()
        if existing:
            return existing
    name = f'{(user.first_name or "").strip()} {(user.last_name or "").strip()}'.strip() or email or f'Usuario {user.id}'
    payload = contact_svc.validate_contact_payload(
        {
            'contact_type': 'person',
            'display_name': name,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'email': email,
            'phone': getattr(user, 'phone', None),
            'identification_type': 'consumer_final',
            'is_customer': True,
        },
        organization_id=oid,
    )
    row = Contact(organization_id=oid, **payload)
    db.session.add(row)
    db.session.flush()
    return row


def resolve_invoice_customer(
    organization_id: int,
    *,
    contact_id: int | None = None,
    customer_contact_id: int | None = None,
    customer_id: int | None = None,
) -> tuple[Contact, int]:
    """
    Resuelve contacto fiscal (en1_contact) + user_id legacy para FK invoices.customer_id.
    Acepta contact_id o customer_contact_id (alias API).
    """
    oid = int(organization_id)
    cid = int(contact_id or customer_contact_id or 0) or None
    if cid:
        c = contact_svc.get_contact(oid, cid)
        if not c:
            raise ValueError('El contacto cliente no existe en esta organización.')
        if not c.active:
            raise ValueError('El contacto cliente está inactivo.')
        uid = _shadow_user_for_contact(oid, c, customer_id)
        return c, uid
    if customer_id:
        u = User.query.get(int(customer_id))
        if not u:
            raise ValueError('Cliente (usuario) no encontrado.')
        c = find_or_create_contact_from_user(oid, u)
        return c, int(u.id)
    raise ValueError('Indique un contacto cliente (contact_id).')


def get_invoice_fiscal_contact(invoice) -> Contact | None:
    oid = int(invoice.organization_id)
    raw = getattr(invoice, 'contact_id', None) or getattr(invoice, 'customer_contact_id', None)
    if not raw:
        return None
    return contact_svc.get_contact(oid, int(raw))


def contact_itbms_exempt(c: Contact) -> bool:
    return bool(c.is_tax_exempt or c.identification_type == 'consumer_final' or c.contact_type == 'consumer_final')


def contact_receptor_block(c: Contact) -> dict[str, Any]:
    """Bloque informacionReceptor para efacturapty."""
    email = fiscal_email(c) or 'consumidor@example.com'
    addr = (c.fiscal_address or 'Ciudad de Panama').strip()[:500]
    phone = (c.phone or c.mobile or '6000-0000').strip()[:30]
    name = fiscal_display_name(c)[:200]
    country = (c.country or 'PA')[:8]
    if c.identification_type == 'consumer_final' or c.contact_type == 'consumer_final' or not (c.tax_id or '').strip():
        return {
            'tipoReceptorFe': '02',
            'nombreRazonReceptor': name or 'CONSUMIDOR FINAL',
            'direccionReceptor': addr,
            'correoElectronicoReceptor': email,
            'paisReceptor': country,
            'telefonoContactoReceptor': phone,
        }
    is_company = c.contact_type == 'company' or c.identification_type == 'ruc'
    block: dict[str, Any] = {
        'tipoReceptorFe': '01',
        'nombreRazonReceptor': name,
        'direccionReceptor': addr,
        'correoElectronicoReceptor': email,
        'paisReceptor': country,
        'telefonoContactoReceptor': phone,
        'datosRucReceptor': {
            'tipoContribuyente': '2' if is_company else '1',
            'numeroRuc': (c.tax_id or '').strip(),
            'digitoVerificador': (c.dv or '').strip() or None,
        },
    }
    return block
