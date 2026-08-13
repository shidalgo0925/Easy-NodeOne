"""Admin DiscountCode — promos por producto ETS (plataforma)."""

from __future__ import annotations

import traceback
from datetime import datetime

from flask import Blueprint, jsonify, redirect, render_template, request, url_for
from flask_login import current_user

from nodeone.services.discount_code_admin import (
    list_commercial_products,
    normalize_product_codes,
    parse_optional_dates,
    product_codes_query,
    resolve_discount_code,
    serialize_product_discount_row,
    validate_discount_value,
)
from nodeone.services.discount_codes import generate_discount_code

admin_product_discount_codes_bp = Blueprint('admin_product_discount_codes', __name__)


def _platform_admin(f):
    from app import platform_admin_required

    return platform_admin_required(f)


@admin_product_discount_codes_bp.route('/admin/discount-codes')
def legacy_discount_codes_redirect():
    """Ruta legacy → promos por producto (evita panel duplicado con scope roto)."""
    return redirect(url_for('admin_product_discount_codes.index'))


@admin_product_discount_codes_bp.route('/admin/commercial/product-discount-codes')
@_platform_admin
def index():
    import app as M

    search = request.args.get('search', '').strip()
    status_filter = request.args.get('status', 'all')
    product_filter = (request.args.get('product') or '').strip().lower()
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 15, type=int), 100)

    query = product_codes_query(M)
    if search:
        query = query.filter(
            M.db.or_(
                M.DiscountCode.code.ilike(f'%{search}%'),
                M.DiscountCode.name.ilike(f'%{search}%'),
            )
        )
    if status_filter == 'active':
        query = query.filter_by(is_active=True)
    elif status_filter == 'inactive':
        query = query.filter_by(is_active=False)
    if product_filter and hasattr(M.DiscountCode, 'product_codes'):
        query = query.filter(M.DiscountCode.product_codes.ilike(f'%"{product_filter}"%'))

    query = query.order_by(M.DiscountCode.created_at.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return render_template(
        'admin/product_discount_codes.html',
        codes=pagination.items,
        pagination=pagination,
        search=search,
        status_filter=status_filter,
        product_filter=product_filter,
        products=list_commercial_products(),
    )


@admin_product_discount_codes_bp.route('/admin/commercial/product-discount-codes/create', methods=['POST'])
@_platform_admin
def create():
    import app as M

    try:
        data = request.get_json() if request.is_json else request.form
        name = (data.get('name') or '').strip()
        if not name:
            return jsonify({'success': False, 'error': 'El nombre es requerido'}), 400

        product_codes = normalize_product_codes(data.get('product_codes') or data.getlist('product_codes'))
        if not product_codes:
            return jsonify({'success': False, 'error': 'Seleccione al menos un producto'}), 400

        generate_auto = str(data.get('generate_auto', 'false')).lower() in ('1', 'true', 'yes')
        prefix = (data.get('prefix') or 'PROD').strip().upper() or 'PROD'
        discount_type = (data.get('discount_type') or 'percentage').strip().lower()
        value = float(data.get('value', 0))

        code, code_err = resolve_discount_code(
            M,
            code_input=(data.get('code') or '').strip().upper(),
            generate_auto=generate_auto,
            prefix=prefix,
        )
        if code_err:
            return jsonify({'success': False, 'error': code_err}), 400

        val_err = validate_discount_value(discount_type, value)
        if val_err:
            return jsonify({'success': False, 'error': val_err}), 400

        start_date, end_date = parse_optional_dates(data.get('start_date'), data.get('end_date'))
        max_uses_total = int(data.get('max_uses_total')) if data.get('max_uses_total') else None
        max_uses_per_user = int(data.get('max_uses_per_user') or 1)

        row = M.DiscountCode(
            code=code,
            name=name,
            description=(data.get('description') or '').strip() or None,
            discount_type=discount_type,
            value=value,
            applies_to='products',
            start_date=start_date,
            end_date=end_date,
            max_uses_total=max_uses_total,
            max_uses_per_user=max_uses_per_user,
            created_by=current_user.id,
            is_active=True,
        )
        row.set_product_codes_list(product_codes)
        M.db.session.add(row)
        M.db.session.commit()
        return jsonify({'success': True, 'code_id': row.id, 'code': row.code})
    except ValueError as exc:
        M.db.session.rollback()
        return jsonify({'success': False, 'error': str(exc)}), 400
    except Exception as exc:
        M.db.session.rollback()
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(exc)}), 500


@admin_product_discount_codes_bp.route('/admin/commercial/product-discount-codes/<int:code_id>', methods=['GET'])
@_platform_admin
def get_one(code_id: int):
    import app as M

    row = product_codes_query(M).filter(M.DiscountCode.id == code_id).first()
    if row is None:
        return jsonify({'success': False, 'error': 'No encontrado'}), 404
    return jsonify({'success': True, 'code': serialize_product_discount_row(row)})


@admin_product_discount_codes_bp.route('/admin/commercial/product-discount-codes/<int:code_id>/update', methods=['POST'])
@_platform_admin
def update(code_id: int):
    import app as M

    row = product_codes_query(M).filter(M.DiscountCode.id == code_id).first()
    if row is None:
        return jsonify({'success': False, 'error': 'No encontrado'}), 404
    data = request.get_json() if request.is_json else request.form
    try:
        if 'name' in data:
            row.name = (data.get('name') or '').strip()
        if 'description' in data:
            row.description = (data.get('description') or '').strip() or None
        if 'discount_type' in data:
            row.discount_type = data.get('discount_type')
        if 'value' in data:
            value = float(data.get('value', 0))
            val_err = validate_discount_value(row.discount_type or 'percentage', value)
            if val_err:
                return jsonify({'success': False, 'error': val_err}), 400
            row.value = value
        if 'product_codes' in data or 'product_codes[]' in data:
            codes = normalize_product_codes(data.get('product_codes') or data.getlist('product_codes'))
            if not codes:
                return jsonify({'success': False, 'error': 'Seleccione al menos un producto'}), 400
            row.set_product_codes_list(codes)
        if 'start_date' in data:
            s = data.get('start_date')
            row.start_date = datetime.strptime(s, '%Y-%m-%d') if s else None
        if 'end_date' in data:
            e = data.get('end_date')
            row.end_date = datetime.strptime(e, '%Y-%m-%d') if e else None
        if 'max_uses_total' in data:
            m = data.get('max_uses_total')
            row.max_uses_total = int(m) if m else None
        if 'max_uses_per_user' in data:
            row.max_uses_per_user = int(data.get('max_uses_per_user') or 1)
        if 'is_active' in data:
            row.is_active = str(data.get('is_active')).lower() in ('1', 'true', 'yes')
        row.applies_to = 'products'
        row.updated_at = datetime.utcnow()
        M.db.session.commit()
        return jsonify({'success': True})
    except Exception as exc:
        M.db.session.rollback()
        return jsonify({'success': False, 'error': str(exc)}), 500


@admin_product_discount_codes_bp.route('/admin/commercial/product-discount-codes/<int:code_id>/delete', methods=['POST'])
@_platform_admin
def delete(code_id: int):
    import app as M

    row = product_codes_query(M).filter(M.DiscountCode.id == code_id).first()
    if row is None:
        return jsonify({'success': False, 'error': 'No encontrado'}), 404
    if row.applications:
        return jsonify({'success': False, 'error': 'No se puede eliminar: ya tiene usos'}), 400
    M.db.session.delete(row)
    M.db.session.commit()
    return jsonify({'success': True})


@admin_product_discount_codes_bp.route('/api/admin/commercial/product-discount-codes/generate', methods=['POST'])
@_platform_admin
def api_generate():
    data = request.get_json() or {}
    prefix = (data.get('prefix') or 'PROD').strip().upper() or 'PROD'
    code = generate_discount_code(prefix=prefix, length=int(data.get('length') or 8))
    return jsonify({'success': True, 'code': code})


# Compat: API legacy bajo /api/admin/discount-codes/generate
@admin_product_discount_codes_bp.route('/api/admin/discount-codes/generate', methods=['POST'])
@_platform_admin
def api_generate_legacy():
    return api_generate()
