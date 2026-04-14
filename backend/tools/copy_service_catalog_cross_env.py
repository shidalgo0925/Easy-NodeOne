#!/usr/bin/env python3
"""
Copia catálogo de servicios (service + service_category faltantes + service_pricing_rule)
de una BD/org a otra (p. ej. dev org 2 → prod org 3).

Los FKs appointment_type_id, diagnostic_appointment_type_id y default_tax_id se ponen en NULL
en destino porque los IDs no son portables entre entornos.

Uso:
  python tools/copy_service_catalog_cross_env.py \\
    --source-env /opt/easynodeone/dev/.env --source-org 2 \\
    --target-env /opt/easynodeone/prod/.env --target-org 3

  --dry-run   solo muestra conteos, sin escribir
"""
from __future__ import annotations

import argparse
import os
import re
from datetime import UTC, datetime
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text


def _uri_from_env(env_path: str) -> str:
    load_dotenv(env_path, override=True)
    u = (os.environ.get('SQLALCHEMY_DATABASE_URI') or os.environ.get('DATABASE_URL') or '').strip()
    if not u:
        raise SystemExit(f'Sin SQLALCHEMY_DATABASE_URI / DATABASE_URL en {env_path}')
    return u


def _slugify(name: str) -> str:
    s = re.sub(r'[^a-z0-9]+', '-', (name or '').lower()).strip('-')
    return s or 'categoria'


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--source-env', required=True, help='Ruta .env del origen (ej. dev)')
    ap.add_argument('--source-org', type=int, required=True)
    ap.add_argument('--target-env', required=True, help='Ruta .env del destino (ej. prod)')
    ap.add_argument('--target-org', type=int, required=True)
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()

    src_uri = _uri_from_env(args.source_env)
    # Cargar destino sin mezclar: segundo load_dotenv override
    tgt_uri = _uri_from_env(args.target_env)

    if src_uri == tgt_uri and args.source_org == args.target_org:
        raise SystemExit('Origen y destino son el mismo par org/BD; abortado.')

    src = create_engine(src_uri)
    tgt = create_engine(tgt_uri)

    q_services = text(
        """
        SELECT s.id, s.name, s.description, s.icon, s.membership_type, s.category_id,
               s.external_link, s.base_price, s.is_active, s.display_order, s.service_type,
               s.requires_diagnostic_appointment,
               s.requires_payment_before_appointment, s.deposit_amount, s.deposit_percentage,
               s.created_at, s.updated_at,
               c.name AS cat_name, c.slug AS cat_slug, c.description AS cat_description,
               c.icon AS cat_icon, c.color AS cat_color, c.display_order AS cat_display_order,
               c.is_active AS cat_is_active
        FROM service s
        LEFT JOIN service_category c ON c.id = s.category_id
        WHERE s.organization_id = :oid
        ORDER BY s.id
        """
    )

    with src.connect() as sc:
        org = sc.execute(
            text('SELECT id, name FROM saas_organization WHERE id = :id'),
            {'id': args.source_org},
        ).fetchone()
        if not org:
            raise SystemExit(f'Origen: no existe saas_organization id={args.source_org}')
        rows = list(sc.execute(q_services, {'oid': args.source_org}).mappings())

    if not rows:
        print('Origen: 0 servicios; nada que copiar.')
        return 0

    old_ids = [int(r['id']) for r in rows]
    q_rules = text(
        """
        SELECT id, service_id, membership_type, price, discount_percentage, is_included, is_active, created_at
        FROM service_pricing_rule
        WHERE service_id = ANY(:ids)
        ORDER BY service_id, id
        """
    )

    with src.connect() as sc:
        rule_rows = list(sc.execute(q_rules, {'ids': old_ids}).mappings())

    print(
        f"Origen org {args.source_org} ({org[1]}): {len(rows)} servicios, {len(rule_rows)} reglas de precio."
    )

    with tgt.connect() as tc:
        torg = tc.execute(
            text('SELECT id, name FROM saas_organization WHERE id = :id'),
            {'id': args.target_org},
        ).fetchone()
        if not torg:
            raise SystemExit(f'Destino: no existe saas_organization id={args.target_org}')
        n_before = tc.execute(
            text('SELECT COUNT(*) FROM service WHERE organization_id = :oid'),
            {'oid': args.target_org},
        ).scalar()
        print(f'Destino org {args.target_org} ({torg[1]}): {n_before} servicios antes.')

    if args.dry_run:
        print('Dry-run: no se escribió nada.')
        return 0

    def ensure_category(conn, cat_name, cat_slug, cat_desc, cat_icon, cat_color, cat_order, cat_active):
        if cat_name and str(cat_name).strip():
            cid = conn.execute(
                text('SELECT id FROM service_category WHERE lower(trim(name)) = lower(trim(:n))'),
                {'n': str(cat_name).strip()},
            ).scalar()
            if cid:
                return int(cid)
        slug = (cat_slug or '').strip() or _slugify(cat_name or 'cat')
        cid = conn.execute(text('SELECT id FROM service_category WHERE slug = :s'), {'s': slug}).scalar()
        if cid:
            return int(cid)
        now = datetime.now(UTC).replace(tzinfo=None)
        cid = conn.execute(
            text(
                """
                INSERT INTO service_category
                  (name, slug, description, icon, color, display_order, is_active, created_at, updated_at)
                VALUES
                  (:name, :slug, :description, :icon, :color, :display_order, :is_active, :ca, :ua)
                RETURNING id
                """
            ),
            {
                'name': (cat_name or slug).strip() or slug,
                'slug': slug,
                'description': cat_desc,
                'icon': cat_icon or 'fas fa-folder',
                'color': cat_color or 'primary',
                'display_order': int(cat_order or 0),
                'is_active': bool(cat_active) if cat_active is not None else True,
                'ca': now,
                'ua': now,
            },
        ).scalar()
        return int(cid)

    old_to_new: dict[int, int] = {}

    ins_svc = text(
        """
        INSERT INTO service (
          name, description, icon, membership_type, category_id, external_link, base_price,
          is_active, display_order, service_type, requires_diagnostic_appointment,
          diagnostic_appointment_type_id, appointment_type_id, requires_payment_before_appointment,
          deposit_amount, deposit_percentage, created_at, updated_at, organization_id, default_tax_id
        ) VALUES (
          :name, :description, :icon, :membership_type, :category_id, :external_link, :base_price,
          :is_active, :display_order, :service_type, :requires_diagnostic_appointment,
          NULL, NULL, :requires_payment_before_appointment,
          :deposit_amount, :deposit_percentage, :created_at, :updated_at, :organization_id, NULL
        )
        RETURNING id
        """
    )

    ins_rule = text(
        """
        INSERT INTO service_pricing_rule
          (service_id, membership_type, price, discount_percentage, is_included, is_active, created_at)
        VALUES
          (:service_id, :membership_type, :price, :discount_percentage, :is_included, :is_active, :created_at)
        ON CONFLICT ON CONSTRAINT uq_service_pricing_membership DO UPDATE SET
          price = EXCLUDED.price,
          discount_percentage = EXCLUDED.discount_percentage,
          is_included = EXCLUDED.is_included,
          is_active = EXCLUDED.is_active
        """
    )

    with tgt.begin() as conn:
        for r in rows:
            cat_id = None
            if r['cat_name'] or r['cat_slug']:
                cat_id = ensure_category(
                    conn,
                    r['cat_name'],
                    r['cat_slug'],
                    r['cat_description'],
                    r['cat_icon'],
                    r['cat_color'],
                    r['cat_display_order'],
                    r['cat_is_active'],
                )

            st = (r['service_type'] or 'AGENDABLE').upper()
            if st not in ('AGENDABLE', 'CONSULTIVO'):
                st = 'AGENDABLE'

            new_id = conn.execute(
                ins_svc,
                {
                    'name': r['name'],
                    'description': r['description'],
                    'icon': r['icon'] or 'fas fa-cog',
                    'membership_type': r['membership_type'] or 'basic',
                    'category_id': cat_id,
                    'external_link': r['external_link'],
                    'base_price': float(r['base_price'] or 0),
                    'is_active': bool(r['is_active']) if r['is_active'] is not None else True,
                    'display_order': int(r['display_order'] or 0),
                    'service_type': st,
                    'requires_diagnostic_appointment': bool(r['requires_diagnostic_appointment'] or False),
                    'requires_payment_before_appointment': bool(
                        r['requires_payment_before_appointment']
                        if r['requires_payment_before_appointment'] is not None
                        else True
                    ),
                    'deposit_amount': r['deposit_amount'],
                    'deposit_percentage': r['deposit_percentage'],
                    'created_at': r['created_at'] or datetime.utcnow(),
                    'updated_at': r['updated_at'] or datetime.utcnow(),
                    'organization_id': args.target_org,
                },
            ).scalar()
            old_to_new[int(r['id'])] = int(new_id)

        for pr in rule_rows:
            sid = int(pr['service_id'])
            if sid not in old_to_new:
                continue
            conn.execute(
                ins_rule,
                {
                    'service_id': old_to_new[sid],
                    'membership_type': pr['membership_type'],
                    'price': pr['price'],
                    'discount_percentage': float(pr['discount_percentage'] or 0),
                    'is_included': bool(pr['is_included'] or False),
                    'is_active': bool(pr['is_active']) if pr['is_active'] is not None else True,
                    'created_at': pr['created_at'] or datetime.utcnow(),
                },
            )

    print(f'Listo: {len(old_to_new)} servicios insertados en org {args.target_org}, reglas aplicadas.')

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
