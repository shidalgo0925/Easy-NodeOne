#!/usr/bin/env python3
"""
Importa agenda legacy desde SQLite: appointment_type, advisor, appointment_advisor,
appointment_slot, appointment (por organization_id en destino).

Requisitos: usuarios ya migrados (mapeo por email) y catálogo de servicios importado
(import_services_sqlite_to_org) para resolver service_id por nombre.

Uso (desde backend/):
  ../venv/bin/python3 tools/import_appointments_sqlite_to_org.py /ruta/backup.db <organization_id_pg>
"""
from __future__ import annotations

import os
import secrets
import sqlite3
import sys
from datetime import datetime

from dotenv import load_dotenv
from sqlalchemy import text


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


def _sync_sequence(conn, table: str, pk: str = 'id') -> None:
    seq = conn.execute(
        text('SELECT pg_get_serial_sequence(:tbl, :pk)'),
        {'tbl': table, 'pk': pk},
    ).scalar()
    if not seq:
        return
    mx = conn.execute(text(f'SELECT COALESCE(MAX("{pk}"), 1) FROM "{table}"')).scalar()
    conn.execute(text('SELECT setval(:seq, :mx, true)'), {'seq': seq, 'mx': int(mx)})


def main() -> int:
    if len(sys.argv) < 3:
        print(
            'Uso: python tools/import_appointments_sqlite_to_org.py <backup.db> <organization_id_pg>',
            file=sys.stderr,
        )
        return 1
    sqlite_path = os.path.abspath(sys.argv[1])
    target_org = int(sys.argv[2])
    if not os.path.isfile(sqlite_path):
        print(f'No existe: {sqlite_path}', file=sys.stderr)
        return 1

    backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    repo_root = os.path.abspath(os.path.join(backend_dir, '..'))
    sys.path.insert(0, backend_dir)
    os.chdir(backend_dir)
    load_dotenv(os.path.join(repo_root, '..', '.env'))

    import app as M
    from models.appointments import (
        Advisor,
        Appointment,
        AppointmentAdvisor,
        AppointmentSlot,
        AppointmentType,
    )
    from models.catalog import Service
    from models.saas import SaasOrganization
    from models.users import User
    from sqlalchemy import func as sqla_func

    con = sqlite3.connect(sqlite_path)
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    with M.app.app_context():
        org = M.db.session.get(SaasOrganization, target_org)
        if not org:
            print(f'No existe saas_organization id={target_org}', file=sys.stderr)
            return 1

        if (
            AppointmentType.query.filter_by(organization_id=target_org).count() > 0
            or Appointment.query.filter_by(organization_id=target_org).count() > 0
        ):
            print(
                f'Ya hay tipos de cita o citas en org {target_org}. Abortando para no duplicar.',
                file=sys.stderr,
            )
            return 1

        # Mapa sqlite user.id -> pg user.id (por email)
        cur.execute('SELECT id, email FROM user WHERE email IS NOT NULL AND trim(email) != ""')
        user_map: dict[int, int] = {}
        for r in cur.fetchall():
            sid = int(r['id'])
            em = (r['email'] or '').strip().lower()
            u = User.query.filter(sqla_func.lower(User.email) == em).first()
            if u:
                user_map[sid] = int(u.id)

        # Mapa sqlite service.id -> pg service.id (mismo nombre, misma org)
        cur.execute('SELECT id, name FROM service')
        svc_map: dict[int, int] = {}
        for r in cur.fetchall():
            oid, name = int(r['id']), (r['name'] or '').strip()
            s = Service.query.filter_by(organization_id=target_org, name=name).first()
            if s:
                svc_map[oid] = int(s.id)

        # 1) appointment_type
        type_map: dict[int, int] = {}
        cur.execute('SELECT * FROM appointment_type ORDER BY id')
        for row in cur.fetchall():
            at = AppointmentType(
                name=(row['name'] or '')[:200] or 'Tipo',
                display_name=(row['name'] or '')[:200],
                description=row['description'],
                service_category=(row['service_category'] or '')[:100] if row['service_category'] else None,
                duration_minutes=int(row['duration_minutes'] or 60),
                is_group_allowed=bool(row['is_group_allowed']) if row['is_group_allowed'] is not None else False,
                max_participants=int(row['max_participants'] or 1),
                base_price=float(row['base_price'] or 0),
                currency=(row['currency'] or 'USD')[:3],
                is_virtual=bool(row['is_virtual']) if row['is_virtual'] is not None else True,
                requires_confirmation=bool(row['requires_confirmation'])
                if row['requires_confirmation'] is not None
                else True,
                color_tag=(row['color_tag'] or '#0d6efd')[:20],
                icon=(row['icon'] or 'fa-calendar-check')[:50],
                display_order=int(row['display_order'] or 1),
                is_active=bool(row['is_active']) if row['is_active'] is not None else True,
                organization_id=target_org,
            )
            if row['created_at']:
                at.created_at = _parse_dt(row['created_at'])
            if row['updated_at']:
                at.updated_at = _parse_dt(row['updated_at'])
            M.db.session.add(at)
            M.db.session.flush()
            type_map[int(row['id'])] = at.id

        # 2) advisor (perfil por user_id)
        advisor_map: dict[int, int] = {}
        cur.execute('SELECT * FROM advisor ORDER BY id')
        for row in cur.fetchall():
            aid = int(row['id'])
            suid = int(row['user_id'])
            pg_uid = user_map.get(suid)
            if not pg_uid:
                print(f'  [skip advisor sqlite id={aid}] user sqlite {suid} sin match en PG', file=sys.stderr)
                continue
            existing = Advisor.query.filter_by(user_id=pg_uid).first()
            if existing:
                advisor_map[aid] = int(existing.id)
                continue
            adv = Advisor(
                user_id=pg_uid,
                headline=None,
                bio=None,
                specializations=None,
                meeting_url=None,
                photo_url=None,
                average_response_time=None,
                is_active=True,
            )
            if row['created_at']:
                adv.created_at = _parse_dt(row['created_at'])
            M.db.session.add(adv)
            M.db.session.flush()
            advisor_map[aid] = adv.id

        # 3) appointment_advisor
        n_aa = 0
        try:
            cur.execute('SELECT * FROM appointment_advisor ORDER BY id')
            for row in cur.fetchall():
                tid = type_map.get(int(row['appointment_type_id']))
                advid = advisor_map.get(int(row['advisor_id']))
                if not tid or not advid:
                    continue
                aa = AppointmentAdvisor(
                    appointment_type_id=tid,
                    advisor_id=advid,
                    priority=int(row['priority'] or 1),
                    is_active=bool(row['is_active']) if row['is_active'] is not None else True,
                )
                if row['created_at']:
                    aa.created_at = _parse_dt(row['created_at'])
                M.db.session.add(aa)
                n_aa += 1
        except sqlite3.OperationalError:
            pass

        # 4) appointment_slot
        slot_map: dict[int, int] = {}
        cur.execute('SELECT * FROM appointment_slot ORDER BY id')
        for row in cur.fetchall():
            tid = type_map.get(int(row['appointment_type_id']))
            advid = advisor_map.get(int(row['advisor_id']))
            if not tid or not advid:
                print(
                    f"  [skip slot id={row['id']}] type o advisor sin mapa",
                    file=sys.stderr,
                )
                continue
            cb = user_map.get(int(row['created_by'])) if row['created_by'] else None
            sl = AppointmentSlot(
                appointment_type_id=tid,
                advisor_id=advid,
                start_datetime=_parse_dt(row['start_datetime']),
                end_datetime=_parse_dt(row['end_datetime']),
                capacity=int(row['capacity'] or 1),
                reserved_seats=int(row['reserved_seats'] or 0),
                is_available=bool(row['is_available']) if row['is_available'] is not None else True,
                is_auto_generated=bool(row['is_auto_generated'])
                if row['is_auto_generated'] is not None
                else True,
                created_by=cb,
            )
            if row['created_at']:
                sl.created_at = _parse_dt(row['created_at'])
            if row['updated_at']:
                sl.updated_at = _parse_dt(row['updated_at'])
            M.db.session.add(sl)
            M.db.session.flush()
            slot_map[int(row['id'])] = sl.id

        # 5) appointment
        cur.execute('SELECT * FROM appointment ORDER BY id')
        n_app = 0
        for row in cur.fetchall():
            tid = type_map.get(int(row['appointment_type_id']))
            advid = advisor_map.get(int(row['advisor_id']))
            uid = user_map.get(int(row['user_id']))
            if not tid or not advid or not uid:
                print(
                    f"  [skip appointment id={row['id']}] falta type/advisor/user en mapa",
                    file=sys.stderr,
                )
                continue
            sid = None
            if row['service_id']:
                sid = svc_map.get(int(row['service_id']))
            slot_pg = None
            if row['slot_id']:
                slot_pg = slot_map.get(int(row['slot_id']))

            ref = secrets.token_hex(5).upper()[:40]
            ap = Appointment(
                reference=ref,
                appointment_type_id=tid,
                advisor_id=advid,
                slot_id=slot_pg,
                user_id=uid,
                membership_type=(row['membership_type'] or '')[:50] if row['membership_type'] else None,
                is_group=bool(row['is_group']) if row['is_group'] is not None else False,
                start_datetime=_parse_dt(row['start_datetime']) if row['start_datetime'] else None,
                end_datetime=_parse_dt(row['end_datetime']) if row['end_datetime'] else None,
                status=(row['status'] or 'pending')[:20],
                queue_position=int(row['queue_position']) if row['queue_position'] is not None else None,
                advisor_confirmed=bool(row['advisor_confirmed']) if row['advisor_confirmed'] is not None else False,
                advisor_confirmed_at=_parse_dt(row['advisor_confirmed_at']) if row['advisor_confirmed_at'] else None,
                is_initial_consult=bool(row['is_initial_consult'])
                if row['is_initial_consult'] is not None
                else True,
                advisor_response_notes=row['advisor_response_notes'],
                confirmed_at=_parse_dt(row['confirmed_at']) if row['confirmed_at'] else None,
                cancellation_reason=row['cancellation_reason'],
                cancelled_by=(row['cancelled_by'] or '')[:20] if row['cancelled_by'] else None,
                cancelled_at=_parse_dt(row['cancelled_at']) if row['cancelled_at'] else None,
                base_price=float(row['base_price'] or 0),
                final_price=float(row['final_price'] or 0),
                discount_applied=float(row['discount_applied'] or 0),
                payment_status=(row['payment_status'] or 'pending')[:20],
                payment_method=(row['payment_method'] or '')[:50] if row['payment_method'] else None,
                payment_reference=(row['payment_reference'] or '')[:100] if row['payment_reference'] else None,
                user_notes=row['user_notes'],
                advisor_notes=row['advisor_notes'],
                calendar_sync_url=(row['calendar_sync_url'] or '')[:500] if row['calendar_sync_url'] else None,
                calendar_event_id=(row['calendar_event_id'] or '')[:200] if row['calendar_event_id'] else None,
                reminder_sent=bool(row['reminder_sent']) if row['reminder_sent'] is not None else False,
                reminder_sent_at=_parse_dt(row['reminder_sent_at']) if row['reminder_sent_at'] else None,
                confirmation_sent=bool(row['confirmation_sent']) if row['confirmation_sent'] is not None else False,
                confirmation_sent_at=_parse_dt(row['confirmation_sent_at']) if row['confirmation_sent_at'] else None,
                cancellation_sent=bool(row['cancellation_sent']) if row['cancellation_sent'] is not None else False,
                cancellation_sent_at=_parse_dt(row['cancellation_sent_at']) if row['cancellation_sent_at'] else None,
                meeting_url=(row['meeting_url'] or '')[:500] if row['meeting_url'] else None,
                meeting_password=(row['meeting_password'] or '')[:100] if row['meeting_password'] else None,
                check_in_time=_parse_dt(row['check_in_time']) if row['check_in_time'] else None,
                check_out_time=_parse_dt(row['check_out_time']) if row['check_out_time'] else None,
                duration_actual=int(row['duration_actual']) if row['duration_actual'] is not None else None,
                rating=int(row['rating']) if row['rating'] is not None else None,
                rating_comment=row['rating_comment'],
                service_id=sid,
                payment_id=None,
                organization_id=target_org,
            )
            if row['created_at']:
                ap.created_at = _parse_dt(row['created_at'])
            if row['updated_at']:
                ap.updated_at = _parse_dt(row['updated_at'])
            M.db.session.add(ap)
            n_app += 1

        M.db.session.commit()

        with M.db.engine.begin() as conn:
            for tbl in (
                'appointment_type',
                'advisor',
                'appointment_advisor',
                'appointment_slot',
                'appointment',
            ):
                _sync_sequence(conn, tbl)

        print(
            f'OK: org={target_org} tipos={len(type_map)} asesores_map={len(advisor_map)} '
            f'appointment_advisor={n_aa} slots={len(slot_map)} citas={n_app}'
        )
    con.close()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
