#!/usr/bin/env python3
"""
Copia filas de membership_plan de organization_id origen → destino (mismo slug).

No copia `id`: el destino asigna PK nuevas. Las suscripciones usan `membership_type`
(texto/slug), no FK a membership_plan.

Uso:
  python tools/copy_membership_plans_cross_env.py \\
    --source-env /opt/easynodeone/relatic/.env --source-org 1 \\
    --target-env /opt/easynodeone/dev/.env --target-org 3
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text


def _uri_from_env(env_path: str) -> str:
    load_dotenv(env_path, override=True)
    u = (os.environ.get('SQLALCHEMY_DATABASE_URI') or os.environ.get('DATABASE_URL') or '').strip()
    if not u:
        raise SystemExit(f'Sin SQLALCHEMY_DATABASE_URI / DATABASE_URL en {env_path}')
    if u.startswith('postgres://'):
        u = u.replace('postgres://', 'postgresql://', 1)
    return u


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--source-env', type=Path, required=True)
    ap.add_argument('--source-org', type=int, required=True)
    ap.add_argument('--target-env', type=Path, required=True)
    ap.add_argument('--target-org', type=int, required=True)
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()

    src_uri = _uri_from_env(str(args.source_env))
    tgt_uri = _uri_from_env(str(args.target_env))

    if src_uri == tgt_uri and args.source_org == args.target_org:
        raise SystemExit('Origen y destino idénticos; abortado.')

    src = create_engine(src_uri)
    tgt = create_engine(tgt_uri)

    cols = (
        'slug, name, description, price_yearly, price_monthly, display_order, level, '
        'badge, color, is_active, created_at, updated_at, organization_id'
    )

    with src.connect() as sc:
        rows = list(
            sc.execute(
                text(f'SELECT {cols} FROM membership_plan WHERE organization_id = :oid ORDER BY display_order, id'),
                {'oid': args.source_org},
            ).mappings()
        )

    print(f'Origen org {args.source_org}: {len(rows)} planes')
    if args.dry_run:
        with tgt.connect() as tc:
            n = tc.execute(
                text('SELECT COUNT(*) FROM membership_plan WHERE organization_id = :oid'),
                {'oid': args.target_org},
            ).scalar()
        print(f'Dry-run destino org {args.target_org}: ya tiene {n} planes (sin cambios)')
        return 0

    insert_sql = text(
        f"""
        INSERT INTO membership_plan ({cols})
        VALUES (
            :slug, :name, :description, :price_yearly, :price_monthly, :display_order, :level,
            :badge, :color, :is_active, :created_at, :updated_at, :organization_id
        )
        """
    )

    inserted = 0
    with tgt.begin() as tc:
        for r in rows:
            exists = tc.execute(
                text(
                    'SELECT 1 FROM membership_plan WHERE organization_id = :oid AND slug = :slug LIMIT 1'
                ),
                {'oid': args.target_org, 'slug': r['slug']},
            ).scalar()
            if exists:
                continue
            tc.execute(
                insert_sql,
                {
                    'slug': r['slug'],
                    'name': r['name'],
                    'description': r['description'],
                    'price_yearly': r['price_yearly'],
                    'price_monthly': r['price_monthly'],
                    'display_order': r['display_order'],
                    'level': r['level'],
                    'badge': r['badge'],
                    'color': r['color'],
                    'is_active': r['is_active'],
                    'created_at': r['created_at'],
                    'updated_at': r['updated_at'],
                    'organization_id': args.target_org,
                },
            )
            inserted += 1
        tc.execute(
            text(
                "SELECT setval(pg_get_serial_sequence('membership_plan', 'id'), "
                "(SELECT COALESCE(MAX(id), 1) FROM membership_plan))"
            )
        )

    print(f'Destino org {args.target_org}: insertados {inserted} planes (omitidos si slug ya existía)')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
