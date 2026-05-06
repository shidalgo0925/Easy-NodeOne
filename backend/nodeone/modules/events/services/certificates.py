"""Generación de certificados de evento (EventParticipant → EventCertificate): código, QR, PDF."""

from __future__ import annotations

import base64
import io
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
    try:
        import qrcode

        buf = io.BytesIO()
        qrcode.make(verify_url).save(buf, format='PNG')
        return base64.b64encode(buf.getvalue()).decode()
    except Exception:
        return None


def _pdf_reportlab_event(
    full_name: str,
    event_title: str,
    certificate_title: str,
    date_emission: str,
    certificate_code: str,
    verify_url: str,
    qr_base64: str | None,
) -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen import canvas

    buf = io.BytesIO()
    w, h = A4
    c = canvas.Canvas(buf, pagesize=A4)
    c.setTitle('Certificado')
    c.setStrokeColorRGB(0.79, 0.64, 0.15)
    c.setLineWidth(2)
    c.rect(10 * mm, 10 * mm, w - 20 * mm, h - 20 * mm)
    c.setStrokeColorRGB(0.12, 0.23, 0.37)
    c.setLineWidth(1)
    c.rect(14 * mm, 14 * mm, w - 28 * mm, h - 28 * mm)
    c.setFont('Helvetica-Bold', 22)
    c.drawCentredString(w / 2, h - 45 * mm, certificate_title or 'Certificado')
    c.setFont('Helvetica-Bold', 18)
    c.drawCentredString(w / 2, h - 65 * mm, full_name or '—')
    c.setFont('Helvetica', 14)
    c.drawCentredString(w / 2, h - 80 * mm, event_title or '—')
    c.setFont('Helvetica', 10)
    c.drawCentredString(
        w / 2,
        h - 100 * mm,
        f'Fecha de emisión: {date_emission}  |  Código: {certificate_code}',
    )
    if qr_base64:
        try:
            raw = base64.b64decode(qr_base64)
            img = ImageReader(io.BytesIO(raw))
            c.drawImage(img, w - 55 * mm, 22 * mm, width=45 * mm, height=45 * mm)
        except Exception:
            pass
    c.setFont('Helvetica', 8)
    short = verify_url if len(verify_url) <= 72 else verify_url[:69] + '...'
    c.drawString(18 * mm, 18 * mm, f'Validación: {short}')
    c.save()
    buf.seek(0)
    return buf.getvalue()


def relative_static_path_from_abs(abs_path: str, app) -> str:
    static_root = os.path.abspath(os.path.join(app.root_path, '..', 'static'))
    abs_path = os.path.abspath(abs_path)
    if abs_path.startswith(static_root):
        rel = abs_path[len(static_root) :].replace(os.sep, '/').lstrip('/')
        return f'/static/{rel}'
    return '/static/' + os.path.basename(abs_path)


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
    date_str = datetime.utcnow().strftime('%d/%m/%Y')
    ctype = 'reviewer' if prefix == PREFIX_REVIEWER else 'participation'
    title_txt = certificate_title or ('Certificado de revisor' if ctype == 'reviewer' else 'Certificado de participación')

    qr_b64 = _qr_base64_png(verify_url)
    pdf_bytes = _pdf_reportlab_event(
        display_name,
        getattr(event, 'title', '') or 'Evento',
        title_txt,
        date_str,
        cert_number,
        verify_url,
        qr_b64,
    )
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
        issued_date=datetime.utcnow(),
        issued_by=issued_by_user_id,
        status='generated',
        is_active=True,
    )
    db.session.add(ec)
    participant.certificate_status = 'issued'
    db.session.add(participant)
    db.session.commit()
    return ec, None


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
