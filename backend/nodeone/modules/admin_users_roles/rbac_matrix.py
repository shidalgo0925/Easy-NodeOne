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
    'general': 'General',
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


def build_rbac_matrix_view(active_module: str | None = None) -> dict[str, Any]:
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
