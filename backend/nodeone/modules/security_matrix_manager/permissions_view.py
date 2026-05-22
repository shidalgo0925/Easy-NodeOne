"""Modelos de vista para permisos/grupos (UI visual)."""

from __future__ import annotations

from typing import Any


def _login_key(login: str | None) -> str:
    return (login or '').strip().lower()


def build_group_lookup(catalog: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for g in catalog.get('groups') or []:
        if not isinstance(g, dict):
            continue
        xml_id = (g.get('xml_id') or '').strip()
        if xml_id:
            out[xml_id] = g
    return out


def build_critical_xml_ids(catalog: dict[str, Any]) -> set[str]:
    return {
        (c.get('xml_id') or '').strip()
        for c in (catalog.get('critical_groups') or [])
        if isinstance(c, dict) and (c.get('xml_id') or '').strip()
    }


def build_preview_maps(
    previews: list[Any] | None,
) -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    add_map: dict[str, set[str]] = {}
    remove_map: dict[str, set[str]] = {}
    for p in previews or []:
        login = _login_key(getattr(p, 'odoo_user', None) or (p.get('odoo_user') if isinstance(p, dict) else ''))
        xml_id = (getattr(p, 'group_xml_id', None) or (p.get('group_xml_id') if isinstance(p, dict) else '') or '').strip()
        action = (getattr(p, 'action', None) or (p.get('action') if isinstance(p, dict) else '') or '').strip()
        if not login or not xml_id:
            continue
        if action == 'add':
            add_map.setdefault(login, set()).add(xml_id)
        elif action == 'remove':
            remove_map.setdefault(login, set()).add(xml_id)
    return add_map, remove_map


def _chip(xml_id: str, groups_by_xml: dict[str, dict], critical: set[str], state: str) -> dict[str, Any]:
    g = groups_by_xml.get(xml_id) or {}
    return {
        'xml_id': xml_id,
        'name': g.get('name') or xml_id,
        'state': state,
        'critical': xml_id in critical,
    }


def build_user_permission_rows(
    catalog: dict[str, Any],
    previews: list[Any] | None = None,
    *,
    only_with_changes: bool = False,
    search: str = '',
) -> list[dict[str, Any]]:
    """Filas por usuario con chips de grupos (actual / agregar / quitar)."""
    groups_by_xml = build_group_lookup(catalog)
    critical = build_critical_xml_ids(catalog)
    add_map, remove_map = build_preview_maps(previews)

    memberships: dict[str, set[str]] = {}
    for m in catalog.get('memberships') or []:
        if not isinstance(m, dict):
            continue
        login = _login_key(m.get('user_login'))
        xml_id = (m.get('group_xml_id') or '').strip()
        if login and xml_id:
            memberships.setdefault(login, set()).add(xml_id)

    users_by_login = {
        _login_key(u.get('login')): u for u in (catalog.get('users') or []) if isinstance(u, dict)
    }

    q = (search or '').strip().lower()
    rows: list[dict[str, Any]] = []

    logins = set(users_by_login.keys()) | set(memberships.keys()) | set(add_map.keys()) | set(remove_map.keys())
    for login in sorted(logins):
        if not login:
            continue
        u = users_by_login.get(login) or {}
        if u and not u.get('active', True):
            continue
        name = u.get('name') or login
        if q and q not in login and q not in (name or '').lower():
            continue

        current = memberships.get(login, set())
        to_add = add_map.get(login, set()) - current
        to_remove = remove_map.get(login, set()) & current

        if only_with_changes and not to_add and not to_remove:
            continue

        chips: list[dict[str, Any]] = []
        for xml_id in sorted(current):
            if xml_id in to_remove:
                chips.append(_chip(xml_id, groups_by_xml, critical, 'remove'))
            else:
                chips.append(_chip(xml_id, groups_by_xml, critical, 'current'))
        for xml_id in sorted(to_add):
            chips.append(_chip(xml_id, groups_by_xml, critical, 'add'))

        rows.append({
            'login': login,
            'name': name,
            'group_count': len(current),
            'add_count': len(to_add),
            'remove_count': len(to_remove),
            'chips': chips,
            'has_changes': bool(to_add or to_remove),
        })
    return rows


def build_group_summary_rows(catalog: dict[str, Any], search: str = '') -> list[dict[str, Any]]:
    """Grupos con cantidad de usuarios (vista por rol)."""
    groups_by_xml = build_group_lookup(catalog)
    critical = build_critical_xml_ids(catalog)
    counts: dict[str, int] = {}
    for m in catalog.get('memberships') or []:
        if not isinstance(m, dict):
            continue
        xml_id = (m.get('group_xml_id') or '').strip()
        if xml_id:
            counts[xml_id] = counts.get(xml_id, 0) + 1

    q = (search or '').strip().lower()
    rows = []
    for xml_id, g in sorted(groups_by_xml.items(), key=lambda x: (x[1].get('name') or x[0]).lower()):
        name = g.get('name') or xml_id
        if q and q not in xml_id.lower() and q not in name.lower():
            continue
        rows.append({
            'xml_id': xml_id,
            'name': name,
            'member_count': counts.get(xml_id, 0),
            'critical': xml_id in critical,
        })
    return rows


def build_import_stats(previews: list[Any] | None) -> dict[str, int]:
    add_n = remove_n = critical_n = 0
    for p in previews or []:
        action = getattr(p, 'action', None) or ''
        risk = getattr(p, 'risk_level', None) or ''
        if action == 'add':
            add_n += 1
        elif action == 'remove':
            remove_n += 1
        if risk == 'critical':
            critical_n += 1
    return {'add': add_n, 'remove': remove_n, 'critical': critical_n, 'total': add_n + remove_n}


def build_matriz_design_rows(import_rows: list[Any]) -> list[dict[str, Any]]:
    """Filas de hoja MATRIZ_GENERAL para vista de diseño."""
    out = []
    for r in import_rows or []:
        sheet = getattr(r, 'sheet_name', None) or ''
        if sheet != 'MATRIZ_GENERAL':
            continue
        out.append({
            'row': getattr(r, 'row_number', 0),
            'area': getattr(r, 'area', '') or '',
            'module': getattr(r, 'module', '') or '',
            'screen': getattr(r, 'screen', '') or '',
            'odoo_group': getattr(r, 'odoo_group', '') or '',
            'status': getattr(r, 'validation_status', '') or 'ok',
        })
    return out
