"""Admin: descuentos por membresía y descuento maestro."""

from datetime import datetime
from functools import wraps

from flask import Blueprint, jsonify, render_template, request
from flask_login import current_user, login_required

admin_membership_discounts_bp = Blueprint('admin_membership_discounts', __name__)


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


@admin_membership_discounts_bp.route('/admin/membership-discounts')
@_admin_required_lazy
def admin_membership_discounts():
    """Panel de administración de descuentos por membresía"""
    import app as M

    discounts = M.MembershipDiscount.query.order_by(
        M.MembershipDiscount.product_type,
        M.MembershipDiscount.membership_type,
    ).all()
    return render_template('admin/membership_discounts.html', discounts=discounts)


@admin_membership_discounts_bp.route('/api/admin/membership-discounts/create', methods=['POST'])
@_admin_required_lazy
def admin_membership_discounts_create():
    """Crear nuevo descuento de membresía"""
    import app as M

    try:
        data = request.get_json() or {}

        existing = M.MembershipDiscount.query.filter_by(
            membership_type=data.get('membership_type'),
            product_type=data.get('product_type'),
        ).first()

        if existing:
            return jsonify({
                'success': False,
                'error': f'Ya existe un descuento para {data.get("membership_type")} - {data.get("product_type")}',
            }), 400

        discount = M.MembershipDiscount(
            membership_type=data.get('membership_type'),
            product_type=data.get('product_type'),
            discount_percentage=float(data.get('discount_percentage', 0)),
            is_active=data.get('is_active', True),
        )

        M.db.session.add(discount)
        M.db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Descuento creado exitosamente',
            'discount': discount.to_dict(),
        })
    except Exception as e:
        M.db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400


@admin_membership_discounts_bp.route('/api/admin/membership-discounts/update/<int:discount_id>', methods=['PUT'])
@_admin_required_lazy
def admin_membership_discounts_update(discount_id):
    """Actualizar descuento de membresía"""
    import app as M

    try:
        discount = M.MembershipDiscount.query.get_or_404(discount_id)
        data = request.get_json() or {}

        new_membership_type = data.get('membership_type', discount.membership_type)
        new_product_type = data.get('product_type', discount.product_type)

        if new_membership_type != discount.membership_type or new_product_type != discount.product_type:
            existing = M.MembershipDiscount.query.filter_by(
                membership_type=new_membership_type,
                product_type=new_product_type,
            ).first()

            if existing and existing.id != discount_id:
                return jsonify({
                    'success': False,
                    'error': f'Ya existe un descuento para {new_membership_type} - {new_product_type}',
                }), 400

        discount.membership_type = new_membership_type
        discount.product_type = new_product_type
        discount.discount_percentage = float(data.get('discount_percentage', discount.discount_percentage))
        discount.is_active = data.get('is_active', discount.is_active)
        discount.updated_at = datetime.utcnow()

        M.db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Descuento actualizado exitosamente',
            'discount': discount.to_dict(),
        })
    except Exception as e:
        M.db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400


@admin_membership_discounts_bp.route('/api/admin/membership-discounts/<int:discount_id>', methods=['GET'])
@_admin_required_lazy
def admin_membership_discounts_get(discount_id):
    """Obtener un descuento por ID"""
    import app as M

    try:
        discount = M.MembershipDiscount.query.get_or_404(discount_id)
        return jsonify({'success': True, 'discount': discount.to_dict()})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 404


@admin_membership_discounts_bp.route('/api/admin/membership-discounts/delete/<int:discount_id>', methods=['DELETE'])
@_admin_required_lazy
def admin_membership_discounts_delete(discount_id):
    """Eliminar descuento de membresía"""
    import app as M

    try:
        discount = M.MembershipDiscount.query.get_or_404(discount_id)
        M.db.session.delete(discount)
        M.db.session.commit()

        return jsonify({'success': True, 'message': 'Descuento eliminado exitosamente'})
    except Exception as e:
        M.db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400


@admin_membership_discounts_bp.route('/admin/master-discount', methods=['GET', 'POST'])
@_admin_required_lazy
def admin_master_discount():
    """Gestionar descuento maestro"""
    import app as M

    if request.method == 'GET':
        master_discount = M.Discount.query.filter_by(is_master=True, is_active=True).first()
        return render_template('admin/master_discount.html', master_discount=master_discount)

    try:
        data = request.get_json() if request.is_json else request.form

        M.Discount.query.filter_by(is_master=True).update({'is_master': False})

        is_active = data.get('is_active', 'false') == 'true'

        if not is_active:
            M.db.session.commit()
            return jsonify({
                'success': True,
                'message': 'Descuento maestro desactivado',
            })

        discount_id = data.get('discount_id')

        if discount_id:
            discount = M.Discount.query.get_or_404(discount_id)
            discount.is_master = True
            discount.is_active = True
        else:
            name = data.get('name', 'Descuento Maestro').strip()
            discount_type = data.get('discount_type', 'percentage')
            value = float(data.get('value', 0))

            if value <= 0:
                return jsonify({'success': False, 'error': 'El valor debe ser mayor a 0'}), 400

            discount = M.Discount(
                name=name,
                code=f'MASTER-{int(datetime.utcnow().timestamp())}',
                discount_type=discount_type,
                value=value,
                is_master=True,
                is_active=True,
                applies_automatically=True,
            )
            M.db.session.add(discount)

        M.db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Descuento maestro configurado exitosamente',
            'discount_id': discount.id,
        })

    except Exception as e:
        M.db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
