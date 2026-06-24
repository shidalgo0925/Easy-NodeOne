# Módulo Certificados - NodeOne
# GET /api/my-certificates, POST /api/request-certificate/<event_id>, GET /verify/<code>, GET /api/certificates/<code>/download

import os
import hashlib
import io
import logging
from datetime import datetime
from flask import Blueprint, jsonify, request, send_file, redirect, url_for, render_template_string, render_template, Response
from flask_login import login_required, current_user
from types import SimpleNamespace

logger = logging.getLogger(__name__)


def _cert_admin_org_id():
    from app import _catalog_org_for_admin_catalog_routes
    return _catalog_org_for_admin_catalog_routes()


def _cert_member_org_id():
    """Misma regla que beneficios/planes: tenant del miembro o sesión del admin."""
    from app import tenant_data_organization_id

    return int(tenant_data_organization_id())


certificates_api_bp = Blueprint('certificates_api', __name__, url_prefix='/api')
certificates_public_bp = Blueprint('certificates_public', __name__)
certificates_page_bp = Blueprint('certificates_page', __name__)


def _get_base_url():
    from flask import request
    if request and request.url_root:
        return request.url_root.rstrip('/')
    return os.getenv('BASE_URL', 'https://app.easynodeone.com')


def _user_qualified_for_event(user, cert_event):
    from nodeone.services.certificate_membership_rules import user_qualified_for_certificate_event

    return user_qualified_for_certificate_event(user, cert_event, org_id=_cert_member_org_id())


def _user_active_membership_plan_id(user):
    from nodeone.services.certificate_membership_rules import user_active_membership_plan_id

    return user_active_membership_plan_id(user, org_id=_cert_member_org_id())


def _user_completed_event_ids(user):
    """Set de event_id en los que el usuario está confirmado o completado."""
    from app import EventRegistration
    rows = EventRegistration.query.filter(
        EventRegistration.user_id == user.id,
        EventRegistration.registration_status.in_(['confirmed', 'completed'])
    ).with_entities(EventRegistration.event_id).all()
    return {r[0] for r in rows}


def _requirement_text(cert_event):
    from nodeone.services.certificate_membership_rules import requirement_text_for_certificate_event

    return requirement_text_for_certificate_event(cert_event)


def _certificates_upload_dir():
    """Directorio para subir fondos, logos y sellos de certificados."""
    from flask import current_app
    d = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'uploads', 'certificates')
    os.makedirs(d, exist_ok=True)
    return d


def _parse_template_id(v):
    """Convierte valor de template_id del request a int o None."""
    if v is None or v == '' or v == 0:
        return None
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _seed_org_certificate_events(oid: int):
    """Crea tablas si hace falta y siembra REG + certificado por cada plan de membresía."""
    from app import db

    from nodeone.services.certificate_membership_rules import seed_membership_certificate_events_for_org

    try:
        seed_membership_certificate_events_for_org(db, int(oid))
    except Exception:
        db.session.rollback()


def _ensure_certificate_events():
    """Compat: siembra org 1 (instalaciones que llaman sin contexto de tenant)."""
    from utils.organization import default_organization_id

    _seed_org_certificate_events(int(default_organization_id()))


def _ensure_membership_certificate_event():
    """Eventos REG/MEM para la org del usuario actual (miembro o admin en sesión)."""
    _seed_org_certificate_events(_cert_member_org_id())


@certificates_api_bp.route('/my-certificates', methods=['GET'])
@login_required
def my_certificates():
    """Lista TODOS los eventos de certificado activos; por cada uno indica si el usuario puede emitir y estado."""
    from app import CertificateEvent, Certificate, db
    _ensure_membership_certificate_event()
    coid = _cert_member_org_id()
    cert_event_list = CertificateEvent.query.filter_by(
        organization_id=coid, is_active=True
    ).order_by(CertificateEvent.name).all()
    from nodeone.services.certificate_membership_rules import membership_certificate_events_visible_to_user

    cert_event_list = membership_certificate_events_visible_to_user(
        current_user, cert_event_list, coid
    )
    result = []
    for ev in cert_event_list:
        qualified = _user_qualified_for_event(current_user, ev)
        existing = Certificate.query.filter_by(
            user_id=current_user.id,
            certificate_event_id=ev.id
        ).first()
        result.append({
            'certificate_event_id': ev.id,
            'name': ev.name,
            'start_date': ev.start_date.isoformat() if ev.start_date else None,
            'end_date': ev.end_date.isoformat() if ev.end_date else None,
            'institution': ev.institution,
            'requirement_text': _requirement_text(ev),
            'qualified': qualified,
            'already_issued': existing is not None,
            'certificate_code': existing.certificate_code if existing else None,
            'download_url': url_for('certificates_api.download_certificate', certificate_code=existing.certificate_code, _external=True) if existing else None,
        })
    return jsonify({'available': result})


def _next_certificate_code(cert_event):
    """Genera código único tipo REL-2026-0001 o REL-O2-2026-0001 si catálogo multi-tenant activo."""
    from app import Certificate, db, _enable_multi_tenant_catalog
    year = datetime.utcnow().year
    base = cert_event.code_prefix or 'REL'
    oid = int(getattr(cert_event, 'organization_id', None) or 1)
    if _enable_multi_tenant_catalog():
        prefix = f"{base}-O{oid}-{year}-"
    else:
        prefix = f"{base}-{year}-"
    last = Certificate.query.filter(Certificate.certificate_code.like(prefix + '%')).order_by(Certificate.id.desc()).first()
    if last:
        try:
            num = int(last.certificate_code.rsplit('-', 1)[-1]) + 1
        except (ValueError, IndexError):
            num = 1
    else:
        num = 1
    return f"{prefix}{num:04d}"


def _qr_base64(verify_url):
    """Base64 PNG del QR (delega al renderer institucional compartido)."""
    from nodeone.services.certificate_institutional_pdf import qr_png_base64

    return qr_png_base64(verify_url)


def _background_path_from_url(url):
    """Si url es /static/uploads/certificates/xxx (o file://... con ese path), devuelve ruta absoluta al archivo; si no, None."""
    if not url:
        return None
    u = (url or '').strip()
    # Aceptar file:///path/.../static/uploads/certificates/xxx o /static/uploads/certificates/xxx
    if '/static/uploads/certificates/' in u:
        name = u.split('/static/uploads/certificates/')[-1].split('?')[0].strip()
        if name:
            root = _certificates_upload_dir()
            path = os.path.abspath(os.path.join(root, name))
            if os.path.isfile(path):
                return path
            logger.warning("Certificado fondo: archivo no encontrado path=%s (url=%s)", path, u[:80])
    return None


def _render_pdf_reportlab(
    full_name,
    event_name,
    date_emission,
    certificate_code,
    verify_url,
    qr_base64=None,
    membership_type=None,
    membership_start='',
    membership_end='',
    background_path=None,
    cert_event=None,
):
    """Fallback PDF: renderer institucional compartido (mismo motor que eventos)."""
    from nodeone.services.certificate_institutional_pdf import (
        build_context_from_membership,
        render_institutional_pdf,
    )

    try:
        issued = datetime.strptime((date_emission or '')[:10], '%Y-%m-%d')
    except ValueError:
        issued = datetime.utcnow()

    if cert_event is not None:
        ctx = build_context_from_membership(
            cert_event=cert_event,
            full_name=full_name,
            program_name=event_name,
            certificate_code=certificate_code,
            verify_url=verify_url,
            issued_at=issued,
            app_root=os.path.dirname(os.path.dirname(__file__)),
            membership_type=membership_type or '',
            membership_start=membership_start or '',
            membership_end=membership_end or '',
        )
    else:
        from nodeone.services.certificate_institutional_pdf import CertificateRenderContext

        ctx = CertificateRenderContext(
            participant_name=full_name or '—',
            document_id='No registrado',
            program_name=event_name or 'Certificado',
            certificate_code=certificate_code,
            verify_url=verify_url,
            issued_at=issued,
            qr_base64=qr_base64 or _qr_base64(verify_url),
            membership_type=membership_type or '',
            membership_period=f'{membership_start} – {membership_end}'.strip(' –') if (membership_start or membership_end) else '',
        )
    return render_institutional_pdf(ctx)


def _render_pdf(cert_event, user, certificate_code, verification_hash, verify_url):
    """Genera PDF usando el mismo HTML que la vista previa (_get_certificate_html). Así pantalla y descarga son idénticos."""
    full_name = f"{user.first_name} {user.last_name}".strip()
    event_name = cert_event.name
    date_str = datetime.utcnow().strftime('%Y-%m-%d')
    membership = user.get_active_membership()
    membership_type = getattr(membership, 'membership_type', None) if membership else None
    membership_start = getattr(membership, 'start_date', None)
    membership_end = getattr(membership, 'end_date', None)
    if membership_start and hasattr(membership_start, 'strftime'):
        membership_start = membership_start.strftime('%Y-%m-%d')
    if membership_end and hasattr(membership_end, 'strftime'):
        membership_end = membership_end.strftime('%Y-%m-%d')
    sample_data = {
        'participant_name': full_name,
        'document_id': getattr(user, 'document_id', None) or getattr(user, 'cedula', None) or '',
        'program_name': event_name,
        'hours': cert_event.duration_hours or '',
        'issue_date': date_str,
        'certificate_code': certificate_code,
        'verification_url': verify_url,
        'institution': cert_event.institution or '',
        'membership_type': membership_type or '',
        'membership_start': membership_start or '',
        'membership_end': membership_end or '',
    }
    html = _get_certificate_html(cert_event, sample_data, verify_url, use_file_urls=True)
    if not html:
        logger.warning("_get_certificate_html devolvió None para event_id=%s", getattr(cert_event, 'id'))
        return None
    try:
        from weasyprint import HTML
        pdf_bytes = HTML(string=html).write_pdf()
        return pdf_bytes
    except Exception as e1:
        logger.warning("WeasyPrint PDF falló: %s", e1)
        try:
            import weasyprint
            pdf_bytes = weasyprint.HTML(string=html).write_pdf()
            return pdf_bytes
        except Exception as e2:
            logger.warning("WeasyPrint (alt) falló: %s", e2)
    try:
        qr_b64 = _qr_base64(verify_url)
        bg_path = _background_path_from_url(getattr(cert_event, 'background_url', None))
        return _render_pdf_reportlab(
            full_name=full_name,
            event_name=event_name,
            date_emission=date_str,
            certificate_code=certificate_code,
            verify_url=verify_url,
            qr_base64=qr_b64,
            membership_type=membership_type,
            membership_start=membership_start or '',
            membership_end=membership_end or '',
            background_path=bg_path,
            cert_event=cert_event,
        )
    except Exception as e3:
        logger.exception("Fallback ReportLab PDF falló: %s", e3)
        return None


def _default_template():
    """Estructura tipo certificado institucional: bordes dorado/azul, cabecera dos logos, centro datos, pie dos firmas + sello. Tamaño fijo 1024x768 para que coincida vista previa y PDF."""
    return """<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
@page { size: 1024px 768px; margin: 0; }
* { box-sizing: border-box; }
body { font-family: 'Times New Roman', serif; margin: 0; padding: 0; width: 1024px; height: 768px; background: #f5f4f0; color: #333; overflow: hidden; }
.cert-wrap { position: relative; width: 1024px; height: 768px; padding: 24px; {% if background_url %} background-image: url({{ background_url }}); background-size: cover; background-position: center; {% endif %} }
/* Bordes decorativos dorado y azul */
.cert-wrap::before { content: ''; position: absolute; top: 0; left: 0; right: 0; bottom: 0; border: 2px solid #c9a227; pointer-events: none; }
.cert-wrap::after { content: ''; position: absolute; top: 6px; left: 6px; right: 6px; bottom: 6px; border: 1px solid #1e3a5f; pointer-events: none; }
.cert-inner { position: relative; z-index: 1; padding: 20px 28px; }
/* Cabecera: dos logos */
.header { display: table; width: 100%; margin-bottom: 24px; }
.header-left { display: table-cell; width: 50%; text-align: left; vertical-align: top; }
.header-right { display: table-cell; width: 50%; text-align: right; vertical-align: top; }
.header img { max-height: 72px; max-width: 160px; }
/* Contenido central */
.main { text-align: center; padding: 32px 24px; margin: 20px 0; }
.main h1 { font-size: 22px; margin: 0 0 28px 0; font-weight: bold; letter-spacing: 0.02em; }
.main .name { font-size: 20px; margin: 12px 0; font-weight: bold; }
.main .event { font-size: 16px; margin: 8px 0; }
.main .meta { font-size: 13px; margin: 16px 0 0 0; color: #555; }
.qr-block { margin-top: 20px; }
.qr-block img { width: 88px; height: 88px; }
/* Pie: dos firmas + sello */
.footer { display: table; width: 100%; margin-top: 28px; padding-top: 16px; }
.footer-left { display: table-cell; width: 33%; text-align: left; vertical-align: top; }
.footer-center { display: table-cell; width: 34%; text-align: center; vertical-align: middle; }
.footer-right { display: table-cell; width: 33%; text-align: right; vertical-align: top; }
.footer .sig-line { border-bottom: 1px solid #333; width: 180px; margin: 0 auto 6px auto; height: 28px; }
.footer-left .sig-line { margin-left: 0; }
.footer-right .sig-line { margin-right: 0; margin-left: auto; }
.footer .sig-name { font-size: 13px; font-weight: bold; margin: 4px 0 2px 0; }
.footer .sig-role { font-size: 12px; margin: 0; }
.footer .sig-org { font-size: 11px; color: #555; margin: 0; }
.seal { width: 64px; height: 64px; margin: 0 auto; }
</style></head>
<body>
<div class="cert-wrap">
<div class="cert-inner">
  <div class="header">
    <div class="header-left">{% if logo_left_url %}<img src="{{ logo_left_url }}" alt=""/>{% endif %}
      {% if institution %}<div style="font-size:12px;margin-top:4px;">{{ institution }}</div>{% endif %}
    </div>
    <div class="header-right">{% if logo_right_url %}<img src="{{ logo_right_url }}" alt=""/>{% endif %}
      {% if partner_organization %}<div style="font-size:12px;margin-top:4px;">{{ partner_organization }}</div>{% endif %}
    </div>
  </div>
  <div class="main">
    <h1>Certificado</h1>
    <p class="name">{{ full_name }}</p>
    <p class="event">{{ event_name }}</p>
    {% if membership_type %}<p class="meta">Membresía: {{ membership_type|upper }}</p>{% if membership_start or membership_end %}<p class="meta">Vigente: {{ membership_start }} – {{ membership_end }}</p>{% endif %}{% endif %}
    {% if duration_hours %}<p class="meta">Duración: {{ duration_hours }} horas</p>{% endif %}
    <p class="meta">Fecha de emisión: {{ date_emission }} &nbsp;|&nbsp; Código: {{ certificate_code }}</p>
    {% if qr_base64 %}<div class="qr-block"><img src="data:image/png;base64,{{ qr_base64 }}" alt="QR"/> <span style="font-size:11px;">Verificar: {{ verify_url }}</span></div>{% endif %}
  </div>
  <div class="footer">
    <div class="footer-left">
      <div class="sig-line"></div>
      <p class="sig-name">{{ rector_name }}</p>
      <p class="sig-role">{{ rector_title }}</p>
      <p class="sig-org">{{ institution }}</p>
    </div>
    <div class="footer-center">{% if seal_url %}<img class="seal" src="{{ seal_url }}" alt=""/>{% else %}<span style="display:inline-block;width:64px;height:64px;border:2px solid #c9a227;border-radius:50%;"></span>{% endif %}</div>
    <div class="footer-right">
      <div class="sig-line"></div>
      <p class="sig-name">{{ academic_director_name }}</p>
      <p class="sig-role">{{ director_title }}</p>
      <p class="sig-org">{{ partner_organization }}</p>
    </div>
  </div>
</div>
</div>
</body></html>"""


def _get_certificate_html(event_like, sample_data, verification_url=None, use_file_urls=False):
    """
    Genera solo el HTML del certificado (sin convertir a PDF). Misma lógica para vista previa y PDF.
    event_like: CertificateEvent o objeto con template_id, name, institution, template_html, logos, etc.
    sample_data: dict con participant_name, program_name, hours, issue_date, certificate_code, verification_url, institution.
    use_file_urls: si True (generación PDF) usa file:// para assets locales; si False (vista previa en navegador) solo HTTP.
    Retorna str HTML o None.
    """
    base = _get_base_url()
    verify_url = (sample_data.get('verification_url') or verification_url or (base + '/verify/PREVIEW')).strip()
    qr_b64 = _qr_base64(verify_url)
    full_name = sample_data.get('participant_name', 'Nombre de Ejemplo')
    event_name = sample_data.get('program_name', getattr(event_like, 'name', 'Certificado'))
    date_str = sample_data.get('issue_date', datetime.utcnow().strftime('%Y-%m-%d'))
    certificate_code = sample_data.get('certificate_code', 'PREVIEW-0000')
    # Plantilla JSON
    tid = getattr(event_like, 'template_id', None)
    template_obj = None
    if tid:
        from app import CertificateTemplate, _enable_multi_tenant_catalog
        template_obj = CertificateTemplate.query.get(tid)
        if template_obj and _enable_multi_tenant_catalog():
            ev_org = int(getattr(event_like, 'organization_id', None) or 1)
            if int(getattr(template_obj, 'organization_id', None) or 1) != ev_org:
                template_obj = None
    json_layout = (getattr(template_obj, 'json_layout', None) or '').strip() if template_obj else ''
    if template_obj and json_layout:
        try:
            from certificate_template_routes import render_html_from_json_layout
            from nodeone.services.certificate_template_data import build_certificate_template_data

            data = build_certificate_template_data(
                event_like,
                participant_name=full_name,
                document_id=sample_data.get('document_id', ''),
                program_name=event_name,
                certificate_code=certificate_code,
                verification_url=verify_url,
                issue_date=date_str,
                membership_type=sample_data.get('membership_type', ''),
                membership_start=sample_data.get('membership_start', ''),
                membership_end=sample_data.get('membership_end', ''),
                body_text=sample_data.get('body_text', ''),
            )
            upload_dir = _certificates_upload_dir()
            html = render_html_from_json_layout(template_obj, data, base, qr_b64, upload_dir, use_file_urls=use_file_urls)
            if html:
                return html
        except Exception as e:
            logger.warning("Plantilla JSON falló: %s", e)
    # HTML/Jinja
    from jinja2 import Template
    template_html = getattr(event_like, 'template_html', None) or _default_template()
    partner_org = getattr(event_like, 'partner_organization', None) or 'Easy NodeOne'

    def _abs(u):
        if not u:
            return ''
        u = (u or '').strip()
        if u.startswith('http'):
            return u
        if u.startswith('/'):
            return base + u
        return base + '/' + u

    logo_left_url = _abs(getattr(event_like, 'logo_left_url', None))
    logo_right_url = _abs(getattr(event_like, 'logo_right_url', None))
    seal_url = _abs(getattr(event_like, 'seal_url', None))
    raw_bg = getattr(event_like, 'background_url', None)
    background_url = _abs(raw_bg)
    if use_file_urls:
        for url_val, ref in [(getattr(event_like, 'logo_left_url', None), 'logo_left_url'), (getattr(event_like, 'logo_right_url', None), 'logo_right_url'), (getattr(event_like, 'seal_url', None), 'seal_url'), (raw_bg, 'background_url')]:
            if url_val and '/static/uploads/certificates/' in (url_val or ''):
                p = _background_path_from_url(url_val)
                if p and os.path.isfile(p):
                    val = 'file://' + os.path.abspath(p)
                    if ref == 'logo_left_url':
                        logo_left_url = val
                    elif ref == 'logo_right_url':
                        logo_right_url = val
                    elif ref == 'seal_url':
                        seal_url = val
                    else:
                        background_url = val

    return Template(template_html).render(
        full_name=full_name,
        event_name=event_name,
        date_emission=date_str,
        certificate_code=certificate_code,
        verification_hash='',
        verify_url=verify_url,
        qr_base64=qr_b64,
        institution=getattr(event_like, 'institution', '') or '',
        partner_organization=partner_org,
        duration_hours=getattr(event_like, 'duration_hours', None),
        rector_name=getattr(event_like, 'rector_name', '') or '',
        academic_director_name=getattr(event_like, 'academic_director_name', '') or '',
        rector_title='Rector',
        director_title='Directora Académica',
        logo_left_url=logo_left_url,
        logo_right_url=logo_right_url,
        seal_url=seal_url,
        background_url=background_url,
        membership_type=sample_data.get('membership_type', ''),
        membership_start=sample_data.get('membership_start', ''),
        membership_end=sample_data.get('membership_end', ''),
    )


@certificates_api_bp.route('/request-certificate/<int:event_id>', methods=['POST'])
@login_required
def request_certificate(event_id):
    """Genera certificado para el certificate_event event_id. Retorna download_url y certificate_code."""
    import app as _cert_app
    from app import app, db, CertificateEvent, Certificate
    cert_event = CertificateEvent.query.get(event_id)
    if not cert_event:
        return jsonify({'error': 'Evento no encontrado'}), 404
    uo = int(_cert_member_org_id())
    if int(getattr(cert_event, 'organization_id', None) or 1) != uo:
        return jsonify({'error': 'Evento no encontrado'}), 404
    if not cert_event.is_active:
        return jsonify({'error': 'Evento de certificado no activo'}), 400
    if not _user_qualified_for_event(current_user, cert_event):
        return jsonify({'error': 'No cumple requisitos de membresía o evento'}), 403
    existing = Certificate.query.filter_by(
        user_id=current_user.id,
        certificate_event_id=cert_event.id
    ).first()
    if existing:
        base = _get_base_url()
        return jsonify({
            'certificate_code': existing.certificate_code,
            'download_url': f"{base}/api/certificates/{existing.certificate_code}/download",
            'already_issued': True,
        }), 200
    certificate_code = _next_certificate_code(cert_event)
    verification_hash = hashlib.sha256(
        (certificate_code + app.config.get('SECRET_KEY', '')).encode()
    ).hexdigest()
    base = _get_base_url()
    verify_url = f"{base}/verify/{certificate_code}"
    try:
        db.session.refresh(cert_event)
    except Exception:
        pass
    tid = getattr(cert_event, 'template_id', None)
    logger.info("Certificado emisión event_id=%s template_id=%s", cert_event.id, tid)
    pdf_bytes = _render_pdf(cert_event, current_user, certificate_code, verification_hash, verify_url)
    if not pdf_bytes:
        return jsonify({'error': 'No se pudo generar el PDF'}), 500
    cert_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'instance', 'certificates')
    os.makedirs(cert_dir, exist_ok=True)
    safe_code = certificate_code.replace('/', '_')
    pdf_path = os.path.join(cert_dir, f"{safe_code}.pdf")
    with open(pdf_path, 'wb') as f:
        f.write(pdf_bytes)
    cert = Certificate(
        user_id=current_user.id,
        certificate_event_id=cert_event.id,
        certificate_code=certificate_code,
        verification_hash=verification_hash,
        pdf_path=pdf_path,
        status='generated',
    )
    db.session.add(cert)
    db.session.commit()
    download_url = f"{base}/api/certificates/{certificate_code}/download"
    if _cert_app.Mail and getattr(current_user, 'email', None):
        try:
            from flask_mail import Message

            cert_oid = int(
                getattr(cert_event, 'organization_id', None) or _cert_member_org_id()
            )
            try:
                ok_smtp, _ = _cert_app.apply_transactional_smtp_for_organization(cert_oid)
                if ok_smtp and _cert_app.mail:
                    msg = Message(
                        subject=f"Tu certificado: {cert_event.name}",
                        recipients=[current_user.email],
                        body=(
                            f"Hola {current_user.first_name},\n\nAdjunto tu certificado.\n"
                            f"Código: {certificate_code}\nVerificación: {verify_url}"
                        ),
                        attachments=[
                            (f"certificado_{safe_code}.pdf", "application/pdf", pdf_bytes)
                        ],
                    )
                    _cert_app.mail.send(msg)
            finally:
                _cert_app.apply_email_config_from_db()
        except Exception:
            pass
    return jsonify({
        'certificate_code': certificate_code,
        'download_url': download_url,
        'already_issued': False,
    }), 201


@certificates_page_bp.route('/certificates')
@login_required
def certificates_page():
    """Documentos → Certificados: eventos emitidos + membresía (solicitar/descargar)."""
    from flask_login import current_user

    event_certificates = []
    events_enabled = False
    try:
        from app import has_saas_module_enabled, tenant_data_organization_id

        oid = int(tenant_data_organization_id())
        events_enabled = bool(has_saas_module_enabled(oid, 'events'))
    except Exception:
        events_enabled = False

    if events_enabled:
        try:
            from nodeone.modules.events.services.user_certificates import (
                link_unassigned_participants_for_user,
                query_user_event_certificates,
            )

            link_unassigned_participants_for_user(current_user)
            event_certificates = query_user_event_certificates(current_user)
        except Exception:
            event_certificates = []

    return render_template(
        'certificates.html',
        event_certificates=event_certificates,
        events_enabled=events_enabled,
        verify_endpoint='certificates_public.verify_event_certificate_alias',
    )


def _certificates_pdf_dir():
    """Directorio canónico donde se guardan los PDFs de certificados (con sep final)."""
    d = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'instance', 'certificates')
    return os.path.normpath(os.path.abspath(d)) + os.sep


@certificates_api_bp.route('/certificates/<certificate_code>/download', methods=['GET'])
@login_required
def download_certificate(certificate_code):
    """Descarga el PDF del certificado si pertenece al usuario."""
    from app import Certificate
    cert = Certificate.query.filter_by(certificate_code=certificate_code).first()
    if not cert:
        return jsonify({'error': 'Certificado no encontrado'}), 404
    if cert.user_id != current_user.id:
        return jsonify({'error': 'No autorizado'}), 403
    if not cert.pdf_path or not os.path.isfile(cert.pdf_path):
        return jsonify({'error': 'Archivo no disponible'}), 404
    allowed_dir = _certificates_pdf_dir()
    real_path = os.path.normpath(os.path.realpath(cert.pdf_path))
    if not real_path.startswith(allowed_dir):
        return jsonify({'error': 'Archivo no disponible'}), 404
    return send_file(
        real_path,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f"certificado_{certificate_code.replace('/', '_')}.pdf",
    )


def _admin_required(f):
    from functools import wraps
    @wraps(f)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated or not getattr(current_user, 'is_admin', False):
            return jsonify({'error': 'No autorizado'}), 403
        return f(*args, **kwargs)
    return wrapped


def _reject_orphan_certificate_event_payload(data, *, partial: bool = False) -> str | None:
    """Formatos sin plan ni evento no están permitidos en esta pantalla."""
    mem = data.get('membership_required_id')
    ev = data.get('event_required_id')
    mem_id = int(mem) if mem not in (None, '') else None
    ev_id = int(ev) if ev not in (None, '') else None
    if mem_id is not None or ev_id is not None:
        return None
    if partial and 'is_active' not in data:
        return None
    if partial and not data.get('is_active'):
        return None
    return (
        'No se permiten certificados huérfanos. Asigne un plan de membresía '
        'o administre seminarios desde Eventos → Certificados.'
    )


def _reject_orphan_certificate_event_model(ev, data) -> str | None:
    mem_id = ev.membership_required_id
    ev_id = ev.event_required_id
    if 'membership_required_id' in data:
        v = data['membership_required_id']
        mem_id = int(v) if v not in (None, '') else None
    if 'event_required_id' in data:
        v = data['event_required_id']
        ev_id = int(v) if v not in (None, '') else None
    if mem_id is not None or ev_id is not None:
        return None
    if 'is_active' in data and not data.get('is_active'):
        return None
    return (
        'No se permiten certificados huérfanos. Asigne un plan de membresía '
        'o administre seminarios desde Eventos → Certificados.'
    )


def _validate_certificate_event_refs_for_org(org_id, data, partial=False):
    from app import MembershipPlan, CertificateTemplate, Event
    oid = int(org_id)
    if (not partial) or ('membership_required_id' in data):
        v = data.get('membership_required_id')
        if v not in (None, ''):
            p = MembershipPlan.query.filter_by(id=int(v), organization_id=oid).first()
            if not p:
                return 'Plan de membresía no válido para esta organización'
    if (not partial) or ('event_required_id' in data):
        v = data.get('event_required_id')
        if v not in (None, ''):
            e = Event.query.get(int(v))
            if not e:
                return 'Evento no válido'
    if (not partial) or ('template_id' in data):
        if partial and 'template_id' not in data:
            pass
        else:
            tid = _parse_template_id(data.get('template_id'))
            if tid:
                t = CertificateTemplate.query.filter_by(id=tid, organization_id=oid).first()
                if not t:
                    return 'Plantilla no válida para esta organización'
    return None


def _user_display_name(user) -> str:
    if not user:
        return '—'
    parts = [
        getattr(user, 'first_name', None),
        getattr(user, 'last_name', None),
    ]
    name = ' '.join(p for p in parts if p).strip()
    return name or getattr(user, 'email', None) or f'Usuario #{getattr(user, "id", "?")}'


def _certificate_to_admin_dict(cert) -> dict:
    user = getattr(cert, 'user', None)
    return {
        'id': cert.id,
        'certificate_code': cert.certificate_code,
        'user_id': cert.user_id,
        'user_name': _user_display_name(user),
        'user_email': getattr(user, 'email', None) if user else None,
        'generated_at': cert.generated_at.isoformat() if cert.generated_at else None,
        'status': cert.status or 'generated',
    }


def _remove_certificate_pdf_file(pdf_path: str | None) -> None:
    if not pdf_path:
        return
    allowed_dir = _certificates_pdf_dir()
    real_path = os.path.normpath(os.path.realpath(pdf_path))
    if not real_path.startswith(allowed_dir) or not os.path.isfile(real_path):
        return
    try:
        os.remove(real_path)
    except OSError:
        logger.warning('No se pudo eliminar PDF de certificado: %s', real_path)


def _cert_event_to_dict(e):
    """Serializa un CertificateEvent para API."""
    return {
        'id': e.id,
        'organization_id': getattr(e, 'organization_id', None) or 1,
        'name': e.name,
        'is_active': e.is_active,
        'verification_enabled': getattr(e, 'verification_enabled', True),
        'code_prefix': e.code_prefix or 'REL',
        'institution': e.institution,
        'convenio': e.convenio,
        'partner_organization': getattr(e, 'partner_organization', None),
        'rector_name': e.rector_name,
        'academic_director_name': e.academic_director_name,
        'logo_left_url': e.logo_left_url,
        'logo_right_url': e.logo_right_url,
        'seal_url': e.seal_url,
        'background_url': getattr(e, 'background_url', None),
        'template_id': getattr(e, 'template_id', None),
        'membership_required_id': e.membership_required_id,
        'event_required_id': e.event_required_id,
        'duration_hours': e.duration_hours,
        'start_date': e.start_date.isoformat() if e.start_date else None,
        'end_date': e.end_date.isoformat() if e.end_date else None,
        'template_html': e.template_html,
        'created_at': e.created_at.isoformat() if e.created_at else None,
    }


@certificates_api_bp.route('/admin/certificate-events', methods=['GET'])
@login_required
@_admin_required
def admin_list_certificate_events():
    """Lista formatos MEM/REG/PLAN y formatos vinculados a eventos EN1."""
    from app import CertificateEvent, EventCertificate

    coid = _cert_admin_org_id()
    _seed_org_certificate_events(coid)
    events = CertificateEvent.query.filter_by(organization_id=coid).order_by(
        CertificateEvent.created_at.desc()
    ).all()
    from app import Certificate

    mem_reg = [_cert_event_to_dict(e) for e in events if e.membership_required_id is not None]
    for row in mem_reg:
        row['kind'] = 'certificate_event'
        row['issued_count'] = Certificate.query.filter_by(
            certificate_event_id=row['id']
        ).count()

    event_formats = [_cert_event_to_dict(e) for e in events if e.event_required_id is not None]
    for row in event_formats:
        row['kind'] = 'event_seminar'
        row['event_id'] = int(row['event_required_id'])
        row['issued_count'] = EventCertificate.query.filter_by(event_id=row['event_id']).count()

    return jsonify({'items': mem_reg + event_formats})


@certificates_api_bp.route('/admin/certificate-events', methods=['POST'])
@login_required
@_admin_required
def admin_create_certificate_event():
    """Crea un CertificateEvent (admin)."""
    from app import db, CertificateEvent
    data = request.get_json() or {}
    name = data.get('name')
    if not name:
        return jsonify({'error': 'name es obligatorio'}), 400
    coid = _cert_admin_org_id()
    err = _reject_orphan_certificate_event_payload(data, partial=False)
    if err:
        return jsonify({'error': err}), 400
    err = _validate_certificate_event_refs_for_org(coid, data, partial=False)
    if err:
        return jsonify({'error': err}), 400
    ev = CertificateEvent(
        organization_id=coid,
        name=name,
        start_date=datetime.fromisoformat(data['start_date'].replace('Z', '+00:00')) if data.get('start_date') else None,
        end_date=datetime.fromisoformat(data['end_date'].replace('Z', '+00:00')) if data.get('end_date') else None,
        duration_hours=float(data['duration_hours']) if data.get('duration_hours') is not None else None,
        institution=data.get('institution'),
        convenio=data.get('convenio'),
        rector_name=data.get('rector_name'),
        academic_director_name=data.get('academic_director_name'),
        partner_organization=data.get('partner_organization'),
        logo_left_url=data.get('logo_left_url'),
        logo_right_url=data.get('logo_right_url'),
        seal_url=data.get('seal_url'),
        background_url=data.get('background_url'),
        membership_required_id=int(data['membership_required_id']) if data.get('membership_required_id') not in (None, '') else None,
        event_required_id=int(data['event_required_id']) if data.get('event_required_id') not in (None, '') else None,
        template_html=data.get('template_html'),
        template_id=_parse_template_id(data.get('template_id')),
        is_active=bool(data.get('is_active', True)),
        verification_enabled=bool(data.get('verification_enabled', True)),
        code_prefix=(data.get('code_prefix') or 'REL').strip().upper()[:20],
    )
    db.session.add(ev)
    db.session.commit()
    return jsonify({'success': True, 'item': _cert_event_to_dict(ev)}), 201


@certificates_api_bp.route('/admin/certificate-events/<int:event_id>', methods=['GET'])
@login_required
@_admin_required
def admin_get_certificate_event(event_id):
    """Obtiene un CertificateEvent por id."""
    from app import CertificateEvent
    coid = _cert_admin_org_id()
    ev = CertificateEvent.query.filter_by(id=event_id, organization_id=coid).first()
    if not ev:
        return jsonify({'error': 'No encontrado'}), 404
    return jsonify({'item': _cert_event_to_dict(ev)})


@certificates_api_bp.route('/admin/certificate-events/<int:event_id>', methods=['PUT', 'PATCH'])
@login_required
@_admin_required
def admin_update_certificate_event(event_id):
    """Actualiza un CertificateEvent (admin)."""
    from app import db, CertificateEvent
    coid = _cert_admin_org_id()
    ev = CertificateEvent.query.filter_by(id=event_id, organization_id=coid).first()
    if not ev:
        return jsonify({'error': 'No encontrado'}), 404
    data = request.get_json() or {}
    err = _reject_orphan_certificate_event_model(ev, data)
    if err:
        return jsonify({'error': err}), 400
    err = _validate_certificate_event_refs_for_org(coid, data, partial=True)
    if err:
        return jsonify({'error': err}), 400
    if data.get('name'):
        ev.name = data['name']
    if 'start_date' in data:
        ev.start_date = datetime.fromisoformat(data['start_date'].replace('Z', '+00:00')) if data.get('start_date') else None
    if 'end_date' in data:
        ev.end_date = datetime.fromisoformat(data['end_date'].replace('Z', '+00:00')) if data.get('end_date') else None
    if 'duration_hours' in data:
        ev.duration_hours = float(data['duration_hours']) if data.get('duration_hours') is not None else None
    for key in ('institution', 'convenio', 'rector_name', 'academic_director_name', 'partner_organization',
                'logo_left_url', 'logo_right_url', 'seal_url', 'template_html'):
        if key in data:
            setattr(ev, key, data.get(key) or None)
    if 'background_url' in data and hasattr(ev, 'background_url'):
        ev.background_url = data.get('background_url') or None
    if 'template_id' in data and hasattr(ev, 'template_id'):
        ev.template_id = _parse_template_id(data.get('template_id'))
    if 'code_prefix' in data:
        ev.code_prefix = (data.get('code_prefix') or 'REL').strip().upper()[:20]
    if 'membership_required_id' in data:
        v = data['membership_required_id']
        ev.membership_required_id = int(v) if v not in (None, '') else None
    if 'event_required_id' in data:
        v = data['event_required_id']
        ev.event_required_id = int(v) if v not in (None, '') else None
    if 'is_active' in data:
        ev.is_active = bool(data['is_active'])
    if 'verification_enabled' in data:
        ev.verification_enabled = bool(data['verification_enabled'])
    db.session.commit()
    return jsonify({'success': True, 'item': _cert_event_to_dict(ev)})


@certificates_api_bp.route('/admin/certificate-events/<int:event_id>/certificates', methods=['GET'])
@login_required
@_admin_required
def admin_list_issued_certificates(event_id):
    """Lista certificados emitidos para un formato MEM/REG/PLAN (admin)."""
    from app import CertificateEvent, Certificate

    coid = _cert_admin_org_id()
    ev = CertificateEvent.query.filter_by(id=event_id, organization_id=coid).first()
    if not ev:
        return jsonify({'error': 'No encontrado'}), 404
    rows = (
        Certificate.query.filter_by(certificate_event_id=event_id)
        .order_by(Certificate.generated_at.desc(), Certificate.id.desc())
        .all()
    )
    return jsonify({
        'event': _cert_event_to_dict(ev),
        'items': [_certificate_to_admin_dict(c) for c in rows],
    })


@certificates_api_bp.route('/admin/certificates/<int:cert_id>', methods=['DELETE'])
@login_required
@_admin_required
def admin_delete_issued_certificate(cert_id):
    """Elimina un certificado emitido (registro + PDF) para permitir re-emisión."""
    from app import db, Certificate, CertificateEvent

    coid = _cert_admin_org_id()
    cert = Certificate.query.get(cert_id)
    if not cert:
        return jsonify({'error': 'No encontrado'}), 404
    ev = CertificateEvent.query.filter_by(
        id=cert.certificate_event_id,
        organization_id=coid,
    ).first()
    if not ev:
        return jsonify({'error': 'No autorizado'}), 403
    code = cert.certificate_code
    _remove_certificate_pdf_file(cert.pdf_path)
    db.session.delete(cert)
    db.session.commit()
    return jsonify({'success': True, 'certificate_code': code})


@certificates_api_bp.route('/admin/certificate-events/<int:event_id>', methods=['DELETE'])
@login_required
@_admin_required
def admin_delete_certificate_event(event_id):
    """Elimina un CertificateEvent (admin). No borra certificados ya emitidos."""
    from app import db, CertificateEvent
    from nodeone.services.certificate_assets import certificate_event_delete_blocked

    coid = _cert_admin_org_id()
    ev = CertificateEvent.query.filter_by(id=event_id, organization_id=coid).first()
    if not ev:
        return jsonify({'error': 'No encontrado'}), 404
    blocked = certificate_event_delete_blocked(ev)
    if blocked:
        return jsonify({'error': blocked}), 400
    db.session.delete(ev)
    db.session.commit()
    return jsonify({'success': True})


@certificates_api_bp.route('/admin/certificate-events/upload', methods=['POST'])
@login_required
@_admin_required
def admin_upload_certificate_asset():
    """Sube imagen para certificado: fondo, logo_left, logo_right, seal. Multipart: file + type (fondo|logo_left|logo_right|seal)."""
    if 'file' not in request.files and 'upload' not in request.files:
        return jsonify({'error': 'Falta el archivo'}), 400
    f = request.files.get('file') or request.files.get('upload')
    asset_type = (request.form.get('type') or request.form.get('asset_type') or 'fondo').strip().lower()
    if asset_type not in ('fondo', 'logo_left', 'logo_right', 'seal'):
        asset_type = 'fondo'
    if not f or f.filename == '':
        return jsonify({'error': 'No se seleccionó archivo'}), 400
    ext = os.path.splitext(f.filename)[1].lower() or '.png'
    if ext not in ('.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg'):
        return jsonify({'error': 'Formato no permitido. Use PNG, JPG, GIF, WebP o SVG.'}), 400
    import uuid
    safe_name = f"{asset_type}_{uuid.uuid4().hex[:12]}{ext}"
    upload_dir = _certificates_upload_dir()
    path = os.path.join(upload_dir, safe_name)
    f.save(path)
    url = f"/static/uploads/certificates/{safe_name}"
    return jsonify({'success': True, 'url': url, 'filename': safe_name})


@certificates_api_bp.route('/admin/certificate-events/preview', methods=['POST'])
@login_required
@_admin_required
def admin_certificate_event_preview():
    """
    Vista previa del certificado: body JSON con campos del formato (event_id opcional para cargar y sobreescribir).
    Devuelve HTML para mostrar en iframe.
    """
    from app import CertificateEvent
    data = request.get_json() or {}
    event_id = data.get('event_id')
    if event_id:
        coid = _cert_admin_org_id()
        ev = CertificateEvent.query.filter_by(id=int(event_id), organization_id=coid).first()
        if not ev:
            return jsonify({'error': 'Evento no encontrado'}), 404
        event_like = SimpleNamespace(
            id=ev.id,
            organization_id=getattr(ev, 'organization_id', None) or 1,
            name=data.get('name', ev.name),
            code_prefix=data.get('code_prefix', ev.code_prefix),
            template_id=_parse_template_id(data.get('template_id')) if 'template_id' in data else getattr(ev, 'template_id', None),
            institution=data.get('institution', ev.institution),
            partner_organization=data.get('partner_organization', getattr(ev, 'partner_organization', None)),
            rector_name=data.get('rector_name', ev.rector_name),
            academic_director_name=data.get('academic_director_name', ev.academic_director_name),
            logo_left_url=data.get('logo_left_url', ev.logo_left_url),
            logo_right_url=data.get('logo_right_url', ev.logo_right_url),
            seal_url=data.get('seal_url', ev.seal_url),
            background_url=data.get('background_url', getattr(ev, 'background_url', None)),
            template_html=data.get('template_html', ev.template_html),
            duration_hours=float(data['duration_hours']) if data.get('duration_hours') not in (None, '') else ev.duration_hours,
            start_date=data.get('start_date') or ev.start_date,
            end_date=data.get('end_date') or ev.end_date,
            membership_required_id=data.get('membership_required_id', ev.membership_required_id),
        )
    else:
        event_like = SimpleNamespace(
            id=None,
            organization_id=_cert_admin_org_id(),
            name=data.get('name', 'Vista previa'),
            code_prefix=data.get('code_prefix') or '',
            template_id=_parse_template_id(data.get('template_id')),
            institution=data.get('institution') or '',
            partner_organization=data.get('partner_organization') or '',
            rector_name=data.get('rector_name') or '',
            academic_director_name=data.get('academic_director_name') or '',
            logo_left_url=data.get('logo_left_url') or '',
            logo_right_url=data.get('logo_right_url') or '',
            seal_url=data.get('seal_url') or '',
            background_url=data.get('background_url') or '',
            template_html=data.get('template_html') or '',
            duration_hours=float(data['duration_hours']) if data.get('duration_hours') not in (None, '') else None,
            start_date=data.get('start_date'),
            end_date=data.get('end_date'),
            membership_required_id=data.get('membership_required_id'),
        )
    from nodeone.services.certificate_template_data import build_certificate_template_data

    sample_data = build_certificate_template_data(
        event_like,
        participant_name='Nombre de Ejemplo',
        document_id='8-888-8888',
        program_name=getattr(event_like, 'name', 'Certificado'),
        certificate_code='PREVIEW-0000',
        verification_url=_get_base_url() + '/verify/PREVIEW-0000',
        membership_type='deluxe',
        membership_start='2025-01-01',
        membership_end='2026-01-01',
    )
    html = _get_certificate_html(event_like, sample_data)
    if not html:
        return jsonify({'error': 'No se pudo generar la vista previa'}), 500
    # Misma escala que el PDF (1024px): viewport fijo para que vista previa y descarga se vean igual
    if '<head>' in html:
        html = html.replace('<head>', '<head><meta name="viewport" content="width=1024">', 1)
    return Response(html, mimetype='text/html; charset=utf-8')


def _verify_saas_org_name(organization_id):
    if not organization_id:
        return ''
    try:
        from models.saas import SaasOrganization

        org = SaasOrganization.query.get(int(organization_id))
        return (org.name or '').strip() if org else ''
    except Exception:
        return ''


def _verify_date_range_display(obj):
    if not obj:
        return ''
    sd = getattr(obj, 'start_date', None)
    ed = getattr(obj, 'end_date', None)
    if sd and ed:
        try:
            return f'{sd.strftime("%d/%m/%Y")} — {ed.strftime("%d/%m/%Y")}'
        except Exception:
            pass
    return ''


def _verify_issuer_membership(cert_ev):
    if not cert_ev:
        return ''
    return _verify_saas_org_name(getattr(cert_ev, 'organization_id', None))


def _verify_issuer_event(ev):
    if not ev or not getattr(ev, 'created_by', None):
        return ''
    try:
        from app import User

        u = User.query.get(ev.created_by)
        if not u:
            return ''
        return _verify_saas_org_name(u.organization_id)
    except Exception:
        return ''


def _verify_expired_cert(ec):
    exp_at = getattr(ec, 'expires_at', None)
    if not exp_at:
        return False
    try:
        exp_naive = exp_at.replace(tzinfo=None) if getattr(exp_at, 'tzinfo', None) else exp_at
        return datetime.utcnow() > exp_naive
    except Exception:
        return False


@certificates_public_bp.route('/verify/<certificate_code>')
def verify(certificate_code):
    """Página pública de verificación. Muestra nombre, evento, fecha, estado válido."""
    from sqlalchemy import or_

    from app import Certificate, Event, EventCertificate, EventParticipant

    cert = Certificate.query.filter_by(certificate_code=certificate_code).first()
    if cert:
        ev = cert.certificate_event
        user = cert.user
        full_name = f"{user.first_name} {user.last_name}".strip()
        event_date_range = _verify_date_range_display(ev)
        issuer_organization = _verify_issuer_membership(ev)
        return render_template_string(
            _verify_template(),
            valid=True,
            revoked=False,
            expired_cert=False,
            full_name=full_name,
            event_name=ev.name if ev else '',
            date_emission=cert.generated_at.strftime('%Y-%m-%d') if cert.generated_at else None,
            certificate_code=certificate_code,
            certificate_type='membership',
            document_masked=None,
            event_date_range=event_date_range,
            certificate_title='',
            issuer_organization=issuer_organization,
            expires_display=None,
        ), 200

    ec = (
        EventCertificate.query.filter(
            or_(
                EventCertificate.certificate_number == certificate_code,
                EventCertificate.verification_token == certificate_code,
            )
        )
        .first()
    )
    if ec:
        revoked = (getattr(ec, 'status', '') or '').lower() == 'revoked' or not ec.is_active
        expired_cert = _verify_expired_cert(ec)
        valid_ok = not revoked and not expired_cert
        part = EventParticipant.query.get(ec.participant_id)
        ev = Event.query.get(ec.event_id)
        display = ''
        if part:
            display = (part.full_name or '').strip() or ' '.join(
                p
                for p in (
                    part.first_name,
                    part.middle_name,
                    part.last_name,
                    part.second_last_name,
                )
                if p
            ).strip()
        document_masked = None
        try:
            from nodeone.modules.events.services.certificates import mask_document

            if part and getattr(part, 'document_id', None):
                document_masked = mask_document(part.document_id)
        except Exception:
            document_masked = None
        event_date_range = _verify_date_range_display(ev)
        issuer_organization = _verify_issuer_event(ev)
        cert_title = ((getattr(ec, 'title', None) or '').strip()) or ''
        expires_display = None
        if ec.expires_at:
            try:
                expires_display = ec.expires_at.strftime('%d/%m/%Y %H:%M')
            except Exception:
                expires_display = str(ec.expires_at)
        return render_template_string(
            _verify_template(),
            valid=valid_ok,
            revoked=revoked,
            expired_cert=expired_cert,
            full_name=display or None,
            event_name=(ev.title if ev else '') or '',
            date_emission=ec.issued_date.strftime('%Y-%m-%d') if ec.issued_date else None,
            certificate_code=ec.certificate_number,
            certificate_type=(getattr(ec, 'certificate_type', None) or ''),
            document_masked=document_masked,
            event_date_range=event_date_range,
            certificate_title=cert_title,
            issuer_organization=issuer_organization,
            expires_display=expires_display,
        ), 200

    return render_template_string(
        _verify_template(),
        valid=False,
        revoked=False,
        expired_cert=False,
        full_name=None,
        event_name=None,
        date_emission=None,
        certificate_code=certificate_code,
        certificate_type='',
        document_masked=None,
        event_date_range='',
        certificate_title='',
        issuer_organization='',
        expires_display=None,
    ), 404


@certificates_public_bp.route('/certificates/verify/<certificate_code>')
def verify_event_certificate_alias(certificate_code):
    """Alias planificado: mismo cuerpo que /verify/<code> (certificados de membresía o de evento)."""
    return verify(certificate_code)


def _verify_template():
    return """<!DOCTYPE html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Verificación de certificado</title>
<style>body{font-family:sans-serif;max-width:520px;margin:40px auto;padding:20px;line-height:1.45;} .valid{color:green;} .invalid{color:#999;} .revoked{color:#b45309;} .expired{color:#92400e;}</style></head>
<body>
<h1>Verificación de certificado</h1>
<p><strong>Código:</strong> {{ certificate_code }}</p>
{% if revoked %}
<p><strong>Nombre:</strong> {{ full_name }}</p>
<p><strong>Evento:</strong> {{ event_name }}</p>
{% if certificate_type %}<p><strong>Tipo:</strong> {{ certificate_type }}</p>{% endif %}
{% if certificate_title %}<p><strong>Título:</strong> {{ certificate_title }}</p>{% endif %}
{% if event_date_range %}<p><strong>Fechas del evento:</strong> {{ event_date_range }}</p>{% endif %}
{% if issuer_organization %}<p><strong>Organización emisora:</strong> {{ issuer_organization }}</p>{% endif %}
<p class="revoked">Estado: Revocado o anulado</p>
{% elif expired_cert %}
<p><strong>Nombre:</strong> {{ full_name }}</p>
<p><strong>Evento:</strong> {{ event_name }}</p>
{% if certificate_type %}<p><strong>Tipo:</strong> {{ certificate_type }}</p>{% endif %}
{% if certificate_title %}<p><strong>Título:</strong> {{ certificate_title }}</p>{% endif %}
{% if event_date_range %}<p><strong>Fechas del evento:</strong> {{ event_date_range }}</p>{% endif %}
{% if issuer_organization %}<p><strong>Organización emisora:</strong> {{ issuer_organization }}</p>{% endif %}
{% if expires_display %}<p><strong>Vencimiento:</strong> {{ expires_display }}</p>{% endif %}
{% if document_masked %}<p><strong>Documento:</strong> {{ document_masked }}</p>{% endif %}
<p><strong>Fecha de emisión:</strong> {{ date_emission }}</p>
<p class="expired">Estado: Caducado por fecha</p>
{% elif valid %}
<p><strong>Nombre:</strong> {{ full_name }}</p>
<p><strong>Evento:</strong> {{ event_name }}</p>
{% if certificate_type %}<p><strong>Tipo:</strong> {{ certificate_type }}</p>{% endif %}
{% if certificate_title %}<p><strong>Título:</strong> {{ certificate_title }}</p>{% endif %}
{% if event_date_range %}<p><strong>Fechas del evento:</strong> {{ event_date_range }}</p>{% endif %}
{% if issuer_organization %}<p><strong>Organización emisora:</strong> {{ issuer_organization }}</p>{% endif %}
{% if expires_display %}<p><strong>Vencimiento:</strong> {{ expires_display }}</p>{% endif %}
{% if document_masked %}<p><strong>Documento:</strong> {{ document_masked }}</p>{% endif %}
<p><strong>Fecha de emisión:</strong> {{ date_emission }}</p>
<p class="valid">Estado: Válido</p>
{% else %}
<p class="invalid">No encontrado o no válido.</p>
{% endif %}
</body></html>"""
