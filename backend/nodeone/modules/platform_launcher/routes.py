"""Blueprint Launcher v2 — Mis aplicaciones."""

from __future__ import annotations

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required

from nodeone.core.platform.launcher import (
    build_nav_context_for_user,
    get_active_app_id,
    launcher_mode_for_organization,
    set_active_app_id,
    visible_launcher_apps,
)
from nodeone.core.template_context_gates import user_can_see_tenant_admin_menu

platform_launcher_bp = Blueprint('platform_launcher', __name__, url_prefix='/platform')


def _org_id_for_launcher():
    from app import _org_id_for_module_visibility

    return _org_id_for_module_visibility()


def _org_may_use_launcher(org_id: int | None) -> bool:
    """
    Launcher oficial (Mis aplicaciones).
    Modo ``apps`` siempre; en classic también si la org tiene EPosOne (atajo temporal UX-T1).
    """
    if launcher_mode_for_organization(org_id) == 'apps':
        return True
    if org_id is None:
        return False
    try:
        from nodeone.services.saas_module_cache import has_saas_module_enabled_cached

        return bool(has_saas_module_enabled_cached(int(org_id), 'eposone'))
    except Exception:
        return False


def _require_launcher_access():
    if not user_can_see_tenant_admin_menu(current_user):
        return redirect(url_for('dashboard'))
    org_id = _org_id_for_launcher()
    if not _org_may_use_launcher(org_id):
        try:
            return redirect(url_for('admin_dashboard'))
        except Exception:
            return redirect(url_for('dashboard'))
    return None


@platform_launcher_bp.route('/apps')
@login_required
def apps_home():
    denied = _require_launcher_access()
    if denied is not None:
        return denied

    ctx = build_nav_context_for_user(current_user)
    apps = visible_launcher_apps(ctx)
    if len(apps) == 1:
        set_active_app_id(session, apps[0]['id'])
        return redirect(apps[0]['url'])

    active_id = get_active_app_id(session)
    return render_template(
        'platform/apps_launcher.html',
        launcher_apps=apps,
        active_app_id=active_id,
    )


@platform_launcher_bp.route('/apps/select', methods=['POST'])
@login_required
def apps_select():
    denied = _require_launcher_access()
    if denied is not None:
        return denied

    area_id = (request.form.get('app_id') or '').strip()
    if not area_id:
        flash('Selecciona una aplicación.', 'warning')
        return redirect(url_for('platform_launcher.apps_home'))

    ctx = build_nav_context_for_user(current_user)
    apps = {a['id']: a for a in visible_launcher_apps(ctx)}
    app_row = apps.get(area_id)
    if app_row is None:
        flash('No tienes acceso a esa aplicación.', 'error')
        return redirect(url_for('platform_launcher.apps_home'))

    set_active_app_id(session, area_id)
    return redirect(app_row['url'])


@platform_launcher_bp.route('/apps/switch')
@login_required
def apps_switch():
    denied = _require_launcher_access()
    if denied is not None:
        return denied

    set_active_app_id(session, None)
    return redirect(url_for('platform_launcher.apps_home'))


def register_platform_launcher(app):
    if 'platform_launcher' not in app.blueprints:
        app.register_blueprint(platform_launcher_bp)

    if getattr(app, '_platform_launcher_ctx_registered', False):
        return
    app._platform_launcher_ctx_registered = True

    @app.context_processor
    def _inject_platform_launcher_context():
        from flask import has_request_context
        from flask_login import current_user

        out = {
            'platform_launcher_mode': 'classic',
            'platform_active_app_id': None,
            'platform_launcher_enabled': False,
        }
        if not has_request_context() or not getattr(current_user, 'is_authenticated', False):
            return out
        if not user_can_see_tenant_admin_menu(current_user):
            return out
        try:
            org_id = _org_id_for_launcher()
            mode = launcher_mode_for_organization(org_id)
            out['platform_launcher_mode'] = mode
            out['platform_active_app_id'] = get_active_app_id(session)
            # UX-T1: mostrar entrada a Mis aplicaciones también en classic si hay EPosOne.
            out['platform_launcher_enabled'] = _org_may_use_launcher(org_id)
        except Exception:
            pass
        return out
