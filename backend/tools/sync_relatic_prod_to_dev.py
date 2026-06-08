#!/usr/bin/env python3
"""Sincroniza Relatic aislada → appdev: usuarios, miembros, eventos, pagos y carritos."""
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
    'payment',
    'cart',
    'cart_item',
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


def table_columns(conn, table: str) -> list[str]:
    qtable = '"user"' if table == 'user' else table
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT column_name FROM information_schema.columns
            WHERE table_schema='public' AND table_name=%s
            ORDER BY ordinal_position
            """,
            (table,),
        )
        return [r[0] for r in cur.fetchall()]


def common_table_columns(src, dst, table: str) -> list[str]:
    sc = set(table_columns(src, table))
    dc = set(table_columns(dst, table))
    return [c for c in table_columns(src, table) if c in dc]


def build_user_id_map(src, dst) -> dict[int, int]:
    """Mapa id usuario Relatic → id usuario Dev por email."""
    with src.cursor() as sc:
        sc.execute('SELECT id, lower(trim(email)) FROM "user" WHERE email IS NOT NULL')
        src_rows = sc.fetchall()
    with dst.cursor() as dc:
        dc.execute('SELECT id, lower(trim(email)) FROM "user" WHERE email IS NOT NULL')
        dst_by_email = {em: int(uid) for uid, em in dc.fetchall() if em}
    out: dict[int, int] = {}
    for sid, em in src_rows:
        if em and em in dst_by_email:
            out[int(sid)] = dst_by_email[em]
    return out


def sync_events(src, dst, uid_map: dict[int, int], dry_run: bool) -> None:
    with src.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as sc:
        sc.execute('SELECT * FROM event ORDER BY id')
        rows = sc.fetchall()
    if not rows:
        print('  event: nothing in source')
        return
    cols = common_table_columns(src, dst, 'event')
    if 'id' not in cols:
        cols = ['id'] + [c for c in cols if c != 'id']
    user_fk_cols = [
        c
        for c in ('administrator_id', 'moderator_id', 'speaker_id', 'created_by', 'updated_by')
        if c in cols
    ]
    upd = ', '.join(f'{c}=EXCLUDED.{c}' for c in cols if c != 'id')
    col_list = ', '.join(cols)
    ins = 0
    with dst.cursor() as dc:
        for row in rows:
            if dry_run:
                ins += 1
                continue
            payload = dict(row)
            for fk in user_fk_cols:
                val = payload.get(fk)
                if val is None:
                    continue
                mapped = uid_map.get(int(val))
                if mapped:
                    payload[fk] = mapped
                else:
                    payload[fk] = None
            placeholders = ', '.join(['%s'] * len(cols))
            dc.execute(
                f"""
                INSERT INTO event ({col_list}) VALUES ({placeholders})
                ON CONFLICT (id) DO UPDATE SET {upd}
                """,
                [payload[c] for c in cols],
            )
            ins += 1
    if not dry_run:
        dst.commit()
    print(f'  event: upserted={ins}')


def sync_event_registrations(src, dst, uid_map: dict[int, int], dry_run: bool) -> None:
    with src.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as sc:
        sc.execute('SELECT * FROM event_registration ORDER BY id')
        rows = sc.fetchall()
    cols = [c for c in common_table_columns(src, dst, 'event_registration') if c != 'id']
    col_list = ', '.join(cols)
    ins = skip = 0
    with dst.cursor() as dc:
        for r in rows:
            src_uid = int(r.get('user_id') or 0)
            dst_uid = uid_map.get(src_uid)
            if not dst_uid:
                skip += 1
                continue
            dc.execute(
                'SELECT 1 FROM event_registration WHERE event_id=%s AND user_id=%s',
                (r['event_id'], dst_uid),
            )
            if dc.fetchone():
                skip += 1
                continue
            if dry_run:
                ins += 1
                continue
            row = dict(r)
            row['user_id'] = dst_uid
            placeholders = ', '.join(['%s'] * len(cols))
            dc.execute(
                f'INSERT INTO event_registration ({col_list}) VALUES ({placeholders})',
                [row[c] for c in cols],
            )
            ins += 1
    if not dry_run:
        dst.commit()
    print(f'  event_registration: inserted={ins} skipped={skip}')


def sync_payments(
    src, dst, uid_map: dict[int, int], target_org: int, dry_run: bool
) -> dict[int, int]:
    with src.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as sc:
        sc.execute('SELECT * FROM payment ORDER BY id')
        rows = sc.fetchall()
    cols = [c for c in common_table_columns(src, dst, 'payment') if c != 'id']
    col_list = ', '.join(cols)
    pay_map: dict[int, int] = {}
    ins = skip = 0
    with dst.cursor() as dc:
        for r in rows:
            src_uid = int(r.get('user_id') or 0)
            dst_uid = uid_map.get(src_uid)
            if not dst_uid:
                skip += 1
                continue
            ref = (r.get('payment_reference') or '')[:200]
            amt = int(r.get('amount') or 0)
            created = r.get('created_at')
            dc.execute(
                """
                SELECT id FROM payment
                WHERE user_id=%s AND coalesce(payment_reference,'')=%s
                  AND amount=%s AND created_at=%s
                LIMIT 1
                """,
                (dst_uid, ref, amt, created),
            )
            existing = dc.fetchone()
            if existing:
                pay_map[int(r['id'])] = int(existing[0])
                skip += 1
                continue
            if dry_run:
                ins += 1
                pay_map[int(r['id'])] = -1
                continue
            row = dict(r)
            row['user_id'] = dst_uid
            row['organization_id'] = target_org
            placeholders = ', '.join(['%s'] * len(cols))
            dc.execute(
                f'INSERT INTO payment ({col_list}) VALUES ({placeholders}) RETURNING id',
                [row[c] for c in cols],
            )
            new_id = int(dc.fetchone()[0])
            pay_map[int(r['id'])] = new_id
            ins += 1
    if not dry_run:
        dst.commit()
    print(f'  payment: inserted={ins} skipped={skip}')
    return pay_map


def sync_subscriptions(src, dst, uid_map: dict[int, int], pay_map: dict[int, int], dry_run: bool) -> None:
    with src.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as sc:
        sc.execute('SELECT * FROM subscription ORDER BY id')
        rows = sc.fetchall()
    cols = [c for c in common_table_columns(src, dst, 'subscription') if c != 'id']
    col_list = ', '.join(cols)
    ins = skip = 0
    with dst.cursor() as dc:
        for r in rows:
            dst_uid = uid_map.get(int(r.get('user_id') or 0))
            dst_pid = pay_map.get(int(r.get('payment_id') or 0))
            if not dst_uid or not dst_pid or dst_pid < 0:
                skip += 1
                continue
            dc.execute(
                'SELECT 1 FROM subscription WHERE user_id=%s AND payment_id=%s',
                (dst_uid, dst_pid),
            )
            if dc.fetchone():
                skip += 1
                continue
            if dry_run:
                ins += 1
                continue
            row = dict(r)
            row['user_id'] = dst_uid
            row['payment_id'] = dst_pid
            placeholders = ', '.join(['%s'] * len(cols))
            dc.execute(
                f'INSERT INTO subscription ({col_list}) VALUES ({placeholders})',
                [row[c] for c in cols],
            )
            ins += 1
    if not dry_run:
        dst.commit()
    print(f'  subscription: inserted={ins} skipped={skip}')


def sync_carts(src, dst, uid_map: dict[int, int], dry_run: bool) -> dict[int, int]:
    """Mapa cart_id Relatic → cart_id Dev (por user_id)."""
    cart_map: dict[int, int] = {}
    with src.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as sc:
        sc.execute('SELECT * FROM cart ORDER BY id')
        carts = sc.fetchall()
    ins = skip = 0
    with dst.cursor() as dc:
        for c in carts:
            src_uid = int(c.get('user_id') or 0)
            dst_uid = uid_map.get(src_uid)
            if not dst_uid:
                skip += 1
                continue
            dc.execute('SELECT id FROM cart WHERE user_id=%s ORDER BY id DESC LIMIT 1', (dst_uid,))
            row = dc.fetchone()
            if row:
                cart_map[int(c['id'])] = int(row[0])
                skip += 1
                continue
            if dry_run:
                cart_map[int(c['id'])] = -1
                ins += 1
                continue
            dc.execute(
                """
                INSERT INTO cart (user_id, discount_code_id, created_at, updated_at)
                VALUES (%s, %s, %s, %s) RETURNING id
                """,
                (dst_uid, c.get('discount_code_id'), c.get('created_at'), c.get('updated_at')),
            )
            cart_map[int(c['id'])] = int(dc.fetchone()[0])
            ins += 1
    if not dry_run:
        dst.commit()
    print(f'  cart: created={ins} reused={skip}')

    with src.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as sc:
        sc.execute('SELECT * FROM cart_item ORDER BY id')
        items = sc.fetchall()
    if not items:
        return cart_map
    cols = [c for c in common_table_columns(src, dst, 'cart_item') if c != 'id']
    col_list = ', '.join(cols)
    iins = iskip = 0
    with dst.cursor() as dc:
        for it in items:
            dst_cart = cart_map.get(int(it.get('cart_id') or 0))
            if not dst_cart or dst_cart < 0:
                iskip += 1
                continue
            dc.execute(
                """
                SELECT 1 FROM cart_item
                WHERE cart_id=%s AND product_type=%s AND product_id=%s
                  AND coalesce(item_metadata,'')=%s
                """,
                (
                    dst_cart,
                    it.get('product_type'),
                    it.get('product_id'),
                    it.get('item_metadata') or '',
                ),
            )
            if dc.fetchone():
                iskip += 1
                continue
            if dry_run:
                iins += 1
                continue
            row = dict(it)
            row['cart_id'] = dst_cart
            placeholders = ', '.join(['%s'] * len(cols))
            dc.execute(
                f'INSERT INTO cart_item ({col_list}) VALUES ({placeholders})',
                [row[c] for c in cols],
            )
            iins += 1
    if not dry_run:
        dst.commit()
    print(f'  cart_item: inserted={iins} skipped={iskip}')
    return cart_map


def sync_event_participants(src, dst, uid_map: dict[int, int] | None, dry_run: bool):
    with src.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as sc:
        sc.execute('SELECT * FROM event_participant ORDER BY id')
        rows = sc.fetchall()
    if not rows:
        print('  event_participant: nothing in source')
        return
    cols = [k for k in rows[0].keys() if k != 'id']
    col_list = ', '.join(cols)
    ins = skip = upd = 0
    uid_map = uid_map or {}
    with dst.cursor() as dc:
        for p in rows:
            em = (p.get('email') or '').strip().lower()
            mapped_uid = uid_map.get(int(p.get('user_id') or 0)) if p.get('user_id') else None
            dc.execute(
                'SELECT id, user_id FROM event_participant WHERE event_id=%s AND lower(trim(email))=%s',
                (p['event_id'], em),
            )
            existing = dc.fetchone()
            if em and existing:
                if mapped_uid and not dry_run and int(existing[1] or 0) != mapped_uid:
                    dc.execute(
                        'UPDATE event_participant SET user_id=%s WHERE id=%s',
                        (mapped_uid, existing[0]),
                    )
                    upd += 1
                else:
                    skip += 1
                continue
            if dry_run:
                ins += 1
                continue
            row = dict(p)
            if mapped_uid:
                row['user_id'] = mapped_uid
            placeholders = ', '.join(['%s'] * len(cols))
            dc.execute(
                f'INSERT INTO event_participant ({col_list}) VALUES ({placeholders})',
                [row[c] for c in cols],
            )
            ins += 1
    if not dry_run:
        dst.commit()
    print(f'  event_participant: inserted={ins} updated_user={upd} skipped={skip}')


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
    ap.add_argument('--target', choices=('panama', 'appdev', 'both'), default='appdev')
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
        sync_event_participants(src, dst_p, build_user_id_map(src, dst_p), args.dry_run)
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
        uid_map = build_user_id_map(src, dst_a)
        print(f'  user_id map relatic→dev: {len(uid_map)} emails vinculados')
        sync_events(src, dst_a, uid_map, args.dry_run)
        sync_event_participants(src, dst_a, uid_map, args.dry_run)
        sync_event_registrations(src, dst_a, uid_map, args.dry_run)
        pay_map = sync_payments(src, dst_a, uid_map, target_org=3, dry_run=args.dry_run)
        sync_subscriptions(src, dst_a, uid_map, pay_map, args.dry_run)
        sync_carts(src, dst_a, uid_map, args.dry_run)
        print('\n  post-sync counts:')
        for t, cs, cd, d in compare_report(src, dst_a):
            print(f'  {t:<22} prod={cs:>5} appdev={cd:>5} delta={cd-cs:+d}')
        dst_a.close()

    src.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
