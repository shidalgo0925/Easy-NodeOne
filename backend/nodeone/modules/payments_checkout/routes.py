"""Checkout, callbacks de pago y webhook Stripe."""

import json
import os
from collections import Counter
from datetime import datetime, timedelta

from flask import Blueprint, flash, jsonify, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required
from functools import wraps

from nodeone.services.payment_post_process import process_cart_after_payment, send_payment_to_odoo
from utils.organization import payment_organization_id_for_request

payments_checkout_bp = Blueprint('payments_checkout', __name__)


def _email_verified_check_then(f):
    """Delega en app.email_verified_required sin import circular al cargar el módulo."""
    import app as M
    return M.email_verified_required(f)


def _make_absolute_url(url):
    """
    Convierte una URL relativa a absoluta si es necesario.
    Retorna None si la URL no es válida.
    """
    if not url:
        return None
    if url.startswith('http://') or url.startswith('https://'):
        return url
    if url.startswith('/'):
        return request.url_root.rstrip('/') + url
    return None


def redirect_to_stripe_checkout(payment, service, slot):
    """
    Crea una sesión de Stripe Checkout y redirige al usuario.
    """
    import app as M

    if not M.STRIPE_AVAILABLE or not M.stripe:
        flash('El método de pago con tarjeta no está disponible.', 'error')
        return redirect(url_for('services.request_appointment', service_id=service.id))
    
    try:
        # Crear sesión de checkout
        checkout_session = M.stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': f'Cita: {service.name}',
                        'description': f'Abono para cita el {slot.start_datetime.strftime("%d/%m/%Y %H:%M")}'
                    },
                    'unit_amount': int(payment.amount),  # Ya está en centavos
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=url_for('payments_checkout.service_payment_success_callback', payment_id=payment.id, _external=True),
            # Cancel URL: usar return_url guardado si existe (convertir a absoluto), sino usar la página de solicitud
            cancel_url=_make_absolute_url(session.get('appointment_return_url')) or url_for('services.request_appointment', service_id=service.id, _external=True),
            metadata={
                'payment_id': str(payment.id),
                'service_id': str(service.id),
                'slot_id': str(slot.id)
            }
        )
        
        # Guardar referencia de Stripe
        payment.payment_reference = checkout_session.id
        payment.payment_url = checkout_session.url
        M.db.session.commit()
        
        return redirect(checkout_session.url)
    
    except Exception as e:
        M.db.session.rollback()
        flash(f'Error al crear la sesión de pago: {str(e)}', 'error')
        return redirect(url_for('services.request_appointment', service_id=service.id))


def generate_external_payment_url(payment, payment_method):
    """
    Genera URL para pagos externos (Banco General, Yappy).
    """
    # URL base del sistema
    base_url = request.url_root.rstrip('/')
    
    # URL de callback
    callback_url = url_for('payments_checkout.payment_success', payment_id=payment.id, _external=True)
    cancel_url = url_for('services.list', _external=True)
    
    # Generar URL según el método
    if payment_method == 'banco_general':
        # TODO: Integrar con API de Banco General
        # Por ahora, retornar URL de confirmación manual
        return url_for('payments_checkout.payment_status', payment_id=payment.id, _external=True)
    
    elif payment_method == 'yappy':
        # TODO: Integrar con API de Yappy
        # Por ahora, retornar URL de confirmación manual
        return url_for('payments_checkout.payment_status', payment_id=payment.id, _external=True)
    
    return callback_url

@payments_checkout_bp.route('/create-payment-intent', methods=['POST'])
@_email_verified_check_then
def create_payment_intent():
    """Crear Payment Intent o iniciar pago con el método seleccionado"""
    import app as M
    try:
        # Manejar tanto JSON como FormData (para métodos manuales con archivos)
        if request.is_json:
            data = request.get_json()
        else:
            data = request.form.to_dict()
        
        payment_method = data.get('payment_method', 'stripe')
        
        # Manejar archivo de comprobante si existe (métodos manuales)
        receipt_file = None
        receipt_filename = None
        receipt_url = None
        ocr_data = None
        ocr_status = 'pending'
        
        if 'receipt' in request.files:
            file = request.files['receipt']
            if file and file.filename != '' and M.allowed_file(file.filename):
                # Generar nombre único para el archivo
                import secrets
                file_ext = file.filename.rsplit('.', 1)[1].lower()
                unique_filename = f"{current_user.id}_{secrets.token_hex(8)}.{file_ext}"
                file_path = os.path.join(M.UPLOAD_FOLDER, unique_filename)
                file.save(file_path)
                receipt_filename = file.filename
                receipt_url = f"/static/uploads/receipts/{unique_filename}"
                print(f"✅ Comprobante guardado: {receipt_url}")
                
                # Procesar con OCR si está disponible
                try:
                    from ocr_processor import get_ocr_processor
                    ocr_processor = get_ocr_processor()
                    if ocr_processor:
                        print(f"🔄 Procesando documento con OCR...")
                        extracted_data, ocr_error = ocr_processor.extract_payment_data(file_path)
                        if extracted_data:
                            ocr_data = json.dumps(extracted_data)
                            print(f"✅ OCR completado. Datos extraídos: {extracted_data}")
                        elif ocr_error:
                            print(f"⚠️ Error en OCR: {ocr_error}")
                except Exception as e:
                    print(f"⚠️ Error procesando OCR: {e}")
                    import traceback
                    traceback.print_exc()
        
        cart = M.get_or_create_cart(current_user.id)
        
        if cart.get_items_count() == 0:
            return jsonify({'error': 'El carrito está vacío'}), 400
        
        # Usar el total con descuentos aplicados
        discount_breakdown = cart.get_discount_breakdown()
        total_amount = discount_breakdown['final_total']
        
        # Validar método de pago
        if payment_method not in M.PAYMENT_METHODS:
            return jsonify({'error': f'Método de pago no válido: {payment_method}'}), 400
        
        # Obtener procesador de pago
        if not M.PAYMENT_PROCESSORS_AVAILABLE:
            return jsonify({'error': 'Sistema de pagos no disponible'}), 500
        
        # Config de pagos del tenant (sesión / usuario)
        pay_oid = payment_organization_id_for_request()
        payment_config = M.PaymentConfig.get_active_config(organization_id=pay_oid)
        processor = M.get_payment_processor(payment_method, payment_config)
        
        # Crear metadata para el pago
        import json
        metadata = {
            'user_id': current_user.id,
            'cart_id': cart.id,
            'items_count': cart.get_items_count()
        }
        
        # Crear pago con el procesador
        success, payment_data, error_message = processor.create_payment(
            amount=total_amount,
            currency='usd',
            metadata=metadata
        )
        
        if not success:
            return jsonify({'error': error_message or 'Error al crear el pago'}), 400
        
        # Detectar si estamos en modo demo
        is_demo_mode = payment_data.get('demo_mode', False)
        
        # Si es modo demo, también verificar si no hay credenciales configuradas
        if not is_demo_mode:
            if payment_method == 'stripe':
                if payment_config:
                    has_stripe_key = bool(payment_config.get_stripe_secret_key() and 
                                        not payment_config.get_stripe_secret_key().startswith('sk_test_your_'))
                else:
                    has_stripe_key = bool(os.getenv('STRIPE_SECRET_KEY') and 
                                        not os.getenv('STRIPE_SECRET_KEY', '').startswith('sk_test_your_'))
                is_demo_mode = not has_stripe_key
            elif payment_method == 'paypal':
                if payment_config:
                    has_paypal_creds = bool(payment_config.get_paypal_client_id() and payment_config.get_paypal_client_secret())
                else:
                    has_paypal_creds = bool(os.getenv('PAYPAL_CLIENT_ID') and os.getenv('PAYPAL_CLIENT_SECRET'))
                is_demo_mode = not has_paypal_creds
            else:
                # Métodos manuales siempre están en modo demo hasta que se configuren APIs
                is_demo_mode = True
        
        # Validar datos OCR si existen
        ocr_verified = False
        if ocr_data:
            try:
                extracted = json.loads(ocr_data)
                expected_amount = total_amount / 100.0  # Convertir de centavos a dólares
                extracted_amount = extracted.get('amount')
                
                # Verificar si el monto coincide (con tolerancia de 0.01)
                if extracted_amount and abs(extracted_amount - expected_amount) < 0.01:
                    ocr_status = 'verified'
                    ocr_verified = True
                    print(f"✅ Monto verificado: ${extracted_amount} coincide con ${expected_amount}")
                else:
                    ocr_status = 'needs_review'
                    print(f"⚠️ Monto no coincide: OCR=${extracted_amount}, Esperado=${expected_amount}")
            except Exception as e:
                print(f"⚠️ Error validando OCR: {e}")
                ocr_status = 'needs_review'
        
        # Determinar estado inicial del pago
        # Si es método manual con OCR verificado, aprobar automáticamente
        # Si es modo demo sin OCR, aprobar automáticamente
        # Si OCR necesita revisión, dejar en pending
        if ocr_verified:
            initial_status = 'succeeded'
        elif is_demo_mode and not receipt_url:  # Demo sin archivo
            initial_status = 'succeeded'
        else:
            initial_status = 'pending'
        
        # Guardar pago en la base de datos
        payment = M.Payment(
            user_id=current_user.id,
            payment_method=payment_method,
            payment_reference=payment_data.get('payment_reference', ''),
            amount=total_amount,
            currency='usd',
            status=initial_status,
            membership_type='cart',
            payment_url=payment_data.get('payment_url'),
            payment_metadata=json.dumps(metadata),
            receipt_url=receipt_url,
            receipt_filename=receipt_filename,
            ocr_data=ocr_data,
            ocr_status=ocr_status
        )
        
        if initial_status == 'succeeded':
            payment.paid_at = datetime.utcnow()
            if ocr_verified:
                payment.ocr_verified_at = datetime.utcnow()
        
        M.db.session.add(payment)
        M.db.session.commit()
        
        # Registrar creación de pago en historial
        try:
            from history_module import HistoryLogger
            cart_items = []
            for item in cart.items:
                cart_items.append({
                    'product_type': item.product_type,
                    'product_id': item.product_id,
                    'product_name': item.product_name,
                    'quantity': item.quantity,
                    'unit_price': item.unit_price,
                    'total_price': item.unit_price * item.quantity
                })
            
            HistoryLogger.log_user_action(
                user_id=current_user.id,
                action=f"Pago creado - {payment_method.upper()} - ${total_amount/100:.2f}",
                status=initial_status,
                context={"app": "web", "screen": "checkout", "module": "payment"},
                payload={
                    "payment_id": payment.id,
                    "payment_method": payment_method,
                    "amount": total_amount,
                    "currency": "usd",
                    "cart_id": cart.id,
                    "items_count": cart.get_items_count(),
                    "items": cart_items,
                    "discount_breakdown": discount_breakdown,
                    "demo_mode": is_demo_mode,
                    "ocr_status": ocr_status,
                    "ocr_verified": ocr_verified
                },
                result={
                    "payment_id": payment.id,
                    "status": initial_status,
                    "payment_reference": payment.payment_reference
                },
                visibility="both"
            )
        except Exception as e:
            print(f"⚠️ Error registrando creación de pago en historial: {e}")
        
        # Si el pago está aprobado (demo o OCR verificado), procesar el carrito inmediatamente
        if initial_status == 'succeeded':
            try:
                process_cart_after_payment(cart, payment)
                cart.clear()
                M.db.session.commit()
                print(f"✅ Pago en modo demo procesado exitosamente. Payment ID: {payment.id}")
                
                # Enviar webhook a Odoo (no bloquea si falla)
                try:
                    send_payment_to_odoo(payment, current_user, cart)
                except Exception as e:
                    print(f"⚠️ Error enviando pago a Odoo (no crítico): {e}")
            except Exception as e:
                print(f"⚠️ Error procesando carrito en modo demo: {e}")
                import traceback
                traceback.print_exc()
                M.db.session.rollback()
        
        # Si OCR necesita revisión, enviar notificaciones después del commit
        if ocr_status == 'needs_review':
            try:
                M.send_ocr_review_notifications(payment, current_user, json.loads(ocr_data) if ocr_data else None)
            except Exception as e:
                print(f"⚠️ Error enviando notificaciones OCR: {e}")
        
        # Preparar respuesta según el método
        response_data = {
            'payment_id': payment.id,
            'payment_method': payment_method,
            'amount': total_amount,
            'status': initial_status,
            'demo_mode': is_demo_mode,
            'ocr_data': json.loads(ocr_data) if ocr_data else None,
            'ocr_status': ocr_status,
            'ocr_verified': ocr_verified
        }
        
        # Agregar datos específicos según el método
        if payment_method == 'stripe':
            response_data['client_secret'] = payment_data.get('client_secret', 'demo_client_secret')
        elif payment_method == 'paypal':
            response_data['payment_url'] = payment_data.get('payment_url')
            response_data['order_id'] = payment_data.get('payment_reference')
        elif payment_method == 'banco_general':
            response_data['bank_account'] = payment_data.get('bank_account')
            response_data['payment_reference'] = payment_data.get('payment_reference')
            response_data['manual'] = True
        elif payment_method == 'yappy':
            response_data['yappy_info'] = payment_data.get('yappy_info')
            response_data['payment_reference'] = payment_data.get('payment_reference')
            response_data['manual'] = True
        
        return jsonify(response_data)
        
    except Exception as e:
        print(f"Error en create_payment_intent: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# Ruta legacy para compatibilidad (solo Stripe)
@payments_checkout_bp.route('/create-payment-intent-legacy', methods=['POST'])
@_email_verified_check_then
def create_payment_intent_legacy():
    """Crear Payment Intent de Stripe desde el carrito (método legacy)"""
    import app as M
    try:
        cart = M.get_or_create_cart(current_user.id)
        
        if cart.get_items_count() == 0:
            return jsonify({'error': 'El carrito está vacío'}), 400
        
        total_amount = cart.get_total()
        
        # Modo Demo - Simular pago exitoso
        demo_mode = True  # Cambiar a False cuando tengas Stripe configurado
        
        if demo_mode:
            # Simular Payment Intent
            fake_intent_id = f"pi_demo_{current_user.id}_{datetime.utcnow().timestamp()}"
            
            # Guardar en la base de datos
            payment = M.Payment(
                user_id=current_user.id,
                payment_method='stripe',
                payment_reference=fake_intent_id,
                amount=total_amount,
                membership_type='cart',  # Indica que es un pago del carrito
                status='succeeded'  # Simular pago exitoso
            )
            M.db.session.add(payment)
            M.db.session.commit()
            
            # Procesar cada item del carrito
            subscriptions_created = []
            items_processed = 0
            import json
            
            # Crear copia de la lista antes de procesar
            cart_items_list = list(cart.items)
            
            for item in cart_items_list:
                items_processed += 1
                
                if item.product_type == 'membership':
                    metadata = json.loads(item.item_metadata) if item.item_metadata else {}
                    membership_type = metadata.get('membership_type', 'basic')
                    
                    # Crear suscripción
                    end_date = datetime.utcnow() + timedelta(days=365)
                    subscription = M.Subscription(
                        user_id=current_user.id,
                        payment_id=payment.id,
                        membership_type=membership_type,
                        status='active',
                        end_date=end_date
                    )
                    M.db.session.add(subscription)
                    subscriptions_created.append(subscription)
                
                elif item.product_type == 'event':
                    # Registrar al evento (si existe la funcionalidad)
                    metadata = json.loads(item.item_metadata) if item.item_metadata else {}
                    event_id = metadata.get('event_id')
                    if event_id:
                        # Aquí se podría registrar al evento automáticamente
                        pass
                
            
            M.db.session.commit()
            
            # Vaciar el carrito después del pago exitoso
            cart.clear()
            
            return jsonify({
                'client_secret': 'demo_client_secret',
                'payment_id': payment.id,
                'demo_mode': True,
                'items_processed': items_processed
            })
        else:
            # Modo real con Stripe
            # Crear metadata con información del carrito
            import json
            cart_metadata = {
                'user_id': current_user.id,
                'items_count': cart.get_items_count(),
                'items': [item.to_dict() for item in cart.items]
            }
            
            intent = M.stripe.PaymentIntent.create(
                amount=total_amount,
                currency='usd',
                metadata={
                    'user_id': str(current_user.id),
                    'cart_id': str(cart.id),
                    'items': json.dumps(cart_metadata['items'])
                }
            )
            
            # Guardar en la base de datos
            payment = M.Payment(
                user_id=current_user.id,
                payment_method='stripe',
                payment_reference=intent.id,
                amount=total_amount,
                membership_type='cart',
                status='pending'
            )
            M.db.session.add(payment)
            M.db.session.commit()
            
            return jsonify({
                'client_secret': intent.client_secret,
                'payment_id': payment.id,
                'demo_mode': False
            })
        
    except Exception as e:
        print(f"Error en create_payment_intent: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 400
@payments_checkout_bp.route('/payment-success')
@login_required
def payment_success():
    """Página de éxito del pago"""
    import app as M
    payment_id = request.args.get('payment_id')
    if payment_id:
        payment = M.Payment.query.get(payment_id)
        if payment and payment.user_id == current_user.id:
            # Registrar confirmación de pago en historial si cambió de estado
            if payment.status == 'succeeded':
                try:
                    from history_module import HistoryLogger
                    HistoryLogger.log_user_action(
                        user_id=current_user.id,
                        action=f"Pago confirmado - {payment.payment_method.upper()} - ${payment.amount/100:.2f}",
                        status="success",
                        context={"app": "web", "screen": "payment_success", "module": "payment"},
                        payload={
                            "payment_id": payment.id,
                            "payment_method": payment.payment_method,
                            "amount": payment.amount,
                            "payment_reference": payment.payment_reference
                        },
                        result={
                            "payment_id": payment.id,
                            "status": "succeeded",
                            "paid_at": payment.paid_at.isoformat() if payment.paid_at else None
                        },
                        visibility="both"
                    )
                except Exception as e:
                    print(f"⚠️ Error registrando confirmación de pago en historial: {e}")
            
            # Procesar items del carrito si el pago fue exitoso y aún no se procesó
            if payment.status == 'succeeded':
                cart = M.get_or_create_cart(current_user.id)
                
                # Verificar si el carrito ya fue procesado (tiene items)
                # Si el carrito está vacío, significa que ya fue procesado en modo demo
                if cart.get_items_count() > 0:
                    try:
                        process_cart_after_payment(cart, payment)
                        cart.clear()
                        M.db.session.commit()
                        print(f"✅ Carrito procesado en payment_success para Payment ID: {payment.id}")
                    except Exception as e:
                        print(f"⚠️ Error procesando carrito en payment_success: {e}")
                        import traceback
                        traceback.print_exc()
                        M.db.session.rollback()
                else:
                    print(f"ℹ️ Carrito ya procesado previamente para Payment ID: {payment.id}")
                
                # Enviar webhook a Odoo (no bloquea si falla)
                try:
                    send_payment_to_odoo(payment, current_user, cart)
                except Exception as e:
                    print(f"⚠️ Error enviando pago a Odoo (no crítico): {e}")
            
            return render_template('payment_success.html', payment=payment)
    
    flash('Información de pago no encontrada.', 'error')
    return redirect(url_for('membership'))

@payments_checkout_bp.route('/payment/paypal/return', methods=['GET'])
@login_required
def paypal_return():
    """Callback de retorno de PayPal después del pago"""
    import app as M
    token = request.args.get('token')
    payment_id = request.args.get('payment_id')
    
    if not token or not payment_id:
        flash('Error en el proceso de pago de PayPal.', 'error')
        return redirect(url_for('payments.checkout'))
    
    payment = M.Payment.query.get(payment_id)
    if not payment or payment.user_id != current_user.id:
        flash('Pago no encontrado.', 'error')
        return redirect(url_for('payments.checkout'))
    
    # Capturar el pago de PayPal
    if M.PAYMENT_PROCESSORS_AVAILABLE:
        try:
            pay_oid = payment_organization_id_for_request()
            payment_config = M.PaymentConfig.get_active_config(organization_id=pay_oid)
            processor = M.get_payment_processor('paypal', payment_config)
            # PayPal ya captura automáticamente, solo verificamos
            success, status, payment_data = processor.verify_payment(token)
            
            if success and status == 'succeeded':
                payment.status = 'succeeded'
                payment.paid_at = datetime.utcnow()
                M.db.session.commit()
                
                # Registrar confirmación de pago en historial
                try:
                    from history_module import HistoryLogger
                    HistoryLogger.log_user_action(
                        user_id=current_user.id,
                        action=f"Pago confirmado - PayPal - ${payment.amount/100:.2f}",
                        status="success",
                        context={"app": "web", "screen": "paypal_return", "module": "payment"},
                        payload={
                            "payment_id": payment.id,
                            "payment_method": "paypal",
                            "amount": payment.amount,
                            "payment_reference": payment.payment_reference,
                            "token": token
                        },
                        result={
                            "payment_id": payment.id,
                            "status": "succeeded",
                            "paid_at": payment.paid_at.isoformat() if payment.paid_at else None
                        },
                        visibility="both"
                    )
                except Exception as e:
                    print(f"⚠️ Error registrando confirmación de pago PayPal en historial: {e}")
                
                # Procesar carrito
                cart = M.get_or_create_cart(current_user.id)
                process_cart_after_payment(cart, payment)
                cart.clear()
                M.db.session.commit()
                
                # Enviar webhook a Odoo (no bloquea si falla)
                try:
                    send_payment_to_odoo(payment, current_user, cart)
                except Exception as e:
                    print(f"⚠️ Error enviando pago a Odoo (no crítico): {e}")
                
                return redirect(url_for('payments_checkout.payment_success', payment_id=payment.id))
            else:
                payment.status = 'failed'
                M.db.session.commit()
                flash('El pago no se pudo completar.', 'error')
        except Exception as e:
            print(f"Error procesando retorno de PayPal: {e}")
            flash('Error procesando el pago.', 'error')
    
    return redirect(url_for('payments.checkout'))

@payments_checkout_bp.route('/payment/paypal/cancel', methods=['GET'])
@login_required
def paypal_cancel():
    """Callback de cancelación de PayPal"""
    import app as M
    payment_id = request.args.get('payment_id')
    
    if payment_id:
        payment = M.Payment.query.get(payment_id)
        if payment and payment.user_id == current_user.id:
            payment.status = 'cancelled'
            M.db.session.commit()
    
    flash('Pago cancelado.', 'warning')
    return redirect(url_for('payments.checkout'))


@payments_checkout_bp.route('/payment-cancel')
@login_required
def payment_cancel():
    """Página de cancelación del pago"""
    import app as M
    flash('El pago fue cancelado. Puedes intentar nuevamente.', 'warning')
    return redirect(url_for('membership'))


def _stripe_construct_event_multi_tenant(raw_payload, sig_header):
    """
    Verifica firma Stripe probando STRIPE_WEBHOOK_SECRET y el secret del tenant
    (según Payment del payment_intent), sin confiar en el JSON antes de validar.
    """
    import json

    import app as M

    if not M.STRIPE_AVAILABLE or not M.stripe:
        return None, 'stripe_unavailable'

    secrets_to_try = []
    env_wh = (os.getenv('STRIPE_WEBHOOK_SECRET') or '').strip()
    if env_wh:
        secrets_to_try.append(env_wh)

    try:
        parsed = json.loads(raw_payload.decode('utf-8'))
    except Exception:
        return None, 'invalid_json'

    if parsed.get('type') == 'payment_intent.succeeded':
        obj = (parsed.get('data') or {}).get('object') or {}
        pi_id = obj.get('id')
        if pi_id:
            payment = M.Payment.query.filter_by(payment_reference=pi_id).first()
            if payment:
                cfg = M.PaymentConfig.get_active_config_for_user_id(payment.user_id)
                if cfg:
                    wh = (cfg.get_stripe_webhook_secret() or '').strip()
                    if wh and wh not in secrets_to_try:
                        secrets_to_try.append(wh)

    if not secrets_to_try:
        secrets_to_try.append((os.getenv('STRIPE_WEBHOOK_SECRET') or 'whsec_test').strip() or 'whsec_test')

    last_err = None
    for wh in secrets_to_try:
        if not wh:
            continue
        try:
            return M.stripe.Webhook.construct_event(raw_payload, sig_header, wh), None
        except ValueError as e:
            return None, e
        except M.stripe.error.SignatureVerificationError as e:
            last_err = e
            continue
    return None, last_err


@payments_checkout_bp.route('/stripe-webhook', methods=['POST'])
def stripe_webhook():
    """Webhook de Stripe para confirmar pagos (firma: env y/o secret por tenant)."""
    import app as M

    payload = request.get_data()
    sig_header = request.headers.get('Stripe-Signature')

    event, err = _stripe_construct_event_multi_tenant(payload, sig_header)
    if event is None:
        if err == 'stripe_unavailable':
            return 'Stripe unavailable', 503
        if isinstance(err, ValueError):
            return 'Invalid payload', 400
        return 'Invalid signature', 400

    # Manejar el evento
    if event['type'] == 'payment_intent.succeeded':
        payment_intent = event['data']['object']
        handle_successful_payment(payment_intent, event_type=event.get('type'))

    return jsonify({'status': 'success'})


def handle_successful_payment(payment_intent, event_type=None):
    """Manejar pago exitoso"""
    import app as M
    try:
        # Buscar el pago en la base de datos
        payment = M.Payment.query.filter_by(
            payment_reference=payment_intent['id']
        ).first()
        
        if payment:
            # Actualizar estado del pago
            payment.status = 'succeeded'
            payment.paid_at = datetime.utcnow()
            M.db.session.commit()
            
            # Registrar confirmación de pago vía webhook en historial
            try:
                from history_module import HistoryLogger
                # Registrar como acción del usuario (el pago es del usuario)
                HistoryLogger.log_user_action(
                    user_id=payment.user_id,
                    action=f"Pago confirmado - Stripe Webhook - ${payment.amount/100:.2f}",
                    status="success",
                    context={"app": "webhook", "screen": "payment", "module": "stripe"},
                    payload={
                        "payment_id": payment.id,
                        "payment_method": "stripe",
                        "amount": payment.amount,
                        "event_type": event_type,
                    },
                    result={
                        "payment_id": payment.id,
                        "status": "succeeded",
                        "paid_at": payment.paid_at.isoformat() if payment.paid_at else None
                    },
                    visibility="both"
                )
            except Exception as e:
                print(f"⚠️ Error registrando confirmación de pago Stripe en historial: {e}")
            
            # Crear suscripción
            end_date = datetime.utcnow() + timedelta(days=365)  # 1 año
            subscription = M.Subscription(
                user_id=payment.user_id,
                payment_id=payment.id,
                membership_type=payment.membership_type,
                status='active',
                end_date=end_date
            )
            M.db.session.add(subscription)
            M.db.session.commit()
            
            # Enviar notificación y email de confirmación
            M.NotificationEngine.notify_membership_payment(payment.user, payment, subscription)
            
            # Enviar webhook a Odoo (no bloquea si falla)
            try:
                cart = M.get_or_create_cart(payment.user_id)
                send_payment_to_odoo(payment, payment.user, cart)
            except Exception as e:
                print(f"⚠️ Error enviando pago a Odoo (no crítico): {e}")
            
    except Exception as e:
        print(f"Error handling payment: {e}")


@payments_checkout_bp.route('/payments/status/<int:payment_id>')
@login_required
def payment_status(payment_id):
    """Estado de un pago (p. ej. cita / servicio); antes referenciado sin ruta registrada."""
    import app as M

    payment = M.Payment.query.get_or_404(payment_id)
    if payment.user_id != current_user.id:
        flash('No tienes permiso para ver este pago.', 'error')
        return redirect(url_for('dashboard'))

    service = None
    metadata = {}
    appointment = None
    if payment.payment_metadata:
        try:
            metadata = json.loads(payment.payment_metadata) or {}
        except Exception:
            metadata = {}
    if payment.membership_type == 'service_appointment' and metadata.get('service_id'):
        _pay_co = M.get_current_organization_id()
        if _pay_co is not None:
            service = M.Service.query.filter_by(
                id=metadata.get('service_id'), organization_id=int(_pay_co)
            ).first()
        else:
            service = None
    appointment = M.Appointment.query.filter_by(payment_id=payment.id).first()

    return render_template(
        'payments/payment_status.html',
        payment=payment,
        service=service,
        metadata=metadata,
        appointment=appointment,
    )


@payments_checkout_bp.route('/payments/history')
@login_required
def payments_history():
    """Historial de pagos del usuario con información completa de compras"""
    import app as M

    payments = M.Payment.query.filter_by(user_id=current_user.id).order_by(
        M.Payment.created_at.desc()
    ).all()

    status_counts = Counter(payment.status for payment in payments)

    current_time = datetime.utcnow()
    long_pending_payments = []

    payments_with_details = []
    for payment in payments:
        payment_data = {
            'payment': payment,
            'subscriptions': [],
            'event_registrations': [],
            'purchased_items': [],
            'discount_applications': [],
            'history_transactions': []
        }

        subscriptions = M.Subscription.query.filter_by(payment_id=payment.id).all()
        payment_data['subscriptions'] = subscriptions

        event_registrations = []
        if payment.payment_reference:
            event_registrations = M.EventRegistration.query.filter(
                M.EventRegistration.payment_reference == payment.payment_reference,
                M.EventRegistration.user_id == current_user.id
            ).all()

        if not event_registrations:
            event_registrations = M.EventRegistration.query.filter(
                M.EventRegistration.payment_reference == str(payment.id),
                M.EventRegistration.user_id == current_user.id
            ).all()

        if not event_registrations and payment.paid_at:
            time_window_start = payment.paid_at - timedelta(minutes=10)
            time_window_end = payment.paid_at + timedelta(minutes=10)
            event_registrations = M.EventRegistration.query.filter(
                M.EventRegistration.user_id == current_user.id,
                M.EventRegistration.payment_date >= time_window_start,
                M.EventRegistration.payment_date <= time_window_end,
                M.EventRegistration.payment_status == 'paid'
            ).all()

        history_transactions = M.HistoryTransaction.query.filter(
            M.HistoryTransaction.owner_user_id == current_user.id
        ).filter(
            M.HistoryTransaction.payload.contains(f'"payment_id": {payment.id}')
        ).order_by(M.HistoryTransaction.timestamp.desc()).limit(5).all()

        if not event_registrations:
            for transaction in history_transactions:
                if 'Compra realizada' in transaction.action and transaction.result:
                    try:
                        result = json.loads(transaction.result)
                        if 'events' in result and result['events']:
                            event_ids = [e.get('event_id') for e in result['events'] if e.get('event_id')]
                            if event_ids:
                                found_events = M.EventRegistration.query.filter(
                                    M.EventRegistration.event_id.in_(event_ids),
                                    M.EventRegistration.user_id == current_user.id
                                ).all()
                                if found_events:
                                    event_registrations = found_events
                                    break
                    except Exception:
                        pass

        payment_data['event_registrations'] = event_registrations

        discount_applications = M.DiscountApplication.query.filter_by(payment_id=payment.id).all()
        payment_data['discount_applications'] = discount_applications

        for transaction in history_transactions:
            try:
                if transaction.payload:
                    payload = json.loads(transaction.payload)
                    if 'items' in payload:
                        payment_data['purchased_items'] = payload['items']
                    if 'discount_breakdown' in payload:
                        payment_data['discount_breakdown'] = payload['discount_breakdown']
            except Exception:
                pass

            if 'Compra realizada' in transaction.action:
                try:
                    if transaction.result:
                        result = json.loads(transaction.result)
                        if 'subscriptions' in result:
                            payment_data['subscriptions_info'] = result['subscriptions']
                        if 'events' in result:
                            event_ids = [e.get('event_id') for e in result['events']]
                            if event_ids:
                                event_registrations = M.EventRegistration.query.filter(
                                    M.EventRegistration.event_id.in_(event_ids),
                                    M.EventRegistration.user_id == current_user.id
                                ).all()
                                payment_data['event_registrations'] = event_registrations
                except Exception:
                    pass

        if not payment_data['purchased_items'] and payment.payment_metadata:
            try:
                metadata = json.loads(payment.payment_metadata)
                if 'items' in metadata:
                    payment_data['purchased_items'] = metadata['items']
            except Exception:
                pass

        payment_data['history_transactions'] = [
            {
                'id': t.id,
                'action': t.action,
                'timestamp': t.timestamp,
                'status': t.status
            }
            for t in history_transactions
        ]

        payments_with_details.append(payment_data)

        if payment.status in ['pending', 'awaiting_confirmation'] and payment.created_at:
            time_elapsed = (current_time - payment.created_at).total_seconds() / 60
            if time_elapsed > 5:
                hours = int(time_elapsed / 60)
                minutes = int(time_elapsed % 60)
                if hours > 0:
                    time_elapsed_str = f"{hours}h {minutes}m"
                else:
                    time_elapsed_str = f"{minutes}m"

                long_pending_payments.append({
                    'payment': payment,
                    'time_elapsed': time_elapsed,
                    'time_elapsed_str': time_elapsed_str
                })

    return render_template(
        'payments_history.html',
        payments=payments_with_details,
        status_counts=status_counts,
        long_pending_payments=long_pending_payments,
        current_time=current_time
    )


@payments_checkout_bp.route('/api/payments/<int:payment_id>/success')
@login_required
def service_payment_success_callback(payment_id):
    """
    Callback cuando un pago de servicio es exitoso. Crea el appointment.
    """
    import app as M

    payment = M.Payment.query.get_or_404(payment_id)

    if payment.user_id != current_user.id:
        flash('No tienes permiso para acceder a este pago.', 'error')
        return redirect(url_for('services.list'))

    if payment.membership_type != 'service_appointment':
        return redirect(url_for('payments_checkout.payment_success', payment_id=payment_id))

    if payment.status not in ['succeeded', 'awaiting_confirmation']:
        flash('El pago no se ha completado aún.', 'warning')
        return redirect(url_for('payments_checkout.payment_status', payment_id=payment_id))

    existing_appointment = M.Appointment.query.filter_by(payment_id=payment_id).first()
    if existing_appointment:
        flash('La cita ya fue creada anteriormente.', 'info')
        return redirect(url_for('appointments.appointments_home'))

    try:
        metadata = json.loads(payment.payment_metadata)
    except Exception:
        flash('Error al procesar los datos del pago.', 'error')
        return redirect(url_for('services.list'))

    service_id = metadata.get('service_id')
    slot_id = metadata.get('slot_id')
    case_description = metadata.get('case_description')
    final_price = metadata.get('final_price', 0.0)
    deposit_amount = metadata.get('deposit_amount', 0.0)

    _pay_co = M.get_current_organization_id()
    if _pay_co is None:
        flash('No hay contexto de organización.', 'error')
        return redirect(url_for('services.list'))
    service = M.Service.query.filter_by(id=service_id, organization_id=int(_pay_co)).first()
    slot = M.AppointmentSlot.query.get(slot_id)

    if not service or not slot:
        flash('Error: El servicio o horario seleccionado ya no está disponible.', 'error')
        return redirect(url_for('services.list'))

    if not slot.is_available or slot.remaining_seats() <= 0:
        flash('El horario seleccionado ya no está disponible. Contacta a soporte.', 'error')
        return redirect(url_for('services.list'))

    if deposit_amount >= final_price:
        appt_payment_status = 'paid'
    else:
        appt_payment_status = 'partial'

    membership = current_user.get_active_membership()
    membership_type = membership.membership_type if membership else None

    pricing = service.pricing_for_membership(membership_type)

    appointment = M.Appointment(
        appointment_type_id=service.appointment_type_id,
        advisor_id=slot.advisor_id,
        slot_id=slot.id,
        service_id=service.id,
        payment_id=payment.id,
        user_id=current_user.id,
        membership_type=membership_type,
        start_datetime=slot.start_datetime,
        end_datetime=slot.end_datetime,
        status='pending',
        base_price=pricing['base_price'],
        final_price=final_price,
        discount_applied=pricing['base_price'] - pricing['final_price'],
        payment_status=appt_payment_status,
        payment_method=payment.payment_method,
        user_notes=case_description
    )

    slot.reserved_seats = (slot.reserved_seats or 0) + 1
    if slot.remaining_seats() == 0:
        slot.is_available = False

    M.db.session.add(appointment)
    M.db.session.commit()

    M.ActivityLog.log_activity(
        current_user.id,
        'service_appointment_created',
        'appointment',
        appointment.id,
        f'Cita creada para servicio {service.name} - Referencia: {appointment.reference}',
        request
    )

    flash(f'¡Cita agendada exitosamente! Referencia: {appointment.reference}', 'success')

    return_url = session.pop('appointment_return_url', None)
    if return_url and (return_url.startswith('/') or return_url.startswith(request.url_root)):
        return redirect(return_url)

    return redirect(url_for('appointments.appointments_home'))
