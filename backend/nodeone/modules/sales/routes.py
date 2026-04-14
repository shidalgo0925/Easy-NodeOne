import math
from datetime import datetime

from flask import Blueprint, current_app, jsonify, request
from sqlalchemy import or_
from flask_login import current_user, login_required

from nodeone.core.db import db
from models.catalog import Service
from models.saas import SaasOrganization
from models.users import User
from nodeone.modules.accounting.models import Invoice, InvoiceLine, Tax
from nodeone.modules.sales.mail import perform_quotation_send
from nodeone.modules.sales.models import Quotation, QuotationLine
from nodeone.services.tax_calculation import compute_line_amounts
from nodeone.services.user_organization import user_in_org_clause

sales_bp = Blueprint('sales', __name__, url_prefix='/api/sales/quotations')


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
        current_app.logger.exception('ensure_saas_organization_fiscal_columns en sales._ensure_tables')
    try:
        from nodeone.services.invoices_schema import ensure_invoices_model_columns

        ensure_invoices_model_columns(db, db.engine)
    except Exception:
        current_app.logger.exception('ensure_invoices_model_columns en sales._ensure_tables')
    try:
        from nodeone.services.crm_tenant_contact_schema import ensure_crm_salesperson_and_quotation_columns

        ensure_crm_salesperson_and_quotation_columns(db, db.engine)
    except Exception:
        current_app.logger.exception('ensure_crm_salesperson_and_quotation_columns en sales._ensure_tables')


def _safe_float(v):
    try:
        x = float(v if v is not None else 0)
        if math.isnan(x) or math.isinf(x):
            return 0.0
        return x
    except (TypeError, ValueError):
        return 0.0


def _org_id():
    """Misma resolución de tenant que taller / guards SaaS (evita RuntimeError si falta org en sesión)."""
    from app import admin_data_scope_organization_id, default_organization_id, tenant_data_organization_id

    try:
        return int(tenant_data_organization_id())
    except Exception:
        pass
    try:
        return int(admin_data_scope_organization_id())
    except Exception:
        return int(default_organization_id())


def _can_sales():
    # Si el usuario ya está autenticado y llegó al panel admin, permitir operación.
    # Los guards de acceso viven en las vistas admin.
    return bool(getattr(current_user, 'is_authenticated', False))


def _recompute_quote_totals(quotation):
    lines = QuotationLine.query.filter_by(quotation_id=quotation.id).all()
    subtotal = 0.0
    tax_total = 0.0
    grand = 0.0
    for ln in lines:
        qty = float(ln.quantity or 0)
        pu = float(ln.price_unit or 0)
        tax = Tax.query.filter_by(id=ln.tax_id, organization_id=quotation.organization_id).first() if ln.tax_id else None
        s, t, tx = compute_line_amounts(qty, pu, tax)
        ln.subtotal = s
        ln.total = t
        subtotal += s
        tax_total += tx
        grand += t
    quotation.total = round(subtotal, 2)
    quotation.tax_total = round(tax_total, 2)
    quotation.grand_total = round(grand, 2)


def _next_number(prefix, model, org_id):
    cnt = model.query.filter_by(organization_id=org_id).count() + 1
    return f'{prefix}-{cnt:04d}'


def _serialize_line(ln, product_name=''):
    """product_name: nombre del servicio en catálogo (la UI lo usa tras guardar; no se persiste en la línea)."""
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


def _product_names_for_lines(organization_id, lines):
    ids = list({ln.product_id for ln in lines if getattr(ln, 'product_id', None)})
    if not ids:
        return {}
    rows = Service.query.filter(
        Service.id.in_(ids),
        Service.organization_id == organization_id,
    ).all()
    return {s.id: (s.name or '') for s in rows}


def _has_quotable_lines_for_confirm(q):
    """Al menos una línea de producto (no nota) con cantidad > 0."""
    for ln in QuotationLine.query.filter_by(quotation_id=q.id).all():
        raw = str(ln.description or '')
        if raw.startswith('__NOTE__ '):
            continue
        if float(ln.quantity or 0) > 0:
            return True
    return False


def _validate_salesperson_user_id(organization_id: int, raw_id):
    """Devuelve (User|None, error_code|None). None id limpia el vendedor."""
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


def _default_salesperson_user_id(organization_id: int, user_id):
    if not user_id:
        return None
    u = (
        User.query.filter(
            user_in_org_clause(User, organization_id),
            User.id == int(user_id),
            User.is_salesperson == True,  # noqa: E712
            User.is_active == True,  # noqa: E712
        )
        .first()
    )
    return u.id if u else None


def _serialize_quotation(q, user_by_id=None):
    cust = None
    if q.customer_id:
        if user_by_id is not None:
            cust = user_by_id.get(q.customer_id)
        else:
            try:
                cust = db.session.get(User, int(q.customer_id))
            except (TypeError, ValueError):
                cust = None
    name = ''
    email = ''
    if cust:
        name = f'{getattr(cust, "first_name", "") or ""} {getattr(cust, "last_name", "") or ""}'.strip()
        email = getattr(cust, 'email', '') or ''
    qlines = QuotationLine.query.filter_by(quotation_id=q.id).all()
    pnames = _product_names_for_lines(q.organization_id, qlines)
    inv = None
    try:
        inv = Invoice.query.filter_by(organization_id=q.organization_id, origin_quotation_id=q.id).first()
    except Exception:
        # BD antigua sin origin_quotation_id u otro error de esquema: no romper el listado.
        inv = None
    sp_uid = getattr(q, 'salesperson_user_id', None)
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
    org = SaasOrganization.query.get(q.organization_id)
    return {
        'id': q.id,
        'number': q.number,
        'customer_id': q.customer_id,
        'customer_name': name,
        'customer_email': email,
        'salesperson_user_id': int(sp_uid) if sp_uid else None,
        'salesperson_name': sp_name,
        'salesperson_email': sp_email,
        'salesperson_code': '',
        'crm_lead_id': q.crm_lead_id,
        'status': q.status,
        'invoice_id': inv.id if inv else None,
        'invoice_number': inv.number if inv else None,
        'date': q.date.isoformat() if q.date else None,
        'validity_date': q.validity_date.isoformat() if q.validity_date else None,
        'payment_terms': getattr(q, 'payment_terms', None) or '',
        'total': _safe_float(q.total),
        'tax_total': _safe_float(q.tax_total),
        'grand_total': _safe_float(q.grand_total),
        'created_by': q.created_by,
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
        'lines': [_serialize_line(ln, product_name=pnames.get(ln.product_id, '')) for ln in qlines],
    }


@sales_bp.route('', methods=['GET'])
@login_required
def quotations_get():
    try:
        try:
            _ensure_tables()
        except Exception:
            current_app.logger.exception('quotations_get: ensure_tables failed, intentando listar igual')
        if not _can_sales():
            return jsonify({'error': 'forbidden'}), 403
        oid = _org_id()
        qs = Quotation.query.filter_by(organization_id=oid)
        sp_f = (request.args.get('salesperson_user_id') or '').strip()
        if sp_f.isdigit():
            qs = qs.filter_by(salesperson_user_id=int(sp_f))
        qs = qs.order_by(Quotation.id.desc()).all()
        ids = set()
        for q in qs:
            if q.customer_id:
                ids.add(q.customer_id)
            if getattr(q, 'salesperson_user_id', None):
                ids.add(q.salesperson_user_id)
        user_by_id = {}
        if ids:
            for u in User.query.filter(User.id.in_(list(ids))).all():
                user_by_id[u.id] = u
        payload = []
        for q in qs:
            try:
                payload.append(_serialize_quotation(q, user_by_id))
            except Exception as row_e:
                current_app.logger.warning('Omitiendo cotización id=%s en listado: %s', getattr(q, 'id', '?'), row_e)
        return jsonify(payload)
    except Exception as e:
        current_app.logger.exception('quotations_get failed')
        detail = str(e) if current_app.debug else None
        return jsonify({'error': 'quotations_list_failed', 'detail': detail}), 500


@sales_bp.route('', methods=['POST'])
@login_required
def quotations_post():
    _ensure_tables()
    if not _can_sales():
        return jsonify({'error': 'forbidden'}), 403
    oid = _org_id()
    data = request.get_json() or {}
    customer_id = int(data.get('customer_id') or 0)
    if customer_id < 1:
        return jsonify({'error': 'customer_id_required'}), 400

    q = Quotation(
        organization_id=oid,
        number=_next_number('Q', Quotation, oid),
        customer_id=customer_id,
        crm_lead_id=(int(data.get('crm_lead_id')) if data.get('crm_lead_id') else None),
        date=datetime.utcnow(),
        validity_date=(
            datetime.fromisoformat(str(data.get('validity_date')).replace('Z', '+00:00')).replace(tzinfo=None)
            if data.get('validity_date')
            else None
        ),
        payment_terms=(str(data.get('payment_terms') or '').strip() or None),
        status='draft',
        created_by=getattr(current_user, 'id', None),
    )
    db.session.add(q)
    db.session.flush()

    for row in (data.get('lines') or []):
        is_note = bool(row.get('is_note'))
        desc = str(row.get('description') or '').strip() or 'Item'
        if is_note and not desc.startswith('__NOTE__ '):
            desc = f'__NOTE__ {desc}'
        ln = QuotationLine(
            quotation_id=q.id,
            product_id=(int(row.get('product_id')) if row.get('product_id') else None),
            description=desc,
            quantity=(0.0 if is_note else float(row.get('quantity') or 0)),
            price_unit=(0.0 if is_note else float(row.get('price_unit') or 0)),
            tax_id=((int(row.get('tax_id')) if row.get('tax_id') else None) if not is_note else None),
        )
        db.session.add(ln)
    _recompute_quote_totals(q)
    if 'salesperson_user_id' in data:
        u_sp, err = _validate_salesperson_user_id(oid, data.get('salesperson_user_id'))
        if err:
            db.session.rollback()
            return jsonify(
                {
                    'error': err,
                    'user_message': _salesperson_validation_message(err),
                }
            ), 400
        q.salesperson_user_id = u_sp.id if u_sp else None
    else:
        duid = _default_salesperson_user_id(oid, getattr(current_user, 'id', None))
        if duid:
            q.salesperson_user_id = duid
    db.session.commit()
    return jsonify({'id': q.id, 'number': q.number, 'status': q.status, 'grand_total': q.grand_total}), 201


def _salesperson_validation_message(code: str) -> str:
    return {
        'invalid_salesperson': 'Identificador de vendedor no válido.',
        'salesperson_not_found': 'El vendedor no existe en esta organización.',
        'salesperson_inactive': 'El vendedor está inactivo.',
        'salesperson_not_flagged': 'El usuario no está habilitado como vendedor (actívelo en Usuarios).',
    }.get(code, code)


@sales_bp.route('/<int:qid>', methods=['GET'])
@login_required
def quotation_get(qid):
    _ensure_tables()
    if not _can_sales():
        return jsonify({'error': 'forbidden'}), 403
    oid = _org_id()
    q = Quotation.query.filter_by(id=qid, organization_id=oid).first()
    if not q:
        return jsonify({'error': 'not_found'}), 404
    return jsonify(_serialize_quotation(q))


@sales_bp.route('/<int:qid>', methods=['PUT'])
@login_required
def quotation_put(qid):
    _ensure_tables()
    if not _can_sales():
        return jsonify({'error': 'forbidden'}), 403
    oid = _org_id()
    q = Quotation.query.filter_by(id=qid, organization_id=oid).first()
    if not q:
        return jsonify({'error': 'not_found'}), 404

    data = request.get_json() or {}
    if q.status == 'cancelled':
        st_in = str(data.get('status') or '').lower()
        if st_in == 'cancelled':
            pass
        elif st_in in ('sent', 'confirmed'):
            return jsonify(
                {
                    'error': 'cancelled_quotation_cannot_be_edited',
                    'detail': 'Una cotización cancelada debe volver a borrador antes de enviarla o confirmarla.',
                    'user_message': 'Una cotización cancelada debe volver a borrador antes de enviarla o confirmarla.',
                }
            ), 400
        else:
            q.status = 'draft'

    # sent / confirmed solo vía POST /send y /confirm (no por PUT)
    if 'status' in data:
        st = str(data.get('status') or '').lower()
        if st in ('sent', 'confirmed', 'invoiced', 'paid'):
            return jsonify(
                {
                    'error': 'invalid_state',
                    'user_message': 'Use los botones Enviar, Confirmar o Crear factura; no cambie esos estados manualmente.',
                }
            ), 400
        if st in ('draft', 'cancelled'):
            q.status = st

    if 'salesperson_user_id' in data:
        u_sp, err = _validate_salesperson_user_id(oid, data.get('salesperson_user_id'))
        if err:
            return jsonify({'error': err, 'user_message': _salesperson_validation_message(err)}), 400
        q.salesperson_user_id = u_sp.id if u_sp else None

    _draft_only_keys = ('customer_id', 'lines', 'crm_lead_id', 'validity_date', 'payment_terms')
    if q.status != 'draft':
        if any(k in data for k in _draft_only_keys):
            return jsonify(
                {
                    'error': 'quotation_not_editable',
                    'user_message': 'Solo se puede editar en borrador.',
                }
            ), 400
        _recompute_quote_totals(q)
        db.session.commit()
        return jsonify(_serialize_quotation(q))

    if 'customer_id' in data:
        q.customer_id = int(data.get('customer_id') or q.customer_id)
    if 'crm_lead_id' in data:
        q.crm_lead_id = int(data.get('crm_lead_id') or 0) or None
    if 'validity_date' in data:
        q.validity_date = (
            datetime.fromisoformat(str(data.get('validity_date')).replace('Z', '+00:00')).replace(tzinfo=None)
            if data.get('validity_date')
            else None
        )
    if 'payment_terms' in data:
        q.payment_terms = str(data.get('payment_terms') or '').strip() or None

    if 'lines' in data:
        QuotationLine.query.filter_by(quotation_id=q.id).delete()
        for row in (data.get('lines') or []):
            is_note = bool(row.get('is_note'))
            desc = str(row.get('description') or '').strip() or 'Item'
            if is_note and not desc.startswith('__NOTE__ '):
                desc = f'__NOTE__ {desc}'
            ln = QuotationLine(
                quotation_id=q.id,
                product_id=(int(row.get('product_id')) if row.get('product_id') else None),
                description=desc,
                quantity=(0.0 if is_note else float(row.get('quantity') or 0)),
                price_unit=(0.0 if is_note else float(row.get('price_unit') or 0)),
                tax_id=((int(row.get('tax_id')) if row.get('tax_id') else None) if not is_note else None),
            )
            db.session.add(ln)
    _recompute_quote_totals(q)
    db.session.commit()
    return jsonify(_serialize_quotation(q))


def _perform_quotation_delete(qid: int):
    """Lógica compartida: DELETE /id o POST /id/delete (evita proxies que bloquean DELETE)."""
    _ensure_tables()
    if not _can_sales():
        return jsonify({'error': 'forbidden'}), 403
    oid = _org_id()
    q = Quotation.query.filter_by(id=qid, organization_id=oid).first()
    if not q:
        return jsonify({'error': 'not_found'}), 404
    if q.status in ('invoiced', 'paid'):
        return jsonify(
            {
                'error': 'quotation_cannot_delete_final',
                'user_message': 'No se puede eliminar una cotización facturada o pagada.',
            }
        ), 400
    if Invoice.query.filter_by(origin_quotation_id=q.id, organization_id=oid).first():
        return jsonify(
            {
                'error': 'quotation_has_invoice',
                'user_message': 'No se puede eliminar: existe una factura asociada a esta cotización.',
            }
        ), 400
    QuotationLine.query.filter_by(quotation_id=q.id).delete()
    db.session.delete(q)
    db.session.commit()
    return jsonify({'ok': True}), 200


@sales_bp.route('/<int:qid>/delete', methods=['POST'])
@login_required
def quotation_delete_post(qid):
    return _perform_quotation_delete(qid)


@sales_bp.route('/<int:qid>', methods=['DELETE'])
@login_required
def quotation_delete(qid):
    return _perform_quotation_delete(qid)


@sales_bp.route('/salespersons/search', methods=['GET'])
@login_required
def salespersons_search():
    _ensure_tables()
    if not _can_sales():
        return jsonify({'error': 'forbidden'}), 403
    oid = _org_id()
    qstr = str(request.args.get('q') or '').strip()
    try:
        lim = int(request.args.get('limit') or 30)
    except (TypeError, ValueError):
        lim = 30
    lim = max(1, min(lim, 100))
    query = User.query.filter(
        user_in_org_clause(User, oid),
        User.is_salesperson == True,  # noqa: E712
        User.is_active == True,  # noqa: E712
    )
    if qstr:
        like = f'%{qstr}%'
        query = query.filter(
            or_(
                User.first_name.ilike(like),
                User.last_name.ilike(like),
                User.email.ilike(like),
            )
        )
    rows = query.order_by(User.first_name.asc(), User.last_name.asc(), User.id.asc()).limit(lim).all()
    return jsonify(
        [
            {
                'id': r.id,
                'name': f'{(r.first_name or "").strip()} {(r.last_name or "").strip()}'.strip(),
                'email': (r.email or '').strip(),
                'code': '',
                'phone': (r.phone or '').strip(),
            }
            for r in rows
        ]
    )


@sales_bp.route('/salespersons/default', methods=['GET'])
@login_required
def salespersons_default():
    _ensure_tables()
    if not _can_sales():
        return jsonify({'error': 'forbidden'}), 403
    oid = _org_id()
    duid = _default_salesperson_user_id(oid, getattr(current_user, 'id', None))
    if not duid:
        return jsonify(None)
    u = db.session.get(User, int(duid))
    if not u:
        return jsonify(None)
    return jsonify(
        {
            'id': u.id,
            'name': f'{(u.first_name or "").strip()} {(u.last_name or "").strip()}'.strip(),
            'email': (u.email or '').strip(),
            'code': '',
        }
    )


@sales_bp.route('/products/search', methods=['GET'])
@login_required
def products_search():
    _ensure_tables()
    if not _can_sales():
        return jsonify({'error': 'forbidden'}), 403
    oid = _org_id()
    q = str(request.args.get('q') or '').strip()
    query = Service.query.filter_by(is_active=True, organization_id=oid)
    if q:
        like = f'%{q}%'
        conds = [Service.name.ilike(like), Service.description.ilike(like)]
        if q.isdigit():
            try:
                conds.append(Service.id == int(q))
            except (ValueError, OverflowError):
                pass
        query = query.filter(or_(*conds))
    try:
        lim = int(request.args.get('limit') or 20)
    except (TypeError, ValueError):
        lim = 20
    lim = max(1, min(lim, 500))
    rows = query.order_by(Service.name.asc()).limit(lim).all()
    return jsonify(
        [
            {
                'id': s.id,
                'name': s.name,
                'code': str(s.id),
                'description': s.description or '',
                'price_unit': float(getattr(s, 'base_price', 0.0) or 0.0),
                'default_tax_id': int(getattr(s, 'default_tax_id', None) or 0) or None,
            }
            for s in rows
        ]
    )


@sales_bp.route('/customers/search', methods=['GET'])
@login_required
def customers_search():
    _ensure_tables()
    if not _can_sales():
        return jsonify({'error': 'forbidden'}), 403
    oid = _org_id()
    q = str(request.args.get('q') or '').strip()
    try:
        lim = int(request.args.get('limit') or 20)
    except (TypeError, ValueError):
        lim = 20
    lim = max(1, min(lim, 100))
    query = User.query.filter(user_in_org_clause(User, oid), User.is_active.is_(True))
    if q:
        like = f'%{q}%'
        conds = [
            User.email.ilike(like),
            User.first_name.ilike(like),
            User.last_name.ilike(like),
        ]
        if q.isdigit():
            try:
                conds.append(User.id == int(q))
            except (ValueError, OverflowError):
                pass
        query = query.filter(or_(*conds))
    rows = query.order_by(User.last_name.asc(), User.first_name.asc()).limit(lim).all()
    return jsonify(
        [
            {
                'id': u.id,
                'name': f'{(u.first_name or "").strip()} {(u.last_name or "").strip()}'.strip() or u.email,
                'email': u.email or '',
            }
            for u in rows
        ]
    )


def _quotation_reopen_if_cancelled(q):
    """Permite enviar/confirmar tras cancelar: mismo POST reabre a borrador."""
    if q.status == 'cancelled':
        q.status = 'draft'
        db.session.flush()


@sales_bp.route('/<int:qid>/send', methods=['POST'])
@login_required
def quotations_send(qid):
    _ensure_tables()
    if not _can_sales():
        return jsonify({'error': 'forbidden'}), 403
    oid = _org_id()
    q = Quotation.query.filter_by(id=qid, organization_id=oid).first()
    if not q:
        return jsonify({'error': 'not_found'}), 404
    _quotation_reopen_if_cancelled(q)
    if q.status not in ('draft', 'sent'):
        return jsonify(
            {
                'error': 'invalid_state',
                'detail': 'Solo se puede enviar por correo una cotización en borrador o reenviar una enviada.',
                'user_message': 'Solo se puede enviar por correo una cotización en borrador o reenviar una enviada.',
            }
        ), 400
    customer = User.query.get(q.customer_id)
    if not customer or not getattr(customer, 'email', None):
        return jsonify({'error': 'customer_email_missing'}), 400

    payload = request.get_json(silent=True)
    data = payload if isinstance(payload, dict) else {}
    ok, err_payload = perform_quotation_send(q, customer, oid, data)
    if not ok:
        return jsonify(err_payload), 400
    q.status = 'sent'
    db.session.commit()
    return jsonify({'ok': True, 'status': q.status})


@sales_bp.route('/<int:qid>/confirm', methods=['POST'])
@login_required
def quotations_confirm(qid):
    _ensure_tables()
    if not _can_sales():
        return jsonify({'error': 'forbidden'}), 403
    oid = _org_id()
    q = Quotation.query.filter_by(id=qid, organization_id=oid).first()
    if not q:
        return jsonify({'error': 'not_found'}), 404
    _quotation_reopen_if_cancelled(q)
    if q.status == 'confirmed':
        db.session.commit()
        return jsonify({'ok': True, 'status': q.status})
    if q.status in ('invoiced', 'paid'):
        return jsonify(
            {
                'error': 'invalid_state',
                'user_message': 'La cotización ya está facturada o pagada.',
            }
        ), 400
    if q.status not in ('draft', 'sent'):
        return jsonify(
            {
                'error': 'invalid_state',
                'detail': 'Solo se puede confirmar una cotización en borrador o enviada.',
                'user_message': 'Solo se puede confirmar una cotización en borrador o enviada.',
            }
        ), 400
    if not _has_quotable_lines_for_confirm(q):
        return jsonify(
            {
                'error': 'quotation_needs_lines',
                'user_message': 'Agregue al menos una línea con cantidad mayor que cero antes de confirmar.',
            }
        ), 400
    q.status = 'confirmed'
    db.session.commit()
    return jsonify({'ok': True, 'status': q.status})


@sales_bp.route('/<int:qid>/create-invoice', methods=['POST'])
@login_required
def quotations_create_invoice(qid):
    _ensure_tables()
    if not _can_sales():
        return jsonify({'error': 'forbidden'}), 403
    oid = _org_id()
    q = Quotation.query.filter_by(id=qid, organization_id=oid).first()
    if not q:
        return jsonify({'error': 'not_found'}), 404
    existing = Invoice.query.filter_by(origin_quotation_id=q.id, organization_id=oid).first()
    if existing:
        if q.status == 'confirmed':
            q.status = 'invoiced'
            db.session.commit()
        return jsonify(
            {
                'invoice_id': existing.id,
                'number': existing.number,
                'status': existing.status,
                'quotation_status': q.status,
            }
        )

    if q.status != 'confirmed':
        return jsonify({'error': 'quotation_must_be_confirmed'}), 400

    inv = Invoice(
        organization_id=oid,
        number=_next_number('INV', Invoice, oid),
        customer_id=q.customer_id,
        status='draft',
        origin_quotation_id=q.id,
        salesperson_user_id=getattr(q, 'salesperson_user_id', None),
        date=datetime.utcnow(),
        created_by=getattr(current_user, 'id', None),
    )
    db.session.add(inv)
    db.session.flush()

    lines = QuotationLine.query.filter_by(quotation_id=q.id).all()
    for ln in lines:
        inv_ln = InvoiceLine(
            invoice_id=inv.id,
            product_id=ln.product_id,
            description=ln.description,
            quantity=ln.quantity,
            price_unit=ln.price_unit,
            tax_id=ln.tax_id,
            subtotal=ln.subtotal,
            total=ln.total,
        )
        db.session.add(inv_ln)
    inv.total = q.total
    inv.tax_total = q.tax_total
    inv.grand_total = q.grand_total
    q.status = 'invoiced'
    db.session.commit()
    return jsonify(
        {
            'invoice_id': inv.id,
            'number': inv.number,
            'status': inv.status,
            'quotation_status': q.status,
        }
    ), 201