#!/usr/bin/env python3
"""
Migración DB membresía-relatic → NodeOne.
Uso: MEMBRESIA_SOURCE_DB=/ruta/a/membresia.db python3 migrate_membresia_to_nodeone.py [--dry-run]
O:   python3 migrate_membresia_to_nodeone.py /ruta/a/membresia.db [--dry-run]
"""
import os
import sys
import sqlite3
import argparse

# Destino NodeOne
BASEDIR = os.path.abspath(os.path.dirname(__file__))
NODEONE_DB = os.path.join(os.path.dirname(BASEDIR), 'instance', 'nodeone.db')


def get_source_path():
    if len(sys.argv) >= 2 and not sys.argv[1].startswith('--'):
        return sys.argv[1]
    return os.environ.get('MEMBRESIA_SOURCE_DB', '')


def source_tables(conn):
    cur = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    )
    return [r[0] for r in cur.fetchall()]


def source_columns(conn, table):
    cur = conn.execute(f"PRAGMA table_info({table})")
    return [r[1] for r in cur.fetchall()]


def dest_columns(conn, table):
    cur = conn.execute(f"PRAGMA table_info({table})")
    return [r[1] for r in cur.fetchall()]


def row_to_dict(cursor, row):
    cols = [d[0] for d in cursor.description]
    return dict(zip(cols, row))


def migrate(dry_run=True, source_db=None, only_services=False, only_benefits=False):
    source_db = source_db or get_source_path()
    if not source_db or not os.path.isfile(source_db):
        print("Origen no encontrado. Uso: MEMBRESIA_SOURCE_DB=/ruta/membresia.db python3 migrate_membresia_to_nodeone.py")
        print("  o: python3 migrate_membresia_to_nodeone.py /ruta/membresia.db [--dry-run]")
        return 1
    if not os.path.isfile(NODEONE_DB):
        print("Destino NodeOne no encontrado:", NODEONE_DB)
        return 1

    src = sqlite3.connect(source_db)
    src.row_factory = sqlite3.Row
    dst = sqlite3.connect(NODEONE_DB)
    dst.row_factory = sqlite3.Row

    src_tables = source_tables(src)
    print("Tablas origen:", src_tables)

    user_id_map = {}
    payment_id_map = {}
    event_id_map = {}
    membership_plan_id_map = {}
    category_id_map = {}
    service_id_map = {}

    def run(description, fn):
        print("\n---", description)
        if dry_run:
            fn(dry=True)
            return
        fn(dry=False)

    # 1) membership_plan (si existe en origen)
    def do_plans(dry):
        if 'membership_plan' not in src_tables:
            print("  (no existe membership_plan en origen)")
            return
        cols_src = source_columns(src, 'membership_plan')
        cols_dst = dest_columns(dst, 'membership_plan')
        common = [c for c in cols_src if c in cols_dst]
        cur = src.execute("SELECT * FROM membership_plan")
        rows = cur.fetchall()
        for r in rows:
            row = row_to_dict(cur, r)
            existing = dst.execute(
                "SELECT id FROM membership_plan WHERE slug = ?", (row.get('slug') or row.get('name', ''),)
            ).fetchone()
            if existing:
                membership_plan_id_map[row['id']] = existing[0]
                continue
            vals = [row.get(c) for c in common]
            place = ','.join(['?' for _ in common])
            cols_str = ','.join(common)
            if not dry:
                dst.execute(f"INSERT INTO membership_plan ({cols_str}) VALUES ({place})", vals)
                membership_plan_id_map[row['id']] = dst.execute("SELECT last_insert_rowid()").fetchone()[0]
        if not dry:
            dst.commit()
        print("  Filas membership_plan:", len(rows))

    if not only_services and not only_benefits:
        run("membership_plan", do_plans)

    # 2) user
    user_table = 'user' if 'user' in src_tables else 'users' if 'users' in src_tables else None
    if not user_table:
        print("No se encontró tabla user/users en origen.")
        src.close()
        dst.close()
        return 1

    def do_users(dry):
        cols_src = source_columns(src, user_table)
        cols_dst = dest_columns(dst, 'user')
        common = [c for c in cols_src if c in cols_dst and c != 'id']
        cur = src.execute(f"SELECT * FROM {user_table}")
        rows = cur.fetchall()
        for r in rows:
            row = row_to_dict(cur, r)
            existing = dst.execute("SELECT id FROM user WHERE email = ?", (row.get('email', ''),)).fetchone()
            if existing:
                user_id_map[row['id']] = existing[0]
                continue
            vals = [row.get(c) for c in common]
            place = ','.join(['?' for _ in common])
            cols_str = ','.join(common)
            if not dry:
                dst.execute(f"INSERT INTO user ({cols_str}) VALUES ({place})", vals)
                user_id_map[row['id']] = dst.execute("SELECT last_insert_rowid()").fetchone()[0]
        if not dry:
            dst.commit()
        print("  Filas user:", len(rows), "-> insertados/mapeados:", len(user_id_map))

    if not only_services and not only_benefits:
        run("user", do_users)

    # 3) membership
    def do_membership(dry):
        if 'membership' not in src_tables:
            print("  (no existe membership en origen)")
            return
        cols_src = source_columns(src, 'membership')
        cols_dst = dest_columns(dst, 'membership')
        common = [c for c in cols_src if c in cols_dst and c != 'id']
        if 'user_id' not in common:
            common.append('user_id')
        cur = src.execute("SELECT * FROM membership")
        rows = cur.fetchall()
        n = 0
        for r in rows:
            row = row_to_dict(cur, r)
            uid_old = row.get('user_id')
            if uid_old not in user_id_map:
                continue
            row['user_id'] = user_id_map[uid_old]
            vals = [row.get(c) for c in common if c in row]
            cols_use = [c for c in common if c in row]
            if not cols_use:
                continue
            place = ','.join(['?' for _ in cols_use])
            cols_str = ','.join(cols_use)
            if not dry:
                dst.execute(f"INSERT INTO membership ({cols_str}) VALUES ({place})", vals)
                n += 1
        if not dry:
            dst.commit()
        print("  Filas membership:", len(rows), "-> insertadas:", n)

    if not only_services and not only_benefits:
        run("membership", do_membership)

    # 4) payment
    def do_payment(dry):
        if 'payment' not in src_tables:
            print("  (no existe payment en origen)")
            return
        cols_src = source_columns(src, 'payment')
        cols_dst = dest_columns(dst, 'payment')
        common = [c for c in cols_src if c in cols_dst and c != 'id']
        cur = src.execute("SELECT * FROM payment")
        rows = cur.fetchall()
        n = 0
        for r in rows:
            row = row_to_dict(cur, r)
            uid_old = row.get('user_id')
            if uid_old not in user_id_map:
                continue
            row['user_id'] = user_id_map[uid_old]
            vals = [row.get(c) for c in common if c in row]
            cols_use = [c for c in common if c in row]
            if not cols_use:
                continue
            place = ','.join(['?' for _ in cols_use])
            cols_str = ','.join(cols_use)
            if not dry:
                dst.execute(f"INSERT INTO payment ({cols_str}) VALUES ({place})", vals)
                payment_id_map[row['id']] = dst.execute("SELECT last_insert_rowid()").fetchone()[0]
                n += 1
        if not dry:
            dst.commit()
        print("  Filas payment:", len(rows), "-> insertadas:", n)

    if not only_services and not only_benefits:
        run("payment", do_payment)

    # 5) subscription
    def do_subscription(dry):
        if 'subscription' not in src_tables:
            print("  (no existe subscription en origen)")
            return
        cols_src = source_columns(src, 'subscription')
        cols_dst = dest_columns(dst, 'subscription')
        common = [c for c in cols_src if c in cols_dst and c != 'id']
        cur = src.execute("SELECT * FROM subscription")
        rows = cur.fetchall()
        n = 0
        for r in rows:
            row = row_to_dict(cur, r)
            uid_old = row.get('user_id')
            pid_old = row.get('payment_id')
            if uid_old not in user_id_map:
                continue
            row['user_id'] = user_id_map[uid_old]
            if pid_old is not None and pid_old in payment_id_map:
                row['payment_id'] = payment_id_map[pid_old]
            vals = [row.get(c) for c in common if c in row]
            cols_use = [c for c in common if c in row]
            if not cols_use:
                continue
            place = ','.join(['?' for _ in cols_use])
            cols_str = ','.join(cols_use)
            if not dry:
                dst.execute(f"INSERT INTO subscription ({cols_str}) VALUES ({place})", vals)
                n += 1
        if not dry:
            dst.commit()
        print("  Filas subscription:", len(rows), "-> insertadas:", n)

    if not only_services and not only_benefits:
        run("subscription", do_subscription)

    # 6) benefit
    def do_benefit(dry):
        if 'benefit' not in src_tables:
            print("  (no existe benefit en origen)")
            return
        cols_src = source_columns(src, 'benefit')
        cols_dst = dest_columns(dst, 'benefit')
        common = [c for c in cols_src if c in cols_dst and c != 'id']
        cur = src.execute("SELECT * FROM benefit")
        rows = cur.fetchall()
        n = 0
        for r in rows:
            row = row_to_dict(cur, r)
            if not dry:
                existing = dst.execute(
                    "SELECT id FROM benefit WHERE name = ? AND membership_type = ?",
                    (row.get('name') or '', row.get('membership_type') or ''),
                ).fetchone()
                if existing:
                    continue
            vals = [row.get(c) for c in common]
            place = ','.join(['?' for _ in common])
            cols_str = ','.join(common)
            if not dry:
                dst.execute(f"INSERT INTO benefit ({cols_str}) VALUES ({place})", vals)
                n += 1
        if not dry:
            dst.commit()
        print("  Filas benefit:", len(rows), "-> insertadas:", n)

    if only_benefits:
        run("benefit", do_benefit)
    elif not only_services:
        run("benefit", do_benefit)

    # 6b) service_category
    def do_service_category(dry):
        if 'service_category' not in src_tables:
            print("  (no existe service_category en origen)")
            return
        try:
            cols_dst = dest_columns(dst, 'service_category')
        except Exception:
            print("  (tabla service_category no existe en destino)")
            return
        cols_src = source_columns(src, 'service_category')
        common = [c for c in cols_src if c in cols_dst and c != 'id']
        cur = src.execute("SELECT * FROM service_category")
        rows = cur.fetchall()
        for r in rows:
            row = row_to_dict(cur, r)
            existing = dst.execute(
                "SELECT id FROM service_category WHERE name = ?",
                (row.get('name') or '',),
            ).fetchone()
            if existing:
                category_id_map[row['id']] = existing[0]
                continue
            vals = [row.get(c) for c in common]
            place = ','.join(['?' for _ in common])
            cols_str = ','.join(common)
            if not dry:
                dst.execute(f"INSERT INTO service_category ({cols_str}) VALUES ({place})", vals)
                category_id_map[row['id']] = dst.execute("SELECT last_insert_rowid()").fetchone()[0]
        if not dry:
            dst.commit()
        print("  Filas service_category:", len(rows))

    if not only_benefits:
        run("service_category", do_service_category)

    # 6c) service
    def do_service(dry):
        if 'service' not in src_tables:
            print("  (no existe service en origen)")
            return
        try:
            cols_dst = dest_columns(dst, 'service')
        except Exception:
            print("  (tabla service no existe en destino)")
            return
        cols_src = source_columns(src, 'service')
        common = [c for c in cols_src if c in cols_dst and c != 'id']
        cur = src.execute("SELECT * FROM service")
        rows = cur.fetchall()
        n = 0
        for r in rows:
            row = row_to_dict(cur, r)
            cid = row.get('category_id')
            if cid is not None and cid in category_id_map:
                row['category_id'] = category_id_map[cid]
            elif cid is not None:
                row['category_id'] = None
            vals = [row.get(c) for c in common if c in row]
            cols_use = [c for c in common if c in row]
            if not cols_use:
                continue
            place = ','.join(['?' for _ in cols_use])
            cols_str = ','.join(cols_use)
            if not dry:
                dst.execute(f"INSERT INTO service ({cols_str}) VALUES ({place})", vals)
                service_id_map[row['id']] = dst.execute("SELECT last_insert_rowid()").fetchone()[0]
                n += 1
        if not dry:
            dst.commit()
        print("  Filas service:", len(rows), "-> insertadas:", n)

    if not only_benefits:
        run("service", do_service)

    # 6d) service_pricing_rule
    def do_service_pricing_rule(dry):
        if 'service_pricing_rule' not in src_tables:
            print("  (no existe service_pricing_rule en origen)")
            return
        try:
            cols_dst = dest_columns(dst, 'service_pricing_rule')
        except Exception:
            print("  (tabla service_pricing_rule no existe en destino)")
            return
        cols_src = source_columns(src, 'service_pricing_rule')
        common = [c for c in cols_src if c in cols_dst and c != 'id']
        cur = src.execute("SELECT * FROM service_pricing_rule")
        rows = cur.fetchall()
        n = 0
        for r in rows:
            row = row_to_dict(cur, r)
            sid = row.get('service_id')
            if sid not in service_id_map:
                continue
            row['service_id'] = service_id_map[sid]
            vals = [row.get(c) for c in common if c in row]
            cols_use = [c for c in common if c in row]
            place = ','.join(['?' for _ in cols_use])
            cols_str = ','.join(cols_use)
            if not dry:
                try:
                    dst.execute(f"INSERT INTO service_pricing_rule ({cols_str}) VALUES ({place})", vals)
                    n += 1
                except sqlite3.IntegrityError:
                    pass
        if not dry:
            dst.commit()
        print("  Filas service_pricing_rule:", len(rows), "-> insertadas:", n)

    if not only_benefits:
        run("service_pricing_rule", do_service_pricing_rule)

    # 7) event
    ev_table = 'event' if 'event' in src_tables else 'events' if 'events' in src_tables else None
    if ev_table:

        def do_events(dry):
            cols_src = source_columns(src, ev_table)
            cols_dst = dest_columns(dst, 'event')
            common = [c for c in cols_src if c in cols_dst and c != 'id']
            fk_user_cols = [c for c in ('created_by', 'moderator_id', 'administrator_id', 'speaker_id') if c in common]
            cur = src.execute(f"SELECT * FROM {ev_table}")
            rows = cur.fetchall()
            n = 0
            for r in rows:
                row = row_to_dict(cur, r)
                for col in fk_user_cols:
                    if row.get(col) and row[col] not in user_id_map:
                        row[col] = None
                    elif row.get(col):
                        row[col] = user_id_map[row[col]]
                vals = [row.get(c) for c in common]
                place = ','.join(['?' for _ in common])
                cols_str = ','.join(common)
                if not dry:
                    dst.execute(f"INSERT INTO event ({cols_str}) VALUES ({place})", vals)
                    event_id_map[row['id']] = dst.execute("SELECT last_insert_rowid()").fetchone()[0]
                    n += 1
            if not dry:
                dst.commit()
            print("  Filas event:", len(rows), "-> insertadas:", n)

        if not only_services and not only_benefits:
            run("event", do_events)

    # 8) event_registration
    reg_table = None
    for t in ('event_registration', 'event_registrations', 'eventregistration'):
        if t in src_tables:
            reg_table = t
            break
    if reg_table and event_id_map:

        def do_registrations(dry):
            cols_src = source_columns(src, reg_table)
            cols_dst = dest_columns(dst, 'event_registration')
            common = [c for c in cols_src if c in cols_dst and c != 'id']
            cur = src.execute(f"SELECT * FROM {reg_table}")
            rows = cur.fetchall()
            n = 0
            for r in rows:
                row = row_to_dict(cur, r)
                eid = row.get('event_id')
                uid = row.get('user_id')
                if eid not in event_id_map or uid not in user_id_map:
                    continue
                row['event_id'] = event_id_map[eid]
                row['user_id'] = user_id_map[uid]
                vals = [row.get(c) for c in common if c in row]
                cols_use = [c for c in common if c in row]
                place = ','.join(['?' for _ in cols_use])
                cols_str = ','.join(cols_use)
                if not dry:
                    try:
                        dst.execute(f"INSERT INTO event_registration ({cols_str}) VALUES ({place})", vals)
                        n += 1
                    except sqlite3.IntegrityError:
                        pass
            if not dry:
                dst.commit()
            print("  Filas event_registration:", len(rows), "-> insertadas:", n)

        if not only_services and not only_benefits:
            run("event_registration", do_registrations)

    src.close()
    dst.close()
    print("\nMigración finalizada." + (" (dry-run, sin cambios)" if dry_run else ""))
    return 0


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('source_db', nargs='?', default=None, help='Ruta a la DB de membresía-relatic')
    ap.add_argument('--dry-run', action='store_true', help='Solo mostrar qué se haría')
    ap.add_argument('--only', choices=['services', 'benefits'], help='Migrar solo: services o benefits')
    args = ap.parse_args()
    sys.exit(migrate(dry_run=args.dry_run, source_db=args.source_db or os.environ.get('MEMBRESIA_SOURCE_DB'), only_services=(args.only == 'services'), only_benefits=(args.only == 'benefits')))
