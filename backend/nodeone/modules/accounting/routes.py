from __future__ import annotations

from datetime import datetime
from typing import Optional

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from nodeone.core.db import db
from nodeone.modules.accounting.models import Invoice, InvoiceLine, Tax
from nodeone.modules.sales.models import Quotation, QuotationLine
from nodeone.services.tax_calculation import compute_line_amounts

accounting_bp = Blueprint('accounting', __name__, url_prefix='/invoices')
taxes_bp = Blueprint('accounting_taxes', __name__, url_prefix='/taxes')
taxes_api_bp = Blueprint('accounting_taxes_api', __name__, url_prefix='/api')


@taxes_api_bp.before_request
def _taxes_api_sales_or_tenant_admin():
    return _taxes_sales_or_tenant_admin()


@taxes_bp.before_request
def _taxes_sales_or_tenant_admin():
    """API impuestos: reglas en nodeone.services.admin_tenant_access (no app.py)."""
    from flask import jsonify
    from flask_login import current_user

    if not getattr(current_user, 'is_authenticated', False):
        return None
    from nodeone.services.admin_tenant_access import user_can_access_taxes_api
    from nodeone.services.org_scope import admin_data_scope_organization_id

    oid = int(admin_data_scope_organization_id())
    if user_can_access_taxes_api(current_user, oid):
        return None
    return jsonify({'error': 'forbidden'}), 403


def _ensure_tables():
    Tax.__table__.create(db.engine, checkfirst=True)
    Quotation.__table__.create(db.engine, checkfirst=True)
    QuotationLine.__table__.create(db.engine, checkfirst=True)
    Invoice.__table__.create(db.engine, checkfirst=True)
    InvoiceLine.__table__.create(db.engine, checkfirst=True)


def _org_id():
    from app import admin_data_scope_organization_id, default_organization_id, get_current_organization_id

    oid = get_current_organization_id()
    if oid is None:
        try:
            oid = admin_data_scope_organization_id()
        except Exception:
            oid = default_organization_id()
    return int(oid)


def _can_accounting():
    # Si el usuario ya está autenticado y llegó al panel admin, permitir operación.
    # Los guards de acceso viven en las vistas admin.
    return bool(getattr(current_user, 'is_authenticated', False))


def _next_number(prefix, model, org_id):
    cnt = model.query.filter_by(organization_id=org_id).count() + 1
    return f'{prefix}-{cnt:04d}'


def _serialize_tax(t: Tax):
    pi = getattr(t, 'price_included', None)
    if pi is None:
        pi = t.type == 'included'
    comp = getattr(t, 'computation', None) or 'percent'
    if comp not in ('percent', 'fixed'):
        comp = 'percent'
    ca = getattr(t, 'created_at', None)
    return {
        'id': t.id,
        'name': t.name,
        'rate': float(t.percentage or 0),
        'percentage': float(t.percentage or 0),
        'computation': comp,
        'amount_fixed': float(getattr(t, 'amount_fixed', 0) or 0),
        'price_included': bool(pi),
        'type': 'included' if pi else 'excluded',
        'active': bool(t.active),
        'company_id': t.organization_id,
        'created_at': ca.isoformat() if ca else None,
    }


def _parse_tax_payload(data: dict, existing: Optional[Tax] = None) -> dict:
    """Campos normalizados para crear/actualizar Tax."""
    out: dict = {}
    if 'name' in data:
        out['name'] = str(data.get('name') or '').strip() or (existing.name if existing else 'ITBMS')
    rate = None
    if 'rate' in data:
        rate = float(data.get('rate') or 0)
    elif 'percentage' in data:
        rate = float(data.get('percentage') or 0)
    if rate is not None:
        out['percentage'] = rate

    comp = None
    if 'computation' in data:
        comp = str(data.get('computation') or 'percent').lower()
    elif 'type' in data and str(data.get('type') or '').lower() in ('percent', 'fixed'):
        comp = str(data.get('type') or 'percent').lower()
    if comp is not None:
        out['computation'] = comp if comp in ('percent', 'fixed') else 'percent'

    if 'amount_fixed' in data:
        out['amount_fixed'] = float(data.get('amount_fixed') or 0)

    pi = None
    if 'price_included' in data:
        pi = bool(data.get('price_included'))
    elif 'type' in data and str(data.get('type') or '').lower() in ('included', 'excluded'):
        pi = str(data.get('type')).lower() == 'included'
    if pi is not None:
        out['price_included'] = pi
        out['type'] = 'included' if pi else 'excluded'

    if 'active' in data:
        out['active'] = bool(data.get('active'))
    return out


def _taxes_list_response():
    _ensure_tables()
    if not _can_accounting():
        return jsonify({'error': 'forbidden'}), 403
    oid = _org_id()
    include_inactive = str(request.args.get('include_inactive') or '').lower() in ('1', 'true', 'yes')
    query = Tax.query.filter_by(organization_id=oid)
    if not include_inactive:
        query = query.filter_by(active=True)
    rows = query.order_by(Tax.id.desc()).all()
    return jsonify([_serialize_tax(t) for t in rows])


def _taxes_create_response():
    _ensure_tables()
    if not _can_accounting():
        return jsonify({'error': 'forbidden'}), 403
    oid = _org_id()
    data = request.get_json() or {}
    parsed = _parse_tax_payload(data)
    name = parsed.get('name', str(data.get('name') or '').strip() or 'ITBMS')
    percentage = float(parsed.get('percentage', data.get('rate', data.get('percentage', 0)) or 0))
    computation = parsed.get('computation', 'percent')
    amount_fixed = float(parsed.get('amount_fixed', 0) or 0)
    price_included = bool(parsed.get('price_included', False))
    if 'price_included' not in parsed and str(data.get('type') or '') == 'included':
        price_included = True
    if 'price_included' not in parsed and str(data.get('type') or '') == 'excluded':
        price_included = False
    t = Tax(
        organization_id=oid,
        name=name,
        percentage=percentage,
        type='included' if price_included else 'excluded',
        computation=computation,
        amount_fixed=amount_fixed,
        price_included=price_included,
        active=True,
        created_at=datetime.utcnow(),
    )
    db.session.add(t)
    db.session.commit()
    return jsonify(_serialize_tax(t)), 201


def _taxes_put_response(tid: int):
    _ensure_tables()
    if not _can_accounting():
        return jsonify({'error': 'forbidden'}), 403
    oid = _org_id()
    tax = Tax.query.filter_by(id=tid, organization_id=oid).first()
    if not tax:
        return jsonify({'error': 'not_found'}), 404
    data = request.get_json() or {}
    parsed = _parse_tax_payload(data, tax)
    if 'name' in parsed:
        tax.name = parsed['name']
    if 'percentage' in parsed:
        tax.percentage = parsed['percentage']
    if 'computation' in parsed:
        tax.computation = parsed['computation']
    if 'amount_fixed' in parsed:
        tax.amount_fixed = parsed['amount_fixed']
    if 'price_included' in parsed:
        tax.price_included = parsed['price_included']
        tax.type = parsed.get('type', 'included' if parsed['price_included'] else 'excluded')
    if 'active' in parsed:
        tax.active = parsed['active']
    db.session.commit()
    return jsonify(_serialize_tax(tax))


def _taxes_delete_response(tid: int):
    _ensure_tables()
    if not _can_accounting():
        return jsonify({'error': 'forbidden'}), 403
    oid = _org_id()
    tax = Tax.query.filter_by(id=tid, organization_id=oid).first()
    if not tax:
        return jsonify({'error': 'not_found'}), 404
    tax.active = False
    db.session.commit()
    return jsonify({'ok': True, 'id': tax.id, 'active': False})


@accounting_bp.route('', methods=['POST'])
@login_required
def invoices_post():
    """
    Crear factura manual (sin cotización) o con origen opcional.
    Regla: origin_quotation_id puede ser None.
    """
    _ensure_tables()
    if not _can_accounting():
        return jsonify({'error': 'forbidden'}), 403
    oid = _org_id()
    data = request.get_json() or {}
    customer_id = int(data.get('customer_id') or 0)
    if customer_id < 1:
        return jsonify({'error': 'customer_id_required'}), 400

    origin_qid = int(data.get('origin_quotation_id') or 0) or None
    inv = Invoice(
        organization_id=oid,
        number=_next_number('INV', Invoice, oid),
        customer_id=customer_id,
        status='draft',
        origin_quotation_id=origin_qid,
        total=0.0,
        tax_total=0.0,
        grand_total=0.0,
        created_by=getattr(current_user, 'id', None),
    )
    db.session.add(inv)
    db.session.flush()

    subtotal = 0.0
    tax_total = 0.0
    grand = 0.0
    for row in (data.get('lines') or []):
        qty = float(row.get('quantity') or 0)
        pu = float(row.get('price_unit') or 0)
        tax = Tax.query.filter_by(id=(int(row.get('tax_id')) if row.get('tax_id') else None), organization_id=oid).first() if row.get('tax_id') else None
        ln_sub, ln_total, _ = compute_line_amounts(qty, pu, tax)
        ln = InvoiceLine(
            invoice_id=inv.id,
            product_id=(int(row.get('product_id')) if row.get('product_id') else None),
            description=str(row.get('description') or '').strip() or 'Item',
            quantity=qty,
            price_unit=pu,
            tax_id=(int(row.get('tax_id')) if row.get('tax_id') else None),
            subtotal=float(ln_sub),
            total=float(ln_total),
        )
        db.session.add(ln)
        subtotal += ln_sub
        grand += ln_total
        tax_total += (ln_total - ln_sub)

    inv.total = round(subtotal, 2)
    inv.tax_total = round(tax_total, 2)
    inv.grand_total = round(grand, 2)
    db.session.commit()
    return jsonify({'id': inv.id, 'number': inv.number, 'status': inv.status, 'origin_quotation_id': inv.origin_quotation_id}), 201


@accounting_bp.route('', methods=['GET'])
@login_required
def invoices_get():
    _ensure_tables()
    if not _can_accounting():
        return jsonify({'error': 'forbidden'}), 403
    oid = _org_id()
    rows = Invoice.query.filter_by(organization_id=oid).order_by(Invoice.id.desc()).all()
    return jsonify(
        [
            {
                'id': r.id,
                'number': r.number,
                'customer_id': r.customer_id,
                'status': r.status,
                'origin_quotation_id': r.origin_quotation_id,
                'date': r.date.isoformat() if r.date else None,
                'total': r.total,
                'tax_total': r.tax_total,
                'grand_total': r.grand_total,
            }
            for r in rows
        ]
    )


@accounting_bp.route('/<int:iid>/post', methods=['POST'])
@login_required
def invoice_post(iid):
    _ensure_tables()
    if not _can_accounting():
        return jsonify({'error': 'forbidden'}), 403
    oid = _org_id()
    inv = Invoice.query.filter_by(id=iid, organization_id=oid).first()
    if not inv:
        return jsonify({'error': 'not_found'}), 404
    if inv.status != 'draft':
        return jsonify({'error': 'invoice_must_be_draft'}), 400
    inv.status = 'posted'
    db.session.commit()
    return jsonify({'ok': True, 'status': inv.status})


@accounting_bp.route('/<int:iid>/pay', methods=['POST'])
@login_required
def invoice_pay(iid):
    _ensure_tables()
    if not _can_accounting():
        return jsonify({'error': 'forbidden'}), 403
    oid = _org_id()
    inv = Invoice.query.filter_by(id=iid, organization_id=oid).first()
    if not inv:
        return jsonify({'error': 'not_found'}), 404
    if inv.status != 'posted':
        return jsonify({'error': 'invoice_must_be_posted'}), 400
    inv.status = 'paid'
    if inv.origin_quotation_id:
        q = Quotation.query.filter_by(id=inv.origin_quotation_id, organization_id=oid).first()
        if q and q.status == 'invoiced':
            q.status = 'paid'
    db.session.commit()
    return jsonify({'ok': True, 'status': inv.status})


@accounting_bp.route('/<int:iid>/cancel', methods=['POST'])
@login_required
def invoice_cancel(iid):
    _ensure_tables()
    if not _can_accounting():
        return jsonify({'error': 'forbidden'}), 403
    oid = _org_id()
    inv = Invoice.query.filter_by(id=iid, organization_id=oid).first()
    if not inv:
        return jsonify({'error': 'not_found'}), 404
    if inv.status == 'paid':
        return jsonify({'error': 'paid_invoice_cannot_be_cancelled'}), 400
    inv.status = 'cancelled'
    db.session.commit()
    return jsonify({'ok': True, 'status': inv.status})


@taxes_bp.route('', methods=['GET'])
@login_required
def taxes_get():
    return _taxes_list_response()


@taxes_bp.route('', methods=['POST'])
@login_required
def taxes_post():
    return _taxes_create_response()


@taxes_bp.route('/<int:tid>', methods=['PUT'])
@login_required
def taxes_put(tid):
    return _taxes_put_response(tid)


@taxes_bp.route('/<int:tid>', methods=['DELETE'])
@login_required
def taxes_delete(tid):
    return _taxes_delete_response(tid)


@taxes_api_bp.route('/taxes', methods=['GET'])
@login_required
def api_taxes_get():
    return _taxes_list_response()


@taxes_api_bp.route('/taxes', methods=['POST'])
@login_required
def api_taxes_post():
    return _taxes_create_response()


@taxes_api_bp.route('/taxes/<int:tid>', methods=['PUT'])
@login_required
def api_taxes_put(tid):
    return _taxes_put_response(tid)


@taxes_api_bp.route('/taxes/<int:tid>', methods=['DELETE'])
@login_required
def api_taxes_delete(tid):
    return _taxes_delete_response(tid)

