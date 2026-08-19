"""Configuración Empresa → Regionalización y formatos (por organización)."""

from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user

from nodeone.core.timezone_service import COMMON_IANA_TIMEZONES


def _org_id() -> int:
    from nodeone.services.org_scope import admin_data_scope_organization_id

    return int(admin_data_scope_organization_id())


def _regional_settings_view():
    from nodeone.core.regional_format import (
        ALLOWED_CURRENCIES,
        COUNTRY_CODES,
        DATE_FORMATS,
        NUMBER_FORMATS,
        PAPER_SIZES,
        SYMBOL_POSITIONS,
        TIME_FORMATS,
        WEEK_STARTS,
        RegionalFormatService,
    )

    oid = _org_id()
    if request.method == 'POST':
        try:
            RegionalFormatService.apply_payload(oid, request.form)
            flash('Regionalización y formatos guardados.', 'success')
            return redirect(url_for('admin_regional_settings'))
        except Exception as exc:
            flash('No se pudo guardar: %s' % (exc,), 'error')
    dto = RegionalFormatService.get_or_create(oid)
    return render_template(
        'admin/org_regional.html',
        settings=dto,
        organization_id=oid,
        timezones=COMMON_IANA_TIMEZONES,
        country_codes=COUNTRY_CODES,
        date_formats=DATE_FORMATS,
        time_formats=TIME_FORMATS,
        week_starts=WEEK_STARTS,
        number_formats=NUMBER_FORMATS,
        currencies=ALLOWED_CURRENCIES,
        symbol_positions=SYMBOL_POSITIONS,
        paper_sizes=PAPER_SIZES,
        current_user=current_user,
    )


def register_org_regional_routes(app):
    if 'admin_regional_settings' in getattr(app, 'view_functions', {}):
        return
    from app import admin_required

    app.add_url_rule(
        '/admin/company/regional',
        endpoint='admin_regional_settings',
        view_func=admin_required(_regional_settings_view),
        methods=['GET', 'POST'],
    )
