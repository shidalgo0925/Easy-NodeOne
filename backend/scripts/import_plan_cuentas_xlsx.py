"""
Importa plan de cuentas base desde .xlsx estilo Odoo (columnas: Código, Nombre, Tipo, …).

Lee el XML del xlsx con la biblioteca estándar (sin openpyxl).

Uso:
  cd backend && python3 scripts/import_plan_cuentas_xlsx.py <organization_id> [ruta.xlsx]
  cd backend && python3 scripts/import_plan_cuentas_xlsx.py --all [ruta.xlsx]

Por defecto usa scripts/data/PlanCuentas.xlsx si existe.

Mapeo de la columna «Tipo» (etiquetas típicas de Odoo en español) → tipo núcleo:
  asset: Activos corrientes, Banco y efectivo, Por cobrar, Fuera de balance
  liability: Pasivos corrientes, Por pagar
  equity: Capital, Ganancias del año corriente
  income: Ingreso, Otro ingreso
  expense: Gastos
"""
from __future__ import annotations

import os
import re
import sys
import xml.etree.ElementTree as ET
import zipfile
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

NS_MAIN = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
NS = {'m': NS_MAIN}

# Etiqueta exacta (strip) → tipo núcleo accounting_core
TIPO_ODOO_A_CORE: dict[str, str] = {
    'activos corrientes': 'asset',
    'banco y efectivo': 'asset',
    'por cobrar': 'asset',
    'fuera de balance': 'asset',
    'pasivos corrientes': 'liability',
    'por pagar': 'liability',
    'capital': 'equity',
    'ganancias del año corriente': 'equity',
    'ingreso': 'income',
    'otro ingreso': 'income',
    'gastos': 'expense',
}


def _col_cell(addr: str) -> tuple[str, int]:
    m = re.match(r'([A-Z]+)(\d+)', addr or '')
    if not m:
        return '', 0
    return m.group(1), int(m.group(2))


def _load_shared_strings(z: zipfile.ZipFile) -> list[str]:
    try:
        raw = z.read('xl/sharedStrings.xml')
    except KeyError:
        return []
    root = ET.fromstring(raw)
    out: list[str] = []
    for si in root.findall(f'.//{{{NS_MAIN}}}si'):
        parts: list[str] = []
        for t in si.findall(f'.//{{{NS_MAIN}}}t'):
            parts.append(t.text or '')
        out.append(''.join(parts))
    return out


def _resolve_cell(t: str | None, v: str, shared: list[str]) -> str:
    if t == 's' and v.isdigit():
        i = int(v)
        return shared[i] if i < len(shared) else v
    return v


def parse_plan_cuentas_xlsx(path: str) -> list[dict[str, Any]]:
    rows_out: list[dict[str, Any]] = []
    with zipfile.ZipFile(path, 'r') as z:
        sheet_names = [n for n in z.namelist() if n.startswith('xl/worksheets/sheet') and n.endswith('.xml')]
        if not sheet_names:
            raise ValueError('El archivo no contiene hojas xl/worksheets.')
        sheet_names.sort()
        root = ET.fromstring(z.read(sheet_names[0]))
        shared = _load_shared_strings(z)
        by_row: dict[int, dict[str, str]] = {}
        for c in root.findall('.//m:c', NS):
            addr = c.get('r')
            if not addr:
                continue
            t = c.get('t')
            ve = c.find('m:v', NS)
            if ve is None or ve.text is None:
                continue
            letter, rn = _col_cell(addr)
            val = _resolve_cell(t, ve.text, shared)
            by_row.setdefault(rn, {})[letter] = val
        header = by_row.get(1) or {}
        if (header.get('A') or '').strip().lower() not in ('código', 'codigo'):
            raise ValueError(
                'Se esperaba la fila 1 con columna A «Código» (export Odoo). Cabeceras: %r' % header
            )
        for rn in sorted(by_row):
            if rn < 2:
                continue
            r = by_row[rn]
            code = (r.get('A') or '').strip()
            name = (r.get('B') or '').strip()
            tipo_odoo = (r.get('C') or '').strip()
            if not code or not name:
                continue
            key = tipo_odoo.lower()
            core = TIPO_ODOO_A_CORE.get(key)
            rows_out.append(
                {
                    'code': code,
                    'name': name,
                    'tipo_odoo': tipo_odoo,
                    'core_type': core,
                    'reconcile': (r.get('D') or '').strip(),
                    'currency': (r.get('E') or '').strip(),
                }
            )
    return rows_out


def sync_plan_cuentas_for_org(org_id: int, path: str, *, verbose: bool = True) -> tuple[int, int, list[str], str]:
    from app import db
    from models.accounting_core import Account
    from models.saas import SaasOrganization
    from nodeone.modules.accounting_core.service import ensure_accounting_core_schema

    parsed = parse_plan_cuentas_xlsx(path)
    skipped: list[str] = []
    for row in parsed:
        if row['core_type'] is None:
            skipped.append(f"{row['code']}: tipo desconocido «{row['tipo_odoo']}»")

    ensure_accounting_core_schema()
    org = SaasOrganization.query.get(org_id)
    if org is None:
        raise ValueError(f'organization_id={org_id} no existe.')

    created = updated = 0
    for row in parsed:
        core = row['core_type']
        if not core:
            continue
        code = row['code'][:32]
        name = row['name'][:200]
        existing = Account.query.filter_by(organization_id=org_id, code=code).first()
        if existing is None:
            db.session.add(
                Account(
                    organization_id=org_id,
                    code=code,
                    name=name,
                    type=core,
                        allow_reconcile=str(row.get('reconcile') or '').strip() in {'1', 'true', 'True', 'sí', 'si', 'yes'},
                        currency_code=((row.get('currency') or '').strip()[:16] or None),
                    is_active=True,
                )
            )
            created += 1
        else:
            existing.name = name
            existing.type = core
            existing.allow_reconcile = str(row.get('reconcile') or '').strip() in {'1', 'true', 'True', 'sí', 'si', 'yes'}
            existing.currency_code = ((row.get('currency') or '').strip()[:16] or None)
            existing.is_active = True
            updated += 1
    db.session.commit()
    if verbose:
        print(f'OK org={org_id} ({org.name}): +{created} nuevas, {updated} actualizadas desde {path}')
        if skipped:
            print('Advertencia — filas omitidas (tipo no mapeado):', file=sys.stderr)
            for s in skipped:
                print(f'  {s}', file=sys.stderr)
    return created, updated, skipped, org.name


def sync_plan_cuentas_all_orgs(path: str, *, only_active: bool = True) -> tuple[int, int, int]:
    from models.saas import SaasOrganization

    q = SaasOrganization.query
    if only_active:
        q = q.filter_by(is_active=True)
    orgs = q.order_by(SaasOrganization.id.asc()).all()
    total_created = 0
    total_updated = 0
    total_orgs = 0
    for org in orgs:
        created, updated, _, _ = sync_plan_cuentas_for_org(int(org.id), path, verbose=True)
        total_created += created
        total_updated += updated
        total_orgs += 1
    return total_orgs, total_created, total_updated


def main() -> int:
    if len(sys.argv) < 2:
        print(
            'Uso: python3 scripts/import_plan_cuentas_xlsx.py <organization_id|--all> [ruta.xlsx]',
            file=sys.stderr,
        )
        return 2
    target = (sys.argv[1] or '').strip()
    base = os.path.dirname(os.path.abspath(__file__))
    default_xlsx = os.path.join(base, 'data', 'PlanCuentas.xlsx')
    path = sys.argv[2] if len(sys.argv) > 2 else default_xlsx
    if not os.path.isfile(path):
        print(f'No existe el archivo: {path}', file=sys.stderr)
        return 2

    from app import app

    with app.app_context():
        if target == '--all':
            orgs, created, updated = sync_plan_cuentas_all_orgs(path, only_active=False)
            print(f'OK global: orgs={orgs}, +{created} nuevas, {updated} actualizadas')
        else:
            org_id = int(target)
            sync_plan_cuentas_for_org(org_id, path, verbose=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
