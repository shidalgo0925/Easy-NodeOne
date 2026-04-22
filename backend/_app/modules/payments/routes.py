# Rutas del carrito y checkout.
from flask import Blueprint, request, jsonify, render_template, redirect, url_for
from flask_login import login_required, current_user

from app import email_verified_required, flash
from . import service as svc

payments_bp = Blueprint('payments', __name__, url_prefix='')


@payments_bp.route('/cart')
@login_required
def cart():
    cart = svc.get_or_create_cart(current_user.id)
    return render_template('cart.html', cart=cart)


@payments_bp.route('/cart/add', methods=['POST'])
@login_required
@email_verified_required
def cart_add():
    """Precio y nombre: siempre vía ``resolve_product_for_cart`` (servidor); no confiar en base_price del cliente."""
    try:
        data = request.get_json() if request.is_json else request.form
        product_type = data.get('product_type')
        quantity = int(data.get('quantity', 1))
        resolved, err, status = svc.resolve_product_for_cart(current_user, data)
        if err is not None:
            return jsonify(err), status
        product_id, product_name, product_description, unit_price, metadata = resolved
        cart = svc.add_to_cart(
            current_user.id,
            product_type,
            product_id,
            product_name,
            unit_price,
            quantity,
            product_description,
            metadata,
        )
        return jsonify({
            'success': True,
            'message': 'Producto agregado al carrito',
            'cart_items_count': cart.get_items_count(),
            'cart_total': cart.get_total()
        })
    except ValueError as e:
        return jsonify({'success': False, 'error': f'Error de validación: {str(e)}'}), 400
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@payments_bp.route('/cart/remove/<int:item_id>', methods=['POST'])
@login_required
def cart_remove(item_id):
    try:
        cart_after, err = svc.remove_item(current_user.id, item_id)
        if err is not None:
            return jsonify(err), 404
        return jsonify({
            'success': True,
            'message': 'Producto eliminado del carrito',
            'cart_items_count': cart_after.get_items_count(),
            'cart_total': cart_after.get_total()
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@payments_bp.route('/cart/update/<int:item_id>', methods=['POST'])
@login_required
def cart_update(item_id):
    try:
        data = request.get_json() if request.is_json else request.form
        quantity = int(data.get('quantity', 1))
        cart_after, item, err, status = svc.update_item(current_user.id, item_id, quantity)
        if err is not None:
            return jsonify(err), status
        if cart_after is None:
            return jsonify({'success': False, 'error': 'Item no encontrado'}), 404
        return jsonify({
            'success': True,
            'message': 'Cantidad actualizada',
            'cart_items_count': cart_after.get_items_count(),
            'cart_total': cart_after.get_total(),
            'item_subtotal': item.get_subtotal()
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@payments_bp.route('/cart/count', methods=['GET'])
@login_required
def cart_count():
    try:
        cart = svc.get_or_create_cart(current_user.id)
        return jsonify({
            'count': cart.get_items_count(),
            'total': cart.get_total()
        })
    except Exception:
        return jsonify({'count': 0, 'total': 0})


@payments_bp.route('/checkout')
@login_required
@email_verified_required
def checkout():
    data = svc.get_checkout_data(current_user.id)
    if data[0] is None:
        flash('Tu carrito está vacío. Agrega productos antes de proceder al pago.', 'warning')
        return redirect(url_for(data[1]))
    cart, total_amount, discount_breakdown = data
    try:
        from app import PAYMENT_METHODS, PAYMENT_PROCESSORS_AVAILABLE, STRIPE_PUBLISHABLE_KEY
        payment_methods = PAYMENT_METHODS if PAYMENT_PROCESSORS_AVAILABLE else {'stripe': 'Stripe (Tarjeta de Crédito)'}
        stripe_pk = STRIPE_PUBLISHABLE_KEY
    except Exception:
        payment_methods = {'stripe': 'Stripe (Tarjeta de Crédito)'}
        stripe_pk = None
    return render_template(
        'checkout.html',
        cart=cart,
        total_amount=total_amount,
        discount_breakdown=discount_breakdown,
        stripe_publishable_key=stripe_pk,
        payment_methods=payment_methods,
    )


@payments_bp.route('/checkout/<membership_type>')
@login_required
def checkout_membership(membership_type):
    redirect_ok, redirect_err = svc.add_membership_to_cart_and_checkout(current_user.id, membership_type)
    if redirect_err:
        flash('Tipo de membresía inválido.', 'error')
        return redirect(url_for(redirect_err))
    return redirect(url_for(redirect_ok))


@payments_bp.route('/api/cart/apply-discount-code', methods=['POST'])
@login_required
def api_apply_discount_code():
    try:
        data = request.get_json() or {}
        code = data.get('code', '').strip().upper()
        success, message, breakdown = svc.apply_discount_code(current_user.id, code)
        if success:
            return jsonify({
                'success': True,
                'message': message,
                'breakdown': breakdown
            })
        return jsonify({'success': False, 'error': message}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@payments_bp.route('/api/cart/remove-discount-code', methods=['POST'])
@login_required
def api_remove_discount_code():
    try:
        breakdown = svc.remove_discount_code(current_user.id)
        return jsonify({
            'success': True,
            'message': 'Código de descuento removido',
            'breakdown': breakdown
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
