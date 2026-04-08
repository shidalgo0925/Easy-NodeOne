"""Admin: códigos de descuento (CRUD + generación)."""

import json
import traceback
from datetime import datetime
from functools import wraps

from flask import Blueprint, jsonify, render_template, request
from flask_login import current_user, login_required

from nodeone.services.discount_codes import generate_discount_code

admin_discount_codes_bp = Blueprint('admin_discount_codes', __name__)


def _scope_user_ids_query(M):
    helper = getattr(M, '_admin_scope_user_ids_only', None)
    if callable(helper):
        return helper()
    from nodeone.services.user_organization import user_ids_query_in_organization

    scope_oid = M.admin_data_scope_organization_id()
    q = user_ids_query_in_organization(scope_oid)
    try:
        can_view_users = bool(getattr(current_user, 'is_admin', False) or current_user.has_permission('users.view'))
    except Exception:
        can_view_users = bool(getattr(current_user, 'is_admin', False))
    if not can_view_users:
        q = q.filter(M.User.id == current_user.id)
    return q


def _scoped_discount_codes_query(M):
    q = M.DiscountCode.query
    if hasattr(M.DiscountCode, 'organization_id'):
        return q.filter(M.DiscountCode.organization_id == M.admin_data_scope_organization_id())
    uids = _scope_user_ids_query(M)
    return q.filter(M.DiscountCode.created_by.in_(uids))


def _admin_required_lazy(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        import app as M
        from flask import flash, redirect, url_for

        if bool(getattr(current_user, 'must_change_password', False)):
            flash('Debes cambiar tu contraseña antes de continuar.', 'warning')
            return redirect(url_for('auth.change_password'))
        if not current_user.is_admin and not M._user_has_any_admin_permission(current_user):
            flash('No tienes permisos para acceder a esta página.', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)

    return decorated_function


@admin_discount_codes_bp.route('/admin/discount-codes')
@_admin_required_lazy
def admin_discount_codes():
    """Panel de gestión de códigos de descuento"""
    import app as M

    search = request.args.get('search', '').strip()
    status_filter = request.args.get('status', 'all')
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 10, type=int), 100)

    query = _scoped_discount_codes_query(M)

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

    query = query.order_by(M.DiscountCode.created_at.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    codes = pagination.items

    master_discount = M.Discount.query.filter_by(is_master=True, is_active=True).first()
    events = M.Event.query.filter_by(publish_status='published').order_by(M.Event.title).all()

    return render_template(
        'admin/discount_codes.html',
        codes=codes,
        pagination=pagination,
        search=search,
        status_filter=status_filter,
        master_discount=master_discount,
        events=events,
    )


@admin_discount_codes_bp.route('/admin/discount-codes/create', methods=['POST'])
@_admin_required_lazy
def admin_discount_code_create():
    """Crear nuevo código de descuento"""
    import app as M

    try:
        data = request.get_json() if request.is_json else request.form

        name = data.get('name', '').strip()
        description = data.get('description', '').strip()
        code_input = data.get('code', '').strip().upper()
        generate_auto = data.get('generate_auto', 'false') == 'true'
        prefix = data.get('prefix', 'DSC').strip().upper()
        discount_type = data.get('discount_type', 'percentage')
        value = float(data.get('value', 0))
        applies_to = data.get('applies_to', 'all')
        event_ids = data.get('event_ids', [])

        if generate_auto:
            code = generate_discount_code(prefix=prefix)
        else:
            if not code_input:
                return jsonify({'success': False, 'error': 'El código es requerido'}), 400

            if _scoped_discount_codes_query(M).filter_by(code=code_input).first():
                return jsonify({'success': False, 'error': 'Este código ya existe'}), 400

            code = code_input

        if value <= 0:
            return jsonify({'success': False, 'error': 'El valor del descuento debe ser mayor a 0'}), 400

        if discount_type == 'percentage' and value > 100:
            return jsonify({'success': False, 'error': 'El porcentaje no puede ser mayor a 100%'}), 400

        start_date_str = data.get('start_date')
        end_date_str = data.get('end_date')
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d') if start_date_str else None
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d') if end_date_str else None

        if start_date and end_date and start_date > end_date:
            return jsonify({'success': False, 'error': 'La fecha de inicio debe ser anterior a la fecha de fin'}), 400

        max_uses_total = int(data.get('max_uses_total', 0)) if data.get('max_uses_total') else None
        max_uses_per_user = int(data.get('max_uses_per_user', 1))
        valid_for_office365 = data.get('valid_for_office365') in (True, 'true', '1', 1)

        event_ids_json = None
        if event_ids and isinstance(event_ids, list):
            event_ids_json = json.dumps(event_ids)

        discount_code = M.DiscountCode(
            code=code,
            name=name,
            description=description,
            discount_type=discount_type,
            value=value,
            applies_to=applies_to,
            event_ids=event_ids_json,
            start_date=start_date,
            end_date=end_date,
            max_uses_total=max_uses_total,
            max_uses_per_user=max_uses_per_user,
            created_by=current_user.id,
            is_active=True,
            valid_for_office365=valid_for_office365,
        )
        if hasattr(M.DiscountCode, 'organization_id'):
            discount_code.organization_id = M.admin_data_scope_organization_id()

        M.db.session.add(discount_code)
        M.db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Código de descuento creado exitosamente',
            'code_id': discount_code.id,
            'code': discount_code.code,
        })

    except ValueError as e:
        M.db.session.rollback()
        return jsonify({'success': False, 'error': f'Error en los datos: {str(e)}'}), 400
    except Exception as e:
        M.db.session.rollback()
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_discount_codes_bp.route('/admin/discount-codes/<int:code_id>', methods=['GET'])
@_admin_required_lazy
def admin_discount_code_get(code_id):
    """Obtener información de un código de descuento"""
    import app as M

    try:
        code = _scoped_discount_codes_query(M).filter(M.DiscountCode.id == code_id).first()
        if not code:
            return jsonify({'success': False, 'error': 'No autorizado'}), 403

        event_ids = []
        if code.event_ids:
            try:
                event_ids = json.loads(code.event_ids)
            except Exception:
                pass

        return jsonify({
            'success': True,
            'code': {
                'id': code.id,
                'code': code.code,
                'name': code.name,
                'description': code.description,
                'discount_type': code.discount_type,
                'value': code.value,
                'applies_to': code.applies_to,
                'event_ids': event_ids,
                'start_date': code.start_date.isoformat() if code.start_date else None,
                'end_date': code.end_date.isoformat() if code.end_date else None,
                'max_uses_total': code.max_uses_total,
                'max_uses_per_user': code.max_uses_per_user,
                'is_active': code.is_active,
                'current_uses': code.current_uses,
                'valid_for_office365': getattr(code, 'valid_for_office365', False),
            },
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_discount_codes_bp.route('/admin/discount-codes/<int:code_id>/update', methods=['POST'])
@_admin_required_lazy
def admin_discount_code_update(code_id):
    """Actualizar código de descuento"""
    import app as M

    try:
        code = _scoped_discount_codes_query(M).filter(M.DiscountCode.id == code_id).first()
        if not code:
            return jsonify({'success': False, 'error': 'No autorizado'}), 403
        data = request.get_json() if request.is_json else request.form

        if 'name' in data:
            code.name = data.get('name', '').strip()
        if 'description' in data:
            code.description = data.get('description', '').strip()
        if 'discount_type' in data:
            code.discount_type = data.get('discount_type')
        if 'value' in data:
            value = float(data.get('value', 0))
            if value <= 0:
                return jsonify({'success': False, 'error': 'El valor debe ser mayor a 0'}), 400
            if code.discount_type == 'percentage' and value > 100:
                return jsonify({'success': False, 'error': 'El porcentaje no puede ser mayor a 100%'}), 400
            code.value = value
        if 'applies_to' in data:
            code.applies_to = data.get('applies_to')
        if 'valid_for_office365' in data:
            code.valid_for_office365 = data.get('valid_for_office365') in (True, 'true', '1', 1)
        if 'event_ids' in data:
            event_ids = data.get('event_ids', [])
            code.event_ids = json.dumps(event_ids) if event_ids else None

        if 'start_date' in data:
            start_date_str = data.get('start_date')
            code.start_date = datetime.strptime(start_date_str, '%Y-%m-%d') if start_date_str else None
        if 'end_date' in data:
            end_date_str = data.get('end_date')
            code.end_date = datetime.strptime(end_date_str, '%Y-%m-%d') if end_date_str else None

        if code.start_date and code.end_date and code.start_date > code.end_date:
            return jsonify({'success': False, 'error': 'La fecha de inicio debe ser anterior a la fecha de fin'}), 400

        if 'max_uses_total' in data:
            max_uses = data.get('max_uses_total')
            code.max_uses_total = int(max_uses) if max_uses else None
        if 'max_uses_per_user' in data:
            code.max_uses_per_user = int(data.get('max_uses_per_user', 1))

        if 'is_active' in data:
            code.is_active = bool(data.get('is_active'))

        code.updated_at = datetime.utcnow()
        M.db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Código de descuento actualizado exitosamente',
        })

    except ValueError as e:
        M.db.session.rollback()
        return jsonify({'success': False, 'error': f'Error en los datos: {str(e)}'}), 400
    except Exception as e:
        M.db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_discount_codes_bp.route('/admin/discount-codes/<int:code_id>/delete', methods=['POST'])
@_admin_required_lazy
def admin_discount_code_delete(code_id):
    """Eliminar código de descuento"""
    import app as M

    try:
        code = _scoped_discount_codes_query(M).filter(M.DiscountCode.id == code_id).first()
        if not code:
            return jsonify({'success': False, 'error': 'No autorizado'}), 403

        if code.applications:
            return jsonify({
                'success': False,
                'error': 'No se puede eliminar un código que ya ha sido usado',
            }), 400

        M.db.session.delete(code)
        M.db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Código de descuento eliminado exitosamente',
        })

    except Exception as e:
        M.db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_discount_codes_bp.route('/api/admin/discount-codes/generate', methods=['POST'])
@_admin_required_lazy
def api_generate_discount_code():
    """API para generar código automáticamente"""
    try:
        data = request.get_json() or {}
        prefix = data.get('prefix', 'DSC').strip().upper()
        length = int(data.get('length', 8))
        custom_part = data.get('custom_part', '').strip().upper()

        code = generate_discount_code(
            prefix=prefix,
            length=length,
            custom_part=custom_part if custom_part else None,
        )

        return jsonify({
            'success': True,
            'code': code,
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
