"""Rutas HTML admin — Facturación Electrónica."""

from __future__ import annotations

import json
from decimal import Decimal, InvalidOperation

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from models.efactura import ElectronicInvoiceDocument, ElectronicInvoiceEventLog
from models.saas import SaasOrganization
from nodeone.modules.efactura.services import config_service as cfg_svc
from nodeone.modules.efactura.services import issue as issue_svc
from nodeone.services.efactura_module import is_efactura_enabled_for_org
from nodeone.services.efactura_schema import ensure_efactura_schema

efactura_admin_bp = Blueprint('efactura_admin', __name__, url_prefix='/admin/efactura')


def _org_id() -> int:
    from app import admin_data_scope_organization_id, default_organization_id

    try:
        oid = int(admin_data_scope_organization_id())
    except Exception:
        oid = int(default_organization_id())
    if SaasOrganization.query.get(int(oid)) is None:
        return int(default_organization_id())
    return int(oid)


def _platform_admin() -> bool:
    return bool(current_user.is_authenticated and getattr(current_user, 'is_admin', False))


def _can_admin() -> bool:
    if not current_user.is_authenticated:
        return False
    if _platform_admin():
        return True
    from app import _user_has_any_admin_permission

    return bool(_user_has_any_admin_permission(current_user))


def _guard_module_html():
    oid = _org_id()
    if not is_efactura_enabled_for_org(oid):
        flash('El módulo Facturación Electrónica no está habilitado para esta organización.', 'error')
        return redirect(url_for('dashboard'))
    return None


@efactura_admin_bp.before_request
def _efactura_admin_before():
    from nodeone.core.db import db
    from nodeone.modules.efactura.config import is_efactura_globally_allowed

    if not is_efactura_globally_allowed():
        abort(404)
    if not current_user.is_authenticated:
        return redirect(url_for('auth.login', next=request.path))
    if not _can_admin():
        flash('No tenés permisos de administración.', 'error')
        return redirect(url_for('dashboard'))
    err = _guard_module_html()
    if err:
        return err
    try:
        ensure_efactura_schema(db, db.engine)
    except Exception:
        pass


@efactura_admin_bp.route('/')
@login_required
def efactura_index():
    return redirect(url_for('efactura_admin.efactura_config'))


@efactura_admin_bp.route('/config', methods=['GET', 'POST'])
@login_required
def efactura_config():
    oid = _org_id()
    config = cfg_svc.get_or_create_provider_config(oid)
    if request.method == 'POST':
        config.environment = (request.form.get('environment') or 'sandbox').strip()
        config.api_base_url = (request.form.get('api_base_url') or 'https://api.efacturapty.com').strip()
        config.default_branch = (request.form.get('default_branch') or '').strip() or None
        config.default_pos = (request.form.get('default_pos') or '001').strip() or '001'
        config.default_currency = (request.form.get('default_currency') or 'USD').strip() or 'USD'
        config.enabled = request.form.get('enabled') in ('1', 'on', 'true', 'yes')
        new_token = (request.form.get('api_token') or '').strip()
        if new_token:
            config.api_token_encrypted = new_token
        from nodeone.core.db import db

        db.session.commit()
        flash('Configuración guardada.', 'success')
        return redirect(url_for('efactura_admin.efactura_config'))
    return render_template(
        'efactura/config.html',
        config=config,
        token_display=cfg_svc.token_tail_display(config.api_token_encrypted),
        has_token=bool(cfg_svc.resolve_api_token(config)),
    )


@efactura_admin_bp.route('/emissions')
@login_required
def efactura_emissions():
    oid = _org_id()
    page = max(1, int(request.args.get('page', 1)))
    per_page = 25
    status_filter = (request.args.get('status') or '').strip()
    q = ElectronicInvoiceDocument.query.filter_by(organization_id=oid).order_by(
        ElectronicInvoiceDocument.created_at.desc()
    )
    if status_filter:
        q = q.filter(ElectronicInvoiceDocument.status == status_filter)
    pagination = q.paginate(page=page, per_page=per_page, error_out=False)
    return render_template(
        'efactura/emissions.html',
        pagination=pagination,
        documents=pagination.items,
        status_filter=status_filter,
    )


@efactura_admin_bp.route('/emissions/<int:doc_id>')
@login_required
def efactura_emission_detail(doc_id: int):
    oid = _org_id()
    doc = ElectronicInvoiceDocument.query.filter_by(id=doc_id, organization_id=oid).first_or_404()
    req_json = doc.request_payload
    res_json = doc.response_payload
    try:
        req_pretty = json.dumps(json.loads(req_json), indent=2, ensure_ascii=False) if req_json else ''
    except Exception:
        req_pretty = req_json or ''
    try:
        res_pretty = json.dumps(json.loads(res_json), indent=2, ensure_ascii=False) if res_json else ''
    except Exception:
        res_pretty = res_json or ''
    logs = (
        ElectronicInvoiceEventLog.query.filter_by(organization_id=oid, document_id=doc.id)
        .order_by(ElectronicInvoiceEventLog.created_at.desc())
        .limit(50)
        .all()
    )
    return render_template(
        'efactura/emission_detail.html',
        doc=doc,
        request_pretty=req_pretty,
        response_pretty=res_pretty,
        logs=logs,
    )


@efactura_admin_bp.route('/test-invoice', methods=['GET', 'POST'])
@login_required
def efactura_test_invoice():
    oid = _org_id()
    config = cfg_svc.get_or_create_provider_config(oid)
    if request.method == 'POST':
        try:
            amount = Decimal((request.form.get('amount') or '1').replace(',', '.'))
        except (InvalidOperation, ValueError):
            flash('Monto inválido.', 'error')
            return redirect(url_for('efactura_admin.efactura_test_invoice'))
        description = (request.form.get('description') or 'Servicio de prueba EN1').strip()
        email = (request.form.get('customer_email') or '').strip()
        try:
            doc = issue_svc.issue_test_invoice(
                oid,
                amount=amount,
                description=description,
                customer_email=email,
            )
        except Exception as exc:
            flash(str(exc), 'error')
            return redirect(url_for('efactura_admin.efactura_test_invoice'))
        if doc.status == 'accepted':
            flash(f'Factura autorizada. CUFE: {doc.cufe}', 'success')
        else:
            flash(doc.error_message or doc.authorization_message or 'Emisión no autorizada.', 'warning')
        return redirect(url_for('efactura_admin.efactura_emission_detail', doc_id=doc.id))
    return render_template('efactura/test_invoice.html', config=config)


@efactura_admin_bp.route('/logs')
@login_required
def efactura_logs():
    oid = _org_id()
    logs = (
        ElectronicInvoiceEventLog.query.filter_by(organization_id=oid)
        .order_by(ElectronicInvoiceEventLog.created_at.desc())
        .limit(100)
        .all()
    )
    return render_template('efactura/logs.html', logs=logs)
