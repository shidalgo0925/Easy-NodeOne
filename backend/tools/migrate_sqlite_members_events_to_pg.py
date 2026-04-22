#!/usr/bin/env python3
"""
Migración SQLite → PostgreSQL (relatic u otro): miembros, contraseñas, planes,
pagos/suscripciones y eventos (sin citas).

Uso (desde backend/, con DATABASE_URL en el entorno, p. ej. relatic):
  ../venv/bin/python3 tools/migrate_sqlite_members_events_to_pg.py \\
    --sqlite /ruta/relaticpanama_backup_YYYYMMDD_HHMMSS.db \\
    --dotenv /opt/easynodeone/relatic/.env \\
    --organization-id 1

Sin --apply: solo resumen de conteos (lectura). Para escribir:
  ... --apply

Si PG ya tiene filas en payment o event, el script aborta salvo --force
(evita duplicar la migración).

Fases: users → membership_plan → email_template → discount → payment → subscription →
       event → event_image → event_discount → event_registration

No importa app Flask: solo SQLAlchemy + sqlite3 + dotenv.
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection
from sqlalchemy.exc import IntegrityError


def _load_dotenv(path: Path) -> None:
    try:
        from dotenv import load_dotenv

        load_dotenv(path, override=True)
    except ImportError:
        pass


def _sqlite_cols(con: sqlite3.Connection, table: str) -> dict[str, Any]:
    rows = con.execute(f'PRAGMA table_info("{table}")').fetchall()
    return {r[1]: r for r in rows}


def _as_bool(v: Any, default: bool = False) -> bool:
    if v is None:
        return default
    if isinstance(v, (int, float)):
        return bool(int(v))
    return bool(v)


def _truncate(s: str | None, n: int) -> str | None:
    if s is None:
        return None
    s = str(s)
    return s if len(s) <= n else s[:n]


def _sync_sequence(conn: Connection, table: str, pk: str = "id") -> None:
    seq = conn.execute(
        text(
            "SELECT pg_get_serial_sequence(:tbl, :pk)",
        ),
        {"tbl": table, "pk": pk},
    ).scalar()
    if not seq:
        return
    mx = conn.execute(text(f'SELECT COALESCE(MAX("{pk}"), 1) FROM "{table}"')).scalar()
    conn.execute(text("SELECT setval(:seq, :mx, true)"), {"seq": seq, "mx": int(mx)})


def migrate_users(
    sl: sqlite3.Connection,
    conn: Connection,
    org_id: int,
) -> dict[int, int]:
    """Devuelve mapa sqlite_user.id -> pg user.id."""
    cur = sl.cursor()
    cur.execute(
        """
        SELECT id, email, password_hash, first_name, last_name, phone, country,
               cedula_or_passport, tags, user_group, created_at, is_active, is_admin,
               is_advisor, email_verified, profile_picture
        FROM user ORDER BY id
        """
    )
    rows = cur.fetchall()
    user_map: dict[int, int] = {}

    for r in rows:
        (
            sid,
            email,
            ph,
            fn,
            ln,
            phone,
            country,
            cedula,
            tags,
            ug,
            created_at,
            is_active,
            is_admin,
            is_advisor,
            email_verified,
            pfp,
        ) = r
        email = (email or "").strip().lower()
        if not email:
            continue

        existing = conn.execute(
            text("SELECT id, is_admin FROM \"user\" WHERE lower(email) = lower(:e)"),
            {"e": email},
        ).fetchone()

        if existing:
            pg_id, pg_is_admin = int(existing[0]), bool(existing[1])
            user_map[int(sid)] = pg_id
            if not pg_is_admin:
                conn.execute(
                    text(
                        """
                        UPDATE "user" SET
                          password_hash = :ph,
                          first_name = :fn,
                          last_name = :ln,
                          phone = :phone,
                          country = :country,
                          cedula_or_passport = :ced,
                          tags = :tags,
                          user_group = :ug,
                          is_active = COALESCE(:ia, is_active),
                          is_advisor = COALESCE(:iad, is_advisor),
                          email_verified = COALESCE(:ev, email_verified),
                          profile_picture = COALESCE(:pfp, profile_picture),
                          organization_id = :org
                        WHERE id = :id AND is_admin = false
                        """
                    ),
                    {
                        "id": pg_id,
                        "ph": ph,
                        "fn": _truncate(fn, 50) or "",
                        "ln": _truncate(ln, 50) or "",
                        "phone": _truncate(phone, 20),
                        "country": _truncate(country, 100),
                        "ced": _truncate(cedula, 20),
                        "tags": _truncate(tags, 500),
                        "ug": _truncate(ug, 100),
                        "ia": is_active,
                        "iad": is_advisor,
                        "ev": email_verified,
                        "pfp": _truncate(pfp, 500),
                        "org": org_id,
                    },
                )
            continue

        res = conn.execute(
            text(
                """
                INSERT INTO "user" (
                  email, password_hash, first_name, last_name, phone, country,
                  cedula_or_passport, tags, user_group, created_at,
                  is_active, is_admin, is_advisor, email_verified,
                  email_verification_token, email_verification_token_expires,
                  email_verification_sent_at, password_reset_token,
                  password_reset_token_expires, password_reset_sent_at,
                  profile_picture, must_change_password, email_marketing_status,
                  organization_id, last_selected_organization_id, is_salesperson
                ) VALUES (
                  :email, :ph, :fn, :ln, :phone, :country, :ced, :tags, :ug, :ca,
                  :ia, COALESCE(:iadm, false), COALESCE(:iadv, false), COALESCE(:ev, false),
                  NULL, NULL, NULL, NULL, NULL, NULL,
                  :pfp, false, 'subscribed', :org, NULL, false
                ) RETURNING id
                """
            ),
            {
                "email": email[:120],
                "ph": str(ph)[:128],
                "fn": (_truncate(fn, 50) or "?")[:50],
                "ln": (_truncate(ln, 50) or "?")[:50],
                "phone": _truncate(phone, 20),
                "country": _truncate(country, 100),
                "ced": _truncate(cedula, 20),
                "tags": _truncate(tags, 500),
                "ug": _truncate(ug, 100),
                "ca": created_at or datetime.utcnow(),
                "ia": bool(is_active) if is_active is not None else True,
                "iadm": bool(is_admin) if is_admin is not None else False,
                "iadv": bool(is_advisor) if is_advisor is not None else False,
                "ev": bool(email_verified) if email_verified is not None else False,
                "pfp": _truncate(pfp, 500),
                "org": org_id,
            },
        )
        new_id = int(res.scalar_one())
        user_map[int(sid)] = new_id

    return user_map


def migrate_email_templates(sl: sqlite3.Connection, conn: Connection, org_id: int) -> int:
    """Copia plantillas de correo desde SQLite (tabla email_template) con upsert por org+template_key."""
    cur = sl.cursor()
    cur.execute(
        """
        SELECT template_key, name, subject, html_content, text_content, category,
               is_custom, variables, created_at, updated_at
        FROM email_template ORDER BY id
        """
    )
    rows = cur.fetchall()
    n = 0
    for r in rows:
        tk, name, subj, html, text_plain, cat, iscust, vars_, ca, ua = r
        conn.execute(
            text(
                """
                INSERT INTO email_template (
                  organization_id, template_key, name, subject, html_content, text_content,
                  category, is_custom, variables, created_at, updated_at
                ) VALUES (
                  :oid, :tk, :name, :subj, :html, :txt, :cat, :isc, :vars,
                  COALESCE(:ca, NOW()), COALESCE(:ua, NOW())
                )
                ON CONFLICT (organization_id, template_key) DO UPDATE SET
                  name = EXCLUDED.name,
                  subject = EXCLUDED.subject,
                  html_content = EXCLUDED.html_content,
                  text_content = EXCLUDED.text_content,
                  category = EXCLUDED.category,
                  is_custom = EXCLUDED.is_custom,
                  variables = EXCLUDED.variables,
                  updated_at = EXCLUDED.updated_at
                """
            ),
            {
                "oid": org_id,
                "tk": tk,
                "name": name,
                "subj": subj,
                "html": html or "",
                "txt": text_plain,
                "cat": cat,
                "isc": _as_bool(iscust, False),
                "vars": vars_,
                "ca": ca,
                "ua": ua or ca,
            },
        )
        n += 1
    return n


def ensure_membership_plans(sl: sqlite3.Connection, conn: Connection, org_id: int) -> None:
    cur = sl.cursor()
    cur.execute(
        """
        SELECT membership_type,
               MAX(CASE WHEN lower(billing_cycle) IN ('monthly','month') THEN price END) AS pm,
               MAX(CASE WHEN lower(billing_cycle) IN ('yearly','year','annual') THEN price END) AS py
        FROM membership_pricing
        GROUP BY membership_type
        """
    )
    for membership_type, pm, py in cur.fetchall():
        slug = (membership_type or "basic").strip().lower()[:50]
        exists = conn.execute(
            text("SELECT 1 FROM membership_plan WHERE organization_id = :o AND slug = :s LIMIT 1"),
            {"o": org_id, "s": slug},
        ).fetchone()
        if exists:
            continue
        name = slug.replace("_", " ").title()[:100]
        conn.execute(
            text(
                """
                INSERT INTO membership_plan (
                  slug, name, description, price_yearly, price_monthly,
                  display_order, level, badge, color, is_active,
                  created_at, updated_at, organization_id
                ) VALUES (
                  :slug, :name, NULL, COALESCE(:py, 0), COALESCE(:pm, 0),
                  0, 0, NULL, 'bg-secondary', true,
                  NOW(), NOW(), :org
                )
                """
            ),
            {"slug": slug, "name": name, "pm": float(pm or 0), "py": float(py or 0), "org": org_id},
        )


def migrate_discounts(sl: sqlite3.Connection, conn: Connection) -> dict[int, int]:
    cur = sl.cursor()
    cur.execute("SELECT * FROM discount ORDER BY id")
    cols = [d[0] for d in cur.description]
    disc_map: dict[int, int] = {}
    for row in cur.fetchall():
        d = dict(zip(cols, row))
        oid = int(d["id"])
        base_code = _truncate(d.get("code"), 50) or f"migr-{oid}"
        params = {
            "name": _truncate(d.get("name"), 100) or "Discount",
            "code": base_code[:50],
            "desc": d.get("description"),
            "dtype": (d.get("discount_type") or "percentage")[:20],
            "val": float(d.get("value") or 0),
            "tier": _truncate(d.get("membership_tier"), 50),
            "cat": _truncate(d.get("category"), 50) or "event",
            "auto": bool(d.get("applies_automatically")),
            "active": bool(d.get("is_active")) if d.get("is_active") is not None else True,
            "maxu": d.get("max_uses"),
            "uses": d.get("uses") or 0,
            "cuses": d.get("current_uses") if d.get("current_uses") is not None else d.get("uses"),
            "sd": d.get("start_date"),
            "ed": d.get("end_date"),
            "ca": d.get("created_at") or datetime.utcnow(),
            "ua": d.get("updated_at") or datetime.utcnow(),
        }
        ins = text(
            """
            INSERT INTO discount (
              name, code, description, discount_type, value, membership_tier,
              category, applies_automatically, is_active, is_master, max_uses,
              uses, current_uses, start_date, end_date, created_at, updated_at
            ) VALUES (
              :name, :code, :desc, :dtype, :val, :tier,
              :cat, :auto, :active, false, :maxu,
              COALESCE(:uses, 0), COALESCE(:cuses, 0), :sd, :ed, :ca, :ua
            ) RETURNING id
            """
        )
        with conn.begin_nested():
            try:
                r = conn.execute(ins, params)
                disc_map[oid] = int(r.scalar_one())
            except IntegrityError:
                params["code"] = f"migr-{oid}"[:50]
                r = conn.execute(ins, params)
                disc_map[oid] = int(r.scalar_one())
    return disc_map


def migrate_payments(
    sl: sqlite3.Connection,
    conn: Connection,
    user_map: dict[int, int],
) -> dict[int, int]:
    cur = sl.cursor()
    cur.execute("SELECT * FROM payment ORDER BY id")
    cols = [d[0] for d in cur.description]
    pay_map: dict[int, int] = {}
    for row in cur.fetchall():
        d = dict(zip(cols, row))
        oid = int(d["id"])
        uid = int(d["user_id"])
        if uid not in user_map:
            print(f"  [skip payment id={oid}] user_id={uid} sin mapa")
            continue
        nuid = user_map[uid]
        extra = {
            k: d[k]
            for k in (
                "stripe_payment_intent_id",
                "exchange_rate",
                "original_amount",
                "original_currency",
                "is_recurring",
                "recurring_id",
                "billing_cycle",
                "next_billing_date",
                "parent_payment_id",
                "is_installment",
                "installment_count",
                "installment_number",
                "installment_total",
                "parent_installment_id",
                "invoice_id",
                "yappy_transaction_id",
                "yappy_raw_response",
            )
            if k in d and d[k] is not None
        }
        meta = d.get("payment_metadata")
        if meta and str(meta).strip():
            try:
                parsed = json.loads(meta) if isinstance(meta, str) else meta
            except json.JSONDecodeError:
                parsed = {"legacy": str(meta)[:2000]}
            extra["legacy_payment_metadata"] = parsed
        elif extra:
            pass
        meta_json = json.dumps(extra) if extra else None

        amount = d.get("amount")
        try:
            amount_i = int(amount) if amount is not None else 0
        except (TypeError, ValueError):
            amount_i = int(float(amount or 0))

        r = conn.execute(
            text(
                """
                INSERT INTO payment (
                  user_id, payment_method, payment_reference, amount, currency,
                  status, membership_type, payment_url, receipt_url, receipt_filename,
                  ocr_data, ocr_status, ocr_verified_at, admin_notes, payment_metadata,
                  created_at, updated_at, paid_at
                ) VALUES (
                  :uid, :pm, :pref, :amt, lower(COALESCE(:cur, 'usd')),
                  COALESCE(:st, 'pending'), COALESCE(:mt, 'basic'), :purl, :rurl, :rfn,
                  :ocr, COALESCE(:ocrst, 'pending'), :ocrat, :notes, :meta,
                  COALESCE(:ca, NOW()), COALESCE(:ua, NOW()), :paid
                ) RETURNING id
                """
            ),
            {
                "uid": nuid,
                "pm": (d.get("payment_method") or "unknown")[:50],
                "pref": _truncate(d.get("payment_reference"), 200),
                "amt": amount_i,
                "cur": (d.get("currency") or "usd")[:3],
                "st": (d.get("status") or "pending")[:20],
                "mt": (d.get("membership_type") or "basic")[:50],
                "purl": _truncate(d.get("payment_url"), 500),
                "rurl": _truncate(d.get("receipt_url"), 500),
                "rfn": _truncate(d.get("receipt_filename"), 255),
                "ocr": d.get("ocr_data"),
                "ocrst": (d.get("ocr_status") or "pending")[:20],
                "ocrat": d.get("ocr_verified_at"),
                "notes": d.get("admin_notes"),
                "meta": meta_json,
                "ca": d.get("created_at"),
                "ua": d.get("updated_at"),
                "paid": d.get("paid_at"),
            },
        )
        pay_map[oid] = int(r.scalar_one())
    return pay_map


def migrate_subscriptions(
    sl: sqlite3.Connection,
    conn: Connection,
    user_map: dict[int, int],
    pay_map: dict[int, int],
) -> None:
    cur = sl.cursor()
    cur.execute("SELECT * FROM subscription ORDER BY id")
    cols = [d[0] for d in cur.description]
    for row in cur.fetchall():
        d = dict(zip(cols, row))
        uid = int(d["user_id"])
        pid = int(d["payment_id"])
        if uid not in user_map or pay_map.get(pid) is None:
            print(f"  [skip subscription id={d['id']}] user={uid} pay={pid}")
            continue
        nuid, npid = user_map[uid], pay_map[pid]
        araw = d.get("auto_renew")
        if araw is None:
            auto_renew = True
        elif isinstance(araw, (int, float)):
            auto_renew = bool(int(araw))
        else:
            auto_renew = bool(araw)

        conn.execute(
            text(
                """
                INSERT INTO subscription (
                  user_id, payment_id, membership_type, status,
                  start_date, end_date, auto_renew, created_at, updated_at
                ) VALUES (
                  :uid, :pid, :mt, COALESCE(:st, 'active'),
                  COALESCE(:sd, NOW()), COALESCE(:ed, NOW()), :ar,
                  COALESCE(:ca, NOW()), COALESCE(:ua, NOW())
                )
                """
            ),
            {
                "uid": nuid,
                "pid": npid,
                "mt": (d.get("membership_type") or "basic")[:50],
                "st": (d.get("status") or "active")[:20],
                "sd": d.get("start_date"),
                "ed": d.get("end_date"),
                "ar": auto_renew,
                "ca": d.get("created_at"),
                "ua": d.get("updated_at"),
            },
        )


def _slug_unique(conn: Connection, base: str) -> str:
    b = (base or "event")[:180]
    cand = b
    n = 0
    while True:
        row = conn.execute(
            text("SELECT 1 FROM event WHERE slug = :s LIMIT 1"),
            {"s": cand},
        ).fetchone()
        if not row:
            return cand
        n += 1
        cand = f"{b}-m{n}"[:200]


def migrate_events(
    sl: sqlite3.Connection,
    conn: Connection,
    user_map: dict[int, int],
    disc_map: dict[int, int],
) -> tuple[dict[int, int], dict[int, int]]:
    """event_map, registration uses event_map."""
    cur = sl.cursor()
    cur.execute("SELECT * FROM event ORDER BY id")
    cols = [d[0] for d in cur.description]
    event_map: dict[int, int] = {}

    def remap_user(x: Any) -> Any:
        if x is None:
            return None
        i = int(x)
        return user_map.get(i)

    for row in cur.fetchall():
        d = dict(zip(cols, row))
        oid = int(d["id"])
        slug = _slug_unique(conn, (d.get("slug") or f"event-{oid}").strip())
        r = conn.execute(
            text(
                """
                INSERT INTO event (
                  title, slug, summary, description, category, format, tags,
                  base_price, currency, registration_url, contact_email, contact_phone,
                  location, country, venue, university, is_virtual, has_certificate,
                  certificate_instructions, certificate_template, kahoot_enabled,
                  kahoot_link, kahoot_required,
                  step_1_event_completed, step_2_description_completed, step_3_publicity_completed,
                  step_4_certificate_completed, step_5_kahoot_completed,
                  generates_poster, generates_magazine, generates_book,
                  capacity, registered_count, visibility, publish_status, featured,
                  start_date, end_date, registration_deadline, cover_image,
                  created_by, moderator_id, administrator_id, speaker_id,
                  created_at, updated_at
                ) VALUES (
                  :title, :slug, :summary, :desc, COALESCE(:cat,'general'), COALESCE(:fmt,'virtual'), :tags,
                  COALESCE(:bp,0), COALESCE(lower(:cur),'usd'), :rurl, :cemail, :cphone,
                  :loc, :country, :venue, :univ, :iv, :hc,
                  :cinst, :ctpl, :ke,
                  :kl, :kr,
                  :s1, :s2, :s3, :s4, :s5,
                  :gp, :gm, :gb,
                  COALESCE(:cap,0), COALESCE(:rc,0), COALESCE(:vis,'members'), COALESCE(:pub,'draft'), :feat,
                  :sd, :ed, :rdl, :cover,
                  :cby, :mod, :adm, :spk,
                  COALESCE(:ca, NOW()), COALESCE(:ua, NOW())
                ) RETURNING id
                """
            ),
            {
                "title": (_truncate(d.get("title"), 200) or "Event")[:200],
                "slug": slug[:200],
                "summary": d.get("summary"),
                "desc": d.get("description"),
                "cat": d.get("category"),
                "fmt": d.get("format"),
                "tags": _truncate(d.get("tags"), 500),
                "bp": d.get("base_price"),
                "cur": d.get("currency"),
                "rurl": _truncate(d.get("registration_url"), 500),
                "cemail": _truncate(d.get("contact_email"), 120),
                "cphone": _truncate(d.get("contact_phone"), 20),
                "loc": _truncate(d.get("location"), 200),
                "country": _truncate(d.get("country"), 100),
                "venue": _truncate(d.get("venue"), 200),
                "univ": _truncate(d.get("university"), 200),
                "iv": _as_bool(d.get("is_virtual"), False),
                "hc": _as_bool(d.get("has_certificate"), False),
                "cinst": d.get("certificate_instructions"),
                "ctpl": _truncate(d.get("certificate_template"), 500),
                "ke": _as_bool(d.get("kahoot_enabled"), False),
                "kl": _truncate(d.get("kahoot_link"), 500),
                "kr": _as_bool(d.get("kahoot_required"), False),
                "s1": _as_bool(d.get("step_1_event_completed"), False),
                "s2": _as_bool(d.get("step_2_description_completed"), False),
                "s3": _as_bool(d.get("step_3_publicity_completed"), False),
                "s4": _as_bool(d.get("step_4_certificate_completed"), False),
                "s5": _as_bool(d.get("step_5_kahoot_completed"), False),
                "gp": _as_bool(d.get("generates_poster"), False),
                "gm": _as_bool(d.get("generates_magazine"), False),
                "gb": _as_bool(d.get("generates_book"), False),
                "cap": d.get("capacity"),
                "rc": d.get("registered_count"),
                "vis": d.get("visibility"),
                "pub": d.get("publish_status"),
                "feat": _as_bool(d.get("featured"), False),
                "sd": d.get("start_date"),
                "ed": d.get("end_date"),
                "rdl": d.get("registration_deadline"),
                "cover": _truncate(d.get("cover_image"), 500),
                "cby": remap_user(d.get("created_by")),
                "mod": remap_user(d.get("moderator_id")),
                "adm": remap_user(d.get("administrator_id")),
                "spk": remap_user(d.get("speaker_id")),
                "ca": d.get("created_at"),
                "ua": d.get("updated_at"),
            },
        )
        event_map[oid] = int(r.scalar_one())

    # event_image (sin caption en PG)
    cur.execute("SELECT * FROM event_image ORDER BY id")
    cols = [d[0] for d in cur.description]
    for row in cur.fetchall():
        d = dict(zip(cols, row))
        eid = int(d["event_id"])
        if eid not in event_map:
            continue
        ne = event_map[eid]
        conn.execute(
            text(
                """
                INSERT INTO event_image (event_id, file_path, sort_order, is_primary, created_at)
                VALUES (:eid, :fp, COALESCE(:so,0), :ip, COALESCE(:ca, NOW()))
                """
            ),
            {
                "eid": ne,
                "fp": (_truncate(d.get("file_path"), 500) or "")[:500],
                "so": d.get("sort_order"),
                "ip": _as_bool(d.get("is_primary"), False),
                "ca": d.get("created_at"),
            },
        )

    # event_discount
    cur.execute("SELECT * FROM event_discount ORDER BY id")
    cols = [d[0] for d in cur.description]
    for row in cur.fetchall():
        d = dict(zip(cols, row))
        eid = int(d["event_id"])
        did = int(d["discount_id"])
        if eid not in event_map or did not in disc_map:
            continue
        conn.execute(
            text(
                """
                INSERT INTO event_discount (event_id, discount_id, priority, created_at)
                VALUES (:e, :d, COALESCE(:p,1), COALESCE(:ca, NOW()))
                """
            ),
            {
                "e": event_map[eid],
                "d": disc_map[did],
                "p": d.get("priority"),
                "ca": d.get("created_at"),
            },
        )

    # event_registration
    cur.execute("SELECT * FROM event_registration ORDER BY id")
    cols = [d[0] for d in cur.description]
    for row in cur.fetchall():
        d = dict(zip(cols, row))
        eid = int(d["event_id"])
        uid = int(d["user_id"])
        if eid not in event_map or uid not in user_map:
            continue
        ne, nu = event_map[eid], user_map[uid]
        conn.execute(
            text(
                """
                INSERT INTO event_registration (
                  event_id, user_id, registration_date, registration_status,
                  confirmation_email_sent, reminder_email_sent, certificate_email_sent,
                  base_price, discount_applied, final_price, membership_type,
                  discount_code_used, payment_status, payment_method, payment_reference,
                  payment_date, notes, created_at, updated_at
                ) VALUES (
                  :eid, :uid, COALESCE(:rd, NOW()), COALESCE(:rs, 'confirmed'),
                  :ces, :res, :certs,
                  COALESCE(:bp,0), COALESCE(:da,0), COALESCE(:fp,0), :mt,
                  :dcu, COALESCE(:pst, 'pending'), :pme, :pref, :pdt, :notes,
                  COALESCE(:ca, NOW()), COALESCE(:ua, NOW())
                )
                ON CONFLICT (event_id, user_id) DO NOTHING
                """
            ),
            {
                "eid": ne,
                "uid": nu,
                "rd": d.get("registration_date"),
                "rs": (d.get("registration_status") or "confirmed")[:20],
                "ces": _as_bool(d.get("confirmation_email_sent"), False),
                "res": _as_bool(d.get("reminder_email_sent"), False),
                "certs": _as_bool(d.get("certificate_email_sent"), False),
                "bp": d.get("base_price"),
                "da": d.get("discount_applied"),
                "fp": d.get("final_price"),
                "mt": _truncate(d.get("membership_type"), 50),
                "dcu": _truncate(d.get("discount_code_used"), 50),
                "pst": (d.get("payment_status") or "pending")[:20],
                "pme": _truncate(d.get("payment_method"), 50),
                "pref": _truncate(d.get("payment_reference"), 100),
                "pdt": d.get("payment_date"),
                "notes": d.get("notes"),
                "ca": d.get("created_at"),
                "ua": d.get("updated_at"),
            },
        )

    return event_map, disc_map


def print_summary(sqlite_path: Path, database_url: str, org_id: int) -> None:
    """Solo lectura: filas en SQLite vs PostgreSQL (sin escribir)."""
    sl = sqlite3.connect(str(sqlite_path))

    def sc(table: str) -> int:
        return int(sl.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])

    eng = create_engine(database_url, future=True)
    pairs = [
        ("user", "user"),
        ("payment", "payment"),
        ("subscription", "subscription"),
        ("event", "event"),
        ("event_registration", "event_registration"),
        ("discount", "discount"),
        ("membership_pricing", "membership_plan"),
        ("email_template", "email_template"),
    ]
    print("\n--- Resumen filas (SQLite backup vs PG actual) ---")
    print(f"{'Tabla':<28} {'SQLite':>10} {'PG':>10}")
    with eng.connect() as c:
        for sl_t, pg_t in pairs:
            try:
                s_n = sc(sl_t)
            except sqlite3.Error:
                s_n = -1
            try:
                p_n = c.execute(text(f'SELECT COUNT(*) FROM "{pg_t}"')).scalar()
            except Exception:
                p_n = -1
            print(f"{sl_t} → {pg_t:<18} {s_n:>10} {int(p_n or 0):>10}")
    sl.close()
    print(f"\norganization_id destino previsto: {org_id}")
    print("Para ejecutar la migración real: añadí --apply (tras backup de PG).")


def main() -> int:
    ap = argparse.ArgumentParser(description="Migrar miembros/membresías/eventos desde SQLite a PG.")
    ap.add_argument("--sqlite", required=True, type=Path, help="Ruta al .db SQLite (backup).")
    ap.add_argument("--dotenv", type=Path, help="Cargar variables (p. ej. /opt/easynodeone/relatic/.env).")
    ap.add_argument("--organization-id", type=int, default=1, help="saas_organization.id destino.")
    ap.add_argument(
        "--apply",
        action="store_true",
        help="Escribir en PostgreSQL. Sin este flag solo se imprime el resumen (lectura).",
    )
    ap.add_argument(
        "--force",
        action="store_true",
        help="Con --apply: permitir ejecutar aunque payment/event ya tengan filas (riesgo de duplicados).",
    )
    args = ap.parse_args()

    if not args.sqlite.is_file():
        print(f"No existe archivo: {args.sqlite}", file=sys.stderr)
        return 1

    if args.dotenv:
        _load_dotenv(args.dotenv)
    else:
        _load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

    url = os.environ.get("DATABASE_URL")
    if not url:
        print("DATABASE_URL no definido (usá --dotenv).", file=sys.stderr)
        return 1

    org_id = int(args.organization_id)

    print(f"SQLite: {args.sqlite}")
    print(f"PG: {url.split('@')[-1] if '@' in url else url}")

    if not args.apply:
        print_summary(args.sqlite, url, org_id)
        return 0

    eng = create_engine(url, future=True)
    with eng.connect() as c:
        n_pay = int(c.execute(text('SELECT COUNT(*) FROM "payment"')).scalar() or 0)
        n_ev = int(c.execute(text('SELECT COUNT(*) FROM "event"')).scalar() or 0)
    if (n_pay > 0 or n_ev > 0) and not args.force:
        print(
            f"Abort: PG ya tiene payment={n_pay}, event={n_ev}. "
            "Hacé pg_dump, vaciá tablas objetivo o usá --force si insistís.",
            file=sys.stderr,
        )
        return 2

    sl = sqlite3.connect(str(args.sqlite))
    sl.row_factory = sqlite3.Row

    print(f"organization_id={org_id} (--apply)")

    with eng.begin() as conn:
        user_map = migrate_users(sl, conn, org_id)
        print(f"Usuarios: mapa sqlite->pg {len(user_map)} entradas")

        ensure_membership_plans(sl, conn, org_id)
        print("Planes membership_plan: asegurados.")

        n_tpl = migrate_email_templates(sl, conn, org_id)
        print(f"Plantillas email_template: {n_tpl} upserts.")

        disc_map = migrate_discounts(sl, conn)
        print(f"Descuentos: {len(disc_map)} reinsertados con mapa id.")

        pay_map = migrate_payments(sl, conn, user_map)
        print(f"Pagos: {len(pay_map)} insertados.")

        migrate_subscriptions(sl, conn, user_map, pay_map)
        print("Suscripciones: insertadas.")

        migrate_events(sl, conn, user_map, disc_map)
        print("Eventos + imágenes + event_discount + registrations: insertados.")

        for tbl in (
            "user",
            "membership_plan",
            "email_template",
            "discount",
            "payment",
            "subscription",
            "event",
            "event_image",
            "event_discount",
            "event_registration",
        ):
            _sync_sequence(conn, tbl)
        print("Secuencias serial ajustadas.")

    sl.close()
    print("OK. Revisá login de usuarios de prueba y reiniciá el servicio si hace falta.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
