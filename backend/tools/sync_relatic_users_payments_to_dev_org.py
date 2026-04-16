#!/usr/bin/env python3
"""
Copia usuarios (y pagos + suscripciones asociados) desde la BD Relatic hacia DEV
para un organization_id destino, mapeando por email (usuarios nuevos o vínculo user_organization).

Uso (desde backend/):
  ../venv/bin/python3 tools/sync_relatic_users_payments_to_dev_org.py --dry-run
  ../venv/bin/python3 tools/sync_relatic_users_payments_to_dev_org.py

Por defecto: origen Relatic org 1 → destino DEV org 3 (Relatic Panama Dev).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text


def _parse_dt(val):
    if val is None:
        return None
    if isinstance(val, datetime):
        return val
    s = str(val).replace('Z', '+00:00')
    for fmt in ('%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d %H:%M:%S'):
        try:
            return datetime.strptime(s[:26], fmt)
        except ValueError:
            continue
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--source-dotenv', type=Path, default=Path('/opt/easynodeone/relatic/.env'))
    ap.add_argument('--target-dotenv', type=Path, default=Path('/opt/easynodeone/dev/.env'))
    ap.add_argument('--source-org', type=int, default=1)
    ap.add_argument('--target-org', type=int, default=3)
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()

    backend = Path(__file__).resolve().parent.parent
    os.chdir(backend)
    if str(backend) not in sys.path:
        sys.path.insert(0, str(backend))

    load_dotenv(args.target_dotenv, override=True)
    tgt_url = (os.environ.get('SQLALCHEMY_DATABASE_URI') or os.environ.get('DATABASE_URL') or '').strip()
    if tgt_url.startswith('postgres://'):
        tgt_url = tgt_url.replace('postgres://', 'postgresql://', 1)
    if not tgt_url:
        print('Sin DATABASE_URL en destino', file=sys.stderr)
        return 1

    load_dotenv(args.source_dotenv, override=True)
    src_url = (os.environ.get('SQLALCHEMY_DATABASE_URI') or os.environ.get('DATABASE_URL') or '').strip()
    if src_url.startswith('postgres://'):
        src_url = src_url.replace('postgres://', 'postgresql://', 1)
    if not src_url:
        print('Sin DATABASE_URL en origen', file=sys.stderr)
        return 1

    # Flask/app debe seguir usando solo la BD destino (DEV)
    os.environ['DATABASE_URL'] = tgt_url
    if os.environ.get('SQLALCHEMY_DATABASE_URI'):
        os.environ['SQLALCHEMY_DATABASE_URI'] = tgt_url

    src = create_engine(src_url)
    src_org, tgt_org = int(args.source_org), int(args.target_org)

    with src.connect() as c:
        urows = list(
            c.execute(
                text(
                    """
                    SELECT id, email, password_hash, first_name, last_name, phone, country,
                           cedula_or_passport, tags, user_group, created_at, is_active, is_admin,
                           is_advisor, email_verified, profile_picture, must_change_password,
                           email_marketing_status, last_selected_organization_id
                    FROM "user"
                    WHERE organization_id = :oid
                    ORDER BY id
                    """
                ),
                {'oid': src_org},
            ).mappings()
        )

    print(f'Origen org {src_org}: {len(urows)} usuarios')
    if args.dry_run:
        with src.connect() as c:
            np = c.execute(
                text('SELECT COUNT(*) FROM payment WHERE user_id IN (SELECT id FROM "user" WHERE organization_id = :oid)'),
                {'oid': src_org},
            ).scalar()
            ns = c.execute(
                text('SELECT COUNT(*) FROM subscription WHERE user_id IN (SELECT id FROM "user" WHERE organization_id = :oid)'),
                {'oid': src_org},
            ).scalar()
        print(f'Dry-run: pagos afectados ~{np}, suscripciones ~{ns}')
        return 0

    import app as M
    from models.saas import SaasOrganization
    from models.users import User
    from models.payments import Payment, Subscription
    from nodeone.services.user_organization import ensure_membership
    from sqlalchemy import func as sqla_func

    uid_map: dict[int, int] = {}
    merged_relatic_ids: set[int] = set()

    with M.app.app_context():
        o = M.db.session.get(SaasOrganization, tgt_org)
        if o is None:
            print(f'Destino: no existe saas_organization id={tgt_org}', file=sys.stderr)
            return 1

        for r in urows:
            em = (r['email'] or '').strip().lower()
            if not em:
                continue
            rid = int(r['id'])
            existing = User.query.filter(sqla_func.lower(User.email) == em).first()
            if existing:
                ensure_membership(int(existing.id), tgt_org, role='user')
                uid_map[rid] = int(existing.id)
                merged_relatic_ids.add(rid)
                continue
            nu = User(
                email=em[:120],
                password_hash=r['password_hash'] or '',
                first_name=(r['first_name'] or '')[:50],
                last_name=(r['last_name'] or '')[:50],
                phone=(r['phone'] or '')[:20] if r['phone'] else None,
                country=(r['country'] or '')[:100] if r['country'] else None,
                cedula_or_passport=(r['cedula_or_passport'] or '')[:20] if r['cedula_or_passport'] else None,
                tags=(r['tags'] or '')[:500] if r['tags'] else None,
                user_group=(r['user_group'] or '')[:100] if r['user_group'] else None,
                created_at=_parse_dt(r['created_at']) or datetime.utcnow(),
                is_active=bool(r['is_active']) if r['is_active'] is not None else True,
                is_admin=bool(r['is_admin']) if r['is_admin'] is not None else False,
                is_advisor=bool(r['is_advisor']) if r['is_advisor'] is not None else False,
                email_verified=bool(r['email_verified']) if r['email_verified'] is not None else False,
                profile_picture=(r['profile_picture'] or '')[:500] if r['profile_picture'] else None,
                must_change_password=bool(r['must_change_password']) if r['must_change_password'] is not None else False,
                email_marketing_status=(r['email_marketing_status'] or 'subscribed')[:20],
                organization_id=tgt_org,
                last_selected_organization_id=tgt_org,
            )
            M.db.session.add(nu)
            M.db.session.flush()
            uid_map[rid] = int(nu.id)

        M.db.session.commit()
        print(
            f'Usuarios enlazados/creados: {len(uid_map)} (fusionados por email ya existente en DEV: {len(merged_relatic_ids)})'
        )

        pay_map: dict[int, int] = {}
        with src.connect() as c:
            pids = [k for k in uid_map.keys() if k not in merged_relatic_ids]
            if not pids:
                print('Sin usuarios nuevos para copiar pagos/suscripciones.')
                return 0
            placeholders = ','.join(str(int(x)) for x in pids)
            prow = c.execute(
                text(f'SELECT * FROM payment WHERE user_id IN ({placeholders}) ORDER BY id')
            ).mappings().all()

        for d in prow:
            ouid = int(d['user_id'])
            nuid = uid_map.get(ouid)
            if not nuid or ouid in merged_relatic_ids:
                continue
            meta = d.get('payment_metadata')
            if meta is not None and not isinstance(meta, str):
                meta = json.dumps(meta)
            p = Payment(
                user_id=nuid,
                payment_method=(d.get('payment_method') or 'unknown')[:50],
                payment_reference=(d.get('payment_reference') or '')[:200] if d.get('payment_reference') else None,
                amount=int(d.get('amount') or 0),
                currency=(d.get('currency') or 'usd')[:3],
                status=(d.get('status') or 'pending')[:20],
                membership_type=(d.get('membership_type') or 'basic')[:50],
                payment_url=(d.get('payment_url') or '')[:500] if d.get('payment_url') else None,
                receipt_url=(d.get('receipt_url') or '')[:500] if d.get('receipt_url') else None,
                receipt_filename=(d.get('receipt_filename') or '')[:255] if d.get('receipt_filename') else None,
                ocr_data=d.get('ocr_data'),
                ocr_status=(d.get('ocr_status') or 'pending')[:20],
                ocr_verified_at=_parse_dt(d.get('ocr_verified_at')),
                admin_notes=d.get('admin_notes'),
                payment_metadata=meta,
                created_at=_parse_dt(d.get('created_at')) or datetime.utcnow(),
                updated_at=_parse_dt(d.get('updated_at')) or datetime.utcnow(),
                paid_at=_parse_dt(d.get('paid_at')),
            )
            M.db.session.add(p)
            M.db.session.flush()
            pay_map[int(d['id'])] = int(p.id)

        M.db.session.commit()
        print(f'Pagos insertados: {len(pay_map)}')

        with src.connect() as c:
            srows = c.execute(
                text(f'SELECT * FROM subscription WHERE user_id IN ({placeholders}) ORDER BY id')
            ).mappings().all()  # mismo filtro: solo usuarios nuevos en DEV

        n_sub = 0
        for d in srows:
            ouid = int(d['user_id'])
            opid = int(d['payment_id'])
            if ouid in merged_relatic_ids:
                continue
            nuid = uid_map.get(ouid)
            npid = pay_map.get(opid)
            if not nuid or not npid:
                continue
            araw = d.get('auto_renew')
            if araw is None:
                auto_renew = True
            elif isinstance(araw, (int, float)):
                auto_renew = bool(int(araw))
            else:
                auto_renew = bool(araw)
            s = Subscription(
                user_id=nuid,
                payment_id=npid,
                membership_type=(d.get('membership_type') or 'basic')[:50],
                status=(d.get('status') or 'active')[:20],
                start_date=_parse_dt(d.get('start_date')) or datetime.utcnow(),
                end_date=_parse_dt(d.get('end_date')) or datetime.utcnow(),
                auto_renew=auto_renew,
                created_at=_parse_dt(d.get('created_at')) or datetime.utcnow(),
                updated_at=_parse_dt(d.get('updated_at')) or datetime.utcnow(),
            )
            M.db.session.add(s)
            n_sub += 1

        M.db.session.commit()
        print(f'Suscripciones insertadas: {n_sub}')

        def _sync_seq(conn, table_sql: str):
            seq = conn.execute(
                text('SELECT pg_get_serial_sequence(:t, :pk)'),
                {'t': table_sql, 'pk': 'id'},
            ).scalar()
            if not seq:
                return
            mx = conn.execute(text(f'SELECT COALESCE(MAX(id), 1) FROM {table_sql}')).scalar()
            conn.execute(text('SELECT setval(:s, :m, true)'), {'s': seq, 'm': int(mx)})

        with M.db.engine.begin() as conn:
            _sync_seq(conn, 'payment')
            _sync_seq(conn, 'subscription')
            _sync_seq(conn, '"user"')

    print('OK')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
