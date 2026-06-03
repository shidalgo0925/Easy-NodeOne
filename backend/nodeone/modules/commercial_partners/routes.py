"""Admin + API de contactos / terceros."""

from __future__ import annotations

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from models.saas import SaasOrganization
from nodeone.core.db import db
from nodeone.services import commercial_partner_service as cp_svc
from nodeone.services.commercial_partner_schema import ensure_commercial_partner_schema

commercial_partners_admin_bp = Blueprint(
    'commercial_partners_admin', __name__, url_prefix='/admin/terceros'
)
commercial_partners_api_bp = Blueprint(
    'commercial_partners_api', __name__, url_prefix='/api/admin/terceros'
)


def _org_id() -> int:
    from app import admin_data_scope_organization_id, default_organization_id

    try:
        oid = int(admin_data_scope_organization_id())
    except Exception:
        oid = int(default_organization_id())
    if SaasOrganization.query.get(int(oid)) is None:
        return int(default_organization_id())
    return int(oid)


def _can_admin() -> bool:
    if not current_user.is_authenticated:
        return False
    if getattr(current_user, 'is_admin', False):
        return True
    from app import _user_has_any_admin_permission

    return bool(_user_has_any_admin_permission(current_user))


def _guard_html():
    if not _can_admin():
        flash('Sin permisos.', 'error')
        return redirect(url_for('dashboard'))
    from app import has_saas_module_enabled

    if not has_saas_module_enabled(_org_id(), 'sales'):
        flash('Active el módulo Ventas para gestionar contactos comerciales.', 'error')
        return redirect(url_for('dashboard'))
    return None


def _guard_json():
    if not current_user.is_authenticated:
        return jsonify({'ok': False, 'error': 'unauthorized'}), 401
    if not _can_admin():
        return jsonify({'ok': False, 'error': 'forbidden'}), 403
    from app import has_saas_module_enabled

    if not has_saas_module_enabled(_org_id(), 'sales'):
        return jsonify({'ok': False, 'error': 'sales_module_disabled'}), 403
    return None


@commercial_partners_admin_bp.before_request
@commercial_partners_api_bp.before_request
def _before():
    try:
        ensure_commercial_partner_schema(db, db.engine)
    except Exception:
        pass


@commercial_partners_admin_bp.before_request
def _admin_before():
    g = _guard_html()
    if g is not None:
        return g


@commercial_partners_api_bp.before_request
def _api_before():
    g = _guard_json()
    if g is not None:
        return g


@commercial_partners_admin_bp.route('/')
@login_required
def terceros_index():
    oid = _org_id()
    q = (request.args.get('q') or '').strip()
    rows = cp_svc.search_partners(oid, q, limit=50, customers_only=False)
    return render_template('admin/terceros_list.html', partners=rows, q=q)


@commercial_partners_admin_bp.route('/nuevo', methods=['GET', 'POST'])
@login_required
def terceros_new():
    oid = _org_id()
    if request.method == 'POST':
        try:
            row = cp_svc.create_partner(oid, request.form.to_dict())
            db.session.commit()
            flash('Contacto creado.', 'success')
            return redirect(url_for('commercial_partners_admin.terceros_edit', contact_id=row.id))
        except Exception as exc:
            db.session.rollback()
            flash(str(exc), 'error')
    return render_template('admin/terceros_form.html', partner=None)


@commercial_partners_admin_bp.route('/<int:contact_id>', methods=['GET', 'POST'])
@login_required
def terceros_edit(contact_id: int):
    oid = _org_id()
    row = cp_svc.get_partner(oid, contact_id)
    if not row:
        flash('Contacto no encontrado.', 'error')
        return redirect(url_for('commercial_partners_admin.terceros_index'))
    if request.method == 'POST':
        row.name = (request.form.get('name') or row.name)[:200]
        row.legal_name = (request.form.get('legal_name') or '')[:300] or None
        row.trade_name = (request.form.get('trade_name') or '')[:300] or None
        row.person_type = (request.form.get('person_type') or 'natural')[:30]
        row.tax_id = (request.form.get('tax_id') or '')[:80] or None
        row.tax_dv = (request.form.get('tax_dv') or '')[:10] or None
        row.fiscal_email = (request.form.get('fiscal_email') or '')[:255] or None
        row.fiscal_phone = (request.form.get('fiscal_phone') or '')[:50] or None
        row.fiscal_address = request.form.get('fiscal_address') or None
        row.province = (request.form.get('province') or '')[:120] or None
        row.district = (request.form.get('district') or '')[:120] or None
        row.corregimiento = (request.form.get('corregimiento') or '')[:120] or None
        row.is_customer = request.form.get('is_customer') in ('1', 'on', 'true')
        row.is_supplier = request.form.get('is_supplier') in ('1', 'on', 'true')
        row.itbms_exempt = request.form.get('itbms_exempt') in ('1', 'on', 'true')
        row.is_active = request.form.get('is_active') in ('1', 'on', 'true')
        db.session.commit()
        flash('Contacto actualizado.', 'success')
        return redirect(url_for('commercial_partners_admin.terceros_edit', contact_id=row.id))
    return render_template('admin/terceros_form.html', partner=row)


@commercial_partners_api_bp.route('/search')
@login_required
def api_search():
    q = (request.args.get('q') or '').strip()
    try:
        lim = int(request.args.get('limit') or 20)
    except (TypeError, ValueError):
        lim = 20
    rows = cp_svc.search_partners(_org_id(), q, limit=lim, customers_only=True)
    return jsonify([cp_svc.partner_to_dict(c) for c in rows])


@commercial_partners_api_bp.route('', methods=['POST'])
@login_required
def api_create():
    data = request.get_json(silent=True) or {}
    try:
        row = cp_svc.create_partner(_org_id(), data)
        db.session.commit()
        return jsonify({'ok': True, 'contact': cp_svc.partner_to_dict(row)}), 201
    except Exception as exc:
        db.session.rollback()
        return jsonify({'ok': False, 'error': str(exc)}), 400


def register_commercial_partners_blueprints(app) -> None:
    import os

    if os.environ.get('NODEONE_SKIP_COMMERCIAL_PARTNERS_MODULE', '').strip().lower() in ('1', 'true', 'yes'):
        return
    if 'commercial_partners_admin' not in app.blueprints:
        app.register_blueprint(commercial_partners_admin_bp)
    if 'commercial_partners_api' not in app.blueprints:
        app.register_blueprint(commercial_partners_api_bp)


def register_legacy_terceros_redirects(app) -> None:
    """Compat: /admin/terceros → maestro central /admin/contacts."""
    if 'commercial_partners_legacy.terceros_redirect' in getattr(app, 'view_functions', {}):
        return
    try:
        from nodeone.services.contacts_module import is_contacts_globally_allowed

        if not is_contacts_globally_allowed():
            return
    except ImportError:
        return

    legacy_bp = Blueprint('commercial_partners_legacy', __name__)

    @legacy_bp.route('/admin/terceros')
    @legacy_bp.route('/admin/terceros/')
    @legacy_bp.route('/admin/terceros/<path:subpath>')
    def terceros_redirect(subpath=None):
        from flask import redirect, url_for

        return redirect(url_for('contacts_admin.contacts_index'), code=302)

    if 'commercial_partners_legacy' not in app.blueprints:
        app.register_blueprint(legacy_bp)
