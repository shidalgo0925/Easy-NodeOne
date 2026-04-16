from __future__ import annotations

import math
from datetime import datetime
from typing import Optional

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from nodeone.core.db import db
from models.catalog import Service
from models.saas import SaasOrganization
from models.users import User
from nodeone.modules.accounting.models import Invoice, InvoiceLine, Tax
from nodeone.modules.sales.models import Quotation, QuotationLine
from nodeone.services.tax_calculation import compute_line_amounts
from nodeone.services.user_organization import user_in_org_clause

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
    try:
        from nodeone.services.saas_org_fiscal_schema import ensure_saas_organization_fiscal_columns

        ensure_saas_organization_fiscal_columns(db, db.engine)
    except Exception:
        pass


def _org_id():
    from app import admin_data_scope_organization_id, default_organization_id, tenant_data_organization_id

    try:
        return int(tenant_data_organization_id())
    except Exception:
        pass
    try:
        return int(admin_data_scope_organization_id())
    except Exception:
        return int(default_organization_id())


def _can_accounting():
    # Si el usuario ya está autenticado y llegó al panel admin, permitir operación.
    # Los guards de acceso viven en las vistas admin.
    return bool(getattr(current_user, 'is_authenticated', False))


def _safe_float(v):
    try:
        x = float(v if v is not None else 0)
        if math.isnan(x) or math.isinf(x):
            return 0.0
        return x
    except (TypeError, ValueError):
        return 0.0


def _salesperson_validation_message(code: str) -> str:
    return {
        'invalid_salesperson': 'Identificador de vendedor no válido.',
        'salesperson_not_found': 'El vendedor no existe en esta organización.',
        'salesperson_inactive': 'El vendedor está inactivo.',
        'salesperson_not_flagged': 'El usuario no está habilitado como vendedor (actívelo en Usuarios).',
    }.get(code, code)


def _validate_salesperson_user_id(organization_id: int, raw_id):
    if raw_id is None or raw_id is False or raw_id == '':
        return None, None
    try:
        uid = int(raw_id)
    except (TypeError, ValueError):
        return None, 'invalid_salesperson'
    if uid < 1:
        return None, None
    u = User.query.filter(user_in_org_clause(User, organization_id), User.id == uid).first()
    if not u:
        return None, 'salesperson_not_found'
    if not bool(getattr(u, 'is_active', True)):
        return None, 'salesperson_inactive'
    if not bool(getattr(u, 'is_salesperson', False)):
        return None, 'salesperson_not_flagged'
    return u, None


def _recompute_invoice_totals(inv: Invoice):
    oid = inv.organization_id
    lines = InvoiceLine.query.filter_by(invoice_id=inv.id).order_by(InvoiceLine.id).all()
    subtotal = 0.0
    tax_total = 0.0
    grand = 0.0
    for ln in lines:
        raw = str(ln.description or '')
        is_note = raw.startswith('__NOTE__ ')
        qty = 0.0 if is_note else float(ln.quantity or 0)
        pu = 0.0 if is_note else float(ln.price_unit or 0)
        tax = None
        if ln.tax_id and not is_note:
            tax = Tax.query.filter_by(id=ln.tax_id, organization_id=oid).first()
        ln_sub, ln_total, _ = compute_line_amounts(qty, pu, tax)
        ln.subtotal = float(ln_sub)
        ln.total = float(ln_total)
        subtotal += ln_sub
        grand += ln_total
        tax_total += ln_total - ln_sub
    inv.total = round(subtotal, 2)
    inv.tax_total = round(tax_total, 2)
    inv.grand_total = round(grand, 2)


def _serialize_invoice_line(ln: InvoiceLine, product_name: str = ''):
    raw_desc = str(ln.description or '')
    is_note = raw_desc.startswith('__NOTE__ ')
    clean_desc = raw_desc.replace('__NOTE__ ', '', 1) if is_note else raw_desc
    return {
        'id': ln.id,
        'product_id': ln.product_id,
        'product_name': product_name or '',
        'description': clean_desc,
        'is_note': is_note,
        'quantity': _safe_float(ln.quantity),
        'price_unit': _safe_float(ln.price_unit),
        'tax_id': ln.tax_id,
        'subtotal': _safe_float(ln.subtotal),
        'total': _safe_float(ln.total),
    }


def _product_names_for_invoice_lines(organization_id, lines):
    ids = list({ln.product_id for ln in lines if getattr(ln, 'product_id', None)})
    if not ids:
        return {}
    rows = Service.query.filter(
        Service.id.in_(ids),
        Service.organization_id == organization_id,
    ).all()
    return {s.id: (s.name or '') for s in rows}


def _serialize_invoice(inv: Invoice, user_by_id=None):
    cust = None
    if inv.customer_id:
        if user_by_id is not None:
            cust = user_by_id.get(inv.customer_id)
        else:
            try:
                cust = db.session.get(User, int(inv.customer_id))
            except (TypeError, ValueError):
                cust = None
    name = ''
    email = ''
    if cust:
        name = f'{getattr(cust, "first_name", "") or ""} {getattr(cust, "last_name", "") or ""}'.strip()
        email = getattr(cust, 'email', '') or ''
    ilines = InvoiceLine.query.filter_by(invoice_id=inv.id).order_by(InvoiceLine.id).all()
    pnames = _product_names_for_invoice_lines(inv.organization_id, ilines)
    sp_uid = getattr(inv, 'salesperson_user_id', None)
    sp_name = ''
    sp_email = ''
    if sp_uid:
        sp = None
        if user_by_id is not None:
            sp = user_by_id.get(int(sp_uid))
        if sp is None:
            sp = db.session.get(User, int(sp_uid))
        if sp:
            sp_name = f'{getattr(sp, "first_name", "") or ""} {getattr(sp, "last_name", "") or ""}'.strip()
            sp_email = getattr(sp, 'email', '') or ''
    origin_num = None
    if inv.origin_quotation_id:
        qo = Quotation.query.filter_by(id=inv.origin_quotation_id, organization_id=inv.organization_id).first()
        origin_num = qo.number if qo else None
    org = SaasOrganization.query.get(inv.organization_id)
    return {
        'id': inv.id,
        'number': inv.number,
        'customer_id': inv.customer_id,
        'customer_name': name,
        'customer_email': email,
        'salesperson_user_id': int(sp_uid) if sp_uid else None,
        'salesperson_name': sp_name,
        'salesperson_email': sp_email,
        'status': inv.status,
        'origin_quotation_id': inv.origin_quotation_id,
        'origin_quotation_number': origin_num,
        'enrollment_id': getattr(inv, 'enrollment_id', None),
        'date': inv.date.isoformat() if inv.date else None,
        'due_date': inv.due_date.isoformat() if getattr(inv, 'due_date', None) else None,
        'total': _safe_float(inv.total),
        'tax_total': _safe_float(inv.tax_total),
        'grand_total': _safe_float(inv.grand_total),
        'organization_name': (getattr(org, 'name', '') or '').strip(),
        'organization_legal_name': (getattr(org, 'legal_name', '') or '').strip(),
        'organization_tax_id': (getattr(org, 'tax_id', '') or '').strip(),
        'organization_tax_regime': (getattr(org, 'tax_regime', '') or '').strip(),
        'organization_fiscal_address': (getattr(org, 'fiscal_address', '') or '').strip(),
        'organization_fiscal_city': (getattr(org, 'fiscal_city', '') or '').strip(),
        'organization_fiscal_state': (getattr(org, 'fiscal_state', '') or '').strip(),
        'organization_fiscal_country': (getattr(org, 'fiscal_country', '') or '').strip(),
        'organization_fiscal_phone': (getattr(org, 'fiscal_phone', '') or '').strip(),
        'organization_fiscal_email': (getattr(org, 'fiscal_email', '') or '').strip(),
        'created_by': inv.created_by,
        'lines': [_serialize_invoice_line(ln, product_name=pnames.get(ln.product_id, '')) for ln in ilines],
    }


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
    origin_qid = int(data.get('origin_quotation_id') or 0) or None

    if customer_id < 1 and origin_qid:
        qrow = Quotation.query.filter_by(id=origin_qid, organization_id=oid).first()
        if qrow:
            customer_id = int(qrow.customer_id)
        else:
            return jsonify(
                {
                    'error': 'origin_quotation_not_found',
                    'user_message': 'La cotización de origen no existe en esta organización.',
                }
            ), 404

    if customer_id < 1:
        return jsonify(
            {
                'error': 'customer_id_required',
                'user_message': 'Indique el ID del cliente (miembro) o un número de cotización de origen válido para deducir el cliente.',
            }
        ), 400
    enr_id = int(data.get('enrollment_id') or 0) or None
    due_raw = data.get('due_date')
    due_dt = None
    if due_raw:
        try:
            due_dt = datetime.fromisoformat(str(due_raw).replace('Z', '+00:00'))
        except Exception:
            due_dt = None
    inv = Invoice(
        organization_id=oid,
        number=_next_number('INV', Invoice, oid),
        customer_id=customer_id,
        status='draft',
        origin_quotation_id=origin_qid,
        enrollment_id=enr_id,
        due_date=due_dt,
        total=0.0,
        tax_total=0.0,
        grand_total=0.0,
        created_by=getattr(current_user, 'id', None),
    )
    date_raw = data.get('date')
    if date_raw:
        try:
            inv.date = datetime.fromisoformat(str(date_raw).replace('Z', '+00:00')).replace(tzinfo=None)
        except Exception:
            pass
    db.session.add(inv)
    db.session.flush()

    for row in (data.get('lines') or []):
        is_note = bool(row.get('is_note'))
        desc = str(row.get('description') or '').strip() or ('Nota' if is_note else 'Item')
        if is_note and not desc.startswith('__NOTE__ '):
            desc = f'__NOTE__ {desc}'
        qty = 0.0 if is_note else float(row.get('quantity') or 0)
        pu = 0.0 if is_note else float(row.get('price_unit') or 0)
        tid = (int(row.get('tax_id')) if row.get('tax_id') else None) if not is_note else None
        tax = Tax.query.filter_by(id=tid, organization_id=oid).first() if tid else None
        ln_sub, ln_total, _ = compute_line_amounts(qty, pu, tax)
        ln = InvoiceLine(
            invoice_id=inv.id,
            product_id=(int(row.get('product_id')) if row.get('product_id') and not is_note else None),
            description=desc,
            quantity=qty,
            price_unit=pu,
            tax_id=tid,
            subtotal=float(ln_sub),
            total=float(ln_total),
        )
        db.session.add(ln)

    if 'salesperson_user_id' in data:
        u_sp, err = _validate_salesperson_user_id(oid, data.get('salesperson_user_id'))
        if err:
            db.session.rollback()
            return jsonify({'error': err, 'user_message': _salesperson_validation_message(err)}), 400
        inv.salesperson_user_id = u_sp.id if u_sp else None

    _recompute_invoice_totals(inv)
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
                'enrollment_id': getattr(r, 'enrollment_id', None),
                'due_date': r.due_date.isoformat() if getattr(r, 'due_date', None) else None,
            }
            for r in rows
        ]
    )


@accounting_bp.route('/<int:iid>', methods=['GET'])
@login_required
def invoice_get(iid):
    _ensure_tables()
    if not _can_accounting():
        return jsonify({'error': 'forbidden'}), 403
    oid = _org_id()
    inv = Invoice.query.filter_by(id=iid, organization_id=oid).first()
    if not inv:
        return jsonify({'error': 'not_found', 'user_message': 'Factura no encontrada.'}), 404
    ids = set()
    if inv.customer_id:
        ids.add(inv.customer_id)
    if getattr(inv, 'salesperson_user_id', None):
        ids.add(inv.salesperson_user_id)
    user_by_id = {}
    if ids:
        for u in User.query.filter(User.id.in_(list(ids))).all():
            user_by_id[u.id] = u
    return jsonify(_serialize_invoice(inv, user_by_id))


@accounting_bp.route('/<int:iid>', methods=['PUT'])
@login_required
def invoice_put(iid):
    _ensure_tables()
    if not _can_accounting():
        return jsonify({'error': 'forbidden'}), 403
    oid = _org_id()
    inv = Invoice.query.filter_by(id=iid, organization_id=oid).first()
    if not inv:
        return jsonify({'error': 'not_found', 'user_message': 'Factura no encontrada.'}), 404
    data = request.get_json() or {}

    _draft_only_keys = ('customer_id', 'lines', 'due_date', 'date')
    if inv.status != 'draft':
        if any(k in data for k in _draft_only_keys):
            return jsonify(
                {
                    'error': 'invoice_not_editable',
                    'user_message': 'Solo se puede editar cabecera y líneas en borrador.',
                }
            ), 400
        if 'salesperson_user_id' in data:
            u_sp, err = _validate_salesperson_user_id(oid, data.get('salesperson_user_id'))
            if err:
                return jsonify({'error': err, 'user_message': _salesperson_validation_message(err)}), 400
            inv.salesperson_user_id = u_sp.id if u_sp else None
        _recompute_invoice_totals(inv)
        db.session.commit()
        return jsonify(_serialize_invoice(inv))

    if 'customer_id' in data:
        cid = int(data.get('customer_id') or 0)
        if cid < 1:
            return jsonify(
                {
                    'error': 'customer_id_required',
                    'user_message': 'Seleccione un cliente válido.',
                }
            ), 400
        cust = User.query.filter(
            user_in_org_clause(User, oid),
            User.id == cid,
            User.is_active.is_(True),
        ).first()
        if not cust:
            return jsonify(
                {
                    'error': 'customer_not_in_organization',
                    'user_message': 'El cliente no es un miembro activo de esta organización.',
                }
            ), 400
        inv.customer_id = cid

    if 'date' in data:
        raw_d = data.get('date')
        if raw_d:
            try:
                inv.date = datetime.fromisoformat(str(raw_d).replace('Z', '+00:00')).replace(tzinfo=None)
            except Exception:
                pass
        else:
            inv.date = datetime.utcnow()

    if 'due_date' in data:
        due_raw = data.get('due_date')
        if due_raw:
            try:
                inv.due_date = datetime.fromisoformat(str(due_raw).replace('Z', '+00:00')).replace(tzinfo=None)
            except Exception:
                inv.due_date = None
        else:
            inv.due_date = None

    if 'salesperson_user_id' in data:
        u_sp, err = _validate_salesperson_user_id(oid, data.get('salesperson_user_id'))
        if err:
            return jsonify({'error': err, 'user_message': _salesperson_validation_message(err)}), 400
        inv.salesperson_user_id = u_sp.id if u_sp else None

    if 'lines' in data:
        InvoiceLine.query.filter_by(invoice_id=inv.id).delete()
        for row in (data.get('lines') or []):
            is_note = bool(row.get('is_note'))
            desc = str(row.get('description') or '').strip() or ('Nota' if is_note else 'Item')
            if is_note and not desc.startswith('__NOTE__ '):
                desc = f'__NOTE__ {desc}'
            qty = 0.0 if is_note else float(row.get('quantity') or 0)
            pu = 0.0 if is_note else float(row.get('price_unit') or 0)
            tid = (int(row.get('tax_id')) if row.get('tax_id') else None) if not is_note else None
            tax = Tax.query.filter_by(id=tid, organization_id=oid).first() if tid else None
            ln_sub, ln_total, _ = compute_line_amounts(qty, pu, tax)
            ln = InvoiceLine(
                invoice_id=inv.id,
                product_id=(int(row.get('product_id')) if row.get('product_id') and not is_note else None),
                description=desc,
                quantity=qty,
                price_unit=pu,
                tax_id=tid,
                subtotal=float(ln_sub),
                total=float(ln_total),
            )
            db.session.add(ln)

    _recompute_invoice_totals(inv)
    db.session.commit()
    return jsonify(_serialize_invoice(inv))


@accounting_bp.route('/<int:iid>/delete', methods=['POST'])
@login_required
def invoice_delete(iid):
    _ensure_tables()
    if not _can_accounting():
        return jsonify({'error': 'forbidden'}), 403
    oid = _org_id()
    inv = Invoice.query.filter_by(id=iid, organization_id=oid).first()
    if not inv:
        return jsonify({'error': 'not_found', 'user_message': 'Factura no encontrada.'}), 404
    if inv.status != 'draft':
        return jsonify(
            {
                'error': 'invoice_not_draft',
                'user_message': 'Solo se pueden eliminar facturas en borrador.',
            }
        ), 400
    db.session.delete(inv)
    db.session.commit()
    return jsonify({'ok': True})


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
    try:
        from nodeone.services.academic_service import on_invoice_paid_hook

        on_invoice_paid_hook(inv.id, oid)
    except Exception:
        pass
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
    try:
        from nodeone.services.academic_service import on_invoice_cancelled_hook

        on_invoice_cancelled_hook(inv.id, oid)
    except Exception:
        pass
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

