"""Onboarding (sesión), demo request y API pública para landing externo (OCI)."""

from datetime import datetime

from flask import Blueprint, jsonify, make_response, request, session
from flask_login import login_required

from nodeone.core.db import db
from models.catalog import Service

from . import landing_service

public_api_bp = Blueprint('public_api', __name__)


@public_api_bp.after_request
def _public_landing_cors(response):
    _, _, origins = landing_service.landing_config()
    return landing_service.apply_cors_headers(response, origins)


@public_api_bp.before_request
def _public_landing_options():
    if request.method != 'OPTIONS':
        return None
    path = request.path or ''
    if not (
        path.startswith('/api/public/services')
        or path in ('/api/public/book-service', '/api/public/request-quote')
    ):
        return None
    _, _, origins = landing_service.landing_config()
    resp = make_response('', 204)
    return landing_service.apply_cors_headers(resp, origins)


def _landing_org_id_or_response():
    key, org_id, _ = landing_service.landing_config()
    if not key or org_id is None:
        return None, (jsonify({'ok': False, 'error': 'landing_api_not_configured'}), 503)
    provided = landing_service.extract_api_key_from_request(request)
    if not landing_service.verify_landing_api_key(provided, key):
        return None, (jsonify({'ok': False, 'error': 'unauthorized'}), 401)
    return org_id, None


@public_api_bp.route('/api/onboarding/seen', methods=['POST'])
@login_required
def mark_onboarding_seen():
    """Marca el onboarding como visto."""
    session['onboarding_seen'] = True
    return jsonify({'success': True})


@public_api_bp.route('/api/public/demo-request', methods=['POST'])
def create_demo_request():
    """Recibe solicitudes de demo desde el sitio público."""
    import app as M

    try:
        payload = request.get_json(silent=True) or {}
        name = (payload.get('name') or '').strip()
        company = (payload.get('company') or '').strip()
        phone = (payload.get('phone') or '').strip()
        message = (payload.get('message') or '').strip()
        source = (payload.get('source') or 'landing').strip()[:100]

        if not name or not company or not phone or not message:
            return jsonify({'success': False, 'error': 'Completa todos los campos requeridos.'}), 400
        if len(name) > 200 or len(company) > 200 or len(phone) > 50:
            return jsonify({'success': False, 'error': 'Datos demasiado largos.'}), 400
        if len(message) > 2000:
            return jsonify({'success': False, 'error': 'El mensaje es demasiado largo.'}), 400

        demo_request = M.DemoRequest(
            name=name,
            company=company,
            phone=phone,
            message=message,
            source=source,
        )
        M.db.session.add(demo_request)
        M.db.session.commit()
        return jsonify({'success': True, 'id': demo_request.id}), 201
    except Exception:
        M.db.session.rollback()
        return jsonify({'success': False, 'error': 'No se pudo registrar la solicitud.'}), 500


@public_api_bp.route('/api/public/services', methods=['GET', 'OPTIONS'])
def public_services_list():
    """Catálogo público de servicios activos de la org configurada (requiere API key)."""
    org_id, err = _landing_org_id_or_response()
    if err:
        return err
    if landing_service.check_rate_limit(kind='get'):
        return jsonify({'ok': False, 'error': 'rate_limited'}), 429
    rows = (
        Service.query.filter_by(organization_id=org_id, is_active=True)
        .order_by(Service.display_order, Service.name)
        .all()
    )
    return jsonify({'ok': True, 'services': [landing_service.serialize_public_service(s) for s in rows]})


@public_api_bp.route('/api/public/services/<int:service_id>', methods=['GET', 'OPTIONS'])
def public_service_detail(service_id: int):
    org_id, err = _landing_org_id_or_response()
    if err:
        return err
    if landing_service.check_rate_limit(kind='get'):
        return jsonify({'ok': False, 'error': 'rate_limited'}), 429
    s = Service.query.filter_by(
        id=service_id, organization_id=org_id, is_active=True
    ).first()
    if not s:
        return jsonify({'ok': False, 'error': 'service_not_found'}), 404
    return jsonify({'ok': True, 'service': landing_service.serialize_public_service(s)})


def _handle_book_or_quote(*, intent: str):
    org_id, err = _landing_org_id_or_response()
    if err:
        return err

    idem_key = landing_service.normalize_idempotency_key(
        request.headers.get('Idempotency-Key')
    )
    if idem_key:
        cached = landing_service.get_idempotent_cached_response(org_id, idem_key)
        if cached:
            status, body = cached
            return jsonify(body), status

    if landing_service.check_rate_limit(kind='post'):
        return jsonify({'ok': False, 'error': 'rate_limited'}), 429

    payload = request.get_json(silent=True) or {}
    service_id = int(payload.get('service_id') or 0)
    if service_id < 1:
        return jsonify({'ok': False, 'error': 'service_id_required'}), 400

    service = Service.query.filter_by(
        id=service_id, organization_id=org_id, is_active=True
    ).first()
    if not service:
        return jsonify({'ok': False, 'error': 'service_not_found'}), 404

    name = (payload.get('name') or payload.get('customer_name') or '').strip()
    email = (payload.get('email') or '').strip()
    phone = (payload.get('phone') or '').strip()
    brand = (payload.get('brand') or '').strip()
    model = (payload.get('model') or '').strip()
    year = payload.get('year')
    year_i = int(year) if year not in (None, '') else None
    color = (payload.get('color') or '').strip()
    plate = (payload.get('plate') or '').strip()
    notes = (payload.get('notes') or '').strip()[:2000]
    pref_date = (payload.get('preferred_date') or payload.get('date') or '').strip()
    pref_time = (payload.get('preferred_time') or payload.get('time') or '').strip()
    extra_notes = []
    if pref_date:
        extra_notes.append(f'Fecha deseada: {pref_date[:32]}')
    if pref_time:
        extra_notes.append(f'Hora deseada: {pref_time[:32]}')
    if intent == 'quote':
        extra_notes.append('Origen: solicitud de cotización (landing)')
    else:
        extra_notes.append('Origen: reserva (landing)')
    full_notes = notes
    if extra_notes:
        full_notes = (notes + '\n' + '\n'.join(extra_notes)).strip() if notes else '\n'.join(extra_notes)

    if intent == 'book' and ((pref_date or '').strip() or (pref_time or '').strip()):
        sd = landing_service.parse_preferred_start_utc(pref_date, pref_time)
        if not sd:
            return jsonify({'ok': False, 'error': 'invalid_preferred_datetime'}), 400
        if sd <= datetime.utcnow():
            return (
                jsonify({'ok': False, 'error': 'preferred_datetime_must_be_future'}),
                400,
            )

    appointment = None
    appointment_skip_reason = None

    try:
        user, user_created = landing_service.find_or_create_customer(
            organization_id=org_id,
            name=name,
            email=email,
            phone=phone,
        )
        vehicle, veh_created = landing_service.find_or_create_vehicle(
            organization_id=org_id,
            customer_id=user.id,
            brand=brand,
            model=model,
            year=year_i,
            color=color,
            plate=plate,
        )
        quotation = landing_service.create_draft_quotation_for_service(
            organization_id=org_id,
            customer_id=user.id,
            service=service,
            notes=full_notes,
        )
        appointment, appointment_skip_reason = landing_service.try_create_appointment_for_landing(
            organization_id=org_id,
            service=service,
            user=user,
            preferred_date=pref_date,
            preferred_time=pref_time,
            intent=intent,
            request_for_log=request,
        )
        db.session.commit()
    except ValueError as ve:
        db.session.rollback()
        code = str(ve)
        return jsonify({'ok': False, 'error': code}), 400
    except Exception:
        db.session.rollback()
        return jsonify({'ok': False, 'error': 'server_error'}), 500

    email_sent, email_err = landing_service.send_verification_for_new_portal_user(
        user, user_was_created=user_created
    )

    body = {
        'ok': True,
        'intent': intent,
        'customer_id': user.id,
        'customer_created': user_created,
        'vehicle_id': vehicle.id,
        'vehicle_created': veh_created,
        'quotation_id': quotation.id,
        'quotation_number': quotation.number,
        'message': 'Solicitud registrada. Te contactaremos para confirmar.',
        'email_verification_sent': bool(email_sent),
        'email_verification_error': email_err,
        'appointment_id': appointment.id if appointment else None,
        'appointment_reference': getattr(appointment, 'reference', None),
        'appointment_skip_reason': appointment_skip_reason,
    }
    if idem_key:
        landing_service.store_idempotent_response(org_id, idem_key, 201, body)

    return jsonify(body), 201


@public_api_bp.route('/api/public/book-service', methods=['POST', 'OPTIONS'])
def public_book_service():
    """Alta desde landing: cliente, vehículo (taller), cotización borrador."""
    return _handle_book_or_quote(intent='book')


@public_api_bp.route('/api/public/request-quote', methods=['POST', 'OPTIONS'])
def public_request_quote():
    """Misma orquestación que book-service; distinto intent en auditoría/UI."""
    return _handle_book_or_quote(intent='quote')
