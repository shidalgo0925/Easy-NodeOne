"""Admin EN1: pantalla y API de configuración ECalendar."""

from __future__ import annotations

from datetime import datetime
from functools import wraps

from flask import Blueprint, jsonify, render_template, request
from flask_login import current_user, login_required

from nodeone.core.db import db
from nodeone.modules.ecalendar.services.config import load_ecalendar_config
from nodeone.modules.ecalendar.services.google_calendar import GoogleCalendarError, _access_token
from nodeone.modules.ecalendar.services.settings_store import ensure_ecalendar_settings_table

ecalendar_admin_bp = Blueprint('ecalendar_admin', __name__)


def _admin_required_lazy(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        import app as M
        from flask import flash, redirect, url_for

        if bool(getattr(current_user, 'must_change_password', False)):
            flash('Debes cambiar tu contraseña antes de continuar.', 'warning')
            return redirect(url_for('auth.change_password'))
        if not current_user.is_admin and not M._user_has_any_admin_permission(current_user):
            flash('No tienes permisos para acceder a esta página.', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)

    return decorated_function


def _admin_org_id() -> int:
    import app as M

    return int(M._catalog_org_for_admin_catalog_routes())


def register_ecalendar_admin_routes(app):
    @app.route('/admin/ecalendar')
    @_admin_required_lazy
    def admin_ecalendar_settings_page():
        ensure_ecalendar_settings_table()
        from models.ecalendar import ECalendarSettings

        row = ECalendarSettings.get_or_create_for_organization(_admin_org_id())
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
        return render_template('admin/ecalendar_settings.html', ecalendar_config=row)

    if 'ecalendar_admin' not in app.blueprints:
        app.register_blueprint(ecalendar_admin_bp)


@ecalendar_admin_bp.route('/api/admin/ecalendar/config', methods=['GET', 'POST', 'PUT'])
@_admin_required_lazy
def api_ecalendar_config():
    ensure_ecalendar_settings_table()
    from models.ecalendar import ECalendarSettings

    oid = _admin_org_id()
    row = ECalendarSettings.get_or_create_for_organization(oid)

    if request.method == 'GET':
        return jsonify({'success': True, 'config': row.to_dict()})

    data = request.get_json(silent=True) or {}

    row.enabled = bool(data.get('enabled', row.enabled))
    row.use_for_public_agenda = bool(data.get('use_for_public_agenda', row.use_for_public_agenda))

    cid = (data.get('google_client_id') or row.google_client_id or '').strip()
    if cid:
        row.google_client_id = cid
    if 'google_client_secret' in data and (data.get('google_client_secret') or '').strip():
        row.google_client_secret = (data.get('google_client_secret') or '').strip()
    if 'google_refresh_token' in data and (data.get('google_refresh_token') or '').strip():
        row.google_refresh_token = (data.get('google_refresh_token') or '').strip()

    row.google_calendar_id = (data.get('google_calendar_id') or row.google_calendar_id or 'primary').strip() or 'primary'
    row.google_account_email = (data.get('google_account_email') or row.google_account_email or '').strip()

    row.timezone = (data.get('timezone') or row.timezone or 'America/Panama').strip() or 'America/Panama'
    try:
        row.slot_minutes = max(15, int(data.get('slot_minutes', row.slot_minutes or 30)))
        row.lead_hours = max(0, int(data.get('lead_hours', row.lead_hours or 4)))
        row.horizon_days = max(1, int(data.get('horizon_days', row.horizon_days or 30)))
    except (TypeError, ValueError):
        return jsonify({'success': False, 'error': 'Valores numéricos inválidos.'}), 400

    row.business_start = (data.get('business_start') or row.business_start or '09:00').strip() or '09:00'
    row.business_end = (data.get('business_end') or row.business_end or '17:00').strip() or '17:00'
    row.title_prefix = (data.get('title_prefix') or '').strip()
    row.allowed_origins = (data.get('allowed_origins') or '').strip()
    row.products_json = (data.get('products_json') or '').strip()
    row.is_active = True
    row.updated_at = datetime.utcnow()

    if row.use_for_public_agenda:
        (
            ECalendarSettings.query.filter(
                ECalendarSettings.organization_id != oid,
                ECalendarSettings.use_for_public_agenda.is_(True),
            ).update({'use_for_public_agenda': False}, synchronize_session=False)
        )

    try:
        db.session.commit()
        return jsonify({'success': True, 'config': row.to_dict()})
    except Exception as ex:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(ex)}), 500


@ecalendar_admin_bp.route('/api/admin/ecalendar/test', methods=['POST'])
@_admin_required_lazy
def api_ecalendar_test():
    cfg = load_ecalendar_config(organization_id=_admin_org_id())
    if not cfg.google_configured:
        return jsonify({'success': False, 'error': 'Completa credenciales Google antes de probar.'}), 400
    try:
        _access_token(cfg)
        return jsonify({'success': True, 'message': 'Conexión OAuth OK.'})
    except GoogleCalendarError as ex:
        return jsonify({'success': False, 'error': str(ex)}), 200
