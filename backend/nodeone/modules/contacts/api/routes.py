"""API JSON — Contactos (búsqueda / alta rápida para facturas y cotizaciones)."""

from __future__ import annotations

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from nodeone.core.db import db
from nodeone.modules.contacts import service as contact_svc
from nodeone.modules.contacts.invoice_integration import contact_to_api_dict
from nodeone.services.contacts_module import is_contacts_enabled_for_org, is_contacts_globally_allowed

contacts_api_bp = Blueprint('contacts_api', __name__, url_prefix='/api/admin/contacts')


def _org_id() -> int:
    from app import admin_data_scope_organization_id, default_organization_id

    try:
        return int(admin_data_scope_organization_id())
    except Exception:
        return int(default_organization_id())


def _can_api() -> bool:
    if not current_user.is_authenticated:
        return False
    if getattr(current_user, 'is_admin', False):
        return True
    from app import _user_has_any_admin_permission

    return bool(_user_has_any_admin_permission(current_user))


def _guard_json():
    if not is_contacts_globally_allowed():
        return jsonify({'ok': False, 'error': 'module_disabled'}), 404
    if not _can_api():
        return jsonify({'ok': False, 'error': 'forbidden'}), 403
    if not is_contacts_enabled_for_org(_org_id()):
        return jsonify({'ok': False, 'error': 'contacts_module_disabled'}), 403
    return None


@contacts_api_bp.before_request
def _before():
    if not current_user.is_authenticated:
        return jsonify({'ok': False, 'error': 'unauthorized'}), 401
    err = _guard_json()
    if err:
        return err


@contacts_api_bp.route('/search')
@login_required
def api_search():
    q = (request.args.get('q') or '').strip()
    try:
        lim = int(request.args.get('limit') or 20)
    except (TypeError, ValueError):
        lim = 20
    customers_only = request.args.get('customers_only', '1') not in ('0', 'false', 'no')
    oid = _org_id()
    rows, _ = contact_svc.search_contacts(
        oid,
        q=q,
        role='customer' if customers_only else '',
        active_only=True,
        limit=lim,
    )
    if customers_only and not rows and q:
        rows, _ = contact_svc.search_contacts(oid, q=q, active_only=True, limit=lim)
    return jsonify([contact_to_api_dict(c) for c in rows])


@contacts_api_bp.route('', methods=['POST'])
@login_required
def api_create():
    data = request.get_json(silent=True) or {}
    oid = _org_id()
    name = (data.get('name') or data.get('display_name') or '').strip()
    person_type = (data.get('person_type') or 'natural').strip()
    contact_type = 'company' if person_type == 'juridica' else 'consumer_final' if person_type == 'final_consumer' else 'person'
    id_type = 'consumer_final' if contact_type == 'consumer_final' else 'ruc' if person_type == 'juridica' else 'cedula'
    try:
        row = contact_svc.create_contact(
            oid,
            {
                'contact_type': contact_type,
                'display_name': name,
                'company_name': name if contact_type == 'company' else None,
                'first_name': (data.get('first_name') or name.split()[0] if name else '')[:120],
                'last_name': (data.get('last_name') or '')[:120] or None,
                'email': data.get('email') or data.get('fiscal_email'),
                'phone': data.get('phone') or data.get('fiscal_phone'),
                'identification_type': id_type,
                'tax_id': data.get('tax_id'),
                'dv': data.get('tax_dv') or data.get('dv'),
                'is_customer': True,
            },
        )
        db.session.commit()
        return jsonify({'ok': True, 'contact': contact_to_api_dict(row)}), 201
    except contact_svc.ContactValidationError as exc:
        db.session.rollback()
        return jsonify({'ok': False, 'error': str(exc)}), 400
    except Exception as exc:
        db.session.rollback()
        return jsonify({'ok': False, 'error': str(exc)}), 400
