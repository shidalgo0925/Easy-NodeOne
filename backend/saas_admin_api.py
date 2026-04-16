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
    Activa/desactiva módulo. Valida dependencias y core.
    Retorna (ok: bool, error: str|None)
    """
    from app import db, SaasModule, SaasOrgModule, SaasModuleDependency, SaasOrganization

    if SaasOrganization.query.get(organization_id) is None:
        return False, 'Organización no encontrada'

    mod = SaasModule.query.filter_by(code=module_code).first()
    if mod is None:
        return False, 'Código de módulo desconocido'

    if enabled:
        deps = SaasModuleDependency.query.filter_by(module_id=mod.id).all()
        for d in deps:
            parent = SaasModule.query.get(d.depends_on_module_id)
            if not parent:
                continue
            row = SaasOrgModule.query.filter_by(
                organization_id=organization_id, module_id=d.depends_on_module_id
            ).first()
            if parent.is_core:
                continue
            if row is None or not row.enabled:
                return False, f'Active primero el módulo requerido: {parent.code}'
        row = _get_or_create_org_module(organization_id, mod.id)
        row.enabled = True
        db.session.commit()
        clear_saas_request_cache()
        return True, None

    # disable
    if mod.is_core:
        return False, 'Los módulos core no se pueden desactivar'

    dependents = SaasModuleDependency.query.filter_by(depends_on_module_id=mod.id).all()
    for d in dependents:
        child = SaasModule.query.get(d.module_id)
        if not child:
            continue
        row = SaasOrgModule.query.filter_by(organization_id=organization_id, module_id=d.module_id).first()
        if row and row.enabled:
            return False, f'Desactive primero el módulo dependiente: {child.code}'

    row = _get_or_create_org_module(organization_id, mod.id)
    row.enabled = False
    db.session.commit()
    clear_saas_request_cache()
    return True, None


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
