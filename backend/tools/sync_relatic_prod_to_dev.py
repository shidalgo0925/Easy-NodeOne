#!/usr/bin/env python3
"""Sincroniza usuarios, membresías y participantes desde easynodeone_relatic (Relatic aislada)."""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

SRC_DOTENV = Path('/opt/easynodeone/relatic/.env')
APPDEV_DOTENV = Path('/opt/easynodeone/dev/.env')
PANAMA_DOTENV = Path('/opt/easynodeone/relatic-panama-dev/.env')
TABLES_COMPARE = (
    'user',
    'user_organization',
    'membership',
    'subscription',
    'event',
    'event_participant',
    'event_certificate',
    'event_registration',
)


def _load_db_url(dotenv: Path) -> str:
    load_dotenv(dotenv, override=True)
    url = (os.environ.get('SQLALCHEMY_DATABASE_URI') or os.environ.get('DATABASE_URL') or '').strip()
    if url.startswith('postgres://'):
        url = url.replace('postgres://', 'postgresql://', 1)
    if not url:
        raise SystemExit(f'Sin DATABASE_URL en {dotenv}')
    return url


def connect(dotenv: Path):
    return psycopg2.connect(_load_db_url(dotenv))


def count_rows(conn, table: str) -> int:
    q = f'SELECT count(*) FROM "{table}"' if table == 'user' else f'SELECT count(*) FROM {table}'
    with conn.cursor() as cur:
        cur.execute(q)
        return int(cur.fetchone()[0])


def compare_report(src, dst) -> list[tuple[str, int, int, int]]:
    rows = []
    for t in TABLES_COMPARE:
        cs = count_rows(src, t)
        cd = count_rows(dst, t)
        rows.append((t, cs, cd, cd - cs))
    return rows


def user_columns(conn) -> list[str]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT column_name FROM information_schema.columns
            WHERE table_schema='public' AND table_name='user'
            ORDER BY ordinal_position
            """
        )
        return [r[0] for r in cur.fetchall()]


def common_user_columns(src, dst) -> list[str]:
    src_cols = set(user_columns(src))
    dst_cols = set(user_columns(dst))
    common = [c for c in user_columns(src) if c in dst_cols and c != 'id']
    if src_cols - dst_cols:
        print(f'  user columns omitted (not in dest): {sorted(src_cols - dst_cols)}')
    return common


def sync_users_to_org(src, dst, org_id: int, dry_run: bool) -> dict[str, int]:
    """Inserta/actualiza users de prod en destino con organization_id=org_id. Retorna map email→dst_id."""
    cols = common_user_columns(src, dst)
    col_list = ', '.join(cols)
    email_to_id: dict[str, int] = {}

    with src.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as sc:
        sc.execute(f'SELECT * FROM "user" ORDER BY id')
        prod_users = sc.fetchall()

    inserted = updated = skipped = 0
    with dst.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as dc:
        for pu in prod_users:
            email = (pu['email'] or '').strip().lower()
            if not email:
                continue
            dc.execute('SELECT id, organization_id FROM "user" WHERE lower(email)=%s', (email,))
            existing = dc.fetchone()
            row = dict(pu)
            row['organization_id'] = org_id
            if existing:
                email_to_id[email] = int(existing['id'])
                if int(existing['organization_id'] or 0) != org_id:
                    if not dry_run:
                        dc.execute(
                            'UPDATE "user" SET organization_id=%s WHERE id=%s',
                            (org_id, existing['id']),
                        )
                    updated += 1
                else:
                    skipped += 1
                continue
            if dry_run:
                inserted += 1
                continue
            placeholders = ', '.join(['%s'] * len(cols))
            dc.execute(
                f'INSERT INTO "user" ({col_list}) VALUES ({placeholders}) RETURNING id',
                [row[c] for c in cols],
            )
            email_to_id[email] = int(dc.fetchone()['id'])
            inserted += 1
    if not dry_run:
        dst.commit()
    print(f'  users: inserted={inserted} updated_org={updated} unchanged={skipped}')
    return email_to_id


def build_email_id_map(dst) -> dict[str, int]:
    m = {}
    with dst.cursor() as cur:
        cur.execute('SELECT id, lower(email) FROM "user"')
        for uid, em in cur.fetchall():
            if em:
                m[em] = int(uid)
    return m


def sync_user_organization(src, dst, org_id: int, email_map: dict[str, int], dry_run: bool):
    with src.cursor() as sc:
        sc.execute(
            'SELECT user_id, role, status, created_at FROM user_organization WHERE organization_id=1'
        )
        src_rows = sc.fetchall()
    ins = 0
    with dst.cursor() as dc:
        for src_uid, role, status, created_at in src_rows:
            sc2 = src.cursor()
            sc2.execute('SELECT lower(email) FROM "user" WHERE id=%s', (src_uid,))
            em = sc2.fetchone()
            if not em or not em[0]:
                continue
            dst_uid = email_map.get(em[0])
            if not dst_uid:
                continue
            dc.execute(
                'SELECT 1 FROM user_organization WHERE user_id=%s AND organization_id=%s',
                (dst_uid, org_id),
            )
            if dc.fetchone():
                continue
            if dry_run:
                ins += 1
                continue
            dc.execute(
                """
                INSERT INTO user_organization (user_id, organization_id, role, status, created_at)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (user_id, organization_id) DO NOTHING
                """,
                (dst_uid, org_id, role, status, created_at),
            )
            ins += dc.rowcount
    if not dry_run:
        dst.commit()
    print(f'  user_organization: inserted={ins}')


def sync_membership(src, dst, email_map: dict[str, int], dry_run: bool):
    with src.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as sc:
        sc.execute('SELECT m.*, lower(u.email) AS email FROM membership m JOIN "user" u ON u.id=m.user_id')
        rows = sc.fetchall()
    ins = skip = 0
    with dst.cursor() as dc:
        for m in rows:
            dst_uid = email_map.get((m['email'] or '').strip().lower())
            if not dst_uid:
                skip += 1
                continue
            dc.execute(
                'SELECT 1 FROM membership WHERE user_id=%s AND membership_type=%s AND end_date=%s',
                (dst_uid, m['membership_type'], m['end_date']),
            )
            if dc.fetchone():
                skip += 1
                continue
            if dry_run:
                ins += 1
                continue
            dc.execute(
                """
                INSERT INTO membership (user_id, membership_type, start_date, end_date, is_active, payment_status, amount, created_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                """,
                (
                    dst_uid,
                    m['membership_type'],
                    m['start_date'],
                    m['end_date'],
                    m['is_active'],
                    m['payment_status'],
                    m['amount'],
                    m['created_at'],
                ),
            )
            ins += 1
    if not dry_run:
        dst.commit()
    print(f'  membership: inserted={ins} skipped={skip}')


def sync_event_participants(src, dst, dry_run: bool):
    with src.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as sc:
        sc.execute('SELECT * FROM event_participant ORDER BY id')
        rows = sc.fetchall()
    if not rows:
        print('  event_participant: nothing in source')
        return
    cols = [k for k in rows[0].keys() if k != 'id']
    col_list = ', '.join(cols)
    ins = skip = 0
    with dst.cursor() as dc:
        for p in rows:
            em = (p.get('email') or '').strip().lower()
            dc.execute(
                'SELECT 1 FROM event_participant WHERE event_id=%s AND lower(trim(email))=%s',
                (p['event_id'], em),
            )
            if em and dc.fetchone():
                skip += 1
                continue
            if dry_run:
                ins += 1
                continue
            placeholders = ', '.join(['%s'] * len(cols))
            dc.execute(
                f'INSERT INTO event_participant ({col_list}) VALUES ({placeholders})',
                [p[c] for c in cols],
            )
            ins += 1
    if not dry_run:
        dst.commit()
    print(f'  event_participant: inserted={ins} skipped={skip}')


def refresh_panama_users_from_prod(src, dst, dry_run: bool):
    """relatic_panama_dev: alinear users con prod (org 1) sin perder datos ajenos opcional."""
    with src.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as sc:
        sc.execute('SELECT * FROM "user" ORDER BY id')
        prod = {r['email'].lower(): r for r in sc.fetchall() if r.get('email')}
    with dst.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as dc:
        dc.execute('SELECT id, lower(email) AS email FROM "user"')
        dst_users = {r['email']: r['id'] for r in dc.fetchall()}
    added = 0
    for em, pu in prod.items():
        if em in dst_users:
            continue
        if dry_run:
            added += 1
            continue
        cols = [c for c in common_user_columns(src, dst) if c in pu]
        col_list = ', '.join(cols)
        placeholders = ', '.join(['%s'] * len(cols))
        with dst.cursor() as dc:
            dc.execute(
                f'INSERT INTO "user" ({col_list}) VALUES ({placeholders})',
                [pu[c] for c in cols],
            )
            added += 1
    if not dry_run:
        dst.commit()
    print(f'  panama users missing from prod added={added}')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--target', choices=('panama', 'appdev', 'both'), default='both')
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()

    src = connect(SRC_DOTENV)

    if args.target in ('panama', 'both'):
        print('\n=== relatic_panama_dev ===')
        dst_p = connect(PANAMA_DOTENV)
        for t, cs, cd, d in compare_report(src, dst_p):
            mark = ' OK' if d == 0 else f' DELTA {d:+d}'
            print(f'  {t:<22} prod={cs:>5} panama={cd:>5}{mark}')
        refresh_panama_users_from_prod(src, dst_p, args.dry_run)
        sync_event_participants(src, dst_p, args.dry_run)
        dst_p.close()

    if args.target in ('appdev', 'both'):
        print('\n=== easynodeone_dev (org 3 Relatic Panama Dev) ===')
        dst_a = connect(APPDEV_DOTENV)
        for t, cs, cd, d in compare_report(src, dst_a):
            print(f'  {t:<22} prod={cs:>5} appdev={cd:>5} delta={d:+d}')
        email_map = sync_users_to_org(src, dst_a, org_id=3, dry_run=args.dry_run)
        if not email_map and not args.dry_run:
            email_map = build_email_id_map(dst_a)
        elif args.dry_run:
            email_map = build_email_id_map(dst_a)
        sync_user_organization(src, dst_a, 3, email_map, args.dry_run)
        sync_membership(src, dst_a, email_map, args.dry_run)
        sync_event_participants(src, dst_a, args.dry_run)
        print('\n  post-sync counts:')
        for t, cs, cd, d in compare_report(src, dst_a):
            print(f'  {t:<22} prod={cs:>5} appdev={cd:>5} delta={cd-cs:+d}')
        dst_a.close()

    src.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
