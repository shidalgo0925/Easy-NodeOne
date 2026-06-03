"""Matriz visual EN1: módulo × permiso (filas) × rol (columnas)."""

from __future__ import annotations

from typing import Any

from nodeone.core.db import db
from models.users import Permission, Role
from models.associations import role_permission_table
from sqlalchemy import select

MODULE_LABELS: dict[str, str] = {
    'users': 'Usuarios',
    'roles': 'Roles',
    'services': 'Servicios',
    'memberships': 'Membresías',
    'payments': 'Pagos',
    'reports': 'Reportes',
    'analytics': 'Analytics',
    'integrations': 'Integraciones',
    'system': 'Sistema',
    'audit': 'Auditoría',
    'api': 'API',
    'security_matrix': 'Matriz Odoo',
    'contador': 'Contador',
    'academic': 'Académico',
    'workshop': 'Taller',
    'taller': 'Taller',
    'general': 'General',
}

# Prefijo RBAC → código(s) SaaS. Si el primero existe en catálogo, gobierna ON/OFF por org.
PERMISSION_MODULE_SAAS_ALIASES: dict[str, tuple[str, ...]] = {
    'services': ('appointments',),
    'taller': ('workshop',),
    'workshop': ('workshop',),
}

CRITICAL_PERMISSION_CODES = frozenset({
    'users.delete',
    'roles.delete',
    'system.settings.update',
    'payments.refund',
    'api.keys.revoke',
})


def permission_module(code: str) -> str:
    return (code or '').split('.')[0] if '.' in (code or '') else 'general'


def module_label(module_id: str) -> str:
    return MODULE_LABELS.get(module_id, module_id.replace('_', ' ').title())


def saas_codes_for_permission_module(module_id: str) -> tuple[str, ...] | None:
    """Códigos SaaS que filtran la pestaña; None = siempre visible (core RBAC)."""
    from nodeone.services.saas_module_cache import get_catalog_module

    mid = (module_id or '').strip()
    if not mid or mid == 'general':
        return None
    if mid in PERMISSION_MODULE_SAAS_ALIASES:
        return PERMISSION_MODULE_SAAS_ALIASES[mid]
    if get_catalog_module(mid) is not None:
        return (mid,)
    return None


def permission_module_visible_for_org(module_id: str, organization_id: int | None) -> bool:
    """Oculta módulos cuyo SaaS está apagado para la org activa."""
    codes = saas_codes_for_permission_module(module_id)
    if codes is None:
        return True
    from nodeone.services.saas_module_cache import get_catalog_module, has_saas_module_enabled_cached

    for code in codes:
        if get_catalog_module(code) is not None:
            return has_saas_module_enabled_cached(organization_id, code)
    return has_saas_module_enabled_cached(organization_id, codes[-1])


def permission_screen_label(code: str, name: str) -> str:
    """Etiqueta tipo pantalla/acción para la fila."""
    if '.' in code:
        action = code.split('.', 1)[1]
        action_labels = {
            'view': 'Ver / listar',
            'create': 'Crear',
            'update': 'Editar',
            'delete': 'Eliminar',
            'assign': 'Asignar',
            'assign_roles': 'Asignar roles',
            'suspend': 'Suspender',
            'manage': 'Gestionar',
            'refund': 'Reembolsar',
            'export': 'Exportar',
            'revoke': 'Revocar',
            'admin': 'Administración',
            'review': 'Revisar',
            'capture': 'Capturar',
        }
        return action_labels.get(action, name or action)
    return name or code


def build_rbac_matrix_view(
    active_module: str | None = None,
    organization_id: int | None = None,
) -> dict[str, Any]:
    """Construye pestañas por módulo y grilla permiso × rol."""
    roles_all = Role.query.order_by(Role.code).all()
    sa_role = next((r for r in roles_all if r.code == 'SA'), None)
    columns = []
    if sa_role:
        columns.append({
            'id': sa_role.id,
            'code': sa_role.code,
            'name': sa_role.name,
            'readonly': True,
        })
    for r in roles_all:
        if r.code == 'SA':
            continue
        columns.append({
            'id': r.id,
            'code': r.code,
            'name': r.name,
            'readonly': False,
        })

    assigned: set[tuple[int, int]] = {
        (int(rid), int(pid))
        for rid, pid in db.session.execute(
            select(role_permission_table.c.role_id, role_permission_table.c.permission_id)
        ).all()
    }

    perms = Permission.query.order_by(Permission.code).all()
    modules_set: set[str] = set()
    perms_by_module: dict[str, list[Permission]] = {}
    for p in perms:
        mid = permission_module(p.code)
        if not permission_module_visible_for_org(mid, organization_id):
            continue
        modules_set.add(mid)
        perms_by_module.setdefault(mid, []).append(p)

    modules = [
        {'id': mid, 'label': module_label(mid)}
        for mid in sorted(modules_set, key=lambda x: module_label(x))
    ]
    if not modules:
        modules = [{'id': 'general', 'label': 'General'}]

    active = active_module or (modules[0]['id'] if modules else 'general')
    if not any(m['id'] == active for m in modules):
        active = modules[0]['id']

    rows = []
    for p in perms_by_module.get(active, []):
        cells = []
        for col in columns:
            checked = (col['id'], p.id) in assigned
            if col['code'] == 'SA':
                checked = True
            cells.append({
                'role_id': col['id'],
                'permission_id': p.id,
                'checked': checked,
                'readonly': col['readonly'],
            })
        rows.append({
            'permission_id': p.id,
            'code': p.code,
            'name': p.name,
            'screen': permission_screen_label(p.code, p.name),
            'critical': p.code in CRITICAL_PERMISSION_CODES,
            'cells': cells,
        })

    return {
        'modules': modules,
        'active_module': active,
        'columns': columns,
        'rows': rows,
        'has_data': bool(rows),
    }
