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
    # Preflight CORS: demo-request (landing estático) y rutas de catálogo/reserva OCI.
    if path == '/api/public/demo-request' or path.startswith('/api/public/services') or path in (
        '/api/public/book-service',
        '/api/public/request-quote',
    ):
        _, _, origins = landing_service.landing_config()
        resp = make_response('', 204)
        return landing_service.apply_cors_headers(resp, origins)
    return None


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


@public_api_bp.route('/api/public/academic-programs/<slug>/lead', methods=['POST', 'OPTIONS'])
def public_academic_program_pdf_lead(slug: str):
    """Captura lead (público, sin login) y envía correo de confirmación antes del PDF.

    Contrato:
      POST /api/public/academic-programs/<slug>/lead
      Body JSON con campos: name, email, phone, country?, company?, message?, source?, utm_*
      Responde con {success, message, requires_email_confirmation: true} (sin download_url hasta confirmar).
    """
    import re

    from flask import current_app, jsonify, make_response

    from nodeone.modules.public_api import landing_service
    from utils.organization import resolve_current_organization

    # CORS allowlist (especificación del flujo IIUS).
    _ALLOWED_ORIGINS = {
        'https://internationalinstitute.us',
        'https://www.internationalinstitute.us',
    }

    def _apply_cors(resp):
        try:
            req_origin = (request.headers.get('Origin') or '').strip()
            if req_origin and req_origin in _ALLOWED_ORIGINS:
                resp.headers['Access-Control-Allow-Origin'] = req_origin
                resp.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
                resp.headers['Access-Control-Allow-Headers'] = 'Content-Type'
                resp.headers['Access-Control-Max-Age'] = '600'
        except Exception:
            pass
        return resp

    if request.method == 'OPTIONS':
        return _apply_cors(make_response('', 204))

    if landing_service.check_rate_limit(kind='post'):
        return _apply_cors(jsonify({'success': False, 'message': 'rate_limited'})), 429

    from models.academic_program import AcademicProgram
    from models.academic_program_pdf_lead import AcademicProgramPdfLead
    from nodeone.modules.academic_enrollment.program_academic_pdf import (
        program_has_public_academic_pdf,
        _stored_pdf_filesystem_path,
    )

    slug_norm = (slug or '').strip().lower()
    if not slug_norm:
        return _apply_cors(jsonify({'success': False, 'message': 'program_slug_required'})), 400

    payload = request.get_json(silent=True) or {}

    # Honeypot: cualquier valor en el campo oculto => spam.
    hp = (
        payload.get('hp')
        or payload.get('honeypot')
        or payload.get('website')
        or payload.get('leave_blank')
        or ''
    )
    if isinstance(hp, str) and hp.strip():
        return _apply_cors(jsonify({'success': False, 'message': 'spam_detected'})), 400

    def _strip_nohtml(s: str | None, *, max_len: int | None = None) -> str:
        # Quita tags HTML/XML (y evita esquemas tipo <script>).
        out = re.sub(r'<[^>]*?>', '', (s or '').strip())
        # Bloquea scripts por si venían como texto sin tags.
        if re.search(r'(?i)script', out):
            out = ''
        if max_len is not None:
            out = out[:max_len]
        return out

    name = _strip_nohtml(payload.get('name'), max_len=200)
    email = (payload.get('email') or '').strip().lower()
    phone = (payload.get('phone') or '').strip()
    program_slug_body = (payload.get('program_slug') or '').strip().lower()
    source = _strip_nohtml(payload.get('source'), max_len=120) or 'wp_landing_pdf'

    country = _strip_nohtml(payload.get('country'), max_len=120) or None
    company = _strip_nohtml(payload.get('company'), max_len=255) or None
    message = _strip_nohtml(payload.get('message'), max_len=2000) or None

    utm_source = _strip_nohtml(payload.get('utm_source'), max_len=120) or None
    utm_medium = _strip_nohtml(payload.get('utm_medium'), max_len=120) or None
    utm_campaign = _strip_nohtml(payload.get('utm_campaign'), max_len=120) or None

    # Validaciones obligatorias (sin “falsos vacíos”).
    if not name:
        return _apply_cors(jsonify({'success': False, 'message': 'Nombre es requerido.'})), 400
    if not program_slug_body:
        return _apply_cors(jsonify({'success': False, 'message': 'program_slug es requerido.'})), 400
    if program_slug_body != slug_norm:
        return _apply_cors(jsonify({'success': False, 'message': 'program_slug inválido para este programa.'})), 400
    if not email or '@' not in email or len(email) > 255 or re.search(r'\s', email):
        return _apply_cors(jsonify({'success': False, 'message': 'Email es requerido y debe ser válido.'})), 400
    if not phone or len(phone) < 6 or len(re.sub(r'\D+', '', phone)) < 6:
        return _apply_cors(jsonify({'success': False, 'message': 'Teléfono es requerido.'})), 400

    # Anti-spam básico adicional para message (no HTML/script).
    if message and ('<' in (message or '') or '>' in (message or '')):
        return _apply_cors(jsonify({'success': False, 'message': 'Mensaje inválido.'})), 400

    oid = resolve_current_organization()
    if oid is None:
        return _apply_cors(jsonify({'success': False, 'message': 'organization_not_resolved'})), 503

    program = (
        AcademicProgram.query.filter_by(slug=slug_norm, organization_id=int(oid), status='published')
        .order_by(AcademicProgram.id.asc())
        .first()
    )
    if program is None:
        return _apply_cors(jsonify({'success': False, 'message': 'program_not_found'})), 404

    if not program_has_public_academic_pdf(program):
        return _apply_cors(jsonify({'success': False, 'message': 'pdf_not_available'})), 404

    # Validar que exista el archivo local cuando está en EN1 (no confundir con URL vacía).
    stored_path = _stored_pdf_filesystem_path(getattr(program, 'academic_program_pdf_url', '') or '')
    if stored_path is None:
        # Si el URL era externa https, program_has_public_academic_pdf ya lo permitiría; en esa fase mínima
        # tratamos como no disponible (evita “link sin archivo”).
        return _apply_cors(jsonify({'success': False, 'message': 'pdf_not_available'})), 404

    from nodeone.core.db import db
    from nodeone.modules.academic_enrollment.pdf_lead_confirmation import (
        assign_confirmation_token,
        send_confirmation_email,
    )
    from nodeone.services.academic_program_pdf_lead_schema import ensure_academic_program_pdf_lead_schema

    ensure_academic_program_pdf_lead_schema(db, db.engine)

    base_url = request.host_url.rstrip('/')

    existing = (
        AcademicProgramPdfLead.query.filter_by(
            organization_id=int(oid),
            program_id=program.id,
            email=email,
        )
        .filter(AcademicProgramPdfLead.status.in_(('pending', 'new')))
        .order_by(AcademicProgramPdfLead.id.desc())
        .first()
    )

    if existing is not None:
        lead = existing
        lead.name = name
        lead.phone = phone
        lead.country = country
        lead.company = company
        lead.message = message
        lead.source = source[:120]
        lead.utm_source = utm_source
        lead.utm_medium = utm_medium
        lead.utm_campaign = utm_campaign
        lead.ip_address = (request.headers.get('X-Forwarded-For') or request.remote_addr or '')[:64]
        lead.user_agent = (request.headers.get('User-Agent') or '')[:500]
    else:
        lead = AcademicProgramPdfLead(
            organization_id=int(oid),
            program_id=program.id,
            program_slug=slug_norm,
            name=name,
            email=email,
            phone=phone,
            country=country,
            company=company,
            message=message,
            source=source[:120],
            utm_source=utm_source,
            utm_medium=utm_medium,
            utm_campaign=utm_campaign,
            ip_address=(request.headers.get('X-Forwarded-For') or request.remote_addr or '')[:64],
            user_agent=(request.headers.get('User-Agent') or '')[:500],
            status='pending',
        )
        db.session.add(lead)

    assign_confirmation_token(lead)
    db.session.commit()

    sent_ok, send_err = send_confirmation_email(lead, program, base_url=base_url)
    if not sent_ok:
        current_app.logger.warning(
            '[pdf_lead] email no enviado lead_id=%s err=%s', lead.id, send_err
        )
        if send_err in ('smtp_not_configured', 'smtp_credentials_missing', 'email_service_unavailable'):
            user_msg = (
                'El servidor de correo de la plataforma no está configurado. '
                'Contactá al administrador (Configuración → Email / SMTP).'
            )
        else:
            user_msg = (
                'No pudimos enviar el correo de confirmación. '
                'Revisá que el email sea correcto e intentá de nuevo en unos minutos.'
            )
        return _apply_cors(jsonify({'success': False, 'message': user_msg})), 503

    return _apply_cors(
        jsonify(
            {
                'success': True,
                'requires_email_confirmation': True,
                'message': (
                    'Te enviamos un correo de confirmación. '
                    'Abrí el enlace del mensaje para descargar el programa académico. '
                    'Revisá también la carpeta de spam.'
                ),
            }
        )
    ), 200
