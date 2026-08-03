"""Portal usuario: certificados de evento asociados al participante (user_id / email)."""

from __future__ import annotations

from sqlalchemy import and_, func, or_

from nodeone.modules.events.services.certificates import abs_path_from_certificate_url


def _normalize_email(value: str | None) -> str:
    return (value or '').strip().lower()


def participant_owned_by_user(participant, user) -> bool:
    """user_id tiene prioridad; email solo si user_id del participante es NULL."""
    if participant is None or user is None:
        return False
    pid = getattr(participant, 'user_id', None)
    if pid is not None:
        try:
            return int(pid) == int(user.id)
        except (TypeError, ValueError):
            return False
    u_email = _normalize_email(getattr(user, 'email', None))
    p_email = _normalize_email(getattr(participant, 'email', None))
    return bool(u_email and p_email and u_email == p_email)


def _participant_ownership_clause(participant_model, user):
    uid = int(user.id)
    u_email = _normalize_email(getattr(user, 'email', None))
    if not u_email:
        return participant_model.user_id == uid
    email_match = func.lower(func.trim(participant_model.email)) == u_email
    return or_(
        participant_model.user_id == uid,
        and_(participant_model.user_id.is_(None), email_match),
    )


def link_unassigned_participants_for_user(user) -> int:
    """
    Vincula participantes sin user_id cuyo email coincide con el usuario (una sola vez).
    Facilita que cada usuario vea sus certificados al entrar a Documentos → Certificados.
    """
    from app import EventParticipant, db

    email = _normalize_email(getattr(user, 'email', None))
    if not email:
        return 0
    rows = (
        EventParticipant.query.filter(EventParticipant.user_id.is_(None))
        .filter(func.lower(func.trim(EventParticipant.email)) == email)
        .all()
    )
    if not rows:
        return 0
    for p in rows:
        p.user_id = int(user.id)
    db.session.commit()
    return len(rows)


def query_user_event_certificates(user):
    """
    Certificados activos del usuario (no revocados).
    Devuelve lista de dicts listos para plantilla.
    """
    from app import Event, EventCertificate, EventParticipant

    q = (
        EventCertificate.query.join(
            EventParticipant, EventCertificate.participant_id == EventParticipant.id
        )
        .join(Event, EventCertificate.event_id == Event.id)
        .filter(_participant_ownership_clause(EventParticipant, user))
        .filter(EventCertificate.status != 'revoked')
        .filter(EventCertificate.is_active.is_(True))
        .order_by(EventCertificate.issued_date.desc(), EventCertificate.id.desc())
    )
    rows = []
    for cert in q.all():
        event = cert.event
        ctype = (getattr(cert, 'certificate_type', None) or 'participation').strip().lower()
        title = (getattr(cert, 'title', None) or '').strip()
        if not title:
            title = 'Certificado de revisor' if ctype == 'reviewer' else 'Certificado de participación'
        rows.append(
            {
                'id': cert.id,
                'title': title,
                'event_title': (getattr(event, 'title', None) or '—').strip(),
                'event_date': getattr(event, 'start_date', None),
                'event_end_date': getattr(event, 'end_date', None),
                'certificate_number': cert.certificate_number,
                'issued_date': cert.issued_date,
                'status': cert.status or 'generated',
                'certificate_url': cert.certificate_url,
                'has_pdf': bool(cert.certificate_url),
            }
        )
    return rows


def get_user_event_certificate(user, certificate_id: int):
    """Certificado por id si pertenece al usuario y no está revocado; si no, None."""
    from app import EventCertificate, EventParticipant

    cert = (
        EventCertificate.query.join(
            EventParticipant, EventCertificate.participant_id == EventParticipant.id
        )
        .filter(EventCertificate.id == int(certificate_id))
        .filter(_participant_ownership_clause(EventParticipant, user))
        .filter(EventCertificate.status != 'revoked')
        .filter(EventCertificate.is_active.is_(True))
        .first()
    )
    return cert


def resolve_certificate_pdf_path(app, cert) -> str | None:
    """Ruta absoluta segura al PDF del certificado."""
    return abs_path_from_certificate_url(app, getattr(cert, 'certificate_url', None))
