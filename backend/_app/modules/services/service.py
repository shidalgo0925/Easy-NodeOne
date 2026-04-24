# Lógica de servicios (usuario): listado, solicitud de cita, calendario API.
from __future__ import annotations

from datetime import datetime, timedelta
import json
import os
import re
import unicodedata

from app import (
    Service,
    ServiceCategory,
    ServicePricingRule,
    AppointmentAdvisor,
    AppointmentSlot,
    Advisor,
    Appointment,
    db,
)
from sqlalchemy.orm import joinedload

from . import repository


# ---- Miniatura de tarjeta: misma foto que el landing (/opt/easynodeone/landings/relatic-public/src/data/servicesCatalog.ts) ----
def _q_card() -> str:
    return "auto=format&fit=crop&w=400&q=80"


def _norm_name(s: str) -> str:
    return " ".join((s or "").split())


def _fold_ascii(s: str) -> str:
    """Minusculas + sin tildes/diacríticos: empareja 'Artículos' con 'articulos'."""
    s = unicodedata.normalize("NFD", _norm_name(s))
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s.lower()


# Misma imagen de respaldo que el menú en servicesCatalog (cuando no matchea etiqueta)
_DEFAULT_LANDING: str = f"https://images.unsplash.com/photo-1503676260728-1c00da094a0b?{_q_card()}"


_LANDING_IMAGES: dict[str, str] = {
    "Publicación de artículos": f"https://images.unsplash.com/photo-1456513080510-7bf3a84b82f8?{_q_card()}",
    "Revistas indexadas": f"https://images.unsplash.com/photo-1507842217343-583bb7270b66?{_q_card()}",
    "Libros digitales": f"https://images.unsplash.com/photo-1524995997946-a1c2e315a42f?{_q_card()}",
    "Carteles científicos": f"https://images.unsplash.com/photo-1523240795612-9a054b0db644?{_q_card()}",
    "Asesorías": f"https://images.unsplash.com/photo-1521737604893-d14cc237f11d?{_q_card()}",
    "Postdoctorados": f"https://images.unsplash.com/photo-1522071820081-009f0129c71c?{_q_card()}",
}

_CATALOG_NAME_TO_LANDING: dict[str, str] = {
    "Asesoría, Vinculación a revistas y editoriales": "Asesorías",
    "Registro de Hoja de Vida": "Asesorías",
    "Artículos/Revistas": "Publicación de artículos",
    "Artículos / Revistas": "Publicación de artículos",
    "Carteles": "Carteles científicos",
    "Carteles científicos": "Carteles científicos",
    "Libros digitales": "Libros digitales",
    "Cursos": "Postdoctorados",
    "Indexación de revistas": "Revistas indexadas",
    "Organización de eventos": "Carteles científicos",
}

_LANDING_LOOKUP: dict[str, str] = {}
for _alias, _lk in _CATALOG_NAME_TO_LANDING.items():
    _LANDING_LOOKUP[_norm_name(_alias).casefold()] = _lk
    _LANDING_LOOKUP[_fold_ascii(_alias)] = _lk
for _k in _LANDING_IMAGES:
    _LANDING_LOOKUP[_norm_name(_k).casefold()] = _k
    _LANDING_LOOKUP[_fold_ascii(_k)] = _k


def _keyword_landing_key(name: str) -> str | None:
    """Heurística por palabras (nombres distintos a los del landing Relatic)."""
    a = _fold_ascii(name)
    a = re.sub(r"[^a-z0-9\s]", " ", a)
    a = re.sub(r"\s+", " ", a).strip()
    if "index" in a and "revist" in a:
        return "Revistas indexadas"
    if "articul" in a and "revist" in a:
        return "Publicación de artículos"
    if "cartel" in a or "posters" in a or "poster" in a:
        return "Carteles científicos"
    if "libro" in a and "digital" in a:
        return "Libros digitales"
    if ("hoja" in a and "vida" in a) or ("registro" in a and "vida" in a):
        return "Asesorías"
    if "asesor" in a or "vinculacion" in a or "vinculación" in name.lower():
        return "Asesorías"
    if "evento" in a or "organizacion" in a or "organización" in name.lower():
        return "Carteles científicos"
    if "curso" in a or "taller" in a or "diplomado" in a or "neuro" in a:
        return "Postdoctorados"
    if "publicacion" in a or "publicación" in name.lower():
        return "Publicación de artículos"
    return None


def resolve_service_card_image_url(name: str | None, stored_url: str | None) -> str:
    """
    URL de la miniatura: primero `image_url` en BD (admin), luego mapeo landing por nombre/alias,
    luego heurística por palabras, y al final la misma foto genérica del menú en servicesCatalog.
    """
    s = (stored_url or "").strip()
    if s and s.lower() not in ("none", "null", "0", "-"):
        return s
    n = (name or "").strip()
    if not n:
        return _DEFAULT_LANDING
    ck = _norm_name(n).casefold()
    key = _LANDING_LOOKUP.get(ck) or _LANDING_LOOKUP.get(_fold_ascii(n))
    if not key:
        key = _keyword_landing_key(n)
    if not key or key not in _LANDING_IMAGES:
        return _DEFAULT_LANDING
    return _LANDING_IMAGES.get(key) or _DEFAULT_LANDING


def _absolute_public_external_link(href):
    """
    Catálogo / services: si ``external_link`` es ruta en el mismo sitio (/...) y existe env
    ``BASE_URL`` (portal NodeOne público), devolver URL absoluta. Así los CTAs no apuntan
    por error a Moodle u otro host donde /inscripcion/ no existe en esta app.
    """
    if not href:
        return href
    h = str(href).strip()
    if h.startswith('//') or h.startswith('http://') or h.startswith('https://'):
        return h
    base = (os.environ.get('BASE_URL') or '').strip().rstrip('/')
    if not base:
        return h
    if h.startswith('/'):
        return base + h
    return f'{base}/{h}'


# Fallback cuando no hay tabla membership_plan (incl. basic: sin pago, servicios con precio 0 o incluidos según reglas)
PLANS_INFO_FALLBACK = {
    'basic': {
        'name': 'BÁSICO',
        'price': '$0',
        'badge': 'Gratis · acceso a servicios del plan gratuito',
        'color': 'bg-success',
    },
    'personal': {'name': 'PERSONAL', 'price': '$149/año', 'badge': 'Inicia tu crecimiento', 'color': 'bg-success'},
    'emprendedor': {'name': 'EMPRENDEDOR', 'price': '$449/año', 'badge': 'Desarrolla tu negocio', 'color': 'bg-info'},
    'ejecutivo': {'name': 'EJECUTIVO', 'price': '$949/año', 'badge': 'Liga Empresarial', 'color': 'bg-primary'},
    'admin': {'name': 'ADMIN', 'price': '$0', 'badge': 'Plataforma', 'color': 'bg-secondary'},
}


def _get_plans_info(user=None, organization_id=None):
    """Etiquetas de planes para /services: BD (MembershipPlan) + fallback para slugs sin fila en BD."""
    fb = PLANS_INFO_FALLBACK.copy()
    try:
        from app import MembershipPlan, _enable_multi_tenant_catalog

        oid = None
        if organization_id is not None:
            try:
                oid = int(organization_id)
            except (TypeError, ValueError):
                oid = None
        elif user is not None and _enable_multi_tenant_catalog():
            oid = int(getattr(user, 'organization_id', None) or 1)
        out = MembershipPlan.get_plans_info(organization_id=oid)
        if not out:
            return fb
        merged = dict(fb)
        merged.update(out)
        return merged
    except Exception:
        return fb


def get_services_page_data(user=None, organization_id=None):
    """
    Datos para la página /services.
    organization_id: si se pasa (p. ej. visitante anónimo en subdominio tenant), filtra catálogo por esa org.
    """
    if user is not None and getattr(user, 'is_authenticated', False):
        active_membership = user.get_active_membership()
    else:
        active_membership = None
    membership_type = active_membership.membership_type if active_membership else 'basic'

    org_kw = {}
    if organization_id is not None:
        org_kw['organization_id'] = int(organization_id)

    categories = repository.get_active_categories(**org_kw)
    all_services = repository.get_active_services(**org_kw)
    from app import MembershipPlan, default_organization_id

    _oid_mp = int(organization_id) if organization_id is not None else int(
        getattr(user, 'organization_id', None) or default_organization_id()
    )
    _paid_slugs = [
        p.slug
        for p in MembershipPlan.query.filter_by(organization_id=_oid_mp, is_active=True).order_by(
            MembershipPlan.display_order, MembershipPlan.level
        )
        if (p.level or 0) > 0 and (p.slug or '') not in ('admin', 'basic')
    ]
    if not _paid_slugs:
        _paid_slugs = ['personal', 'emprendedor', 'ejecutivo']

    services_by_plan = {}
    for service in all_services:
        pricing_rules = ServicePricingRule.query.filter_by(
            service_id=service.id, is_active=True
        ).all()
        available_plans = set()
        if service.membership_type:
            smt = (service.membership_type or '').strip().lower()
            if smt == 'basic':
                # Básico: sección explícita en /services (antes solo se replicaba a planes de pago; no existía clave "basic")
                available_plans.add('basic')
                for ps in _paid_slugs:
                    available_plans.add(ps)
            else:
                available_plans.add(service.membership_type)
        for rule in pricing_rules:
            available_plans.add(rule.membership_type)
        if not available_plans:
            mt = (getattr(service, 'membership_type', None) or 'basic')
            if isinstance(mt, str):
                mt = mt.strip()
            available_plans.add(mt if mt else 'basic')
        user_pricing = service.pricing_for_membership(membership_type)
        at_id = service.appointment_type_id or getattr(service, 'diagnostic_appointment_type_id', None)
        advisors_list = []
        if at_id:
            for aa in AppointmentAdvisor.query.filter_by(appointment_type_id=at_id, is_active=True).all():
                if aa.advisor and getattr(aa.advisor, 'is_active', True) and aa.advisor.user:
                    advisors_list.append({
                        'id': aa.advisor.id,
                        'name': f"{aa.advisor.user.first_name} {aa.advisor.user.last_name}"
                    })
        from nodeone.services.commercial_flow import (
            flow_cta_labels,
            flow_type_badge_label,
            resolve_commercial_flow_type,
        )

        _flow = resolve_commercial_flow_type(service, user_pricing)
        _cta_label, _cta_hint = flow_cta_labels(_flow)
        service_data = {
            'id': service.id,
            'name': service.name,
            'description': service.description,
            'icon': service.icon or 'fas fa-cog',
            'image_url': resolve_service_card_image_url(service.name, service.image_url),
            'external_link': _absolute_public_external_link(service.external_link),
            'base_price': service.base_price,
            'pricing': user_pricing,
            'requires_diagnostic_appointment': service.requires_diagnostic_appointment if service.requires_diagnostic_appointment is not None else False,
            'appointment_type_id': service.appointment_type_id,
            'requires_appointment': service.requires_appointment(),
            'is_free': service.is_free_service(membership_type),
            'service_type': getattr(service, 'service_type', 'AGENDABLE') or 'AGENDABLE',
            'advisors': advisors_list,
            'diagnostic_appointment_type_id': getattr(service, 'diagnostic_appointment_type_id', None),
            'program_slug': (getattr(service, 'program_slug', None) or '').strip(),
            'commercial_flow_type': _flow,
            'commercial_flow_badge': flow_type_badge_label(_flow),
            'cta_label': _cta_label,
            'cta_hint': _cta_hint,
        }
        for plan_type in available_plans:
            if plan_type not in services_by_plan:
                services_by_plan[plan_type] = []
            services_by_plan[plan_type].append(service_data)
    oid_plans = organization_id
    if oid_plans is None and user is not None and getattr(user, 'is_authenticated', False):
        oid_plans = getattr(user, 'organization_id', None)

    # Orden estable: Básico primero (gratis), luego planes de pago frecuentes, luego el resto alfabéticamente
    _canonical_plan_order = ('basic', 'personal', 'emprendedor', 'ejecutivo', 'pro', 'premium', 'deluxe', 'corporativo', 'admin')
    _present = list(services_by_plan.keys())
    plan_slugs_ordered = [s for s in _canonical_plan_order if s in _present]
    for s in sorted(_present):
        if s not in plan_slugs_ordered:
            plan_slugs_ordered.append(s)

    # Una entrada por servicio (orden: primer plan donde aparece). Evita triplicar tarjetas en la vista «Todos».
    _seen_service_ids = set()
    services_unique = []
    for _slug in plan_slugs_ordered:
        for _svc in services_by_plan.get(_slug) or []:
            _sid = _svc.get('id')
            if _sid is None or _sid in _seen_service_ids:
                continue
            _seen_service_ids.add(_sid)
            services_unique.append(_svc)

    featured_events = _featured_events_for_services_rail(
        organization_id=organization_id,
        user=user,
        membership_type=membership_type,
        limit=5,
    )

    return {
        'membership': active_membership,
        'services_by_plan': services_by_plan,
        'services_unique': services_unique,
        'featured_events': featured_events,
        'plans_info': _get_plans_info(user, organization_id=oid_plans),
        'categories': categories,
        'user_membership_type': membership_type,
        'membership_type': membership_type,
        'plan_slugs_ordered': plan_slugs_ordered,
    }


def _featured_events_for_services_rail(*, organization_id, user, membership_type, limit: int = 5):
    """
    Carril opcional en /services: pocos eventos próximos (destacados primero).
    No reemplaza el listado principal: ``GET /events``.
    """
    from flask import url_for

    from app import default_organization_id
    from nodeone.services.events_portal import get_portal_featured_events

    out = []
    try:
        _oid = int(organization_id) if organization_id is not None else int(
            getattr(user, 'organization_id', None) or default_organization_id()
        )
        rows = get_portal_featured_events(organization_id=_oid, user=user, limit=limit)
        for ev in rows:
            pr = ev.pricing_for_membership(membership_type)
            cu = ev.cover_url()
            img = _absolute_public_external_link(cu) if cu else None
            durl = url_for('events.event_detail', slug=ev.slug)
            desc = (ev.summary or ev.description or '').strip()
            if len(desc) > 400:
                desc = desc[:397] + '...'
            out.append(
                {
                    'kind': 'event',
                    'id': ev.id,
                    'slug': ev.slug,
                    'name': ev.title,
                    'description': desc,
                    'image_url': img,
                    'icon': 'fas fa-calendar-day',
                    'format': (getattr(ev, 'format', None) or 'virtual'),
                    'pricing': {
                        'base_price': float(pr.get('base_price') or 0.0),
                        'final_price': float(pr.get('final_price') or 0.0),
                    },
                    'start_date': ev.start_date,
                    'category': (ev.category or 'general').strip(),
                    'currency': (ev.currency or 'USD').strip(),
                    'capacity': ev.capacity,
                    'commercial_flow_type': 'EVENT',
                    'commercial_flow_badge': 'Evento',
                    'cta_label': 'Inscribirse',
                    'cta_hint': 'Flyer completo y datos en la ficha del evento.',
                    'detail_url': durl,
                }
            )
    except Exception as e:
        print(f'⚠️ _featured_events_for_services_rail: {e}')
    return out


def get_request_appointment_data(service_id, user, selected_advisor_id=None, return_url=None):
    """
    Devuelve (data_dict, None) para render o (None, (redirect_url, code)) en caso de error.
    """
    from flask import url_for
    service = repository.get_service_or_404(service_id)
    if not service.is_active:
        return None, (url_for('services.list'), 'Este servicio no está disponible.', 'error')
    if not service.requires_appointment():
        return None, (url_for('services.list'), 'Este servicio no requiere cita.', 'info')
    membership = user.get_active_membership()
    if not membership:
        return None, (url_for('services.list'), 'Necesitas una membresía activa para solicitar citas.', 'warning')
    membership_type = membership.membership_type
    # Si el precio de catálogo es $0 pero el servicio sí requiere cita (agenda), permitir reservar.
    if service.is_free_service(membership_type) and not service.requires_appointment():
        return None, (url_for('services.list'), 'Este servicio es gratuito y no requiere cita con pago.', 'info')
    appointment_type = repository.get_appointment_type(service.appointment_type_id)
    if not appointment_type or not appointment_type.is_active:
        return None, (url_for('services.list'), 'El tipo de cita asociado no está disponible.', 'error')
    pricing = service.pricing_for_appointment_booking(membership_type, user.id)
    deposit_info = service.calculate_deposit_from_pricing(pricing)
    today = datetime.utcnow().date()
    future_date = today + timedelta(days=90)
    advisors_list = []
    advisors_with_schedules = set()
    for assignment in repository.get_advisor_assignments(service.appointment_type_id):
        if not assignment.is_active or not assignment.advisor.is_active:
            continue
        advisor = assignment.advisor
        aid = advisor.id
        if not repository.advisor_has_availability(aid, service.appointment_type_id, today, future_date):
            continue
        advisors_list.append({
            'id': advisor.id,
            'name': f"{advisor.user.first_name} {advisor.user.last_name}" if advisor.user else 'Asesor',
            'bio': advisor.bio,
            'specializations': advisor.specializations,
            'photo_url': advisor.photo_url
        })
        advisors_with_schedules.add(aid)
    if not advisors_list:
        return None, (url_for('services.list'), 'Este servicio no tiene asesores con horarios configurados. Por favor, contacta al administrador.', 'error')
    # Generar slots si faltan
    from nodeone.modules.appointments.slot_generation import generate_slots_from_availability
    for aid in advisors_with_schedules:
        try:
            if repository.count_slots(aid, service.appointment_type_id, 30) < 10:
                try:
                    generate_slots_from_availability(aid, service.appointment_type_id, days_ahead=30)
                except Exception:
                    pass
        except Exception:
            continue
    slots = AppointmentSlot.query.options(
        joinedload(AppointmentSlot.advisor).joinedload(Advisor.user)
    ).filter(
        AppointmentSlot.appointment_type_id == service.appointment_type_id,
        AppointmentSlot.start_datetime >= datetime.utcnow(),
        AppointmentSlot.start_datetime <= datetime.utcnow() + timedelta(days=30),
        AppointmentSlot.is_available == True
    ).order_by(AppointmentSlot.start_datetime.asc()).limit(200).all()
    slots_data = []
    for slot in slots:
        try:
            advisor_name = 'Asesor'
            if slot.advisor:
                advisor_name = (f"{slot.advisor.user.first_name} {slot.advisor.user.last_name}" if slot.advisor.user else f"Asesor #{slot.advisor.id}")
            slots_data.append({
                'id': slot.id,
                'advisor_id': slot.advisor_id,
                'advisor_name': advisor_name,
                'start_datetime': slot.start_datetime.isoformat() if slot.start_datetime else None,
                'end_datetime': slot.end_datetime.isoformat() if slot.end_datetime else None,
                'capacity': slot.capacity if slot.capacity else 1,
                'remaining_seats': slot.remaining_seats() if hasattr(slot, 'remaining_seats') else 1
            })
        except Exception:
            continue
    return {
        'service': service,
        'appointment_type': appointment_type,
        'advisors': advisors_list,
        'selected_advisor_id': selected_advisor_id,
        'membership': membership,
        'pricing': pricing,
        'deposit_info': deposit_info,
        'available_slots_json': json.dumps(slots_data),
        'available_slots': slots,
        'user': user,
        'return_url': return_url,
    }, None


def finalize_free_slot_appointment_booking(service, user, slot, case_description, membership_type, pricing):
    """Primera cita con slot a $0: confirma cita y reserva hueco sin checkout."""
    advisor_id = slot.advisor_id
    appointment_type_id = service.appointment_type_id
    base_price = float(pricing.get('base_price') or 0.0)
    final_price = float(pricing.get('final_price') or 0.0)
    discount_applied = max(0.0, base_price - final_price)

    appointment = Appointment(
        appointment_type_id=appointment_type_id,
        organization_id=int(getattr(service, 'organization_id', None) or 1),
        advisor_id=advisor_id,
        slot_id=slot.id,
        service_id=service.id,
        payment_id=None,
        user_id=user.id,
        membership_type=membership_type,
        start_datetime=slot.start_datetime,
        end_datetime=slot.end_datetime,
        status='CONFIRMADA',
        is_initial_consult=False,
        base_price=base_price,
        final_price=final_price,
        discount_applied=discount_applied,
        payment_status='paid',
        payment_method='free',
        user_notes=case_description,
    )
    slot.reserved_seats = (slot.reserved_seats or 0) + 1
    if slot.remaining_seats() == 0:
        slot.is_available = False
    db.session.add(appointment)
    db.session.flush()
    try:
        from nodeone.services.service_request_actions import attach_pending_service_request_to_appointment

        attach_pending_service_request_to_appointment(
            user_id=int(user.id),
            service_id=int(service.id),
            appointment_id=int(appointment.id),
            organization_id=int(getattr(service, 'organization_id', None) or 1),
        )
    except Exception as _e_sr:
        print(f'⚠️ attach_pending_service_request_to_appointment: {_e_sr}')
    try:
        from nodeone.services.notification_engine import NotificationEngine

        advisor_user = None
        if advisor_id:
            advisor_obj = Advisor.query.get(advisor_id)
            if advisor_obj and getattr(advisor_obj, 'user', None):
                advisor_user = advisor_obj.user
        NotificationEngine.notify_appointment_created(appointment, user, advisor_user, service)
        if advisor_user:
            NotificationEngine.notify_appointment_new_to_advisor(appointment, user, advisor_user, service)
        NotificationEngine.notify_appointment_new_to_admins(appointment, user, advisor_user, service)
        from nodeone.services.communication_dispatch import (
            dispatch_appointment_slot_payment_communication_engine,
        )

        dispatch_appointment_slot_payment_communication_engine(appointment, user, advisor_user, service)
    except Exception as e:
        import traceback

        print(f'⚠️ Notificaciones cita sin pago: {e}')
        traceback.print_exc()
    db.session.commit()
    return True


def submit_request_appointment(service_id, user, form):
    """
    Valida formulario y agrega al carrito. Devuelve (redirect_response, None) o (None, (redirect_url, flash_message, flash_category)).
    """
    from flask import url_for
    from app import add_to_cart
    service = repository.get_service_or_404(service_id)
    if not service.is_active or not service.requires_appointment():
        return None, (url_for('services.list'), 'Este servicio no está disponible para citas.', 'error')
    membership = user.get_active_membership()
    if not membership:
        return None, (url_for('services.list'), 'Necesitas una membresía activa.', 'warning')
    slot_id = form.get('slot_id', type=int)
    case_description = (form.get('case_description') or '').strip()
    if not case_description or len(case_description) < 20:
        return None, (url_for('services.request_appointment', service_id=service_id), 'La descripción del caso debe tener al menos 20 caracteres.', 'error')
    if len(case_description) > 1000:
        return None, (url_for('services.request_appointment', service_id=service_id), 'La descripción del caso no puede exceder 1000 caracteres.', 'error')
    if not slot_id:
        return None, (url_for('services.request_appointment', service_id=service_id), 'Debes seleccionar un horario disponible.', 'error')
    slot = AppointmentSlot.query.get_or_404(slot_id)
    if slot.appointment_type_id != service.appointment_type_id:
        return None, (url_for('services.request_appointment', service_id=service_id), 'El horario seleccionado no corresponde a este servicio.', 'error')
    if not slot.is_available or slot.remaining_seats() <= 0:
        return None, (url_for('services.request_appointment', service_id=service_id), 'Este horario ya no está disponible. Por favor selecciona otro.', 'warning')
    membership_type = membership.membership_type
    pricing = service.pricing_for_appointment_booking(membership_type, user.id)
    final_price = float(pricing.get('final_price') or 0.0)
    if final_price <= 0:
        try:
            finalize_free_slot_appointment_booking(
                service, user, slot, case_description, membership_type, pricing
            )
        except Exception as e:
            db.session.rollback()
            return None, (url_for('services.request_appointment', service_id=service_id), str(e), 'error')
        msg = (
            'Primera cita reservada sin costo. Podés verla en Mis citas.'
            if pricing.get('first_appointment_free_applied')
            else 'Cita reservada sin costo. Podés verla en Mis citas.'
        )
        return ('appointments.appointments_home', msg, 'success'), None

    cart_metadata = {
        'service_id': service.id,
        'service_name': service.name,
        'slot_id': slot.id,
        'slot_datetime': slot.start_datetime.isoformat(),
        'case_description': case_description,
        'final_price': final_price,
        'base_price': float(pricing.get('base_price') or 0.0),
        'appointment_type_id': service.appointment_type_id,
        'advisor_id': slot.advisor_id,
        'requires_appointment': True,
        'slot_end_datetime': slot.end_datetime.isoformat() if slot.end_datetime else None,
    }
    try:
        add_to_cart(
            user_id=user.id,
            product_type='service',
            product_id=service.id,
            product_name=f"{service.name} - Cita",
            unit_price=int(round(final_price * 100)),
            quantity=1,
            product_description=f"Servicio con cita agendada: {case_description[:100]}...",
            metadata=cart_metadata
        )
        return ('payments.cart', 'Servicio agregado al carrito. Continuá con el pago para confirmar la cita.', 'success'), None
    except Exception as e:
        db.session.rollback()
        return None, (url_for('services.request_appointment', service_id=service_id), str(e), 'error')


def get_calendar_data(service_id, start_date=None, end_date=None, advisor_id_filter=None):
    """
    Datos para GET /api/services/<id>/calendar. Devuelve dict para jsonify o (None, error_msg, status_code).
    """
    from nodeone.modules.appointments.slot_generation import generate_slots_from_availability
    from app import Advisor, Appointment
    service = repository.get_service_or_404(service_id)
    if not service.is_active:
        return None, 'Este servicio no está disponible', 400
    if not service.requires_appointment():
        return None, 'Este servicio no requiere cita', 400
    appointment_type_id = service.appointment_type_id
    if not appointment_type_id:
        return None, 'Este servicio no tiene tipo de cita configurado', 400
    appointment_type = repository.get_appointment_type(appointment_type_id)
    if not appointment_type or not appointment_type.is_active:
        return None, 'El tipo de cita asociado no está disponible', 400
    advisor_assignments = AppointmentAdvisor.query.filter_by(
        appointment_type_id=appointment_type_id, is_active=True
    ).join(Advisor).filter(Advisor.is_active == True).all()
    if not advisor_assignments:
        return {
            'success': True,
            'service': {'id': service.id, 'name': service.name},
            'advisors': [],
            'events': [],
            'total_slots': 0,
            'message': 'No hay asesores asignados a este servicio'
        }, None, None
    advisor_ids = [aa.advisor_id for aa in advisor_assignments]
    if advisor_id_filter and advisor_id_filter not in advisor_ids:
        return None, 'Asesor no asignado a este servicio', 400
    if advisor_id_filter:
        advisor_ids = [advisor_id_filter]
    for aid in advisor_ids:
        if repository.count_slots(aid, appointment_type_id, 30) < 10:
            try:
                generate_slots_from_availability(aid, appointment_type_id, days_ahead=30)
            except Exception:
                pass
    if start_date:
        try:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        except Exception:
            start_dt = datetime.utcnow()
    else:
        start_dt = datetime.utcnow()
    if end_date:
        try:
            end_dt = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
        except Exception:
            end_dt = start_dt + timedelta(days=30)
    else:
        end_dt = start_dt + timedelta(days=30)
    slots = AppointmentSlot.query.options(
        joinedload(AppointmentSlot.advisor).joinedload(Advisor.user)
    ).filter(
        AppointmentSlot.appointment_type_id == appointment_type_id,
        AppointmentSlot.advisor_id.in_(advisor_ids),
        AppointmentSlot.start_datetime >= start_dt,
        AppointmentSlot.start_datetime < end_dt,
        AppointmentSlot.is_available == True
    ).order_by(AppointmentSlot.start_datetime.asc()).all()
    appointments = Appointment.query.options(
        joinedload(Appointment.advisor).joinedload(Advisor.user)
    ).filter(
        Appointment.appointment_type_id == appointment_type_id,
        Appointment.advisor_id.in_(advisor_ids),
        Appointment.status.in_(['CONFIRMADA', 'PENDIENTE', 'confirmed', 'pending']),
        Appointment.start_datetime.isnot(None),
        Appointment.start_datetime >= start_dt,
        Appointment.start_datetime < end_dt
    ).all()
    calendar_events = []
    for slot in slots:
        try:
            advisor_name = 'Asesor'
            if slot.advisor and slot.advisor.user:
                advisor_name = f"{slot.advisor.user.first_name} {slot.advisor.user.last_name}"
            elif slot.advisor:
                advisor_name = f"Asesor #{slot.advisor.id}"
            if not slot.start_datetime or not slot.end_datetime:
                continue
            remaining = slot.remaining_seats() if hasattr(slot, 'remaining_seats') else (slot.capacity or 1)
            calendar_events.append({
                'id': f'slot_{slot.id}',
                'title': f'Disponible - {advisor_name}',
                'start': slot.start_datetime.isoformat(),
                'end': slot.end_datetime.isoformat(),
                'backgroundColor': '#28a745',
                'borderColor': '#28a745',
                'textColor': '#fff',
                'extendedProps': {
                    'type': 'slot', 'slot_id': slot.id, 'advisor_id': slot.advisor_id,
                    'advisor_name': advisor_name, 'service_id': service_id, 'service_name': service.name,
                    'remaining_seats': remaining, 'capacity': slot.capacity or 1, 'available': True
                }
            })
        except Exception:
            continue
    for apt in appointments:
        if not apt.start_datetime or not apt.end_datetime:
            continue
        try:
            advisor_name = 'Asesor'
            if apt.advisor and apt.advisor.user:
                advisor_name = f"{apt.advisor.user.first_name} {apt.advisor.user.last_name}"
            label = 'Confirmada' if apt.status in ('CONFIRMADA', 'confirmed') else 'Pendiente'
            calendar_events.append({
                'id': f'apt_{apt.id}',
                'title': f'Cita ({label}) - {advisor_name}',
                'start': apt.start_datetime.isoformat(),
                'end': (apt.end_datetime or apt.start_datetime).isoformat(),
                'backgroundColor': '#17a2b8' if apt.status in ('PENDIENTE', 'pending') else '#6f42c1',
                'borderColor': '#17a2b8' if apt.status in ('PENDIENTE', 'pending') else '#6f42c1',
                'textColor': '#fff',
                'extendedProps': {'type': 'appointment', 'appointment_id': apt.id, 'status': apt.status, 'advisor_id': apt.advisor_id}
            })
        except Exception:
            continue
    advisors_info = []
    for assignment in advisor_assignments:
        advisor = assignment.advisor
        if advisor_id_filter and advisor.id != advisor_id_filter:
            continue
        name = (f"{advisor.user.first_name} {advisor.user.last_name}" if advisor.user else f"Asesor #{advisor.id}")
        advisors_info.append({
            'id': advisor.id,
            'name': name,
            'bio': advisor.bio or '',
            'specializations': advisor.specializations or '',
            'photo_url': advisor.photo_url or ''
        })
    return {
        'success': True,
        'service': {
            'id': service.id,
            'name': service.name,
            'appointment_type_id': appointment_type_id,
            'appointment_type_name': appointment_type.name,
            'duration_minutes': appointment_type.duration_minutes
        },
        'advisors': advisors_info,
        'events': calendar_events,
        'total_slots': len(calendar_events),
        'date_range': {'start': start_dt.isoformat(), 'end': end_dt.isoformat()}
    }, None, None
