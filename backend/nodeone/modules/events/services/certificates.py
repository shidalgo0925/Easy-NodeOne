"""Generación de certificados de evento (EventParticipant → EventCertificate): código, QR, PDF."""

from __future__ import annotations

import os
import secrets
from datetime import datetime
PREFIX_REVIEWER = 'REV'
PREFIX_DEFAULT = 'EN1'


def organization_id_for_event(event) -> int:
    """Org del creador del evento (multi-tenant rutas admin)."""
    try:
        cr = getattr(event, 'creator', None)
        if cr is not None:
            return int(getattr(cr, 'organization_id', None) or 1)
    except Exception:
        pass
    from app import User

    u = User.query.get(getattr(event, 'created_by', None))
    return int(getattr(u, 'organization_id', None) or 1) if u else 1


def certificates_storage_dir(app, org_id: int, event_id: int) -> str:
    path = os.path.abspath(
        os.path.join(app.root_path, '..', 'static', 'uploads', 'certificates', str(org_id), str(event_id))
    )
    os.makedirs(path, exist_ok=True)
    return path


def code_prefix_for_participant(participant) -> str:
    if (getattr(participant, 'participant_type', None) or '').strip().lower() == 'reviewer':
        return PREFIX_REVIEWER
    return PREFIX_DEFAULT


def participant_eligible_for_certificate(participant) -> bool:
    st = (getattr(participant, 'attendance_status', None) or '').strip().lower()
    if st in ('checked_in', 'attended'):
        return True
    if (getattr(participant, 'participant_type', None) or '').strip().lower() == 'reviewer':
        return True
    return False


def participant_active_certificate(participant_id: int, event_id: int):
    from app import EventCertificate

    return (
        EventCertificate.query.filter_by(participant_id=participant_id, event_id=event_id)
        .filter(EventCertificate.status != 'revoked')
        .filter(EventCertificate.is_active.is_(True))
        .first()
    )


def generate_unique_certificate_number_with_prefix(prefix: str) -> str:
    from app import EventCertificate

    p = (prefix or PREFIX_DEFAULT).strip().upper()[:12]
    year = datetime.utcnow().year
    for _ in range(60):
        suf = secrets.token_hex(3).upper()
        code = f"{p}-{year}-{suf}"
        if EventCertificate.query.filter_by(certificate_number=code).first() is None:
            return code
    raise RuntimeError('No se pudo generar código único de certificado')


def generate_verification_token() -> str:
    from app import EventCertificate

    for _ in range(40):
        t = secrets.token_urlsafe(12).replace('.', '').replace('_', '')[:16]
        if len(t) < 8:
            continue
        exists = EventCertificate.query.filter(EventCertificate.verification_token == t).first()
        if exists is None:
            return t
    return secrets.token_urlsafe(14)


def build_verification_url(app, certificate_number: str) -> str:
    # Alias público explícito (plan)
    base = (os.getenv('BASE_URL') or '').strip().rstrip('/')
    if not base:
        try:
            from flask import request

            if request and request.url_root:
                base = request.url_root.rstrip('/')
        except Exception:
            base = ''
    if not base:
        base = 'http://127.0.0.1'
    return f"{base}/certificates/verify/{certificate_number}"


def _qr_base64_png(verify_url: str) -> str | None:
    from nodeone.services.certificate_institutional_pdf import qr_png_base64

    return qr_png_base64(verify_url)


def relative_static_path_from_abs(abs_path: str, app) -> str:
    static_root = os.path.abspath(os.path.join(app.root_path, '..', 'static'))
    abs_path = os.path.abspath(abs_path)
    if abs_path.startswith(static_root):
        rel = abs_path[len(static_root) :].replace(os.sep, '/').lstrip('/')
        return f'/static/{rel}'
    return '/static/' + os.path.basename(abs_path)


def _certificates_upload_dir(app) -> str:
    return os.path.abspath(os.path.join(app.root_path, '..', 'static', 'uploads', 'certificates'))


def _base_url_for_certificate(app) -> str:
    base = (os.getenv('BASE_URL') or '').strip().rstrip('/')
    if base:
        return base
    try:
        from flask import request

        if request and request.url_root:
            return request.url_root.rstrip('/')
    except Exception:
        pass
    return 'http://127.0.0.1'


def _render_event_certificate_pdf_bytes(
    *,
    app,
    event,
    participant,
    display_name: str,
    cert_number: str,
    verify_url: str,
    issued_at: datetime,
    org_id: int,
) -> bytes | None:
    from app import CertificateTemplate, db

    from nodeone.services.event_institutional_certificate_template import (
        is_visual_template,
    )
    from nodeone.services.certificate_institutional_pdf import (
        build_context_from_event_participant,
        compute_academic_hours,
        render_institutional_pdf,
    )

    from nodeone.services.event_institutional_certificate_template import get_fresh_visual_template_for_render

    template = get_fresh_visual_template_for_render(db, CertificateTemplate, event, org_id)
    if template and is_visual_template(template):
        from certificate_template_routes import render_pdf_from_json_layout
        from nodeone.services.event_institutional_certificate_template import build_visual_certificate_data

        sample = build_visual_certificate_data(
            event=event,
            participant=participant,
            display_name=display_name,
            cert_number=cert_number,
            verify_url=verify_url,
            issued_at=issued_at,
            org_id=org_id,
            app_root=app.root_path,
        )
        qr_b64 = _qr_base64_png(verify_url)
        pdf_bytes = render_pdf_from_json_layout(
            template,
            sample,
            _base_url_for_certificate(app),
            qr_b64,
            _certificates_upload_dir(app),
        )
        if pdf_bytes:
            return pdf_bytes

    ctx = build_context_from_event_participant(
        event=event,
        participant=participant,
        certificate_code=cert_number,
        verify_url=verify_url,
        issued_at=issued_at,
        app_root=app.root_path,
        org_id=org_id,
    )
    return render_institutional_pdf(ctx)


def create_event_certificate(
    app,
    event,
    participant,
    issued_by_user_id: int | None,
    certificate_title: str | None = None,
) -> tuple[object | None, str | None]:
    """
    Crea PDF + QR + fila EventCertificate. Devuelve (cert, None) o (None, mensaje error).
    """
    from app import EventCertificate, db

    if not participant_eligible_for_certificate(participant):
        return None, 'El participante no cumple condiciones (check-in o tipo revisor).'
    if participant_active_certificate(participant.id, event.id):
        return None, 'Ya existe un certificado activo para este participante.'

    prefix = code_prefix_for_participant(participant)
    cert_number = generate_unique_certificate_number_with_prefix(prefix)
    vtoken = generate_verification_token()
    verify_url = build_verification_url(app, cert_number)

    org_id = organization_id_for_event(event)
    folder = certificates_storage_dir(app, org_id, event.id)
    base_fs = os.path.join(folder, cert_number.replace('/', '-'))
    pdf_fs = base_fs + '.pdf'

    display_name = (
        (getattr(participant, 'full_name', None) or '').strip()
        or ' '.join(
            x
            for x in (
                participant.first_name,
                participant.middle_name,
                participant.last_name,
                participant.second_last_name,
            )
            if x
        ).strip()
    )
    issued_at = datetime.utcnow()
    ctype = 'reviewer' if prefix == PREFIX_REVIEWER else 'participation'
    title_txt = certificate_title or ('Certificado de revisor' if ctype == 'reviewer' else 'Certificado de participación')

    pdf_bytes = _render_event_certificate_pdf_bytes(
        app=app,
        event=event,
        participant=participant,
        display_name=display_name,
        cert_number=cert_number,
        verify_url=verify_url,
        issued_at=issued_at,
        org_id=org_id,
    )
    if not pdf_bytes:
        return None, 'No se pudo generar el PDF del certificado.'
    with open(pdf_fs, 'wb') as f:
        f.write(pdf_bytes)

    qr_fs = base_fs + '_qr.png'
    try:
        import qrcode

        qrcode.make(verify_url).save(qr_fs, format='PNG')
    except Exception:
        qr_fs = None

    cert_rel = relative_static_path_from_abs(pdf_fs, app)
    qr_rel = relative_static_path_from_abs(qr_fs, app) if qr_fs and os.path.isfile(qr_fs) else None

    ec = EventCertificate(
        event_id=event.id,
        participant_id=participant.id,
        certificate_number=cert_number,
        verification_token=vtoken,
        certificate_type=ctype,
        title=title_txt,
        certificate_url=cert_rel,
        qr_path=qr_rel,
        issued_date=issued_at,
        issued_by=issued_by_user_id,
        status='generated',
        is_active=True,
    )
    db.session.add(ec)
    participant.certificate_status = 'issued'
    db.session.add(participant)
    db.session.commit()
    return ec, None


def regenerate_event_certificate(
    app,
    cert,
    event,
    participant,
    issued_by_user_id: int | None,
) -> tuple[object | None, str | None]:
    """Reemplaza el PDF existente usando la plantilla vigente del evento."""
    from app import db

    if (getattr(cert, 'status', None) or '') == 'revoked' or not getattr(cert, 'is_active', True):
        return None, 'El certificado está revocado o inactivo.'
    if not participant_eligible_for_certificate(participant):
        return None, 'El participante no cumple condiciones para certificado.'

    org_id = organization_id_for_event(event)
    verify_url = build_verification_url(app, cert.certificate_number)
    display_name = (
        (getattr(participant, 'full_name', None) or '').strip()
        or ' '.join(
            x
            for x in (
                participant.first_name,
                participant.middle_name,
                participant.last_name,
                participant.second_last_name,
            )
            if x
        ).strip()
    )
    issued_at = datetime.utcnow()

    pdf_bytes = _render_event_certificate_pdf_bytes(
        app=app,
        event=event,
        participant=participant,
        display_name=display_name,
        cert_number=cert.certificate_number,
        verify_url=verify_url,
        issued_at=issued_at,
        org_id=org_id,
    )
    if not pdf_bytes:
        return None, 'No se pudo regenerar el PDF del certificado.'

    pdf_fs = abs_path_from_certificate_url(app, cert.certificate_url)
    if not pdf_fs:
        folder = certificates_storage_dir(app, org_id, event.id)
        pdf_fs = os.path.join(folder, cert.certificate_number.replace('/', '-') + '.pdf')

    with open(pdf_fs, 'wb') as f:
        f.write(pdf_bytes)

    qr_fs = pdf_fs.replace('.pdf', '_qr.png')
    try:
        import qrcode

        qrcode.make(verify_url).save(qr_fs, format='PNG')
        cert.qr_path = relative_static_path_from_abs(qr_fs, app)
    except Exception:
        pass

    cert.certificate_url = relative_static_path_from_abs(pdf_fs, app)
    cert.issued_date = issued_at
    cert.issued_by = issued_by_user_id
    db.session.add(cert)
    db.session.commit()
    return cert, None


def revoke_event_certificate(cert, revoked_by_user_id: int | None, reason: str | None) -> None:
    from app import db

    cert.status = 'revoked'
    cert.revoked_at = datetime.utcnow()
    cert.revoked_by = revoked_by_user_id
    cert.revoked_reason = (reason or '').strip() or None
    cert.is_active = False
    part = cert.participant
    if part:
        part.certificate_status = 'revoked'
        db.session.add(part)
    db.session.add(cert)
    db.session.commit()


def generate_bulk_for_event(app, event, issued_by_user_id: int | None, participant_ids: list[int] | None):
    """Devuelve dict counts: created, skipped, errors (lista corta)."""
    from app import EventParticipant

    if participant_ids is not None and len(participant_ids) == 0:
        return {'created': 0, 'skipped': 0, 'errors': []}

    q = EventParticipant.query.filter_by(event_id=event.id)
    if participant_ids:
        q = q.filter(EventParticipant.id.in_(participant_ids))
    created = 0
    skipped = 0
    errors: list[str] = []
    for p in q.order_by(EventParticipant.id.asc()).all():
        c, err = create_event_certificate(app, event, p, issued_by_user_id)
        if c:
            created += 1
        else:
            skipped += 1
            if err and len(errors) < 12:
                errors.append(f'#{p.id}: {err}')
    return {'created': created, 'skipped': skipped, 'errors': errors}


def abs_path_from_certificate_url(app, certificate_url: str | None) -> str | None:
    if not certificate_url:
        return None
    u = (certificate_url or '').strip()
    if u.startswith('/static/'):
        rel = u[len('/static/') :]
        fs = os.path.abspath(os.path.join(app.root_path, '..', 'static', rel))
        return fs if os.path.isfile(fs) else None
    return None


def mask_document(doc: str | None) -> str | None:
    d = (doc or '').strip()
    if len(d) <= 4:
        return '****' if d else None
    return '****' + d[-4:]
