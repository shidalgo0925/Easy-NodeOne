#!/usr/bin/env python3
"""
API admin: listar y activar/desactivar módulos SaaS por organización.
Requiere is_admin (o mismo criterio que rutas admin sensibles).
"""

import os

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

saas_admin_bp = Blueprint('saas_admin', __name__, url_prefix='/api/admin/saas')


def _require_admin_json():
    if not current_user.is_authenticated:
        return jsonify({'success': False, 'error': 'No autenticado'}), 401
    if not getattr(current_user, 'is_admin', False):
        return jsonify({'success': False, 'error': 'Solo administradores'}), 403
    return None


def resolve_target_organization_id():
    """organization_id en query o JSON; si no, organización activa en sesión."""
    oid = request.args.get('organization_id', type=int)
    if oid is not None:
        return oid
    if request.is_json:
        body = request.get_json(silent=True) or {}
        if body.get('organization_id') is not None:
            return int(body['organization_id'])
    try:
        from app import get_current_organization_id
        from utils.organization import default_organization_id

        oid = get_current_organization_id()
        if oid is None:
            return default_organization_id()
        return int(oid)
    except Exception:
        from utils.organization import default_organization_id

        return default_organization_id()


def clear_saas_request_cache():
    from flask import g, has_request_context

    if not has_request_context():
        return
    for k in ('_saas_enabled_codes', '_saas_enabled_org'):
        if hasattr(g, k):
            delattr(g, k)


def _get_or_create_org_module(organization_id, module_id):
    from app import db, SaasOrgModule

    row = SaasOrgModule.query.filter_by(organization_id=organization_id, module_id=module_id).first()
    if row is None:
        row = SaasOrgModule(organization_id=organization_id, module_id=module_id, enabled=False)
        db.session.add(row)
        db.session.flush()
    return row


def saas_set_module_enabled(organization_id, module_code, enabled):
    """
    Activa/desactiva módulo. ADR-038 F1: delega a Module Registry (dual-write saas).
    Retorna (ok: bool, error: str|None)
    """
    from nodeone.core.platform.module_registry import (
        disable_module,
        enable_module,
        ensure_module_registry,
        saas_code_to_module_key,
    )

    # Garantiza tablas/seed en entornos que aún no corrieron bootstrap F1.
    try:
        ensure_module_registry(printfn=None, sync_orgs=False)
    except Exception:
        pass

    key = saas_code_to_module_key(module_code.strip().lower())
    if enabled:
        return enable_module(int(organization_id), key)
    return disable_module(int(organization_id), key)


@saas_admin_bp.route('/modules', methods=['GET'])
@login_required
def list_saas_modules():
    err = _require_admin_json()
    if err:
        return err
    from app import SaasModule, SaasOrgModule, SaasModuleDependency

    org_id = resolve_target_organization_id()
    from app import SaasOrganization

    if SaasOrganization.query.get(org_id) is None:
        return jsonify({'success': False, 'error': 'Organización no encontrada'}), 404

    # Autocorregir catálogo/vínculos para que módulos nuevos (ej. workshop/SLA) aparezcan aquí.
    try:
        from nodeone.services.saas_catalog_defaults import (
            ensure_saas_module_catalog,
            ensure_toggleable_tenant_module_links,
        )

        ensure_saas_module_catalog()
        ensure_toggleable_tenant_module_links(organization_id=org_id)
    except Exception:
        pass

    # ADR-038 F1: capa registry encima (sin romper payload legacy).
    try:
        from nodeone.core.platform.module_registry import (
            ensure_module_registry,
            sync_organization_modules_from_saas,
        )

        ensure_module_registry(printfn=None, sync_orgs=False)
        sync_organization_modules_from_saas(org_id)
    except Exception:
        pass

    mods = SaasModule.query.order_by(SaasModule.id).all()
    out = []
    for m in mods:
        row = SaasOrgModule.query.filter_by(organization_id=org_id, module_id=m.id).first()
        # Alinear con has_saas_module_enabled: sin fila → default is_core
        enabled = bool(row.enabled) if row is not None else bool(m.is_core)
        deps = SaasModuleDependency.query.filter_by(module_id=m.id).all()
        dep_codes = []
        for d in deps:
            pm = SaasModule.query.get(d.depends_on_module_id)
            if pm:
                dep_codes.append(pm.code)
        out.append(
            {
                'code': m.code,
                'module_key': m.code,  # F1: identidad saas_code ↔ module_key
                'name': m.name,
                'description': m.description or '',
                'is_core': m.is_core,
                'enabled': enabled,
                'depends_on': dep_codes,
            }
        )
    return jsonify({'success': True, 'organization_id': org_id, 'modules': out})


@saas_admin_bp.route('/modules/<module_code>/enable', methods=['POST'])
@login_required
def enable_saas_module(module_code):
    err = _require_admin_json()
    if err:
        return err
    org_id = resolve_target_organization_id()
    ok, msg = saas_set_module_enabled(org_id, module_code.strip().lower(), True)
    if not ok:
        return jsonify({'success': False, 'error': msg}), 400
    return jsonify({'success': True, 'organization_id': org_id, 'module': module_code, 'enabled': True})


@saas_admin_bp.route('/modules/<module_code>/disable', methods=['POST'])
@login_required
def disable_saas_module(module_code):
    err = _require_admin_json()
    if err:
        return err
    org_id = resolve_target_organization_id()
    ok, msg = saas_set_module_enabled(org_id, module_code.strip().lower(), False)
    if not ok:
        return jsonify({'success': False, 'error': msg}), 400
    return jsonify({'success': True, 'organization_id': org_id, 'module': module_code, 'enabled': False})
