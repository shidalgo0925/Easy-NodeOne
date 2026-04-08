"""Admin: revisión de pagos, aprobación/rechazo y configuración de integración."""

import json
from datetime import datetime
from functools import wraps

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from nodeone.services.payment_post_process import process_cart_after_payment, send_payment_to_odoo

payments_admin_bp = Blueprint('payments_admin', __name__)


def _payment_in_admin_scope_or_403(M, payment):
    from nodeone.services.user_organization import user_has_active_membership

    scope_oid = M.admin_data_scope_organization_id()
    user = M.User.query.get(payment.user_id) if payment else None
    if not user or not user_has_active_membership(user, int(scope_oid)):
        return None
    return user


def _admin_scope_user_ids_only_safe(M):
    """
    Compat: algunos despliegues no exponen M._admin_scope_user_ids_only.
    Fallback seguro por organization_id activo en sesión admin.
    """
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


def _admin_required_lazy(f):
    """Igual que app.admin_required; importa app en request (evita ciclo)."""
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        import app as M

        if bool(getattr(current_user, 'must_change_password', False)):
            flash('Debes cambiar tu contraseña antes de continuar.', 'warning')
            return redirect(url_for('auth.change_password'))
        if not current_user.is_admin and not M._user_has_any_admin_permission(current_user):
            flash('No tienes permisos para acceder a esta página.', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)

    return decorated_function


@payments_admin_bp.route('/admin/payments/review/<int:payment_id>')
@_admin_required_lazy
def admin_payment_review(payment_id):
    """Revisar y aprobar/rechazar pago con OCR"""
    import app as M

    payment = M.Payment.query.get_or_404(payment_id)
    user = _payment_in_admin_scope_or_403(M, payment)
    if not user:
        return ('No autorizado para revisar este pago', 403)

    ocr_data = None
    if payment.ocr_data:
        try:
            ocr_data = json.loads(payment.ocr_data)
        except Exception:
            pass

    return render_template(
        'admin/payment_review.html',
        payment=payment,
        user=user,
        ocr_data=ocr_data
    )


@payments_admin_bp.route('/api/admin/payments/<int:payment_id>/approve', methods=['POST'])
@_admin_required_lazy
def api_approve_payment(payment_id):
    """Aprobar pago y otorgar membresía"""
    import app as M

    try:
        payment = M.Payment.query.get_or_404(payment_id)
        user = _payment_in_admin_scope_or_403(M, payment)
        if not user:
            return jsonify({'success': False, 'error': 'No autorizado para aprobar este pago'}), 403

        if payment.status == 'succeeded':
            return jsonify({'success': False, 'error': 'El pago ya está aprobado'}), 400

        payment.status = 'succeeded'
        payment.ocr_status = 'verified'
        payment.ocr_verified_at = datetime.utcnow()
        payment.paid_at = datetime.utcnow()

        admin_notes = request.json.get('notes', '') if request.is_json else ''
        if admin_notes:
            payment.admin_notes = admin_notes

        M.db.session.commit()

        cart = M.get_or_create_cart(payment.user_id)
        if cart.get_items_count() > 0:
            process_cart_after_payment(cart, payment)
            cart.clear()
            M.db.session.commit()

        if user:
            try:
                subscription = M.Subscription.query.filter_by(payment_id=payment.id).first()
                if subscription:
                    M.NotificationEngine.notify_membership_payment(user, payment, subscription)
                    try:
                        from nodeone.services.communication_dispatch import (
                            dispatch_membership_payment_confirmation,
                        )

                        dispatch_membership_payment_confirmation(user, payment, subscription)
                    except Exception:
                        pass
            except Exception:
                pass

            try:
                send_payment_to_odoo(payment, user, cart)
            except Exception as e:
                print(f"⚠️ Error enviando pago a Odoo (no crítico): {e}")

        return jsonify({'success': True, 'message': 'Pago aprobado exitosamente'})
    except Exception as e:
        M.db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@payments_admin_bp.route('/api/admin/payments/<int:payment_id>/reject', methods=['POST'])
@_admin_required_lazy
def api_reject_payment(payment_id):
    """Rechazar pago"""
    import app as M

    try:
        payment = M.Payment.query.get_or_404(payment_id)
        user = _payment_in_admin_scope_or_403(M, payment)
        if not user:
            return jsonify({'success': False, 'error': 'No autorizado para rechazar este pago'}), 403

        payment.status = 'failed'
        payment.ocr_status = 'rejected'
        payment.ocr_verified_at = datetime.utcnow()

        admin_notes = request.json.get('notes', '') if request.is_json else ''
        if admin_notes:
            payment.admin_notes = admin_notes

        M.db.session.commit()

        if user and M.EMAIL_TEMPLATES_AVAILABLE and M.email_service:
            try:
                html_content = f"""
                <h2>Pago Rechazado</h2>
                <p>Hola {user.first_name},</p>
                <p>Lamentamos informarte que tu pago #{payment.id} ha sido rechazado.</p>
                <p><strong>Razón:</strong> {admin_notes or 'No se pudo verificar el comprobante de pago'}</p>
                <p>Por favor, verifica los datos de tu comprobante y vuelve a intentar.</p>
                <p>Saludos,<br>Equipo RelaticPanama</p>
                """
                M.email_service.send_email(
                    subject='Pago Rechazado - RelaticPanama',
                    recipients=[user.email],
                    html_content=html_content,
                    email_type='payment_rejected',
                    related_entity_type='payment',
                    related_entity_id=payment.id,
                    recipient_id=user.id,
                    recipient_name=f"{user.first_name} {user.last_name}"
                )
            except Exception:
                pass

        return jsonify({'success': True, 'message': 'Pago rechazado'})
    except Exception as e:
        M.db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@payments_admin_bp.route('/admin/payments')
@_admin_required_lazy
def admin_payments():
    """Panel de configuración de métodos de pago y revisión de pagos pendientes"""
    import app as M

    try:
        scope_oid = M.admin_data_scope_organization_id()
        payment_config = M.PaymentConfig.get_active_config(organization_id=scope_oid)

        if payment_config:
            if not isinstance(payment_config, M.PaymentConfig):
                print(f"⚠️ Error: Se obtuvo un objeto de tipo {type(payment_config).__name__} en lugar de PaymentConfig")
                config_dict = None
            elif not hasattr(payment_config, 'to_dict'):
                print("⚠️ Error: PaymentConfig no tiene método to_dict")
                config_dict = None
            else:
                config_dict = payment_config.to_dict()
        else:
            config_dict = None
    except Exception as e:
        print(f"❌ Error obteniendo PaymentConfig: {e}")
        import traceback
        traceback.print_exc()
        config_dict = None

    ppq = M.Payment.query.filter(
        M.Payment.ocr_status.in_(['pending', 'needs_review']),
        M.Payment.status == 'pending'
    )
    uids_sq = _admin_scope_user_ids_only_safe(M)
    if uids_sq is not None:
        ppq = ppq.filter(M.Payment.user_id.in_(uids_sq))
    pending_payments = ppq.order_by(M.Payment.created_at.desc()).limit(20).all()

    htq = M.HistoryTransaction.query.filter(
        M.HistoryTransaction.transaction_type.in_(['payment', 'purchase'])
    )
    if uids_sq is not None:
        htq = htq.filter(M.HistoryTransaction.actor_id.in_(uids_sq))
    payment_transactions = htq.order_by(M.HistoryTransaction.timestamp.desc()).limit(100).all()

    enriched_transactions = []
    for trans in payment_transactions:
        trans_dict = trans.to_dict(include_sensitive=True)

        if trans.actor_id:
            actor = M.User.query.get(trans.actor_id)
            if actor:
                trans_dict['actor'] = {
                    'id': actor.id,
                    'email': actor.email,
                    'first_name': actor.first_name,
                    'last_name': actor.last_name
                }

        payment_id = None
        try:
            if trans.payload:
                payload_data = json.loads(trans.payload)
                payment_id = payload_data.get('payment_id') or payload_data.get('payment', {}).get('id')
            if not payment_id and trans.result:
                result_data = json.loads(trans.result)
                payment_id = result_data.get('payment_id') or result_data.get('payment', {}).get('id')
        except Exception:
            pass

        if payment_id:
            pay = M.Payment.query.get(payment_id)
            if pay:
                trans_dict['payment'] = {
                    'id': pay.id,
                    'amount': float(pay.amount) / 100 if pay.amount else 0,
                    'currency': pay.currency.upper() if pay.currency else 'USD',
                    'status': pay.status,
                    'method': pay.payment_method
                }

        enriched_transactions.append(trans_dict)

    print(f"📊 admin_payments(): Pasando {len(enriched_transactions)} transacciones al template")
    if enriched_transactions:
        print(f"   - Primera transacción: ID {enriched_transactions[0].get('id')}, Tipo: {enriched_transactions[0].get('transaction_type')}")

    return render_template(
        'admin/payments.html',
        payment_config=config_dict,
        pending_payments=pending_payments,
        payment_transactions=enriched_transactions
    )


@payments_admin_bp.route('/api/admin/payments/config', methods=['GET', 'POST', 'PUT'])
@_admin_required_lazy
def api_payment_config():
    """API para obtener y actualizar configuración de pagos"""
    import app as M

    if request.method == 'GET':
        scope_oid = M.admin_data_scope_organization_id()
        config = M.PaymentConfig.get_active_config(organization_id=scope_oid)
        if config:
            return jsonify({'success': True, 'config': config.to_dict()})
        else:
            return jsonify({'success': False, 'message': 'No hay configuración activa'})

    elif request.method in ['POST', 'PUT']:
        data = request.get_json()
        scope_oid = M.admin_data_scope_organization_id()

        M.PaymentConfig.query.filter_by(organization_id=scope_oid).update({'is_active': False})
        config = (
            M.PaymentConfig.query.filter_by(organization_id=scope_oid)
            .order_by(M.PaymentConfig.id.asc())
            .first()
        )

        if not config:
            config = M.PaymentConfig(
                organization_id=scope_oid,
                stripe_secret_key=data.get('stripe_secret_key', ''),
                stripe_publishable_key=data.get('stripe_publishable_key', ''),
                stripe_webhook_secret=data.get('stripe_webhook_secret', ''),
                paypal_client_id=data.get('paypal_client_id', ''),
                paypal_client_secret=data.get('paypal_client_secret', ''),
                paypal_mode=data.get('paypal_mode', 'sandbox'),
                paypal_return_url=data.get('paypal_return_url', ''),
                paypal_cancel_url=data.get('paypal_cancel_url', ''),
                banco_general_merchant_id=data.get('banco_general_merchant_id', ''),
                banco_general_api_key=data.get('banco_general_api_key', ''),
                banco_general_shared_secret=data.get('banco_general_shared_secret', ''),
                banco_general_api_url=data.get('banco_general_api_url', 'https://api.cybersource.com'),
                yappy_api_key=data.get('yappy_api_key', ''),
                yappy_merchant_id=data.get('yappy_merchant_id', ''),
                yappy_api_url=data.get('yappy_api_url', 'https://api.yappy.im'),
                use_environment_variables=bool(data.get('use_environment_variables', True)),
                is_active=True,
            )
            M.db.session.add(config)
        else:
            if getattr(config, 'organization_id', None) != scope_oid:
                config.organization_id = scope_oid
            if 'stripe_secret_key' in data:
                config.stripe_secret_key = data.get('stripe_secret_key', config.stripe_secret_key)
            if 'stripe_publishable_key' in data:
                config.stripe_publishable_key = data.get('stripe_publishable_key', config.stripe_publishable_key)
            if 'stripe_webhook_secret' in data:
                config.stripe_webhook_secret = data.get('stripe_webhook_secret', config.stripe_webhook_secret)
            if 'paypal_client_id' in data:
                config.paypal_client_id = data.get('paypal_client_id', config.paypal_client_id)
            if 'paypal_client_secret' in data:
                config.paypal_client_secret = data.get('paypal_client_secret', config.paypal_client_secret)
            if 'paypal_mode' in data:
                config.paypal_mode = data.get('paypal_mode', config.paypal_mode)
            if 'paypal_return_url' in data:
                config.paypal_return_url = data.get('paypal_return_url', config.paypal_return_url)
            if 'paypal_cancel_url' in data:
                config.paypal_cancel_url = data.get('paypal_cancel_url', config.paypal_cancel_url)
            if 'banco_general_merchant_id' in data:
                config.banco_general_merchant_id = data.get('banco_general_merchant_id', config.banco_general_merchant_id)
            if 'banco_general_api_key' in data:
                config.banco_general_api_key = data.get('banco_general_api_key', config.banco_general_api_key)
            if 'banco_general_shared_secret' in data:
                config.banco_general_shared_secret = data.get('banco_general_shared_secret', config.banco_general_shared_secret)
            if 'banco_general_api_url' in data:
                config.banco_general_api_url = data.get('banco_general_api_url', config.banco_general_api_url)
            if 'yappy_api_key' in data:
                config.yappy_api_key = data.get('yappy_api_key', config.yappy_api_key)
            if 'yappy_merchant_id' in data:
                config.yappy_merchant_id = data.get('yappy_merchant_id', config.yappy_merchant_id)
            if 'yappy_api_url' in data:
                config.yappy_api_url = data.get('yappy_api_url', config.yappy_api_url)
            config.use_environment_variables = bool(data.get('use_environment_variables', config.use_environment_variables))
            config.is_active = True
            config.updated_at = datetime.utcnow()

        try:
            M.db.session.commit()
            return jsonify({
                'success': True,
                'message': 'Configuración de pagos actualizada exitosamente',
                'config': config.to_dict()
            })
        except Exception as e:
            M.db.session.rollback()
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
