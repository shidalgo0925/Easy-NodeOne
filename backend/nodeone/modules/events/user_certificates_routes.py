"""Portal «Mis Certificados» — descarga de certificados de evento por el usuario."""

from __future__ import annotations

from flask import Blueprint, abort, flash, redirect, render_template, send_file, url_for
from flask_login import current_user, login_required

from nodeone.modules.events.services.user_certificates import (
    get_user_event_certificate,
    query_user_event_certificates,
    resolve_certificate_pdf_path,
)

my_event_certificates_bp = Blueprint('my_event_certificates', __name__, url_prefix='/my')


def _events_module_enabled():
    try:
        from app import has_saas_module_enabled, tenant_data_organization_id

        oid = int(tenant_data_organization_id())
        return bool(has_saas_module_enabled(oid, 'events'))
    except Exception:
        return True


@my_event_certificates_bp.route('/certificates')
@login_required
def my_certificates_list():
    """Alias: misma pantalla unificada bajo Documentos → Certificados."""
    return redirect(url_for('certificates_page.certificates_page'))


@my_event_certificates_bp.route('/certificates/<int:certificate_id>/download')
@login_required
def my_certificate_download(certificate_id: int):
    if not _events_module_enabled():
        abort(403)

    from flask import current_app

    cert = get_user_event_certificate(current_user, certificate_id)
    if cert is None:
        abort(403)

    path = resolve_certificate_pdf_path(current_app, cert)
    if not path:
        flash('Certificado no disponible, contacte al administrador.', 'error')
        return redirect(url_for('my_event_certificates.my_certificates_list'))

    safe_name = (cert.certificate_number or f'certificado-{cert.id}').replace('/', '-').replace('\\', '-')
    return send_file(
        path,
        as_attachment=True,
        download_name=f'{safe_name}.pdf',
        mimetype='application/pdf',
    )
