"""API JSON admin — Facturación Electrónica."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from flask import Blueprint, abort, jsonify, request
from flask_login import current_user, login_required

from models.efactura import ElectronicInvoiceDocument
from models.saas import SaasOrganization
from nodeone.modules.efactura.services import issue as issue_svc
from nodeone.services.efactura_module import is_efactura_enabled_for_org
from nodeone.services.efactura_schema import ensure_efactura_schema

efactura_api_bp = Blueprint('efactura_api', __name__, url_prefix='/api/admin/efactura')


def _org_id() -> int:
    from app import admin_data_scope_organization_id, default_organization_id

    try:
        oid = int(admin_data_scope_organization_id())
    except Exception:
        oid = int(default_organization_id())
    if SaasOrganization.query.get(int(oid)) is None:
        return int(default_organization_id())
    return int(oid)


def _guard_json():
    from nodeone.modules.efactura.config import is_efactura_globally_allowed

    if not is_efactura_globally_allowed():
        return jsonify({'ok': False, 'error': 'module_disabled_globally'}), 404
    if not current_user.is_authenticated:
        return jsonify({'ok': False, 'error': 'unauthorized'}), 401
    oid = _org_id()
    if not is_efactura_enabled_for_org(oid):
        return jsonify({'ok': False, 'error': 'efactura_module_disabled'}), 403
    if getattr(current_user, 'is_admin', False):
        return None
    from app import _user_has_any_admin_permission

    if not _user_has_any_admin_permission(current_user):
        return jsonify({'ok': False, 'error': 'forbidden'}), 403
    return None


@efactura_api_bp.before_request
def _efactura_api_before():
    from nodeone.core.db import db

    g = _guard_json()
    if g is not None:
        return g
    try:
        ensure_efactura_schema(db, db.engine)
    except Exception:
        pass


@efactura_api_bp.route('/test-connection', methods=['POST'])
@login_required
def api_test_connection():
    result = issue_svc.test_connection(_org_id())
    return jsonify(result), 200 if result.get('ok') else 400


@efactura_api_bp.route('/test-invoice', methods=['POST'])
@login_required
def api_test_invoice():
    data = request.get_json(silent=True) or {}
    try:
        amount = Decimal(str(data.get('amount', 1)))
    except (InvalidOperation, ValueError, TypeError):
        return jsonify({'ok': False, 'error': 'amount inválido'}), 400
    description = (data.get('description') or 'Servicio de prueba EN1').strip()
    email = (data.get('email') or data.get('customer_email') or '').strip()
    try:
        doc = issue_svc.issue_test_invoice(
            _org_id(),
            amount=amount,
            description=description,
            customer_email=email,
        )
    except Exception as exc:
        return jsonify({'ok': False, 'error': str(exc)}), 400
    return jsonify(
        {
            'ok': doc.status == 'accepted',
            'document_id': doc.id,
            'cufe': doc.cufe,
            'autorizada': doc.status == 'accepted',
            'status': doc.status,
            'message': doc.authorization_message or doc.error_message,
        }
    )


@efactura_api_bp.route('/emissions')
@login_required
def api_emissions_list():
    oid = _org_id()
    page = max(1, int(request.args.get('page', 1)))
    per_page = min(100, max(1, int(request.args.get('per_page', 25))))
    status_filter = (request.args.get('status') or '').strip()
    q = ElectronicInvoiceDocument.query.filter_by(organization_id=oid).order_by(
        ElectronicInvoiceDocument.created_at.desc()
    )
    if status_filter:
        q = q.filter(ElectronicInvoiceDocument.status == status_filter)
    pagination = q.paginate(page=page, per_page=per_page, error_out=False)
    return jsonify(
        {
            'ok': True,
            'page': pagination.page,
            'pages': pagination.pages,
            'total': pagination.total,
            'items': [issue_svc.document_to_dict(d) for d in pagination.items],
        }
    )


@efactura_api_bp.route('/emissions/<int:doc_id>')
@login_required
def api_emission_detail(doc_id: int):
    oid = _org_id()
    doc = ElectronicInvoiceDocument.query.filter_by(id=doc_id, organization_id=oid).first()
    if doc is None:
        abort(404)
    return jsonify({'ok': True, 'document': issue_svc.document_to_dict(doc, include_payloads=True)})
