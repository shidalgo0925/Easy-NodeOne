"""API manifests de apps de plataforma — Etapa 9."""

from __future__ import annotations

from flask import Blueprint, jsonify
from flask_login import current_user, login_required

from nodeone.core.platform.manifest_registry import (
    NEW_APP_MANIFEST_TEMPLATE,
    discover_platform_manifests,
    get_manifest,
    manifest_summary,
    platform_app_checklist,
    platform_apps_health,
)
from nodeone.core.template_context_gates import user_can_see_tenant_admin_menu

platform_apps_bp = Blueprint('platform_apps', __name__, url_prefix='/api/platform/apps')


def _require_platform_admin():
    if not current_user.is_authenticated:
        return jsonify({'error': 'unauthorized'}), 401
    if not user_can_see_tenant_admin_menu(current_user):
        return jsonify({'error': 'forbidden'}), 403
    return None


@platform_apps_bp.route('/manifests', methods=['GET'])
@login_required
def list_manifests():
    gate = _require_platform_admin()
    if gate is not None:
        return gate
    manifests = discover_platform_manifests()
    items = [manifest_summary(m) for m in manifests.values()]
    items.sort(key=lambda x: str(x.get('id') or ''))
    return jsonify({'manifests': items, 'count': len(items)})


@platform_apps_bp.route('/manifests/<app_id>', methods=['GET'])
@login_required
def get_manifest_detail(app_id: str):
    gate = _require_platform_admin()
    if gate is not None:
        return gate
    manifest = get_manifest(app_id)
    if manifest is None:
        return jsonify({'error': 'not_found'}), 404
    return jsonify({'manifest': dict(manifest)})


@platform_apps_bp.route('/manifests/<app_id>/checklist', methods=['GET'])
@login_required
def get_manifest_checklist(app_id: str):
    gate = _require_platform_admin()
    if gate is not None:
        return gate
    return jsonify(platform_app_checklist(app_id))


@platform_apps_bp.route('/health', methods=['GET'])
@login_required
def apps_health():
    gate = _require_platform_admin()
    if gate is not None:
        return gate
    return jsonify(platform_apps_health())


@platform_apps_bp.route('/template', methods=['GET'])
@login_required
def new_app_template():
    gate = _require_platform_admin()
    if gate is not None:
        return gate
    return jsonify({'template': dict(NEW_APP_MANIFEST_TEMPLATE)})


def register_platform_apps_api(app) -> None:
    if 'platform_apps' in app.blueprints:
        return
    app.register_blueprint(platform_apps_bp)
