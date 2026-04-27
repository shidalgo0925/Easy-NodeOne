"""
Notificación opt-in a miembros de la org cuando se publica un evento (checkbox en admin).
No envía nada salvo que el admin marque explícitamente la casilla.
"""

from __future__ import annotations


def notify_org_members_on_event_publish(
    event,
    *,
    organization_id: int,
    public_event_url: str | None = None,
) -> tuple[int, int]:
    """
    Emails a usuarios activos de la org con email y preferencia de marketing aceptable.
    Devuelve (enviados, errores).
    """
    from flask import has_request_context, url_for

    from app import User, default_organization_id, email_service, apply_email_config_from_db

    oid = int(organization_id or default_organization_id())
    try:
        apply_email_config_from_db()
    except Exception:
        pass
    title = (getattr(event, 'title', None) or 'Evento').strip()
    slug = getattr(event, 'slug', None) or ''
    if public_event_url is None and has_request_context() and slug:
        try:
            public_event_url = url_for('events.event_detail', slug=slug, _external=True)
        except Exception:
            public_event_url = None
    if not public_event_url:
        public_event_url = ''

    q = (
        User.query.filter(
            User.organization_id == oid,
            User.is_active.is_(True),
            User.email_verified.is_(True),
        )
    )
    users = q.all()
    sent, errors = 0, 0
    st = (getattr(event, 'start_date', None) and event.start_date.strftime('%d/%m/%Y %H:%M')) or '—'
    mod = (getattr(event, 'format', None) or '—').replace('_', ' ')

    for u in users[: 500]:  # tope de seguridad
        em = (u.email or '').strip()
        if not em:
            continue
        mst = (getattr(u, 'email_marketing_status', None) or 'subscribed').lower()
        if mst in ('bounced', 'unsubscribed'):
            continue
        try:
            html = f"""
            <p>Hola {u.first_name or ''},</p>
            <p>Se publicó un nuevo evento: <strong>{title}</strong>.</p>
            <ul>
              <li><strong>Cuándo:</strong> {st}</li>
              <li><strong>Modalidad:</strong> {mod}</li>
            </ul>
            {f'<p><a href="{public_event_url}">Ver evento e inscripción</a></p>' if public_event_url else ''}
            <p>Saludos,<br>Equipo</p>
            """
            if email_service:
                email_service.send_email(
                    subject=f'Nuevo evento: {title[:80]}',
                    recipients=[em],
                    html_content=html,
                    email_type='event_published_broadcast',
                    related_entity_type='event',
                    related_entity_id=int(getattr(event, 'id', 0) or 0) or None,
                    recipient_id=u.id,
                    recipient_name=f'{u.first_name} {u.last_name}'.strip() or em,
                )
            sent += 1
        except Exception:
            errors += 1

    return sent, errors
