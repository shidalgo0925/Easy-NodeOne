"""Admin EN1: pantalla y API de configuración ECalendar."""

from __future__ import annotations

from datetime import datetime
from functools import wraps

from flask import Blueprint, jsonify, render_template, request
from flask_login import current_user, login_required

from nodeone.core.db import db
from nodeone.modules.ecalendar.services.appointments_admin import (
    cancel_admin_appointment,
    error_http_status,
    error_message,
    load_dev_appointments_config,
    parse_bookings_only_param,
    query_dev_appointments,
)
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


def _appointments_bookings_only() -> bool:
    return parse_bookings_only_param(request.args.get('bookings_only'))


def _json_appointment_error(view, *, status: int | None = None):
    code = view.error or 'google_api_error'
    return jsonify({
        'success': False,
        'error': code,
        'message': error_message(code),
        'appointments': [],
        'organization_id': view.org_id,
        'organization_name': view.org_name,
    }), status or error_http_status(code)


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
        appointments_view = query_dev_appointments(bookings_only=True)
        from nodeone.modules.ecalendar.products import products_payload

        cfg = load_ecalendar_config()
        catalog_products = products_payload(cfg.products_json).get('products') or []
        return render_template(
            'admin/ecalendar_settings.html',
            ecalendar_config=row,
            appointments_preview=appointments_view,
            catalog_products=catalog_products,
        )

    @app.route('/admin/ecalendar/citas')
    @_admin_required_lazy
    def admin_ecalendar_appointments_page():
        ensure_ecalendar_settings_table()
        view = query_dev_appointments(bookings_only=_appointments_bookings_only())
        return render_template(
            'admin/ecalendar_appointments.html',
            ecalendar_tenant_name=view.org_name,
            ecalendar_tenant_id=view.org_id,
            appointments=view.visible_items,
            appointments_total=view.total_events,
            appointments_bookings=view.bookings_count,
            appointments_error=view.error,
            appointments_error_message=view.error_message,
            bookings_only=view.bookings_only,
        )

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


@ecalendar_admin_bp.route('/api/admin/ecalendar/appointments', methods=['GET'])
@_admin_required_lazy
def api_ecalendar_appointments_list():
    view = query_dev_appointments(bookings_only=_appointments_bookings_only())
    if view.error:
        return _json_appointment_error(view)
    return jsonify({
        'success': True,
        'appointments': view.visible_items,
        'count': len(view.visible_items),
        'total_events': view.total_events,
        'bookings_count': view.bookings_count,
        'bookings_only': view.bookings_only,
        'organization_id': view.org_id,
        'organization_name': view.org_name,
        'calendar_id': view.cfg.google_calendar_id,
    })


@ecalendar_admin_bp.route('/api/admin/ecalendar/appointments/<path:event_id>', methods=['DELETE'])
@_admin_required_lazy
def api_ecalendar_appointments_delete(event_id):
    cfg, _org_id, _org_name = load_dev_appointments_config()
    err = cancel_admin_appointment(cfg, event_id)
    if err:
        return jsonify({
            'success': False,
            'error': err,
            'message': error_message(err),
        }), error_http_status(err)
    return jsonify({'success': True, 'message': 'Cita eliminada de Google Calendar.'})
