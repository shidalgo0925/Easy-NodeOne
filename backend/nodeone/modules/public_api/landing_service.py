"""Lógica para reservas / solicitudes desde landing externo (OCI)."""

from __future__ import annotations

import json
import os
import re
import secrets
from datetime import datetime, timedelta

from sqlalchemy.exc import IntegrityError

from nodeone.core.db import db
from models.catalog import Service
from models.users import User
from nodeone.modules.sales.models import Quotation, QuotationLine
from nodeone.modules.workshop.models import WorkshopVehicle
from nodeone.services.tax_calculation import compute_line_amounts
from nodeone.modules.accounting.models import Tax
from werkzeug.security import generate_password_hash

from .landing_pure import (
    normalize_idempotency_key,
    parse_preferred_start_utc,
    verify_landing_api_key,
)


def landing_config():
    """API key, organization_id y orígenes CORS permitidos (coma-separados)."""
    key = (os.environ.get('PUBLIC_LANDING_API_KEY') or '').strip()
    org_raw = (os.environ.get('PUBLIC_LANDING_ORG_ID') or '').strip()
    org_id = int(org_raw) if org_raw.isdigit() else None
    origins = [
        x.strip()
        for x in (os.environ.get('PUBLIC_LANDING_ALLOWED_ORIGINS') or '').split(',')
        if x.strip()
    ]
    return key, org_id, origins


def apply_cors_headers(response, origins: list[str]):
    from flask import request

    req_origin = request.headers.get('Origin')
    if req_origin and origins and req_origin in origins:
        response.headers['Access-Control-Allow-Origin'] = req_origin
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = (
            'Content-Type, Authorization, X-Landing-Api-Key, Idempotency-Key, X-Request-Id'
        )
        response.headers['Access-Control-Max-Age'] = '600'
    return response


def extract_api_key_from_request(request) -> str:
    h = request.headers.get('X-Landing-Api-Key', '').strip()
    if h:
        return h
    auth = (request.headers.get('Authorization') or '').strip()
    if auth.lower().startswith('bearer '):
        return auth[7:].strip()
    return ''


def _split_name(full: str) -> tuple[str, str]:
    full = (full or '').strip()
    if not full:
        return 'Cliente', 'Landing'
    parts = full.split(None, 1)
    if len(parts) == 1:
        return parts[0], '—'
    return parts[0], parts[1]


def _norm_email(email: str) -> str:
    return (email or '').strip().lower()


def _norm_phone(phone: str) -> str:
    return re.sub(r'\s+', '', (phone or '').strip())


def find_or_create_customer(
    *,
    organization_id: int,
    name: str,
    email: str,
    phone: str,
) -> tuple[User, bool]:
    """Devuelve (usuario, created). Email único global en User."""
    email_n = _norm_email(email)
    phone_n = _norm_phone(phone)
    if not email_n or '@' not in email_n:
        raise ValueError('email_invalid')
    if not phone_n or len(phone_n) < 6:
        raise ValueError('phone_invalid')

    user = User.query.filter_by(email=email_n).first()
    if user:
        if int(user.organization_id) != int(organization_id):
            raise ValueError('email_other_org')
        if phone_n and not (user.phone or '').strip():
            user.phone = phone_n
        fn, ln = _split_name(name)
        if fn and fn != 'Cliente':
            user.first_name = fn[:50]
            user.last_name = (ln or '—')[:50]
        return user, False

    fn, ln = _split_name(name)
    user = User(
        email=email_n,
        first_name=fn[:50],
        last_name=(ln or '—')[:50],
        phone=phone_n[:20],
        organization_id=organization_id,
        is_active=True,
        is_admin=False,
        is_advisor=False,
        email_verified=False,
    )
    temp_pw = secrets.token_urlsafe(24)
    user.password_hash = generate_password_hash(temp_pw)
    db.session.add(user)
    db.session.flush()
    return user, True


def find_or_create_vehicle(
    *,
    organization_id: int,
    customer_id: int,
    brand: str,
    model: str,
    year: int | None,
    color: str,
    plate: str,
) -> tuple[WorkshopVehicle, bool]:
    plate_clean = (plate or '').strip()[:32]
    brand = (brand or '').strip()[:80] or '—'
    model = (model or '').strip()[:80] or '—'
    color = (color or '').strip()[:60] or '—'

    q = WorkshopVehicle.query.filter_by(
        organization_id=organization_id,
        customer_id=customer_id,
    )
    if plate_clean:
        existing = q.filter_by(plate=plate_clean).first()
        if existing:
            if year is not None:
                existing.year = year
            existing.brand = brand
            existing.model = model
            existing.color = color
            return existing, False

    v = WorkshopVehicle(
        organization_id=organization_id,
        customer_id=customer_id,
        plate=plate_clean or 'SIN-PLACA',
        brand=brand,
        model=model,
        year=year,
        color=color,
        vin='',
    )
    db.session.add(v)
    db.session.flush()
    return v, True


def _next_quotation_number(organization_id: int) -> str:
    cnt = Quotation.query.filter_by(organization_id=organization_id).count() + 1
    return f'Q-{cnt:04d}'


def _ensure_sales_tables():
    Quotation.__table__.create(db.engine, checkfirst=True)
    QuotationLine.__table__.create(db.engine, checkfirst=True)
    Tax.__table__.create(db.engine, checkfirst=True)
    WorkshopVehicle.__table__.create(db.engine, checkfirst=True)


def create_draft_quotation_for_service(
    *,
    organization_id: int,
    customer_id: int,
    service: Service,
    notes: str | None,
) -> Quotation:
    _ensure_sales_tables()
    q = Quotation(
        organization_id=organization_id,
        number=_next_quotation_number(organization_id),
        customer_id=customer_id,
        crm_lead_id=None,
        date=datetime.utcnow(),
        validity_date=None,
        payment_terms=None,
        status='draft',
        total=0.0,
        tax_total=0.0,
        grand_total=0.0,
        created_by=None,
    )
    db.session.add(q)
    db.session.flush()

    desc = (service.name or 'Servicio')[:500]
    extra = (notes or '').strip()
    if extra:
        desc = f'{desc} — Nota cliente: {extra[:400]}'

    tax_id = getattr(service, 'default_tax_id', None)
    qty = 1.0
    pu = float(service.base_price or 0.0)
    tax = Tax.query.filter_by(id=tax_id, organization_id=organization_id).first() if tax_id else None
    subtotal, line_total, tax_amt = compute_line_amounts(qty, pu, tax)

    ln = QuotationLine(
        quotation_id=q.id,
        product_id=service.id,
        description=desc,
        quantity=qty,
        price_unit=pu,
        tax_id=tax_id,
        subtotal=subtotal,
        total=line_total,
    )
    db.session.add(ln)
    q.total = round(subtotal, 2)
    q.tax_total = round(tax_amt, 2)
    q.grand_total = round(line_total, 2)
    return q


def serialize_public_service(s: Service) -> dict:
    return {
        'id': s.id,
        'name': s.name,
        'description': (s.description or '')[:2000],
        'base_price': float(s.base_price or 0),
        'service_type': getattr(s, 'service_type', None) or 'AGENDABLE',
        'membership_type': getattr(s, 'membership_type', None) or '',
    }


def _rate_limit_max(env_name: str, default: int) -> int:
    raw = (os.environ.get(env_name) or str(default)).strip()
    try:
        return max(0, int(raw))
    except ValueError:
        return default


def rate_limit_post_max() -> int:
    return _rate_limit_max('PUBLIC_LANDING_RATE_LIMIT_POST', 30)


def rate_limit_get_max() -> int:
    return _rate_limit_max('PUBLIC_LANDING_RATE_LIMIT_GET', 120)


def ensure_landing_aux_tables():
    from .models import LandingApiRateBucket, LandingPublicIdempotency

    LandingPublicIdempotency.__table__.create(db.engine, checkfirst=True)
    LandingApiRateBucket.__table__.create(db.engine, checkfirst=True)


def client_ip_for_rate_limit() -> str:
    from flask import request

    xff = (request.headers.get('X-Forwarded-For') or '').split(',')[0].strip()
    if xff:
        return xff[:64]
    return (request.remote_addr or 'unknown')[:64]


def check_rate_limit(*, kind: str) -> str | None:
    """
    None si se permite la petición.
    Retorna código corto ('rate_limited') si se supera el tope (contador persistido en BD).
    """
    if kind == 'post':
        limit = rate_limit_post_max()
    else:
        limit = rate_limit_get_max()
    if limit <= 0:
        return None

    ensure_landing_aux_tables()
    from .models import LandingApiRateBucket

    ip = client_ip_for_rate_limit()
    bucket = datetime.utcnow().strftime('%Y%m%d%H%M')
    norm_kind = 'post' if kind == 'post' else 'get'

    for _attempt in range(4):
        try:
            row = LandingApiRateBucket.query.filter_by(
                ip_address=ip, bucket_minute=bucket, kind=norm_kind
            ).first()
            if row is not None:
                if int(row.hit_count or 0) >= limit:
                    return 'rate_limited'
                row.hit_count = int(row.hit_count or 0) + 1
            else:
                db.session.add(
                    LandingApiRateBucket(
                        ip_address=ip,
                        bucket_minute=bucket,
                        kind=norm_kind,
                        hit_count=1,
                    )
                )
            db.session.commit()
            return None
        except IntegrityError:
            db.session.rollback()
            continue
    return 'rate_limited'


def get_idempotent_cached_response(organization_id: int, key: str) -> tuple[int, dict] | None:
    ensure_landing_aux_tables()
    from .models import LandingPublicIdempotency

    row = LandingPublicIdempotency.query.filter_by(
        organization_id=organization_id, idempotency_key=key
    ).first()
    if not row:
        return None
    try:
        body = json.loads(row.response_body)
        if not isinstance(body, dict):
            return None
        return int(row.response_status), body
    except (json.JSONDecodeError, TypeError, ValueError):
        return None


def store_idempotent_response(organization_id: int, key: str, status: int, body: dict) -> None:
    ensure_landing_aux_tables()
    from .models import LandingPublicIdempotency

    row = LandingPublicIdempotency(
        organization_id=organization_id,
        idempotency_key=key,
        response_status=status,
        response_body=json.dumps(body, ensure_ascii=False, default=str),
    )
    db.session.add(row)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()


def landing_appointment_creation_enabled() -> bool:
    return (os.environ.get('PUBLIC_LANDING_CREATE_APPOINTMENT') or '1').strip().lower() not in (
        '0',
        'false',
        'no',
        'off',
    )


def try_create_appointment_for_landing(
    *,
    organization_id: int,
    service: Service,
    user: User,
    preferred_date: str,
    preferred_time: str,
    intent: str,
    request_for_log,
):
    """
    Crea Appointment en cola (PENDIENTE, sin slot) como request_appointment.
    Retorna (appointment|None, skip_reason).
    skip_reason None solo si se creó la cita.
    """
    from models.appointments import (
        ActivityLog,
        Appointment,
        AppointmentAdvisor,
        AppointmentType,
        Advisor,
    )
    from models.communications import Notification

    if intent != 'book':
        return None, 'intent_not_book'
    if not landing_appointment_creation_enabled():
        return None, 'disabled_by_env'
    if not (preferred_date or preferred_time).strip():
        return None, 'missing_preferred_datetime'

    at_id = service.appointment_type_id or service.diagnostic_appointment_type_id
    if not at_id:
        return None, 'no_appointment_type_on_service'

    start_dt = parse_preferred_start_utc(preferred_date, preferred_time)
    if not start_dt:
        return None, 'invalid_preferred_datetime'
    if start_dt <= datetime.utcnow():
        return None, 'preferred_datetime_not_future'

    appointment_type = AppointmentType.query.filter_by(
        id=at_id, organization_id=organization_id, is_active=True
    ).first()
    if not appointment_type:
        return None, 'appointment_type_not_found'

    assignment = AppointmentAdvisor.query.filter_by(
        appointment_type_id=at_id,
        is_active=True,
    ).first()
    if not assignment:
        return None, 'no_advisor_for_appointment_type'
    advisor_id = assignment.advisor_id

    membership = user.get_active_membership() if hasattr(user, 'get_active_membership') else None
    membership_type = membership.membership_type if membership else 'basic'
    pricing = appointment_type.pricing_for_membership(membership_type)
    base_price = float(pricing.get('base_price', 0.0) or 0.0)
    final_price = float(pricing.get('final_price', 0.0) or 0.0)
    discount = max(0.0, base_price - final_price)
    duration = int(appointment_type.duration_minutes or 60)
    end_dt = start_dt + timedelta(minutes=duration)

    appointment = Appointment(
        appointment_type_id=at_id,
        organization_id=organization_id,
        advisor_id=advisor_id,
        slot_id=None,
        user_id=user.id,
        service_id=service.id,
        membership_type=membership_type,
        is_group=False,
        start_datetime=start_dt,
        end_datetime=end_dt,
        status='PENDIENTE',
        is_initial_consult=True,
        advisor_confirmed=False,
        base_price=base_price,
        final_price=final_price,
        discount_applied=discount,
        user_notes=(f'Solicitud desde landing — {service.name or "servicio"}')[:500],
    )
    db.session.add(appointment)
    db.session.flush()

    ActivityLog.log_activity(
        user.id,
        'landing_book_appointment',
        'appointment',
        appointment.id,
        f'Landing: solicitud de cita {appointment.reference}',
        request_for_log,
    )

    advisor = Advisor.query.get(advisor_id)
    advisor_user_id = advisor.user_id if advisor and advisor.user_id else None
    if advisor_user_id:
        try:
            db.session.add(
                Notification(
                    user_id=advisor_user_id,
                    notification_type='appointment_request',
                    title='Nueva solicitud (landing)',
                    message=(
                        f'{user.first_name} {user.last_name} solicita cita para '
                        f'{start_dt.strftime("%d/%m/%Y %H:%M")}. Servicio: {service.name}.'
                    ),
                )
            )
        except Exception:
            pass

    try:
        from app import NotificationEngine
        from models.users import User as UserModel

        advisor_user = UserModel.query.get(advisor_user_id) if advisor_user_id else None
        if advisor_user:
            NotificationEngine.notify_appointment_new_to_advisor(
                appointment, user, advisor_user, service
            )
    except Exception:
        pass

    return appointment, None


def send_verification_for_new_portal_user(user, *, user_was_created: bool) -> tuple[bool, str | None]:
    """Si aplica política y el usuario es nuevo, envía email de verificación (usa app.send_verification_email)."""
    if not user_was_created:
        return False, None
    flag = (os.environ.get('PUBLIC_LANDING_SEND_VERIFICATION_EMAIL') or '1').strip().lower()
    if flag in ('0', 'false', 'no', 'off'):
        return False, None
    import app as M

    ok, err = M.send_verification_email(user)
    return bool(ok), err
