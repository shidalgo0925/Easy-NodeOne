"""API pública ECalendar (agenda EasyTech / Site_2026)."""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from flask import Blueprint, jsonify, make_response, request

from nodeone.modules.ecalendar.products import load_products, products_payload
from nodeone.modules.ecalendar.services.availability import filter_available_slots
from nodeone.modules.ecalendar.services.bookings import create_booking
from nodeone.modules.ecalendar.services.config import load_ecalendar_config
from nodeone.modules.ecalendar.services.google_calendar import (
    GoogleCalendarError,
    list_busy_intervals,
    oauth_valid,
)
from nodeone.modules.public_api.landing_service import apply_cors_headers

_DATE_RE = re.compile(r'^\d{4}-\d{2}-\d{2}$')

ecalendar_bp = Blueprint('ecalendar', __name__, url_prefix='/api/ecalendar')


def _cfg():
    return load_ecalendar_config()


def _origins_list(cfg) -> list[str]:
    return list(cfg.allowed_origins)


@ecalendar_bp.after_request
def _ecalendar_cors(response):
    return apply_cors_headers(response, _origins_list(_cfg()))


@ecalendar_bp.before_request
def _ecalendar_options():
    if request.method != 'OPTIONS':
        return None
    if not (request.path or '').startswith('/api/ecalendar'):
        return None
    resp = make_response('', 204)
    return apply_cors_headers(resp, _origins_list(_cfg()))


def _parse_date_param(raw: str, cfg) -> tuple[date | None, str | None]:
    value = (raw or '').strip()
    if not value or not _DATE_RE.match(value):
        return None, 'invalid_date'
    try:
        day = date.fromisoformat(value)
    except ValueError:
        return None, 'invalid_date'
    tz = ZoneInfo(cfg.timezone)
    today = datetime.now(tz).date()
    if day < today:
        return None, 'past_date'
    if day > today + timedelta(days=cfg.horizon_days):
        return None, 'date_out_of_range'
    return day, None


def _require_active(cfg):
    if not cfg.enabled:
        return jsonify({'ok': False, 'error': 'ecalendar_disabled'}), 503
    return None


@ecalendar_bp.route('/health', methods=['GET'])
def health():
    cfg = _cfg()
    products = load_products(cfg.products_json)
    connected = cfg.google_configured
    valid = oauth_valid(cfg) if connected else False
    return jsonify({
        'ok': True,
        'enabled': cfg.enabled,
        'google_connected': connected,
        'oauth_valid': valid,
        'calendar_id': cfg.google_calendar_id or 'primary',
        'products': len(products),
    })


@ecalendar_bp.route('/products', methods=['GET'])
def products():
    cfg = _cfg()
    blocked = _require_active(cfg)
    if blocked:
        return blocked
    return jsonify(products_payload(cfg.products_json))


@ecalendar_bp.route('/availability', methods=['GET'])
def availability():
    cfg = _cfg()
    blocked = _require_active(cfg)
    if blocked:
        return blocked
    day, err = _parse_date_param(request.args.get('date', ''), cfg)
    if err:
        return jsonify({'ok': False, 'error': err}), 400
    assert day is not None

    if not cfg.google_configured:
        return jsonify({'ok': False, 'error': 'google_not_configured'}), 503

    tz = ZoneInfo(cfg.timezone)
    day_start = datetime.combine(day, datetime.min.time(), tzinfo=tz)
    day_end = day_start + timedelta(days=1)
    try:
        busy = list_busy_intervals(cfg, time_min=day_start, time_max=day_end)
    except GoogleCalendarError:
        return jsonify({'ok': False, 'error': 'google_api_error'}), 502

    slots = filter_available_slots(cfg, day, busy, now=datetime.now(tz))
    return jsonify({
        'ok': True,
        'date': day.isoformat(),
        'timezone': cfg.timezone,
        'slots': slots,
    })


@ecalendar_bp.route('/bookings', methods=['POST'])
def bookings():
    cfg = _cfg()
    blocked = _require_active(cfg)
    if blocked:
        return blocked
    payload = request.get_json(silent=True) or {}
    result, status, err = create_booking(cfg, payload)
    if err:
        return jsonify({'ok': False, 'error': err}), status
    return jsonify(result), status
