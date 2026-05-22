"""Admin: revisión de pagos, aprobación/rechazo y configuración de integración."""

import json
from datetime import datetime, timedelta
from functools import wraps

from flask import Blueprint, abort, current_app, flash, jsonify, make_response, redirect, render_template, request, send_file, send_from_directory, url_for
from flask_login import current_user, login_required
from sqlalchemy import false as sql_false
from sqlalchemy.exc import DBAPIError, OperationalError, ProgrammingError, StatementError

from nodeone.services.payment_post_process import process_cart_after_payment, send_payment_to_odoo

from app import require_permission

payments_admin_bp = Blueprint('payments_admin', __name__)


def _likely_missing_sql_column_error(exc: BaseException) -> bool:
    """MySQL/PyMySQL/SQLite suelen incluir el texto en OperationalError o en orig de StatementError."""
    msg = str(exc).lower()
    if 'unknown column' in msg or 'no such column' in msg or 'undefined column' in msg:
        return True
    # MySQL ER_BAD_FIELD_ERROR (p. ej. PyMySQL (1054, "Unknown column ..."))
    if '1054' in msg and 'column' in msg:
        return True
    return False


def _admin_payments_exc_is_db_schema_compat(exc: BaseException) -> bool:
    if _likely_missing_sql_column_error(exc):
        return True
    orig = getattr(exc, 'orig', None)
    if orig is not None and _likely_missing_sql_column_error(orig):
        return True
    if isinstance(exc, StatementError) and _likely_missing_sql_column_error(exc):
        return True
    if isinstance(exc, (OperationalError, ProgrammingError, DBAPIError)):
        return _likely_missing_sql_column_error(exc) or (
            orig is not None and _likely_missing_sql_column_error(orig)
        )
    return False


def _sanitize_payment_config_api_payload(data):
    """
    Ajusta strings a los límites VARCHAR del modelo PaymentConfig.
    Evita 500 por «Data too long» (MySQL strict), p. ej. teléfono Yappy > 120.
    """
    if not isinstance(data, dict):
        return {}
    out = dict(data)
    limits = (
        ('yappy_phone_or_identifier', 120),
        ('yappy_display_name', 200),
        ('yappy_directory_name', 100),
        ('yappy_business_name', 200),
        ('yappy_qr_image_path', 500),
        ('yappy_merchant_id', 200),
        ('yappy_merchant_phone', 64),
        ('paypal_mode', 20),
        ('intl_wire_swift', 32),
        ('intl_wire_account', 80),
        ('intl_wire_account_type', 80),
        ('intl_wire_country', 120),
        ('intl_wire_bank_name', 200),
        ('intl_wire_beneficiary_name', 400),
    )
    for key, maxlen in limits:
        if key not in out or out[key] is None:
            continue
        if isinstance(out[key], (bool, int, float)):
            continue
        s = str(out[key]).strip()
        if len(s) > maxlen:
            out[key] = s[:maxlen]
        else:
            out[key] = s
    return out


def _exc_is_data_too_long(exc: BaseException) -> bool:
    parts = [str(exc)]
    orig = getattr(exc, 'orig', None)
    if orig is not None:
        parts.append(str(orig))
    msg = ' '.join(parts).lower()
    return 'too long' in msg or '1406' in msg or 'data truncated' in msg


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
        is_platform_admin = bool(getattr(current_user, 'is_admin', False))
        if not is_platform_admin:
            try:
                has_any = bool(M._user_has_any_admin_permission(current_user))
            except Exception:
                current_app.logger.exception(
                    '_admin_required_lazy: fallo en _user_has_any_admin_permission; se niega acceso seguro'
                )
                has_any = False
            if not has_any:
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

        if getattr(payment, 'payment_method', None) == 'yappy_manual':
            return jsonify(
                {'success': False, 'error': 'Los pagos Yappy manual se validan en Administración → Pagos Yappy manual.'}
            ), 400

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

        if getattr(payment, 'payment_method', None) == 'yappy_manual':
            return jsonify(
                {'success': False, 'error': 'Los pagos Yappy manual se rechazan desde el panel Yappy manual.'}
            ), 400

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
                <p>Saludos,<br>Equipo Easy NodeOne</p>
                """
                M.email_service.send_email(
                    subject='Pago Rechazado - Easy NodeOne',
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
    try:
        import app as M

        return _admin_payments_page_inner(M)
    except Exception:
        current_app.logger.exception(
            'admin_payments: fallo no capturado; se sirve panel mínimo (revisa log y migraciones)'
        )
        try:
            flash(
                'No se pudo cargar el panel de pagos por un error interno. Revisa el log del servidor; '
                'si desplegaste código nuevo, ejecuta backend/migrate_yappy_manual_checkout_v3.py y reinicia el proceso.',
                'error',
            )
        except Exception:
            pass
        try:
            return render_template(
                'admin/payments.html',
                payment_config=None,
                pending_payments=[],
                yappy_manual_payments=[],
                payment_transactions=[],
            )
        except Exception:
            current_app.logger.exception('admin_payments: también falló render del panel mínimo (revisá base.html / contexto)')
            return make_response(
                '<!DOCTYPE html><html lang="es"><head><meta charset="utf-8">'
                '<meta name="viewport" content="width=device-width, initial-scale=1">'
                '<title>Pagos — error de plantilla</title></head><body style="font-family:system-ui,sans-serif;padding:1.5rem;">'
                '<h1 style="font-size:1.1rem;">No se pudo cargar el panel de pagos</h1>'
                '<p>El servidor registró un error al renderizar la página (incluso la versión mínima). '
                'Revisá el log del proceso (Gunicorn/uWSGI) y que existan migraciones aplicadas; '
                'en dev: <code>backend/migrate_yappy_manual_checkout_v3.py</code> y reinicio del servicio.</p>'
                '<p><a href="/dashboard">Volver al panel</a></p></body></html>',
                200,
                {'Content-Type': 'text/html; charset=utf-8'},
            )


def _payments_scope_organization_id(M):
    from nodeone.services.org_scope import admin_payments_scope_organization_id

    return int(admin_payments_scope_organization_id())


def _payment_config_for_scope(M, scope_oid: int):
    from nodeone.services.payment_config_provision import dedicated_active_config

    return dedicated_active_config(int(scope_oid))


def _admin_payments_page_inner(M):
    scope_oid = None
    payments_scope_org_name = ''

    try:
        scope_oid = _payments_scope_organization_id(M)
        org_row = M.SaasOrganization.query.get(int(scope_oid))
        payments_scope_org_name = getattr(org_row, 'name', '') if org_row else ''
        payment_config = _payment_config_for_scope(M, scope_oid)

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
        try:
            M.db.session.rollback()
        except Exception:
            pass
        config_dict = None

    pending_payments = []
    yappy_manual_payments = []
    enriched_transactions = []
    _db_compat_warned = False

    def _flash_db_schema_mismatch():
        nonlocal _db_compat_warned
        if _db_compat_warned:
            return
        _db_compat_warned = True
        flash(
            'No se pudieron cargar listas de pagos o el historial: suele indicar que la base de datos '
            'no tiene las columnas nuevas del flujo Yappy manual. En el servidor, ejecuta la migración '
            'backend/migrate_yappy_manual_checkout_v3.py y reinicia la aplicación.',
            'error',
        )

    try:
        uids_sq = _admin_scope_user_ids_only_safe(M)
    except Exception as e:
        current_app.logger.exception('admin_payments: _admin_scope_user_ids_only_safe')
        if _admin_payments_exc_is_db_schema_compat(e):
            _flash_db_schema_mismatch()
            uids_sq = M.db.session.query(M.User.id).filter(sql_false())
        else:
            raise

    try:
        ppq = M.Payment.query.filter(
            M.Payment.ocr_status.in_(['pending', 'needs_review']),
            M.Payment.status == 'pending',
        )
        if uids_sq is not None:
            ppq = ppq.filter(M.Payment.user_id.in_(uids_sq))
        pending_payments = ppq.order_by(M.Payment.created_at.desc()).limit(20).all()
    except Exception as e:
        if _admin_payments_exc_is_db_schema_compat(e):
            current_app.logger.exception('admin_payments: pending_payments query failed (schema mismatch?)')
            _flash_db_schema_mismatch()
        else:
            raise

    try:
        ymq = M.Payment.query.filter(
            M.Payment.payment_method == 'yappy_manual',
            M.Payment.status.in_(
                [
                    'pending_receipt',
                    'pending_payment',
                    'pending_admin_review',
                    'pending_validation',
                    'manual_review',
                    'partially_paid',
                ]
            ),
        )
        if uids_sq is not None:
            ymq = ymq.filter(M.Payment.user_id.in_(uids_sq))
        yappy_manual_payments = ymq.order_by(M.Payment.created_at.desc()).limit(50).all()
    except Exception as e:
        if _admin_payments_exc_is_db_schema_compat(e):
            current_app.logger.exception('admin_payments: yappy_manual_payments query failed (schema mismatch?)')
            _flash_db_schema_mismatch()
        else:
            raise

    payment_transactions = []
    try:
        htq = M.HistoryTransaction.query.filter(
            M.HistoryTransaction.transaction_type.in_(['payment', 'purchase'])
        )
        if uids_sq is not None:
            htq = htq.filter(M.HistoryTransaction.actor_id.in_(uids_sq))
        payment_transactions = htq.order_by(M.HistoryTransaction.timestamp.desc()).limit(100).all()
    except Exception as e:
        if _admin_payments_exc_is_db_schema_compat(e):
            current_app.logger.exception('admin_payments: history_transaction query failed')
            _flash_db_schema_mismatch()
        else:
            raise

    for trans in payment_transactions:
        try:
            trans_dict = trans.to_dict(include_sensitive=True)
        except Exception:
            current_app.logger.exception('admin_payments: HistoryTransaction.to_dict failed for id=%s', trans.id)
            continue

        if trans.actor_id:
            try:
                actor = M.User.query.get(trans.actor_id)
            except Exception as e:
                if _admin_payments_exc_is_db_schema_compat(e):
                    actor = None
                    _flash_db_schema_mismatch()
                else:
                    raise
            if actor:
                trans_dict['actor'] = {
                    'id': actor.id,
                    'email': actor.email,
                    'first_name': actor.first_name,
                    'last_name': actor.last_name,
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
            try:
                pay = M.Payment.query.get(payment_id)
            except Exception as e:
                if _admin_payments_exc_is_db_schema_compat(e):
                    pay = None
                    _flash_db_schema_mismatch()
                else:
                    raise
            if pay:
                trans_dict['payment'] = {
                    'id': pay.id,
                    'amount': float(pay.amount) / 100 if pay.amount else 0,
                    'currency': pay.currency.upper() if pay.currency else 'USD',
                    'status': pay.status,
                    'method': pay.payment_method,
                }

        enriched_transactions.append(trans_dict)

    print(f"📊 admin_payments(): Pasando {len(enriched_transactions)} transacciones al template")
    if enriched_transactions:
        print(f"   - Primera transacción: ID {enriched_transactions[0].get('id')}, Tipo: {enriched_transactions[0].get('transaction_type')}")

    tmpl_ctx = {
        'payment_config': config_dict,
        'pending_payments': pending_payments,
        'yappy_manual_payments': yappy_manual_payments,
        'payment_transactions': enriched_transactions,
        'payments_scope_org_id': scope_oid,
        'payments_scope_org_name': payments_scope_org_name,
    }
    try:
        return render_template('admin/payments.html', **tmpl_ctx)
    except Exception:
        current_app.logger.exception(
            'admin_payments: error al renderizar la plantilla (p. ej. JSON no serializable en historial)'
        )
        flash(
            'Se cargó la configuración pero el historial de transacciones no pudo mostrarse. '
            'Revisa el log del servidor o vacía temporalmente el historial problemático.',
            'warning',
        )
        return render_template(
            'admin/payments.html',
            payment_config=config_dict,
            pending_payments=pending_payments,
            yappy_manual_payments=yappy_manual_payments,
            payment_transactions=[],
        )


@payments_admin_bp.route('/api/admin/payments/org-methods', methods=['GET', 'PUT'])
@require_permission('payments.manage')
def api_organization_payment_methods():
    """Matriz de métodos de pago por organización (habilitar, orden, instrucciones)."""
    import app as M
    from nodeone.services import organization_payment_methods as opm

    try:
        scope_oid = _payments_scope_organization_id(M)
    except Exception:
        from utils.organization import default_organization_id

        scope_oid = int(default_organization_id())

    if request.method == 'GET':
        opm.ensure_organization_payment_methods_schema()
        opm.seed_organization_payment_methods(scope_oid)
        rows = opm.list_methods_for_org(scope_oid, enabled_only=False)
        return jsonify({
            'success': True,
            'organization_id': scope_oid,
            'methods': [r.to_dict() for r in rows],
            'catalog_keys': list(opm.METHOD_CATALOG.keys()),
        })

    payload = request.get_json(silent=True) or {}
    methods = payload.get('methods')
    if not isinstance(methods, list):
        return jsonify({'success': False, 'error': 'Se espera { "methods": [ ... ] }'}), 400
    saved = opm.save_methods_payload(scope_oid, methods)
    org_name = None
    try:
        org_row = M.SaasOrganization.query.get(int(scope_oid))
        org_name = getattr(org_row, 'name', None) if org_row else None
    except Exception:
        pass
    return jsonify({
        'success': True,
        'organization_id': scope_oid,
        'organization_name': org_name,
        'methods': saved,
    })


@payments_admin_bp.route('/api/admin/payments/config', methods=['GET', 'POST', 'PUT'])
@_admin_required_lazy
def api_payment_config():
    """API para obtener y actualizar configuración de pagos"""
    import app as M

    if request.method == 'GET':
        scope_oid = None
        try:
            scope_oid = M.admin_data_scope_organization_id()
        except Exception:
            current_app.logger.exception('api_payment_config GET: admin_data_scope_organization_id')
            try:
                from utils.organization import default_organization_id as _def_org_id

                scope_oid = _def_org_id()
            except Exception:
                scope_oid = None

        try:
            config = _payment_config_for_scope(M, scope_oid)
            org_name = None
            try:
                org_row = M.SaasOrganization.query.get(int(scope_oid))
                org_name = getattr(org_row, 'name', None) if org_row else None
            except Exception:
                pass
            if config:
                try:
                    cfg_dict = config.to_dict()
                except Exception:
                    current_app.logger.exception('api_payment_config GET: PaymentConfig.to_dict')
                    return jsonify(
                        {
                            'success': True,
                            'organization_id': scope_oid,
                            'organization_name': org_name,
                            'config': M.PaymentConfig.empty_config_api_dict(organization_id=scope_oid),
                            'no_active_row': True,
                            'schema_degraded': True,
                            'message': (
                                'No se pudo leer la configuración activa desde la base de datos. '
                                'Ejecuta backend/migrate_yappy_manual_checkout_v3.py y reinicia el servicio.'
                            ),
                        }
                    )
                return jsonify(
                    {
                        'success': True,
                        'organization_id': scope_oid,
                        'organization_name': org_name,
                        'config': cfg_dict,
                        'no_active_row': False,
                    }
                )
            # Sin fila activa: respuesta exitosa con plantilla vacía (el formulario SSR ya puede mostrarse).
            return jsonify(
                {
                    'success': True,
                    'organization_id': scope_oid,
                    'organization_name': org_name,
                    'config': M.PaymentConfig.empty_config_api_dict(organization_id=scope_oid),
                    'no_active_row': True,
                    'message': 'No hay fila de configuración activa para esta empresa. Rellena los campos y guarda para crearla.',
                }
            )
        except Exception as e:
            current_app.logger.exception('api_payment_config GET: lectura PaymentConfig')
            if _admin_payments_exc_is_db_schema_compat(e):
                return jsonify(
                    {
                        'success': True,
                        'config': M.PaymentConfig.empty_config_api_dict(organization_id=scope_oid),
                        'no_active_row': True,
                        'schema_degraded': True,
                        'message': (
                            'La base de datos no tiene las columnas esperadas para payment_config '
                            '(código desplegado sin migración). Ejecuta '
                            'backend/migrate_yappy_manual_checkout_v3.py y reinicia el servicio.'
                        ),
                    }
                )
            # 200 + plantilla vacía: evita "Failed to load resource" en consola y deja el panel usable para revisar logs/migración.
            oid_safe = scope_oid if isinstance(scope_oid, int) else None
            try:
                cfg_empty = M.PaymentConfig.empty_config_api_dict(organization_id=oid_safe)
            except Exception:
                cfg_empty = M.PaymentConfig.empty_config_api_dict(organization_id=None)
            return jsonify(
                {
                    'success': True,
                    'config': cfg_empty,
                    'no_active_row': True,
                    'read_error_degraded': True,
                    'message': (
                        'No se pudo leer la configuración de pagos en el servidor. '
                        'Revisá el log (traceback) y las migraciones de BD. Detalle: '
                        + str(e)[:400]
                    ),
                }
            )

    elif request.method in ['POST', 'PUT']:
        data = _sanitize_payment_config_api_payload(request.get_json(silent=True) or {})
        scope_oid = None
        try:
            scope_oid = _payments_scope_organization_id(M)
        except Exception:
            current_app.logger.exception('api_payment_config POST/PUT: admin_payments_scope_organization_id')
            try:
                from utils.organization import default_organization_id as _def_org_id

                scope_oid = _def_org_id()
            except Exception:
                scope_oid = None

        try:
            if scope_oid is not None:
                scope_oid = int(scope_oid)
        except (TypeError, ValueError):
            scope_oid = None
        if scope_oid is None:
            try:
                from utils.organization import default_organization_id

                scope_oid = int(default_organization_id())
            except Exception:
                scope_oid = 1

        from nodeone.services import organization_payment_methods as opm

        opm.seed_organization_payment_methods(scope_oid)
        _ym_row = opm.get_method_row(scope_oid, 'yappy_manual')
        if _ym_row and _ym_row.enabled:
            from nodeone.services.yappy_manual import validate_yappy_manual_admin_emails_when_enabled

            norm_emails, em_err = validate_yappy_manual_admin_emails_when_enabled(
                data.get('yappy_manual_admin_emails', '')
            )
            if em_err:
                return jsonify({'success': False, 'error': em_err}), 400
            data['yappy_manual_admin_emails'] = ','.join(norm_emails)

        try:
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
                    yappy_directory_name=data.get('yappy_directory_name', ''),
                    yappy_qr_image_path=data.get('yappy_qr_image_path', ''),
                    yappy_business_name=data.get('yappy_business_name', ''),
                    yappy_merchant_phone=(data.get('yappy_merchant_phone') or '').strip() or None,
                    yappy_display_name=(data.get('yappy_display_name') or '').strip() or None,
                    yappy_phone_or_identifier=(data.get('yappy_phone_or_identifier') or '').strip() or None,
                    yappy_instructions=(data.get('yappy_instructions') or '').strip() or None,
                    yappy_requires_receipt=bool(data.get('yappy_requires_receipt', True)),
                    yappy_admin_validation_required=bool(data.get('yappy_admin_validation_required', True)),
                    yappy_manual_enabled=False,
                    yappy_manual_instructions=data.get('yappy_manual_instructions', '') or '',
                    yappy_manual_admin_emails=data.get('yappy_manual_admin_emails', '') or '',
                    intl_wire_enabled=False,
                    intl_wire_beneficiary_name=data.get('intl_wire_beneficiary_name', '') or '',
                    intl_wire_bank_name=data.get('intl_wire_bank_name', '') or '',
                    intl_wire_swift=data.get('intl_wire_swift', '') or '',
                    intl_wire_account=data.get('intl_wire_account', '') or '',
                    intl_wire_account_type=data.get('intl_wire_account_type', '') or '',
                    intl_wire_country=data.get('intl_wire_country', '') or '',
                    intl_wire_instructions=data.get('intl_wire_instructions', '') or '',
                    use_environment_variables=bool(data.get('use_environment_variables', True)),
                    is_active=True,
                )
                M.db.session.add(config)
            else:
                if getattr(config, 'organization_id', None) != scope_oid:
                    config.organization_id = scope_oid
                # Merge completo del JSON (el panel envía todas las claves); evita que falte `if x in data` y no persista.
                config.stripe_secret_key = data.get('stripe_secret_key', config.stripe_secret_key)
                config.stripe_publishable_key = data.get('stripe_publishable_key', config.stripe_publishable_key)
                config.stripe_webhook_secret = data.get('stripe_webhook_secret', config.stripe_webhook_secret)
                config.paypal_client_id = data.get('paypal_client_id', config.paypal_client_id)
                config.paypal_client_secret = data.get('paypal_client_secret', config.paypal_client_secret)
                config.paypal_mode = data.get('paypal_mode', config.paypal_mode)
                config.paypal_return_url = data.get('paypal_return_url', config.paypal_return_url)
                config.paypal_cancel_url = data.get('paypal_cancel_url', config.paypal_cancel_url)
                config.banco_general_merchant_id = data.get('banco_general_merchant_id', config.banco_general_merchant_id)
                config.banco_general_api_key = data.get('banco_general_api_key', config.banco_general_api_key)
                config.banco_general_shared_secret = data.get('banco_general_shared_secret', config.banco_general_shared_secret)
                config.banco_general_api_url = data.get('banco_general_api_url', config.banco_general_api_url)
                config.yappy_api_key = data.get('yappy_api_key', config.yappy_api_key)
                config.yappy_merchant_id = data.get('yappy_merchant_id', config.yappy_merchant_id)
                config.yappy_api_url = data.get('yappy_api_url', config.yappy_api_url)
                config.yappy_directory_name = data.get('yappy_directory_name', config.yappy_directory_name)
                config.yappy_qr_image_path = data.get('yappy_qr_image_path', config.yappy_qr_image_path)
                config.yappy_business_name = data.get('yappy_business_name', config.yappy_business_name)
                if 'yappy_merchant_phone' in data:
                    v = data.get('yappy_merchant_phone')
                    v = '' if v is None else str(v).strip()
                    config.yappy_merchant_phone = v or None
                if 'yappy_display_name' in data:
                    v = data.get('yappy_display_name')
                    v = '' if v is None else str(v).strip()
                    config.yappy_display_name = v or None
                if 'yappy_phone_or_identifier' in data:
                    v = data.get('yappy_phone_or_identifier')
                    v = '' if v is None else str(v).strip()
                    config.yappy_phone_or_identifier = v or None
                if 'yappy_instructions' in data:
                    v = data.get('yappy_instructions')
                    v = '' if v is None else str(v).strip()
                    config.yappy_instructions = v or None
                config.yappy_requires_receipt = bool(data.get('yappy_requires_receipt', config.yappy_requires_receipt))
                config.yappy_admin_validation_required = bool(
                    data.get('yappy_admin_validation_required', config.yappy_admin_validation_required)
                )
                config.yappy_manual_instructions = data.get('yappy_manual_instructions', config.yappy_manual_instructions)
                config.yappy_manual_admin_emails = data.get('yappy_manual_admin_emails', config.yappy_manual_admin_emails)
                config.intl_wire_beneficiary_name = data.get('intl_wire_beneficiary_name', config.intl_wire_beneficiary_name)
                config.intl_wire_bank_name = data.get('intl_wire_bank_name', config.intl_wire_bank_name)
                config.intl_wire_swift = data.get('intl_wire_swift', config.intl_wire_swift)
                config.intl_wire_account = data.get('intl_wire_account', config.intl_wire_account)
                config.intl_wire_account_type = data.get('intl_wire_account_type', config.intl_wire_account_type)
                config.intl_wire_country = data.get('intl_wire_country', config.intl_wire_country)
                config.intl_wire_instructions = data.get('intl_wire_instructions', config.intl_wire_instructions)
                config.use_environment_variables = bool(data.get('use_environment_variables', config.use_environment_variables))
                config.is_active = True
                config.updated_at = datetime.utcnow()

            M.db.session.commit()
            opm.sync_legacy_payment_config_flags(scope_oid)
            try:
                cfg_out = config.to_dict()
            except Exception:
                current_app.logger.exception('api_payment_config POST/PUT: to_dict tras commit')
                cfg_out = M.PaymentConfig.empty_config_api_dict(organization_id=scope_oid)
            org_name = None
            try:
                org_row = M.SaasOrganization.query.get(int(scope_oid))
                org_name = getattr(org_row, 'name', None) if org_row else None
            except Exception:
                pass
            return jsonify(
                {
                    'success': True,
                    'message': 'Configuración guardada correctamente',
                    'organization_id': scope_oid,
                    'organization_name': org_name,
                    'config': cfg_out,
                }
            )
        except Exception as e:
            M.db.session.rollback()
            current_app.logger.exception('api_payment_config POST/PUT')
            if _admin_payments_exc_is_db_schema_compat(e):
                _mig = (
                    'No se puede guardar: la base de datos no tiene las columnas de payment_config '
                    'que espera el código. Ejecuta en el servidor backend/migrate_yappy_manual_checkout_v3.py y reinicia.'
                )
                return jsonify(
                    {
                        'success': False,
                        'schema_migration_required': True,
                        'error': _mig,
                        'message': _mig,
                    }
                ), 503
            if _exc_is_data_too_long(e):
                _msg = 'El identificador/teléfono de Yappy no puede superar 120 caracteres.'
                _err = (
                    _msg
                    + ' Si pegaste otro campo muy largo, acortalo también y volvé a guardar.'
                )
                return jsonify(
                    {
                        'success': False,
                        'error': _err,
                        'message': _msg,
                    }
                ), 400
            _err = str(e)
            return jsonify({'success': False, 'error': _err, 'message': _err}), 500


@payments_admin_bp.route('/admin/payments/verify', methods=['GET'])
@_admin_required_lazy
def admin_payments_verify():
    """Página con botón para ejecutar la misma verificación que el cron (Yappy / PayPal / Stripe)."""
    import app as M

    def _pending_block():
        return {
            'yappy': M.Payment.query.filter(
                M.Payment.payment_method == 'yappy',
                M.Payment.status.in_(['pending', 'awaiting_confirmation']),
            ).count(),
            'paypal': M.Payment.query.filter(
                M.Payment.payment_method == 'paypal',
                M.Payment.status.in_(['pending', 'awaiting_confirmation']),
            ).count(),
            'stripe': M.Payment.query.filter(
                M.Payment.payment_method.in_(['stripe', 'tcr']),
                M.Payment.status.in_(['pending', 'awaiting_confirmation']),
            ).count(),
        }

    pending_payments = _pending_block()
    total_pending = sum(pending_payments.values())
    since = datetime.utcnow() - timedelta(hours=24)
    recently_confirmed = M.Payment.query.filter(
        M.Payment.status == 'succeeded',
        M.Payment.paid_at.isnot(None),
        M.Payment.paid_at >= since,
    ).count()

    return render_template(
        'admin/payments_verify.html',
        total_pending=total_pending,
        pending_payments=pending_payments,
        recently_confirmed=recently_confirmed,
    )


@payments_admin_bp.route('/api/admin/payments/verify-pending', methods=['POST'])
@_admin_required_lazy
def api_verify_pending_payments():
    """Misma lógica que el cron: verify_all_payments, con resumen JSON para el panel admin."""
    try:
        from notification_scheduler import verify_all_payments_stats

        return jsonify(verify_all_payments_stats())
    except Exception as e:
        import traceback

        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@payments_admin_bp.route('/admin/payments/yappy-manual')
@require_permission('payments.manage')
def admin_yappy_manual_list():
    import app as M

    from nodeone.services.yappy_manual_status import yappy_status_label
    uids_sq = _admin_scope_user_ids_only_safe(M)

    def _base_yappy_query():
        q = M.Payment.query.filter(M.Payment.payment_method == 'yappy_manual')
        if uids_sq is not None:
            q = q.filter(M.Payment.user_id.in_(uids_sq))
        return q

    pending_statuses = (
        'pending_receipt',
        'pending_payment',
        'pending_admin_review',
        'pending_validation',
        'manual_review',
        'partially_paid',
    )
    payments_pending = (
        _base_yappy_query()
        .filter(M.Payment.status.in_(pending_statuses))
        .order_by(M.Payment.created_at.desc())
        .limit(100)
        .all()
    )
    payments_approved = (
        _base_yappy_query()
        .filter(M.Payment.status == 'paid')
        .order_by(M.Payment.created_at.desc())
        .limit(100)
        .all()
    )
    payments_rejected = (
        _base_yappy_query()
        .filter(M.Payment.status.in_(('rejected', 'cancelled')))
        .order_by(M.Payment.created_at.desc())
        .limit(100)
        .all()
    )
    return render_template(
        'admin/yappy_manual_list.html',
        payments_pending=payments_pending,
        payments_approved=payments_approved,
        payments_rejected=payments_rejected,
        yappy_status_label=yappy_status_label,
    )


@payments_admin_bp.route('/admin/payments/yappy-manual/<int:payment_id>')
@require_permission('payments.manage')
def admin_yappy_manual_detail(payment_id):
    import app as M

    from nodeone.services.yappy_manual_status import yappy_status_label
    payment = M.Payment.query.get_or_404(payment_id)
    payer = _payment_in_admin_scope_or_403(M, payment)
    if not payer:
        return ('No autorizado para ver este pago', 403)
    cfg = M.PaymentConfig.get_active_config_for_user_id(payment.user_id)
    audit_events = []
    if payment.yappy_manual_audit_json:
        try:
            audit_events = json.loads(payment.yappy_manual_audit_json)
            if not isinstance(audit_events, list):
                audit_events = []
        except Exception:
            audit_events = []
    return render_template(
        'admin/yappy_manual_detail.html',
        payment=payment,
        payer=payer,
        payment_config=cfg,
        audit_events=audit_events,
        yappy_status_label=yappy_status_label,
    )


@payments_admin_bp.route('/admin/payments/yappy')
@require_permission('payments.manage')
def admin_yappy_alias_list():
    return redirect(url_for('payments_admin.admin_yappy_manual_list'))


@payments_admin_bp.route('/admin/payments/yappy/<int:payment_id>')
@require_permission('payments.manage')
def admin_yappy_alias_detail(payment_id):
    return redirect(url_for('payments_admin.admin_yappy_manual_detail', payment_id=payment_id))


@payments_admin_bp.route('/api/admin/payments/yappy/<int:payment_id>/receipt', methods=['GET'])
@payments_admin_bp.route('/admin/payments/yappy/<int:payment_id>/receipt', methods=['GET'])
@require_permission('payments.manage')
def api_admin_yappy_manual_receipt(payment_id):
    import app as M

    from flask import current_app

    from nodeone.services.yappy_receipt_storage import absolute_path_for_disk_rel

    payment = M.Payment.query.get_or_404(payment_id)
    payer = _payment_in_admin_scope_or_403(M, payment)
    if not payer:
        abort(403)
    if payment.payment_method != 'yappy_manual':
        abort(404)
    rel = getattr(payment, 'receipt_disk_path', None) or ''
    abs_path = absolute_path_for_disk_rel(current_app, rel) if rel else None
    if abs_path:
        return send_file(abs_path, conditional=True)
    if payment.receipt_url and payment.receipt_url.startswith('/static/'):
        static_rel = payment.receipt_url.replace('/static/', '', 1)
        return send_from_directory(
            current_app.static_folder,
            static_rel,
            as_attachment=False,
        )
    abort(404)


@payments_admin_bp.route('/api/admin/payments/<int:payment_id>/yappy-manual/validate', methods=['POST'])
@require_permission('payments.manage')
def api_yappy_manual_validate(payment_id):
    """Aprobar (paid), incompleto (partially_paid), rechazar (rejected) o revisión manual (manual_review)."""
    import app as M

    from nodeone.services.yappy_manual import (
        YAPPY_MANUAL_EMAIL_FAILURE_USER_MESSAGE,
        append_yappy_manual_audit,
        notify_client_approved,
        notify_client_manual_review,
        notify_client_partial,
        notify_client_rejected,
    )

    try:
        payment = M.Payment.query.get_or_404(payment_id)
        payer = _payment_in_admin_scope_or_403(M, payment)
        if not payer:
            return jsonify({'success': False, 'error': 'No autorizado'}), 403
        if payment.payment_method != 'yappy_manual':
            return jsonify({'success': False, 'error': 'No es un pago Yappy manual'}), 400
        if payment.status not in ('pending_admin_review', 'pending_validation', 'manual_review'):
            return jsonify({'success': False, 'error': 'Solo se validan pagos en revisión (comprobante recibido).'}), 400

        body = request.get_json(silent=True) or {}
        decision = (body.get('decision') or '').strip().lower()
        observations = (body.get('observations') or '').strip()
        raw_amt = body.get('amount_received_cents')
        try:
            amount_received_cents = int(raw_amt)
        except (TypeError, ValueError):
            return jsonify({'success': False, 'error': 'Indique amount_received_cents (entero, centavos).'}), 400

        expected = int(payment.amount or 0)
        admin_id = current_user.id

        def _json_ok(message: str, mail_ok: bool):
            out = {'success': True, 'message': message}
            if not mail_ok:
                out['email_notification_warning'] = YAPPY_MANUAL_EMAIL_FAILURE_USER_MESSAGE
            return jsonify(out)

        if decision == 'rejected':
            if not observations:
                return jsonify(
                    {'success': False, 'error': 'El motivo de rechazo es obligatorio (campo observaciones / motivo).'}
                ), 400
            payment.status = 'rejected'
            payment.validated_by_user_id = admin_id
            payment.validated_at = datetime.utcnow()
            payment.validation_observations = observations
            payment.rejection_reason = observations or None
            payment.amount_received_cents = amount_received_cents
            append_yappy_manual_audit(
                payment,
                {
                    'event': 'admin_rejected',
                    'admin_user_id': admin_id,
                    'expected_amount_cents': expected,
                    'amount_received_cents': amount_received_cents,
                    'observations': observations,
                },
            )
            M.db.session.commit()
            mail_ok = bool(notify_client_rejected(payment, payer, observations))
            return _json_ok('Pago rechazado.', mail_ok)

        if decision == 'partially_paid':
            if amount_received_cents >= expected:
                return jsonify(
                    {'success': False, 'error': 'Para pago incompleto el monto recibido debe ser menor al esperado.'}
                ), 400
            payment.status = 'partially_paid'
            payment.amount_received_cents = amount_received_cents
            payment.validated_by_user_id = admin_id
            payment.validated_at = datetime.utcnow()
            payment.validation_observations = observations
            append_yappy_manual_audit(
                payment,
                {
                    'event': 'admin_partially_paid',
                    'admin_user_id': admin_id,
                    'expected_amount_cents': expected,
                    'amount_received_cents': amount_received_cents,
                    'observations': observations,
                },
            )
            M.db.session.commit()
            mail_ok = bool(notify_client_partial(payment, payer, observations or None))
            return _json_ok('Marcado como pago incompleto.', mail_ok)

        if decision == 'manual_review':
            payment.status = 'manual_review'
            payment.amount_received_cents = amount_received_cents
            payment.validated_by_user_id = admin_id
            payment.validated_at = datetime.utcnow()
            payment.validation_observations = observations
            append_yappy_manual_audit(
                payment,
                {
                    'event': 'admin_manual_review',
                    'admin_user_id': admin_id,
                    'expected_amount_cents': expected,
                    'amount_received_cents': amount_received_cents,
                    'observations': observations,
                },
            )
            M.db.session.commit()
            mail_ok = bool(notify_client_manual_review(payment, payer, observations or None))
            return _json_ok('Dejado en revisión manual.', mail_ok)

        if decision == 'paid':
            if amount_received_cents < expected:
                return jsonify(
                    {
                        'success': False,
                        'error': 'Monto recibido menor al esperado: use «Pago incompleto» o rechace.',
                    }
                ), 400
            payment.status = 'paid'
            payment.paid_at = datetime.utcnow()
            payment.amount_received_cents = amount_received_cents
            payment.validated_by_user_id = admin_id
            payment.validated_at = datetime.utcnow()
            payment.validation_observations = observations
            payment.ocr_status = 'verified'
            payment.ocr_verified_at = datetime.utcnow()
            append_yappy_manual_audit(
                payment,
                {
                    'event': 'admin_approved_paid',
                    'admin_user_id': admin_id,
                    'expected_amount_cents': expected,
                    'amount_received_cents': amount_received_cents,
                    'observations': observations,
                },
            )
            M.db.session.commit()

            cart = M.get_or_create_cart(payment.user_id)
            if cart.get_items_count() > 0:
                process_cart_after_payment(cart, payment)
                cart.clear()
                M.db.session.commit()

            try:
                subscription = M.Subscription.query.filter_by(payment_id=payment.id).first()
                if subscription:
                    M.NotificationEngine.notify_membership_payment(payer, payment, subscription)
                    try:
                        from nodeone.services.communication_dispatch import (
                            dispatch_membership_payment_confirmation,
                        )

                        dispatch_membership_payment_confirmation(payer, payment, subscription)
                    except Exception:
                        pass
            except Exception:
                pass

            mail_ok = bool(notify_client_approved(payment, payer))

            try:
                send_payment_to_odoo(payment, payer, cart)
            except Exception as e:
                print(f"⚠️ Odoo yappy_manual: {e}")

            return _json_ok('Pago aprobado y compra activada.', mail_ok)

        return jsonify({'success': False, 'error': 'decision inválida (paid|partially_paid|rejected|manual_review).'}), 400
    except Exception as e:
        M.db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
