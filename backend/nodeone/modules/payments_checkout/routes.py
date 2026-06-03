"""Checkout, callbacks de pago y webhook Stripe."""

import json
import os
from collections import Counter
from datetime import datetime, timedelta

from flask import Blueprint, abort, flash, jsonify, redirect, render_template, request, send_file, send_from_directory, session, url_for
from flask_login import current_user, login_required
from functools import wraps

from nodeone.services.payment_post_process import process_cart_after_payment, send_payment_to_odoo
from utils.organization import resolve_current_organization

payments_checkout_bp = Blueprint('payments_checkout', __name__)


def _checkout_no_demo_auto_success():
    """
    True = en modo demo NO marcar el pago como succeeded al crear el intent (queda ``pending``:
    no se vacía el carrito ni se confirma solo).

    Por defecto True para poder probar sin tocar variables.

    Opt-in al comportamiento legacy (auto-éxito demo al crear intent):
        NODEONE_CHECKOUT_DEMO_AUTO_SUCCESS=1   (o true/yes/on)

    Compatibilidad con el nombre anterior:
        NODEONE_CHECKOUT_NO_DEMO_AUTO_SUCCESS=0|false|no|off  → sin hold (auto succeeded en demo)
        NODEONE_CHECKOUT_NO_DEMO_AUTO_SUCCESS=1|true|yes     → forzar hold
    """
    demo_auto = (os.environ.get('NODEONE_CHECKOUT_DEMO_AUTO_SUCCESS') or '').strip().lower() in (
        '1',
        'true',
        'yes',
        'on',
    )
    if demo_auto:
        return False
    no_demo = (os.environ.get('NODEONE_CHECKOUT_NO_DEMO_AUTO_SUCCESS') or '').strip().lower()
    if no_demo in ('0', 'false', 'no', 'off'):
        return False
    if no_demo in ('1', 'true', 'yes', 'on'):
        return True
    return True


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


def _create_yappy_manual_cart_payment(M, cart, total_amount, discount_breakdown, payment_config):
    """
    Crea un Payment en pending_receipt (sin comprobante); sin vaciar carrito.
    La activación ocurre solo tras validación admin (estado paid).
    """
    from flask import url_for

    from nodeone.services.yappy_manual import (
        append_yappy_manual_audit,
        effective_yappy_display_name,
        effective_yappy_phone_or_identifier,
    )

    from nodeone.services import organization_payment_methods as opm

    oid_check = int(resolve_current_organization())
    if not opm.is_method_enabled(oid_check, "yappy_manual"):
        return jsonify({"error": "Yappy manual no está activado para esta organización."}), 400
    if not payment_config:
        return jsonify({"error": "Configuración de pagos no disponible."}), 400
    has_qr = bool((getattr(payment_config, "yappy_qr_image_path", None) or "").strip())
    has_dir = bool((getattr(payment_config, "yappy_directory_name", None) or "").strip())
    has_display = bool(effective_yappy_display_name(payment_config))
    has_phone = bool(effective_yappy_phone_or_identifier(payment_config))
    if not has_qr and not has_dir and not has_display and not has_phone:
        return jsonify(
            {
                "error": "Active «Yappy manual» en Administración → Pagos e indique al menos el nombre del comercio o el identificador/teléfono en Yappy."
            }
        ), 400

    oid = int(resolve_current_organization())

    metadata = {
        "user_id": current_user.id,
        "cart_id": cart.id,
        "items_count": cart.get_items_count(),
        "yappy_manual": True,
        "integration": "manual_receipt",
        "organization_id": oid,
    }
    payment = M.Payment(
        user_id=current_user.id,
        organization_id=oid,
        payment_method="yappy_manual",
        payment_reference="PENDING",
        amount=total_amount,
        currency="usd",
        status="pending_receipt",
        membership_type="cart",
        payment_url=None,
        payment_metadata=json.dumps(metadata),
        receipt_url=None,
        receipt_filename=None,
        ocr_data=None,
        ocr_status="pending",
    )
    M.db.session.add(payment)
    M.db.session.flush()
    payment.payment_reference = f"ORD-{payment.id}"
    append_yappy_manual_audit(
        payment,
        {
            "event": "order_created",
            "expected_amount_cents": total_amount,
            "reference": payment.payment_reference,
            "cart_id": cart.id,
        },
    )
    M.db.session.commit()

    try:
        from history_module import HistoryLogger

        HistoryLogger.log_user_action(
            user_id=current_user.id,
            action=f"Pago por Yappy creado — {payment.payment_reference} — USD {total_amount / 100:.2f}",
            status="pending_receipt",
            context={"app": "web", "screen": "checkout", "module": "payment"},
            payload={
                "payment_id": payment.id,
                "payment_method": "yappy_manual",
                "amount": total_amount,
                "cart_id": cart.id,
                "discount_breakdown": discount_breakdown,
            },
            result={"payment_id": payment.id, "reference": payment.payment_reference},
            visibility="both",
        )
    except Exception as e:
        print(f"⚠️ historial yappy_manual: {e}")

    redirect_url = url_for("payments_checkout.payment_yappy_manual_instructions", payment_id=payment.id)
    return jsonify(
        {
            "payment_id": payment.id,
            "payment_method": "yappy_manual",
            "amount": total_amount,
            "status": "pending_receipt",
            "payment_reference": payment.payment_reference,
            "redirect_url": redirect_url,
            "yappy_manual": True,
        }
    )


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
        
        payment_method = data.get('payment_method', 'paypal')
        # Bloquear solo Yappy por API; `yappy_manual` es el flujo independiente por comprobante.
        if payment_method == 'yappy':
            return jsonify({'error': 'El método Yappy con API no está disponible. Use Yappy manual.'}), 400
        # Stripe deshabilitado temporalmente (reactivar con PAYMENT_METHODS y checkout).
        # if payment_method == 'stripe':
        #     return jsonify({'error': 'El método Stripe no está disponible temporalmente.'}), 400

        # Manejar archivo de comprobante si existe (métodos manuales)
        receipt_file = None
        receipt_filename = None
        receipt_url = None
        ocr_data = None
        ocr_status = 'pending'
        
        if payment_method != 'yappy_manual' and 'receipt' in request.files:
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
        
        pay_oid = int(resolve_current_organization())
        payment_config = M.PaymentConfig.get_active_config(organization_id=pay_oid)

        from nodeone.services import organization_payment_methods as opm

        if not opm.is_known_method_key(payment_method):
            return jsonify({'error': f'Método de pago no válido: {payment_method}'}), 400

        if not opm.is_method_enabled(pay_oid, payment_method):
            return jsonify({'error': 'Método de pago no habilitado para esta organización.'}), 400

        if payment_method == 'yappy_manual':
            return _create_yappy_manual_cart_payment(M, cart, total_amount, discount_breakdown, payment_config)

        # Obtener procesador de pago (métodos con integración)
        if not M.PAYMENT_PROCESSORS_AVAILABLE:
            return jsonify({'error': 'Sistema de pagos no disponible'}), 500

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

        if payment_method == 'wire_international' and payment_data.get('bank_account'):
            metadata['intl_wire'] = payment_data.get('bank_account')
        if payment_method == 'banco_general' and payment_data.get('bank_account'):
            metadata['banco_general_transfer'] = payment_data.get('bank_account')
        
        # Detectar si estamos en modo demo
        is_demo_mode = payment_data.get('demo_mode', False)
        
        # Si es modo demo, también verificar si no hay credenciales configuradas
        if not is_demo_mode:
            # if payment_method == 'stripe':
            #     if payment_config:
            #         has_stripe_key = bool(payment_config.get_stripe_secret_key() and
            #                             not payment_config.get_stripe_secret_key().startswith('sk_test_your_'))
            #     else:
            #         has_stripe_key = bool(os.getenv('STRIPE_SECRET_KEY') and
            #                             not os.getenv('STRIPE_SECRET_KEY', '').startswith('sk_test_your_'))
            #     is_demo_mode = not has_stripe_key
            if payment_method == 'paypal':
                if payment_config:
                    has_paypal_creds = bool(payment_config.get_paypal_client_id() and payment_config.get_paypal_client_secret())
                else:
                    has_paypal_creds = bool(os.getenv('PAYPAL_CLIENT_ID') and os.getenv('PAYPAL_CLIENT_SECRET'))
                is_demo_mode = not has_paypal_creds
            else:
                # Métodos manuales siempre están en modo demo hasta que se configuren APIs
                is_demo_mode = True

        if payment_method == 'wire_international':
            is_demo_mode = False
        
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
        elif payment_method == 'wire_international':
            initial_status = 'pending'
        elif is_demo_mode and not receipt_url:
            # Demo sin comprobante: por defecto auto-aprobado; con NODEONE_CHECKOUT_NO_DEMO_AUTO_SUCCESS queda pending para QA.
            initial_status = 'pending' if _checkout_no_demo_auto_success() else 'succeeded'
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
            'demo_hold_for_ui': bool(is_demo_mode and initial_status == 'pending' and _checkout_no_demo_auto_success()),
            'ocr_data': json.loads(ocr_data) if ocr_data else None,
            'ocr_status': ocr_status,
            'ocr_verified': ocr_verified
        }
        
        # Agregar datos específicos según el método
        # if payment_method == 'stripe':
        #     response_data['client_secret'] = payment_data.get('client_secret', 'demo_client_secret')
        if payment_method == 'paypal':
            response_data['payment_url'] = payment_data.get('payment_url')
            response_data['order_id'] = payment_data.get('payment_reference')
        elif payment_method == 'banco_general':
            response_data['bank_account'] = payment_data.get('bank_account')
            response_data['payment_reference'] = payment_data.get('payment_reference')
            response_data['manual'] = True
        elif payment_method == 'wire_international':
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
# @payments_checkout_bp.route('/create-payment-intent-legacy', methods=['POST'])
# @_email_verified_check_then
# def create_payment_intent_legacy():
#     """Crear Payment Intent de Stripe desde el carrito (método legacy)"""
#     import app as M
#     try:
#         cart = M.get_or_create_cart(current_user.id)
        
#         if cart.get_items_count() == 0:
#             return jsonify({'error': 'El carrito está vacío'}), 400
        
#         total_amount = cart.get_total()
        
#         # Modo Demo - Simular pago exitoso (salvo pruebas con NODEONE_CHECKOUT_NO_DEMO_AUTO_SUCCESS)
#         demo_mode = True  # Cambiar a False cuando tengas Stripe configurado

#         if demo_mode and _checkout_no_demo_auto_success():
#             fake_intent_id = f"pi_demo_{current_user.id}_{datetime.utcnow().timestamp()}"
#             payment = M.Payment(
#                 user_id=current_user.id,
#                 payment_method='stripe',
#                 payment_reference=fake_intent_id,
#                 amount=total_amount,
#                 membership_type='cart',
#                 status='pending',
#             )
#             M.db.session.add(payment)
#             M.db.session.commit()
#             return jsonify(
#                 {
#                     'client_secret': 'demo_client_secret',
#                     'payment_id': payment.id,
#                     'demo_mode': True,
#                     'status': 'pending',
#                 }
#             )

#         if demo_mode:
#             # Simular Payment Intent
#             fake_intent_id = f"pi_demo_{current_user.id}_{datetime.utcnow().timestamp()}"
            
#             # Guardar en la base de datos
#             payment = M.Payment(
#                 user_id=current_user.id,
#                 payment_method='stripe',
#                 payment_reference=fake_intent_id,
#                 amount=total_amount,
#                 membership_type='cart',  # Indica que es un pago del carrito
#                 status='succeeded'  # Simular pago exitoso
#             )
#             M.db.session.add(payment)
#             M.db.session.commit()
            
#             # Procesar cada item del carrito
#             subscriptions_created = []
#             items_processed = 0
#             import json
            
#             # Crear copia de la lista antes de procesar
#             cart_items_list = list(cart.items)
            
#             for item in cart_items_list:
#                 items_processed += 1
                
#                 if item.product_type == 'membership':
#                     metadata = json.loads(item.item_metadata) if item.item_metadata else {}
#                     membership_type = metadata.get('membership_type', 'basic')
                    
#                     # Crear suscripción
#                     end_date = datetime.utcnow() + timedelta(days=365)
#                     subscription = M.Subscription(
#                         user_id=current_user.id,
#                         payment_id=payment.id,
#                         membership_type=membership_type,
#                         status='active',
#                         end_date=end_date
#                     )
#                     M.db.session.add(subscription)
#                     subscriptions_created.append(subscription)
                
#                 elif item.product_type == 'event':
#                     # Registrar al evento (si existe la funcionalidad)
#                     metadata = json.loads(item.item_metadata) if item.item_metadata else {}
#                     event_id = metadata.get('event_id')
#                     if event_id:
#                         # Aquí se podría registrar al evento automáticamente
#                         pass
                
            
#             M.db.session.commit()
            
#             # Vaciar el carrito después del pago exitoso
#             cart.clear()
            
#             return jsonify({
#                 'client_secret': 'demo_client_secret',
#                 'payment_id': payment.id,
#                 'demo_mode': True,
#                 'items_processed': items_processed
#             })
#         else:
#             # Modo real con Stripe
#             # Crear metadata con información del carrito
#             import json
#             cart_metadata = {
#                 'user_id': current_user.id,
#                 'items_count': cart.get_items_count(),
#                 'items': [item.to_dict() for item in cart.items]
#             }
            
#             intent = M.stripe.PaymentIntent.create(
#                 amount=total_amount,
#                 currency='usd',
#                 metadata={
#                     'user_id': str(current_user.id),
#                     'cart_id': str(cart.id),
#                     'items': json.dumps(cart_metadata['items'])
#                 }
#             )
            
#             # Guardar en la base de datos
#             payment = M.Payment(
#                 user_id=current_user.id,
#                 payment_method='stripe',
#                 payment_reference=intent.id,
#                 amount=total_amount,
#                 membership_type='cart',
#                 status='pending'
#             )
#             M.db.session.add(payment)
#             M.db.session.commit()
            
#             return jsonify({
#                 'client_secret': intent.client_secret,
#                 'payment_id': payment.id,
#                 'demo_mode': False
#             })
        
#     except Exception as e:
#         print(f"Error en create_payment_intent: {e}")
#         import traceback
#         traceback.print_exc()
#         return jsonify({'error': str(e)}), 400
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
            _confirmed = payment.status == 'succeeded' or (
                payment.payment_method == 'yappy_manual' and payment.status == 'paid'
            )
            if _confirmed:
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
                            "status": payment.status,
                            "paid_at": payment.paid_at.isoformat() if payment.paid_at else None
                        },
                        visibility="both"
                    )
                except Exception as e:
                    print(f"⚠️ Error registrando confirmación de pago en historial: {e}")

            # succeeded (integraciones) o yappy_manual en paid: activar compra si el carrito sigue con ítems
            _fulfill = payment.status == 'succeeded' or (
                payment.payment_method == 'yappy_manual' and payment.status == 'paid'
            )
            if _fulfill:
                cart = M.get_or_create_cart(current_user.id)
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
                try:
                    send_payment_to_odoo(payment, current_user, cart)
                except Exception as e:
                    print(f"⚠️ Error enviando pago a Odoo (no crítico): {e}")

            pcfg = M.PaymentConfig.get_active_config_for_user_id(payment.user_id)
            intl_wire = None
            banco_general_transfer = None
            if payment.payment_metadata:
                try:
                    meta = json.loads(payment.payment_metadata)
                    intl_wire = meta.get('intl_wire')
                    banco_general_transfer = meta.get('banco_general_transfer')
                except Exception:
                    intl_wire = None
                    banco_general_transfer = None
            from nodeone.services.manual_payment_flow import (
                is_manual_validation_method,
                method_requires_receipt,
            )
            from nodeone.services.yappy_manual_status import (
                is_pending_admin_review,
                is_pending_receipt,
                yappy_status_label,
            )

            oid_pay = getattr(payment, 'organization_id', None) or int(resolve_current_organization())
            mv = is_manual_validation_method(payment.payment_method)
            return render_template(
                'payment_success.html',
                payment=payment,
                payment_config=pcfg,
                intl_wire=intl_wire,
                banco_general_transfer=banco_general_transfer,
                manual_validation_payment=mv,
                manual_can_upload_receipt=mv
                and (is_pending_receipt(payment.status) or (payment.status or '').strip() == 'rejected'),
                manual_pending_review=mv and is_pending_admin_review(payment.status),
                manual_receipt_requires=method_requires_receipt(int(oid_pay), payment.payment_method)
                if mv
                else False,
                manual_status_label=yappy_status_label(payment.status) if mv else None,
            )
    
    flash('Información de pago no encontrada.', 'error')
    return redirect(url_for('membership'))


def _yappy_manual_submit_receipt_core(payment_id: int):
    """Lógica compartida: subir comprobante Yappy manual → pending_admin_review."""
    import app as M

    from flask import current_app
    from nodeone.services.yappy_manual import (
        YAPPY_MANUAL_EMAIL_FAILURE_USER_MESSAGE,
        append_yappy_manual_audit,
        effective_yappy_instructions_html,
        notify_admin_new_receipt,
        notify_client_receipt_received,
    )
    from nodeone.services.yappy_manual_status import is_pending_receipt
    from nodeone.services.yappy_receipt_storage import save_yappy_receipt_file

    payment = M.Payment.query.get_or_404(payment_id)
    if payment.user_id != current_user.id:
        return jsonify({'success': False, 'error': 'No autorizado'}), 403
    if payment.payment_method != 'yappy_manual':
        return jsonify({'success': False, 'error': 'No es un pago Yappy manual'}), 400

    cfg = M.PaymentConfig.get_active_config_for_user_id(payment.user_id) if payment.user_id else None
    requires = True if not cfg else bool(getattr(cfg, 'yappy_requires_receipt', True))

    st = (payment.status or '').strip()
    allow_resubmit = st == 'rejected'
    if not is_pending_receipt(st) and not allow_resubmit:
        return jsonify({'success': False, 'error': 'Este pago ya no admite comprobante en este paso.'}), 400

    user_ref = (request.form.get('user_reference') or request.form.get('payment_user_reference') or '').strip()[:500]
    if user_ref:
        payment.payment_user_reference = user_ref

    file = request.files.get('receipt')
    if requires:
        if not file or not file.filename:
            return jsonify({'success': False, 'error': 'Debes adjuntar un comprobante (JPG, PNG, WEBP o PDF, máx. 5 MB).'}), 400
    elif not file or not file.filename:
        payment.status = 'pending_admin_review'
        payment.ocr_status = 'needs_review'
        payment.receipt_uploaded_at = datetime.utcnow()
        append_yappy_manual_audit(
            payment,
            {
                'event': 'receipt_optional_skipped',
                'expected_amount_cents': payment.amount,
                'user_reference': user_ref or None,
            },
        )
        M.db.session.commit()
        payer = M.User.query.get(payment.user_id)
        mail_flags = []
        if payer:
            mail_flags.append(bool(notify_client_receipt_received(payment, payer)))
        if payer and cfg:
            mail_flags.append(bool(notify_admin_new_receipt(payment, payer, cfg)))
        warn = YAPPY_MANUAL_EMAIL_FAILURE_USER_MESSAGE if mail_flags and not all(mail_flags) else None
        return (
            jsonify(
                {
                    'success': True,
                    'message': 'Solicitud registrada. Tu pago está pendiente de validación administrativa.',
                    'email_notification_warning': warn,
                }
            ),
            200,
        )

    if allow_resubmit and payment.receipt_disk_path:
        try:
            from nodeone.services.yappy_receipt_storage import absolute_path_for_disk_rel

            old_abs = absolute_path_for_disk_rel(current_app, payment.receipt_disk_path)
            if old_abs and os.path.isfile(old_abs):
                os.remove(old_abs)
        except Exception:
            pass
        payment.rejection_reason = None

    try:
        rel_path, orig_name = save_yappy_receipt_file(
            current_app, file, organization_id=getattr(payment, 'organization_id', None)
        )
    except ValueError as ve:
        return jsonify({'success': False, 'error': str(ve)}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': f'No se pudo guardar el archivo: {e}'}), 500

    payment.receipt_disk_path = rel_path
    payment.receipt_filename = orig_name
    payment.receipt_url = None
    payment.status = 'pending_admin_review'
    payment.receipt_uploaded_at = datetime.utcnow()
    payment.ocr_status = 'needs_review'
    append_yappy_manual_audit(
        payment,
        {
            'event': 'receipt_submitted',
            'receipt_disk_path': rel_path,
            'receipt_filename': orig_name,
            'expected_amount_cents': payment.amount,
            'user_reference': user_ref or None,
            'instructions_preview': (effective_yappy_instructions_html(cfg) if cfg else '')[:200],
        },
    )
    M.db.session.commit()

    payer = M.User.query.get(payment.user_id)
    mail_flags = []
    if payer:
        mail_flags.append(bool(notify_client_receipt_received(payment, payer)))
    if payer and cfg:
        mail_flags.append(bool(notify_admin_new_receipt(payment, payer, cfg)))
    warn = YAPPY_MANUAL_EMAIL_FAILURE_USER_MESSAGE if mail_flags and not all(mail_flags) else None

    return (
        jsonify(
            {
                'success': True,
                'message': 'Comprobante enviado correctamente. Tu pago está pendiente de validación.',
                'email_notification_warning': warn,
            }
        ),
        200,
    )


@payments_checkout_bp.route('/payment/yappy-manual/<int:payment_id>')
@login_required
def payment_yappy_manual_instructions(payment_id):
    """Instrucciones QR, referencia ORD-*, subida de comprobante (Yappy manual)."""
    import app as M

    payment = M.Payment.query.get_or_404(payment_id)
    if payment.user_id != current_user.id:
        flash('No autorizado.', 'error')
        return redirect(url_for('payments.checkout'))
    if payment.payment_method != 'yappy_manual':
        return redirect(url_for('payments_checkout.payment_success', payment_id=payment.id))
    cfg = M.PaymentConfig.get_active_config_for_user_id(payment.user_id)
    from nodeone.services.yappy_manual_status import is_pending_admin_review, is_pending_receipt

    can_upload = is_pending_receipt(payment.status) or (payment.status or '').strip() == 'rejected'
    pending_review = is_pending_admin_review(payment.status)
    from nodeone.services.yappy_manual import (
        effective_yappy_display_name,
        effective_yappy_instructions_html,
        effective_yappy_phone_or_identifier,
    )

    ydisp = effective_yappy_display_name(cfg) if cfg else ''
    yinstr = effective_yappy_instructions_html(cfg) if cfg else ''
    yphone = effective_yappy_phone_or_identifier(cfg) if cfg else ''
    receipt_requires = bool(getattr(cfg, 'yappy_requires_receipt', True)) if cfg else True
    return render_template(
        'payment_yappy_manual.html',
        payment=payment,
        payment_config=cfg,
        yappy_can_upload=can_upload,
        yappy_pending_review=pending_review,
        yappy_display_name=ydisp,
        yappy_instructions_html=yinstr,
        yappy_phone=yphone,
        receipt_requires=receipt_requires,
    )


@payments_checkout_bp.route('/payment/yappy-manual/<int:payment_id>/estado')
@login_required
def payment_yappy_manual_order_status(payment_id):
    """Estado del pedido (cliente): resumen visual alineado al flujo mockup."""
    import app as M

    from nodeone.services.yappy_manual_status import yappy_status_label

    payment = M.Payment.query.get_or_404(payment_id)
    if payment.user_id != current_user.id:
        flash('No autorizado.', 'error')
        return redirect(url_for('payments.checkout'))
    if payment.payment_method != 'yappy_manual':
        return redirect(url_for('payments_checkout.payment_success', payment_id=payment.id))
    cfg = M.PaymentConfig.get_active_config_for_user_id(payment.user_id)
    return render_template(
        'payment_yappy_order_status.html',
        payment=payment,
        payment_config=cfg,
        status_label=yappy_status_label(payment.status),
    )


@payments_checkout_bp.route('/api/payment/yappy-manual/<int:payment_id>/submit-receipt', methods=['POST'])
@login_required
def api_yappy_manual_submit_receipt(payment_id):
    return _yappy_manual_submit_receipt_core(payment_id)


@payments_checkout_bp.route('/checkout/yappy/submit', methods=['POST'])
@_email_verified_check_then
def checkout_yappy_submit():
    """Alias del formulario checkout: multipart con payment_id + receipt (+ user_reference)."""
    pid = request.form.get('payment_id', type=int)
    if not pid:
        return jsonify({'success': False, 'error': 'Falta payment_id.'}), 400
    return _yappy_manual_submit_receipt_core(pid)


@payments_checkout_bp.route('/payments/yappy/status/<int:payment_id>', methods=['GET'])
@login_required
def payment_yappy_status_json(payment_id):
    import app as M

    from nodeone.services.yappy_manual_status import yappy_status_label

    payment = M.Payment.query.get_or_404(payment_id)
    if payment.user_id != current_user.id:
        return jsonify({'success': False, 'error': 'No autorizado'}), 403
    if payment.payment_method != 'yappy_manual':
        return jsonify({'success': False, 'error': 'No es Yappy manual'}), 400
    return jsonify(
        {
            'success': True,
            'payment_id': payment.id,
            'status': payment.status,
            'status_label': yappy_status_label(payment.status),
            'payment_reference': payment.payment_reference,
            'amount_cents': payment.amount,
            'currency': (payment.currency or 'usd').upper(),
            'receipt_uploaded_at': (
                getattr(payment, 'receipt_uploaded_at', None).isoformat()
                if getattr(payment, 'receipt_uploaded_at', None)
                else None
            ),
            'user_reference': (getattr(payment, 'payment_user_reference', None) or '') or '',
        }
    )


@payments_checkout_bp.route('/api/payment/yappy-manual/<int:payment_id>/receipt', methods=['GET'])
@login_required
def api_yappy_manual_download_receipt_owner(payment_id):
    """Descarga del comprobante solo para el titular del pago."""
    import app as M

    from flask import current_app, send_file

    from nodeone.services.yappy_receipt_storage import absolute_path_for_disk_rel

    payment = M.Payment.query.get_or_404(payment_id)
    if payment.user_id != current_user.id:
        abort(403)
    if payment.payment_method != 'yappy_manual':
        abort(404)
    rel = getattr(payment, 'receipt_disk_path', None) or ''
    abs_path = absolute_path_for_disk_rel(current_app, rel) if rel else None
    if abs_path:
        dl_name = payment.receipt_filename or os.path.basename(abs_path)
        return send_file(abs_path, as_attachment=True, download_name=dl_name)
    if payment.receipt_url and payment.receipt_url.startswith('/static/'):
        static_rel = payment.receipt_url.replace('/static/', '', 1)
        return send_from_directory(
            current_app.static_folder,
            static_rel,
            as_attachment=True,
            download_name=payment.receipt_filename or 'comprobante',
        )
    abort(404)


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
            pay_oid = int(resolve_current_organization())
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
            try:
                from nodeone.services.communication_dispatch import dispatch_membership_payment_confirmation

                dispatch_membership_payment_confirmation(payment.user, payment, subscription)
            except Exception:
                pass

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
