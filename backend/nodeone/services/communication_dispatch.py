"""
Ejecución del CommunicationEngine en producto: hooks reales y entrada desde eventos.

- Emails: plantilla marketing + cola email_queue (mismo criterio que automatizaciones).
- In-app: filas Notification.

Desactivar motor: NODEONE_SKIP_COMMUNICATION_ENGINE=1
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from nodeone.modules.communications.services.engine import CommunicationEngine, CommunicationHooks


def communication_engine_enabled() -> bool:
    return os.environ.get('NODEONE_SKIP_COMMUNICATION_ENGINE', '').strip().lower() not in (
        '1',
        'true',
        'yes',
    )


def request_base_url_optional() -> Optional[str]:
    """URL base absoluta desde el request Flask (host_url → url_root → request.url); sin contexto → None."""
    try:
        from flask import has_request_context, request as req
        from urllib.parse import urlparse

        if not has_request_context() or not req:
            return None
        raw = (getattr(req, 'host_url', None) or getattr(req, 'url_root', None) or '')
        raw = raw.rstrip('/')
        if raw:
            return raw
        url = getattr(req, 'url', None) or ''
        if url:
            p = urlparse(url)
            if p.scheme and p.netloc:
                return f'{p.scheme}://{p.netloc}'
        return None
    except Exception:
        return None


def communication_rules_exist(event_code: str, organization_id: Optional[int]) -> bool:
    from sqlalchemy import or_

    from models.communication_rules import CommunicationEvent, CommunicationRule

    ev = CommunicationEvent.query.filter_by(code=event_code).first()
    if not ev:
        return False
    q = CommunicationRule.query.filter_by(event_id=ev.id, enabled=True)
    if organization_id is not None:
        oid = int(organization_id)
        q = q.filter(
            or_(
                CommunicationRule.organization_id.is_(None),
                CommunicationRule.organization_id == oid,
            )
        )
    return q.first() is not None


def _enqueue_email_from_rule(rule, user_id, organization_id, context, delay_minutes: int) -> None:
    import app as M
    from _app.modules.marketing.service import render_template_html

    from models.communications import EmailQueueItem, MarketingTemplate

    uid = int(user_id)
    u = M.User.query.get(uid)
    if not u:
        return
    tid = getattr(rule, 'marketing_template_id', None)
    if not tid:
        return
    template = MarketingTemplate.query.get(int(tid))
    if not template:
        return

    ctx = dict(context or {})
    base_url = ctx.get('base_url')
    render_ctx = {
        'nombre': f"{getattr(u, 'first_name', '') or ''} {getattr(u, 'last_name', '') or ''}".strip()
        or u.email,
        'empresa': getattr(u, 'user_group', '') or '',
        'email': u.email,
        'user_id': u.id,
        **{k: v for k, v in ctx.items() if k not in ('base_url', 'in_app_title', 'in_app_message', 'notification_type')},
    }
    html = render_template_html(template.html, template.variables, render_ctx, base_url=base_url)
    subject = getattr(template, 'subject', None) or template.name or 'Notificación'
    payload = json.dumps({'subject': subject, 'html': html, 'to_email': u.email})

    oid_queue = organization_id
    if oid_queue is None:
        oid_queue = int(getattr(u, 'organization_id', None) or M.default_organization_id())

    send_after = None
    if delay_minutes and int(delay_minutes) > 0:
        send_after = datetime.utcnow() + timedelta(minutes=int(delay_minutes))

    M.db.session.add(
        EmailQueueItem(
            organization_id=int(oid_queue),
            recipient_id=None,
            campaign_id=None,
            payload=payload,
            status='pending',
            send_after=send_after,
        )
    )


def _create_in_app_from_rule(rule, user_id, organization_id, context) -> None:
    import app as M

    ctx = dict(context or {})
    title = (ctx.get('in_app_title') or ctx.get('title') or 'Notificación')[:200]
    message = ctx.get('in_app_message') or ctx.get('message') or title
    ntype = (ctx.get('notification_type') or 'communication_engine')[:50]
    event_id = ctx.get('event_id')
    if event_id is not None:
        try:
            event_id = int(event_id)
        except (TypeError, ValueError):
            event_id = None

    M.db.session.add(
        M.Notification(
            user_id=int(user_id),
            event_id=event_id,
            notification_type=ntype,
            title=title,
            message=message if isinstance(message, str) else str(message),
        )
    )


def default_communication_hooks(base_url: Optional[str] = None) -> CommunicationHooks:
    ctx_base: Dict[str, Any] = {}
    if base_url:
        ctx_base['base_url'] = base_url

    def enqueue_email(rule, user_id, organization_id, context, delay_minutes=0):
        merged = {**ctx_base, **(context or {})}
        _enqueue_email_from_rule(rule, user_id, organization_id, merged, int(delay_minutes or 0))

    def create_in_app(rule, user_id, organization_id, context):
        merged = {**ctx_base, **(context or {})}
        _create_in_app_from_rule(rule, user_id, organization_id, merged)

    return CommunicationHooks(enqueue_email=enqueue_email, create_in_app=create_in_app)


def run_communication_engine_if_configured(
    event_code: str,
    user_id: int,
    organization_id: Optional[int] = None,
    context: Optional[Dict[str, Any]] = None,
    *,
    base_url: Optional[str] = None,
    legacy_notification_type: Optional[str] = None,
) -> Optional[Any]:
    """
    Si hay reglas activas para el evento (y ámbito org), ejecuta el motor con hooks de producto.
    Respetar NotificationSettings legado cuando legacy_notification_type coincide con un tipo conocido.
    """
    if not communication_engine_enabled():
        return None
    try:
        oid = organization_id
        if oid is not None:
            oid = int(oid)
        if not communication_rules_exist(event_code, oid):
            return None
        hooks = default_communication_hooks(base_url=base_url)
        return CommunicationEngine.trigger(
            event_code,
            int(user_id),
            organization_id=oid,
            context=context or {},
            hooks=hooks,
            use_legacy_notification_settings=bool(legacy_notification_type),
            legacy_notification_type=legacy_notification_type,
            commit=True,
        )
    except Exception as ex:  # noqa: BLE001
        print(f'communication_dispatch {event_code} uid={user_id}: {ex}')
        try:
            import app as M

            M.db.session.rollback()
        except Exception:
            pass
        return None


def dispatch_membership_payment_confirmation(user, payment, subscription) -> None:
    """Tras notify_membership_payment: reglas membership_payment."""
    run_communication_engine_if_configured(
        'membership_payment',
        int(user.id),
        getattr(user, 'organization_id', None),
        {
            'payment_id': payment.id,
            'subscription_id': subscription.id,
            'in_app_title': 'Pago confirmado',
            'in_app_message': 'Tu pago de membresía fue registrado.',
            'notification_type': 'membership_payment',
        },
    )


def dispatch_event_registered(
    user_id: int,
    organization_id: Optional[int],
    event_id: int,
    event_title: str,
    base_url: Optional[str],
) -> None:
    run_communication_engine_if_configured(
        'event_registered',
        int(user_id),
        organization_id,
        {
            'base_url': base_url,
            'event_id': int(event_id),
            'in_app_title': (f'Inscripción: {event_title}')[:200],
            'in_app_message': 'Te has registrado al evento.',
            'notification_type': 'event_registered',
        },
        base_url=base_url,
    )


def dispatch_membership_renewed(user_id: int, organization_id: Optional[int], base_url: Optional[str]) -> None:
    run_communication_engine_if_configured(
        'membership_renewed',
        int(user_id),
        organization_id,
        {'base_url': base_url},
        base_url=base_url,
    )


def dispatch_member_created(user_id: int, organization_id: Optional[int], base_url: Optional[str]) -> None:
    run_communication_engine_if_configured(
        'member_created',
        int(user_id),
        organization_id,
        {'base_url': base_url},
        base_url=base_url,
    )


def dispatch_welcome(user, base_url: Optional[str]) -> None:
    run_communication_engine_if_configured(
        'welcome',
        int(user.id),
        getattr(user, 'organization_id', None),
        {
            'base_url': base_url,
            'in_app_title': 'Bienvenida',
            'in_app_message': (f"Hola {getattr(user, 'first_name', '') or ''}".strip() or 'Te damos la bienvenida.'),
            'notification_type': 'welcome',
        },
        base_url=base_url,
        legacy_notification_type='welcome',
    )


def _oid_fallback(*candidates):
    for c in candidates:
        if c is not None:
            try:
                v = int(c)
                if v >= 1:
                    return v
            except (TypeError, ValueError):
                pass
    return None


def dispatch_membership_expiring(user, subscription, days_left: int) -> None:
    run_communication_engine_if_configured(
        'membership_expiring',
        int(user.id),
        _oid_fallback(getattr(user, 'organization_id', None)),
        {
            'days_left': int(days_left),
            'subscription_id': getattr(subscription, 'id', None),
            'in_app_title': 'Membresía por vencer',
            'in_app_message': f'Te quedan {days_left} día(s) de membresía.',
            'notification_type': 'membership_expiring',
        },
        legacy_notification_type='membership_expiring',
    )


def dispatch_membership_expired(user, subscription) -> None:
    run_communication_engine_if_configured(
        'membership_expired',
        int(user.id),
        _oid_fallback(getattr(user, 'organization_id', None)),
        {
            'subscription_id': getattr(subscription, 'id', None),
            'in_app_title': 'Membresía expirada',
            'in_app_message': 'Tu membresía ha expirado.',
            'notification_type': 'membership_expired',
        },
        legacy_notification_type='membership_expired',
    )


def dispatch_appointment_confirmation_member(appointment, client_user, advisor_user, base_url: Optional[str]) -> None:
    oid = _oid_fallback(
        getattr(appointment, 'organization_id', None),
        getattr(client_user, 'organization_id', None),
    )
    st = getattr(appointment, 'start_datetime', None)
    when = st.strftime('%d/%m/%Y %H:%M') if st else 'próximamente'
    adv = f'{advisor_user.first_name} {advisor_user.last_name}'.strip() if advisor_user else 'tu asesor'
    run_communication_engine_if_configured(
        'appointment_confirmation',
        int(client_user.id),
        oid,
        {
            'base_url': base_url,
            'appointment_id': appointment.id,
            'in_app_title': 'Cita confirmada',
            'in_app_message': f'Cita con {adv} el {when}.',
            'notification_type': 'appointment_confirmation',
        },
        base_url=base_url,
        legacy_notification_type='appointment_confirmation',
    )


def dispatch_appointment_cancellation_member(
    appointment, client_user, base_url: Optional[str], reason: Optional[str] = None, cancelled_by: str = 'member'
) -> None:
    oid = _oid_fallback(
        getattr(appointment, 'organization_id', None),
        getattr(client_user, 'organization_id', None),
    )
    run_communication_engine_if_configured(
        'appointment_cancellation',
        int(client_user.id),
        oid,
        {
            'base_url': base_url,
            'appointment_id': appointment.id,
            'cancellation_reason': reason or '',
            'cancelled_by': cancelled_by,
            'in_app_title': 'Cita cancelada',
            'in_app_message': (reason or 'Tu cita fue cancelada.')[:500],
            'notification_type': 'appointment_cancellation',
        },
        base_url=base_url,
        legacy_notification_type='appointment_cancellation',
    )


def dispatch_appointment_reminder_member(
    appointment, user, _advisor_user, hours_before: int, base_url: Optional[str] = None
) -> None:
    oid = _oid_fallback(
        getattr(appointment, 'organization_id', None),
        getattr(user, 'organization_id', None),
    )
    run_communication_engine_if_configured(
        'appointment_reminder',
        int(user.id),
        oid,
        {
            'base_url': base_url,
            'appointment_id': appointment.id,
            'hours_before': int(hours_before),
            'in_app_title': f'Recordatorio: cita en {hours_before}h',
            'in_app_message': 'Tienes una cita próxima.',
            'notification_type': 'appointment_reminder',
        },
        base_url=base_url,
        legacy_notification_type='appointment_reminder',
    )


def dispatch_appointment_booked_member(
    appointment, member_user, advisor_user, service, base_url: Optional[str] = None
) -> None:
    """Tras pago con slot: cliente recibe reglas `appointment_booked` (distinto de aviso al asesor)."""
    oid = _oid_fallback(
        getattr(appointment, 'organization_id', None),
        getattr(member_user, 'organization_id', None),
    )
    svc = getattr(service, 'name', '') or getattr(getattr(appointment, 'appointment_type', None), 'name', '') or 'servicio'
    st = getattr(appointment, 'start_datetime', None)
    when = st.strftime('%d/%m/%Y %H:%M') if st else 'próximamente'
    run_communication_engine_if_configured(
        'appointment_booked',
        int(member_user.id),
        oid,
        {
            'base_url': base_url,
            'appointment_id': appointment.id,
            'in_app_title': 'Cita agendada',
            'in_app_message': f'Tu cita para "{svc}" el {when}.',
            'notification_type': 'appointment_created',
        },
        base_url=base_url,
    )


def dispatch_appointment_new_to_advisor(
    appointment, member_user, advisor_user, service, base_url: Optional[str] = None
) -> None:
    oid = _oid_fallback(
        getattr(advisor_user, 'organization_id', None),
        getattr(member_user, 'organization_id', None),
        getattr(appointment, 'organization_id', None),
    )
    svc = getattr(service, 'name', '') or 'servicio'
    run_communication_engine_if_configured(
        'appointment_created',
        int(advisor_user.id),
        oid,
        {
            'base_url': base_url,
            'appointment_id': appointment.id,
            'in_app_title': 'Nueva solicitud de cita',
            'in_app_message': f'{member_user.first_name} {member_user.last_name} — {svc}'.strip(),
            'notification_type': 'appointment_request',
        },
        base_url=base_url,
    )


def dispatch_appointment_new_to_admins(
    appointment, member_user, advisor_user, service, base_url: Optional[str] = None
) -> None:
    """Paridad con NotificationEngine.notify_appointment_new_to_admins: un trigger por admin activo."""
    import app as M

    svc = (
        getattr(service, 'name', None)
        or getattr(getattr(appointment, 'appointment_type', None), 'name', None)
        or 'servicio'
    )
    adv_label = (
        f'{advisor_user.first_name} {advisor_user.last_name}'.strip()
        if advisor_user
        else 'No asignado'
    )
    oid_ctx = _oid_fallback(
        getattr(appointment, 'organization_id', None),
        getattr(member_user, 'organization_id', None),
    )
    try:
        admins = M.User.query.filter_by(is_admin=True, is_active=True).all()
    except Exception:
        admins = []
    for admin in admins or []:
        oid = _oid_fallback(getattr(admin, 'organization_id', None), oid_ctx)
        run_communication_engine_if_configured(
            'appointment_new_admin',
            int(admin.id),
            oid,
            {
                'base_url': base_url,
                'appointment_id': appointment.id,
                'member_user_id': int(member_user.id),
                'advisor_label': adv_label,
                'in_app_title': 'Nueva cita creada',
                'in_app_message': (
                    f'{member_user.first_name} {member_user.last_name} ({getattr(member_user, "email", "")}) '
                    f'— {svc} con {adv_label}'
                )[:500],
                'notification_type': 'appointment_new_admin',
            },
            base_url=base_url,
        )


def dispatch_event_registration_staff(event, registrant_user, registration, base_url: Optional[str] = None) -> None:
    try:
        recipients = event.get_notification_recipients()
    except Exception:
        recipients = []
    for recipient in recipients or []:
        oid = _oid_fallback(
            getattr(recipient, 'organization_id', None),
            getattr(registrant_user, 'organization_id', None),
            getattr(event, 'organization_id', None),
        )
        run_communication_engine_if_configured(
            'event_registration',
            int(recipient.id),
            oid,
            {
                'base_url': base_url,
                'event_id': event.id,
                'registration_id': registration.id,
                'registrant_user_id': registrant_user.id,
                'in_app_title': f'Nuevo registro: {event.title}'[:200],
                'in_app_message': f'{registrant_user.first_name} {registrant_user.last_name} se registró.',
                'notification_type': 'event_registration',
            },
            base_url=base_url,
            legacy_notification_type='event_registration',
        )


def dispatch_event_registration_user_side(event, user, registration, base_url: Optional[str] = None) -> None:
    oid = _oid_fallback(getattr(user, 'organization_id', None), getattr(event, 'organization_id', None))
    run_communication_engine_if_configured(
        'event_registration_user',
        int(user.id),
        oid,
        {
            'base_url': base_url,
            'event_id': event.id,
            'registration_id': registration.id,
            'in_app_title': f'Registro: {event.title}'[:200],
            'in_app_message': 'Tu registro al evento fue registrado.',
            'notification_type': 'event_registration_user',
        },
        base_url=base_url,
        legacy_notification_type='event_registration_user',
    )


def dispatch_event_cancellation_staff(event, cancelling_user, base_url: Optional[str] = None) -> None:
    try:
        recipients = event.get_notification_recipients()
    except Exception:
        recipients = []
    for recipient in recipients or []:
        oid = _oid_fallback(
            getattr(recipient, 'organization_id', None),
            getattr(cancelling_user, 'organization_id', None),
            getattr(event, 'organization_id', None),
        )
        run_communication_engine_if_configured(
            'event_cancellation',
            int(recipient.id),
            oid,
            {
                'base_url': base_url,
                'event_id': event.id,
                'in_app_title': f'Cancelación: {event.title}'[:200],
                'in_app_message': f'{cancelling_user.first_name} canceló su registro.',
                'notification_type': 'event_cancellation',
            },
            base_url=base_url,
            legacy_notification_type='event_cancellation',
        )


def dispatch_event_cancellation_user_side(event, user, base_url: Optional[str] = None) -> None:
    oid = _oid_fallback(getattr(user, 'organization_id', None), getattr(event, 'organization_id', None))
    run_communication_engine_if_configured(
        'event_cancellation_user',
        int(user.id),
        oid,
        {
            'base_url': base_url,
            'event_id': event.id,
            'in_app_title': f'Registro cancelado: {event.title}'[:200],
            'in_app_message': 'Tu registro al evento fue cancelado.',
            'notification_type': 'event_cancellation_user',
        },
        base_url=base_url,
        legacy_notification_type='event_cancellation_user',
    )


def dispatch_event_confirmation_staff(event, confirmed_user, registration, base_url: Optional[str] = None) -> None:
    try:
        recipients = event.get_notification_recipients()
    except Exception:
        recipients = []
    for recipient in recipients or []:
        oid = _oid_fallback(
            getattr(recipient, 'organization_id', None),
            getattr(confirmed_user, 'organization_id', None),
            getattr(event, 'organization_id', None),
        )
        run_communication_engine_if_configured(
            'event_confirmation',
            int(recipient.id),
            oid,
            {
                'base_url': base_url,
                'event_id': event.id,
                'registration_id': registration.id,
                'in_app_title': f'Registro confirmado: {event.title}'[:200],
                'in_app_message': f'{confirmed_user.first_name} — registro confirmado.',
                'notification_type': 'event_confirmation',
            },
            base_url=base_url,
            legacy_notification_type='event_confirmation',
        )


def dispatch_event_update_recipients(event, base_url: Optional[str] = None) -> None:
    import app as M

    seen = set()

    def _one(uid: int, oid_cand):
        if uid in seen:
            return
        seen.add(uid)
        oid = _oid_fallback(oid_cand, getattr(event, 'organization_id', None))
        u = M.User.query.get(uid)
        if u and getattr(u, 'organization_id', None):
            oid = oid or int(u.organization_id)
        run_communication_engine_if_configured(
            'event_update',
            int(uid),
            oid,
            {
                'base_url': base_url,
                'event_id': event.id,
                'in_app_title': f'Evento actualizado: {event.title}'[:200],
                'in_app_message': 'El evento al que estás vinculado fue modificado.',
                'notification_type': 'event_update',
            },
            base_url=base_url,
            legacy_notification_type='event_update',
        )

    if getattr(event, 'created_by', None):
        _one(int(event.created_by), getattr(event, 'organization_id', None))

    for reg in M.EventRegistration.query.filter_by(
        event_id=event.id, registration_status='confirmed'
    ).all():
        _one(int(reg.user_id), None)


def dispatch_appointment_slot_payment_communication_engine(
    appointment,
    member_user,
    advisor_user,
    service,
    base_url: Optional[str] = None,
) -> None:
    """Tras NotificationEngine en pago con slot: motor para cliente, asesor (si hay) y admins."""
    if base_url is None:
        base_url = request_base_url_optional()
    try:
        dispatch_appointment_booked_member(appointment, member_user, advisor_user, service, base_url)
        if advisor_user:
            dispatch_appointment_new_to_advisor(appointment, member_user, advisor_user, service, base_url)
        dispatch_appointment_new_to_admins(appointment, member_user, advisor_user, service, base_url)
    except Exception:
        pass


def dispatch_cart_checkout_communication_engine(
    payment_user_id: int,
    subscriptions_created,
    events_registered,
    base_url: Optional[str] = None,
) -> None:
    """Membresía renovada + registro a evento (miembro y staff) tras carrito pagado."""
    import app as M

    if base_url is None:
        base_url = request_base_url_optional()
    try:
        if subscriptions_created:
            u = M.User.query.get(payment_user_id)
            dispatch_membership_renewed(
                payment_user_id,
                getattr(u, 'organization_id', None) if u else None,
                base_url,
            )
        for event_reg in events_registered:
            u = M.User.query.get(event_reg.user_id)
            etitle = event_reg.event.title if getattr(event_reg, 'event', None) else ''
            dispatch_event_registered(
                event_reg.user_id,
                getattr(u, 'organization_id', None) if u else None,
                event_reg.event_id,
                etitle,
                base_url,
            )
            ev = event_reg.event if getattr(event_reg, 'event', None) else None
            if u and ev:
                dispatch_event_registration_staff(ev, u, event_reg, base_url)
    except Exception as ex:
        print(f'Communication engine (cart checkout): {ex}')
