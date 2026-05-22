"""Vista matriz módulo × pantalla × grupo (diseño MATRIZ_GENERAL)."""

from __future__ import annotations

import re
from typing import Any

from nodeone.modules.security_matrix_manager.permissions_view import (
    build_critical_xml_ids,
    build_group_lookup,
)

# Filas de diseño por defecto (módulos del boceto) hasta que suban XLS propio.
DEFAULT_MATRIZ_ROWS: list[dict[str, str]] = [
    # CxC
    {'area': 'Finanzas', 'modulo': 'CxC', 'pantalla': 'Clientes / deudores', 'grupo_odoo_xml_id': 'account.group_account_invoice'},
    {'area': 'Finanzas', 'modulo': 'CxC', 'pantalla': 'Facturas cliente', 'grupo_odoo_xml_id': 'account.group_account_invoice'},
    {'area': 'Finanzas', 'modulo': 'CxC', 'pantalla': 'Cobros / pagos cliente', 'grupo_odoo_xml_id': 'account.group_account_invoice'},
    {'area': 'Finanzas', 'modulo': 'CxC', 'pantalla': 'Seguimiento de cobros', 'grupo_odoo_xml_id': 'account.group_account_user'},
    {'area': 'Finanzas', 'modulo': 'CxC', 'pantalla': 'Informes CxC', 'grupo_odoo_xml_id': 'account.group_account_readonly'},
    # Facturación
    {'area': 'Finanzas', 'modulo': 'Fact', 'pantalla': 'Facturas', 'grupo_odoo_xml_id': 'account.group_account_invoice'},
    {'area': 'Finanzas', 'modulo': 'Fact', 'pantalla': 'Notas crédito', 'grupo_odoo_xml_id': 'account.group_account_invoice'},
    {'area': 'Finanzas', 'modulo': 'Fact', 'pantalla': 'Rectificativas', 'grupo_odoo_xml_id': 'account.group_account_manager'},
    {'area': 'Finanzas', 'modulo': 'Fact', 'pantalla': 'Configuración fiscal', 'grupo_odoo_xml_id': 'account.group_account_manager'},
    {'area': 'Finanzas', 'modulo': 'Fact', 'pantalla': 'Informes facturación', 'grupo_odoo_xml_id': 'account.group_account_readonly'},
    # Inventario
    {'area': 'Operaciones', 'modulo': 'Inv', 'pantalla': 'Productos', 'grupo_odoo_xml_id': 'stock.group_stock_user'},
    {'area': 'Operaciones', 'modulo': 'Inv', 'pantalla': 'Recepciones', 'grupo_odoo_xml_id': 'stock.group_stock_user'},
    {'area': 'Operaciones', 'modulo': 'Inv', 'pantalla': 'Entregas', 'grupo_odoo_xml_id': 'stock.group_stock_user'},
    {'area': 'Operaciones', 'modulo': 'Inv', 'pantalla': 'Ajustes inventario', 'grupo_odoo_xml_id': 'stock.group_stock_manager'},
    {'area': 'Operaciones', 'modulo': 'Inv', 'pantalla': 'Informes stock', 'grupo_odoo_xml_id': 'stock.group_stock_user'},
    # Contabilidad
    {'area': 'Finanzas', 'modulo': 'Conta', 'pantalla': 'Diario / asientos', 'grupo_odoo_xml_id': 'account.group_account_user'},
    {'area': 'Finanzas', 'modulo': 'Conta', 'pantalla': 'Conciliación bancaria', 'grupo_odoo_xml_id': 'account.group_account_user'},
    {'area': 'Finanzas', 'modulo': 'Conta', 'pantalla': 'Cierre / bloqueo', 'grupo_odoo_xml_id': 'account.group_account_manager'},
    {'area': 'Finanzas', 'modulo': 'Conta', 'pantalla': 'Plan contable', 'grupo_odoo_xml_id': 'account.group_account_manager'},
    {'area': 'Finanzas', 'modulo': 'Conta', 'pantalla': 'Informes contables', 'grupo_odoo_xml_id': 'account.group_account_readonly'},
]

_MODULE_LABELS: dict[str, str] = {
    'cxc': 'CxC',
    'cxp': 'CxP',
    'fact': 'Fact',
    'facturacion': 'Fact',
    'inv': 'Inv',
    'inventario': 'Inv',
    'conta': 'Conta',
    'contabilidad': 'Conta',
    'ventas': 'Ventas',
    'crm': 'CRM',
    'compras': 'Compras',
    'rrhh': 'RRHH',
}


def _slug(text: str) -> str:
    s = re.sub(r'[^a-z0-9]+', '_', (text or '').strip().lower())
    return s.strip('_') or 'general'


def module_tab_id(modulo: str) -> str:
    raw = (modulo or '').strip()
    if not raw:
        return 'general'
    slug = _slug(raw)
    return slug if slug else 'general'


def module_tab_label(modulo: str) -> str:
    raw = (modulo or '').strip()
    if not raw:
        return 'General'
    sid = module_tab_id(raw)
    if sid in _MODULE_LABELS:
        return _MODULE_LABELS[sid]
    if len(raw) <= 8:
        return raw
    return raw[:12]


def _resolve_group_ref(ref: str, groups_by_xml: dict[str, dict], groups_by_name: dict[str, dict]) -> str | None:
    ref = (ref or '').strip()
    if not ref:
        return None
    if ref in groups_by_xml:
        return ref
    low = ref.lower()
    g = groups_by_name.get(low)
    if g:
        return (g.get('xml_id') or '').strip() or None
    return None


def matriz_entries_from_import_rows(import_rows: list[Any]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for r in import_rows or []:
        if getattr(r, 'sheet_name', None) != 'MATRIZ_GENERAL':
            continue
        out.append({
            'area': getattr(r, 'area', '') or '',
            'modulo': getattr(r, 'module', '') or '',
            'pantalla': getattr(r, 'screen', '') or '',
            'grupo_odoo_xml_id': getattr(r, 'odoo_group', '') or '',
        })
    return out


def _matriz_entries_from_dicts(rows: list[dict[str, Any]]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        modulo = str(row.get('modulo') or row.get('module') or row.get('módulo') or '').strip()
        pantalla = str(row.get('pantalla') or row.get('screen') or '').strip()
        grupo = str(
            row.get('grupo_odoo_xml_id')
            or row.get('grupo_xml_id')
            or row.get('grupo')
            or row.get('group')
            or ''
        ).strip()
        if not modulo and not pantalla:
            continue
        out.append({
            'area': str(row.get('area') or row.get('área') or '').strip(),
            'modulo': modulo,
            'pantalla': pantalla,
            'grupo_odoo_xml_id': grupo,
        })
    return out


def build_module_matrix_view(
    catalog: dict[str, Any],
    matriz_entries: list[dict[str, str]],
    *,
    active_module: str | None = None,
) -> dict[str, Any]:
    """
    Construye pestañas por módulo y grilla pantalla (filas) × grupo Odoo (columnas).
    Celda marcada = existe asignación en MATRIZ_GENERAL.
    """
    groups_by_xml = build_group_lookup(catalog)
    groups_by_name = {
        (g.get('name') or '').strip().lower(): g
        for g in (catalog.get('groups') or [])
        if isinstance(g, dict) and (g.get('name') or '').strip()
    }
    critical = build_critical_xml_ids(catalog)

    # module_id -> screen_key -> set(xml_id)
    assignments: dict[str, dict[str, set[str]]] = {}
    screen_meta: dict[str, dict[str, dict[str, str]]] = {}
    module_labels: dict[str, str] = {}
    module_raw: dict[str, str] = {}

    for entry in matriz_entries:
        modulo = (entry.get('modulo') or '').strip()
        area = (entry.get('area') or '').strip()
        pantalla = (entry.get('pantalla') or '').strip()
        group_ref = (entry.get('grupo_odoo_xml_id') or '').strip()
        if not modulo or not pantalla or not group_ref:
            continue
        mid = module_tab_id(modulo)
        module_labels[mid] = module_tab_label(modulo)
        module_raw.setdefault(mid, modulo)
        xml_id = _resolve_group_ref(group_ref, groups_by_xml, groups_by_name) or group_ref
        screen_key = f'{area}\x1f{pantalla}'
        assignments.setdefault(mid, {}).setdefault(screen_key, set()).add(xml_id)
        screen_meta.setdefault(mid, {})[screen_key] = {'area': area, 'pantalla': pantalla}

    modules = [
        {'id': mid, 'label': module_labels.get(mid, mid)}
        for mid in sorted(module_labels.keys(), key=lambda x: module_labels.get(x, x))
    ]
    if not modules:
        modules = [{'id': 'cxc', 'label': 'CxC'}, {'id': 'fact', 'label': 'Fact'}, {'id': 'inv', 'label': 'Inv'}, {'id': 'conta', 'label': 'Conta'}]

    active = active_module or (modules[0]['id'] if modules else 'cxc')
    if not any(m['id'] == active for m in modules):
        active = modules[0]['id']

    mod_assign = assignments.get(active, {})
    mod_screens = screen_meta.get(active, {})
    all_xml_ids: set[str] = set()
    for s in mod_assign.values():
        all_xml_ids |= s

    columns = []
    for xml_id in sorted(all_xml_ids, key=lambda x: (groups_by_xml.get(x, {}).get('name') or x).lower()):
        g = groups_by_xml.get(xml_id) or {}
        name = g.get('name') or xml_id
        short = name if len(name) <= 18 else name[:16] + '…'
        columns.append({
            'xml_id': xml_id,
            'name': name,
            'short': short,
            'critical': xml_id in critical,
            'valid': xml_id in groups_by_xml,
        })

    rows = []
    for screen_key in sorted(mod_screens.keys(), key=lambda k: (mod_screens[k].get('area', ''), mod_screens[k].get('pantalla', ''))):
        meta = mod_screens[screen_key]
        checked_set = mod_assign.get(screen_key, set())
        cells = []
        for col in columns:
            xml_id = col['xml_id']
            cells.append({
                'xml_id': xml_id,
                'checked': xml_id in checked_set,
                'critical': col['critical'],
                'valid': col['valid'],
            })
        rows.append({
            'area': meta.get('area') or '',
            'screen': meta.get('pantalla') or '',
            'screen_key': screen_key,
            'cells': cells,
        })

    return {
        'modules': modules,
        'active_module': active,
        'active_module_raw': module_raw.get(active, modules[0]['label'] if modules else 'CxC'),
        'columns': columns,
        'rows': rows,
        'has_data': bool(rows),
    }
