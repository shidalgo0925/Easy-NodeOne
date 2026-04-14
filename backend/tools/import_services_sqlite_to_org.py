#!/usr/bin/env python3
"""
Importa service + service_category + service_pricing_rule desde un SQLite de backup
hacia la org indicada en la BD actual (p. ej. PostgreSQL dev).

Uso (desde backend/, con .env del silo cargado):
  python tools/import_services_sqlite_to_org.py /ruta/backup.db <organization_id_pg> [organization_id_sqlite]

Notas:
- Si el SQLite tiene columna organization_id en service, podés pasar un 4º argumento
  para importar solo esa org de origen (ej. 4 = Detailing en nodeone.db).
- Sin 4º argumento: se importan todos los servicios del backup (catálogo único legacy).
- appointment_type_id y diagnostic_appointment_type_id se ponen en NULL (IDs no válidos entre tenants).
"""
from __future__ import annotations

import os
import sqlite3
import sys
from datetime import datetime

from dotenv import load_dotenv


def _parse_dt(val):
    if val is None or val == '':
        return datetime.utcnow()
    if isinstance(val, datetime):
        return val
    s = str(val).replace('Z', '+00:00')
    for fmt in ('%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d %H:%M:%S'):
        try:
            return datetime.strptime(s[:26], fmt)
        except ValueError:
            continue
    return datetime.utcnow()


def _sqlite_has_column(cur: sqlite3.Cursor, table: str, col: str) -> bool:
    cur.execute(f'PRAGMA table_info({table})')
    return any(r[1] == col for r in cur.fetchall())


def main() -> int:
    if len(sys.argv) < 3:
        print(
            'Uso: python tools/import_services_sqlite_to_org.py <backup.db> <organization_id_pg> [organization_id_sqlite]',
            file=sys.stderr,
        )
        return 1
    sqlite_path = os.path.abspath(sys.argv[1])
    target_org = int(sys.argv[2])
    source_org_sqlite: int | None = int(sys.argv[3]) if len(sys.argv) >= 4 else None
    if not os.path.isfile(sqlite_path):
        print(f'No existe: {sqlite_path}', file=sys.stderr)
        return 1

    backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    repo_root = os.path.abspath(os.path.join(backend_dir, '..'))
    sys.path.insert(0, backend_dir)
    os.chdir(backend_dir)
    load_dotenv(os.path.join(repo_root, '..', '.env'))

    import app as M

    con = sqlite3.connect(sqlite_path)
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    if source_org_sqlite is not None and not _sqlite_has_column(cur, 'service', 'organization_id'):
        print('El backup no tiene service.organization_id; no se puede filtrar por org de origen.', file=sys.stderr)
        return 1

    with M.app.app_context():
        org = M.SaasOrganization.query.get(target_org)
        if not org:
            print(f'No existe saas_organization id={target_org}', file=sys.stderr)
            return 1

        existing = M.Service.query.filter_by(organization_id=target_org).count()
        if existing:
            print(
                f'Ya hay {existing} servicio(s) en org {target_org}. '
                'Abortando para no duplicar. Borrá o mové datos antes de reimportar.',
                file=sys.stderr,
            )
            return 1

        cat_map: dict[int, int] = {}

        if source_org_sqlite is not None:
            cur.execute(
                'SELECT * FROM service WHERE organization_id = ? ORDER BY id',
                (source_org_sqlite,),
            )
            svc_rows = cur.fetchall()
            cat_ids = sorted({int(r['category_id']) for r in svc_rows if r['category_id'] is not None})
            if not cat_ids:
                cat_rows = []
            else:
                placeholders = ','.join('?' * len(cat_ids))
                cur.execute(f'SELECT * FROM service_category WHERE id IN ({placeholders})', cat_ids)
                cat_rows = cur.fetchall()
        else:
            cur.execute('SELECT * FROM service_category ORDER BY id')
            cat_rows = cur.fetchall()
            cur.execute('SELECT * FROM service ORDER BY id')
            svc_rows = cur.fetchall()

        for row in cat_rows:
            slug = (row['slug'] or '').strip()
            name = (row['name'] or '').strip()
            existing_cat = M.ServiceCategory.query.filter_by(slug=slug).first() if slug else None
            if not existing_cat and name:
                existing_cat = M.ServiceCategory.query.filter(M.ServiceCategory.name == name).first()
            if existing_cat:
                cat_map[int(row['id'])] = existing_cat.id
                continue
            c = M.ServiceCategory(
                name=name or slug or 'Sin nombre',
                slug=slug or None,
                description=row['description'],
                icon=row['icon'] or 'fas fa-folder',
                color=row['color'] or 'primary',
                display_order=int(row['display_order'] or 0),
                is_active=bool(row['is_active']),
            )
            M.db.session.add(c)
            M.db.session.flush()
            cat_map[int(row['id'])] = c.id

        svc_map: dict[int, int] = {}
        for row in svc_rows:
            cid = row['category_id']
            new_cat = cat_map.get(int(cid)) if cid is not None else None
            st = (row['service_type'] or 'AGENDABLE').strip().upper()
            if st not in ('AGENDABLE', 'CONSULTIVO'):
                st = 'AGENDABLE'
            s = M.Service(
                name=row['name'],
                description=row['description'] or '',
                icon=row['icon'] or 'fas fa-cog',
                membership_type=(row['membership_type'] or 'basic').lower(),
                category_id=new_cat,
                external_link=row['external_link'] or '',
                base_price=float(row['base_price'] or 0),
                is_active=bool(row['is_active']),
                display_order=int(row['display_order'] or 0),
                service_type=st,
                appointment_type_id=None,
                diagnostic_appointment_type_id=None,
                requires_diagnostic_appointment=bool(row['requires_diagnostic_appointment']),
                requires_payment_before_appointment=bool(row['requires_payment_before_appointment'])
                if row['requires_payment_before_appointment'] is not None
                else True,
                deposit_amount=row['deposit_amount'],
                deposit_percentage=row['deposit_percentage'],
                organization_id=target_org,
                default_tax_id=None,
            )
            if row['created_at']:
                s.created_at = _parse_dt(row['created_at'])
            if row['updated_at']:
                s.updated_at = _parse_dt(row['updated_at'])
            M.db.session.add(s)
            M.db.session.flush()
            svc_map[int(row['id'])] = s.id

        if source_org_sqlite is not None and svc_map:
            old_ids = list(svc_map.keys())
            placeholders = ','.join('?' * len(old_ids))
            cur.execute(
                f'SELECT * FROM service_pricing_rule WHERE service_id IN ({placeholders})',
                old_ids,
            )
            pricing_rows = cur.fetchall()
        else:
            cur.execute('SELECT * FROM service_pricing_rule ORDER BY id')
            pricing_rows = cur.fetchall()

        for row in pricing_rows:
            old_sid = int(row['service_id'])
            new_sid = svc_map.get(old_sid)
            if not new_sid:
                continue
            pr = M.ServicePricingRule(
                service_id=new_sid,
                membership_type=row['membership_type'],
                price=row['price'],
                discount_percentage=float(row['discount_percentage'] or 0),
                is_included=bool(row['is_included']),
                is_active=bool(row['is_active']),
            )
            if row['created_at']:
                pr.created_at = _parse_dt(row['created_at'])
            M.db.session.add(pr)

        M.db.session.commit()
        src = f' (origen sqlite org={source_org_sqlite})' if source_org_sqlite is not None else ''
        print(
            f'OK: categorías nuevas/reusadas map={len(cat_map)}, '
            f'servicios importados={len(svc_map)} → org_id={target_org}{src}'
        )
    con.close()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
