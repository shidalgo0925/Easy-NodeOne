#!/opt/easynodeone/dev/app/.venv/bin/python3
"""
Reemplaza el tenant organization_id=3 (Relatic Panama Dev) en easynodeone_dev
con organization_id=1 de easynodeone_dev_relatic_clone. Usuarios por email
(merge); el resto de IDs se regeneran y se remapean en el subgrafo copiado.

  /opt/easynodeone/dev/app/.venv/bin/python3 tools/migrate_org3_from_relatic_clone.py
  /opt/easynodeone/dev/app/.venv/bin/python3 tools/migrate_org3_from_relatic_clone.py --apply
"""
from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import psycopg2

SRC_ORG = 1
DST_ORG = 3

_DEFAULT_DEV_ENV = Path("/opt/easynodeone/dev/.env")
_CLONE_DB = "easynodeone_dev_relatic_clone"


def _load_key_from_envfile(key: str, path: Path = _DEFAULT_DEV_ENV) -> str | None:
    if not path.is_file():
        return None
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        if k.strip() == key:
            return v.strip().strip('"').strip("'")
    return None


def _resolve_dsns() -> tuple[str, str]:
    base = (os.environ.get("DATABASE_URL") or "").strip() or _load_key_from_envfile(
        "DATABASE_URL"
    )
    if not base:
        raise SystemExit(
            "Defina DATABASE_URL o use /opt/easynodeone/dev/.env con DATABASE_URL=..."
        )
    src = (os.environ.get("CLONE_DATABASE_URL") or "").strip()
    b = base.rstrip("/")
    if not src:
        if b.endswith("easynodeone_dev") and not b.endswith(_CLONE_DB):
            src = b[: -len("easynodeone_dev")] + _CLONE_DB
        elif b.endswith(_CLONE_DB):
            src = base
    if not src:
        raise SystemExit("Defina CLONE_DATABASE_URL=... a easynodeone_dev_relatic_clone")
    if _CLONE_DB not in src:
        raise SystemExit("CLONE_DATABASE_URL debe apuntar a " + _CLONE_DB)
    return base, src

USER_FK: Sequence[tuple[str, str]] = (
    ("activity_log", "user_id"),
    ("advisor", "user_id"),
    ("advisor_service_availability", "created_by"),
    ("appointment", "user_id"),
    ("appointment_participant", "invited_by_id"),
    ("appointment_participant", "user_id"),
    ("appointment_slot", "created_by"),
    ("campaign_recipients", "user_id"),
    ("cart", "user_id"),
    ("certificates", "user_id"),
    ("communication_log", "user_id"),
    ("crm_activity", "assigned_to"),
    ("crm_lead", "user_id"),
    ("crm_lead_log", "created_by"),
    ("daily_service_availability", "created_by"),
    ("discount_application", "user_id"),
    ("discount_code", "created_by"),
    ("email_log", "recipient_id"),
    ("event", "administrator_id"),
    ("event", "created_by"),
    ("event", "moderator_id"),
    ("event", "speaker_id"),
    ("event_certificate", "issued_by"),
    ("event_participant", "user_id"),
    ("event_registration", "user_id"),
    ("event_speaker", "user_id"),
    ("event_workshop", "instructor_id"),
    ("export_template", "user_id"),
    ("history_transaction", "actor_id"),
    ("history_transaction", "owner_user_id"),
    ("invoices", "created_by"),
    ("invoices", "customer_id"),
    ("membership", "user_id"),
    ("notification", "user_id"),
    ("office365_request", "user_id"),
    ("organization_invite", "accepted_user_id"),
    ("organization_invite", "invited_by_user_id"),
    ("payment", "user_id"),
    ("policy_acceptance", "user_id"),
    ("proposal", "client_id"),
    ("quotations", "created_by"),
    ("quotations", "customer_id"),
    ("social_auth", "user_id"),
    ("students", "user_id"),
    ("subscription", "user_id"),
    ("user_communication_preference", "user_id"),
    ("user_role", "assigned_by_id"),
    ("user_role", "user_id"),
    ("user_service", "user_id"),
    ("user_settings", "user_id"),
    ("workshop_inspections", "created_by"),
    ("workshop_orders", "advisor_id"),
    ("workshop_orders", "customer_id"),
    ("workshop_vehicles", "customer_id"),
)


def table_exists(cur, table: str) -> bool:
    cur.execute("SELECT to_regclass(%s)", (f"public.{table}",))
    return cur.fetchone()[0] is not None


def get_cols(cur, table: str) -> list[str]:
    cur.execute(
        """
        SELECT column_name FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = %s
        ORDER BY ordinal_position
        """,
        (table,),
    )
    return [r[0] for r in cur.fetchall()]


def org_id_tables_excluding_user(cur) -> list[str]:
    cur.execute(
        """
        SELECT c.table_name
        FROM information_schema.columns c
        JOIN information_schema.tables t
          ON t.table_schema = c.table_schema AND t.table_name = c.table_name
        WHERE c.table_schema = 'public' AND c.column_name = 'organization_id'
          AND t.table_type = 'BASE TABLE'
          AND c.table_name NOT IN ('saas_organization', 'user')
        ORDER BY 1
        """,
    )
    return [r[0] for r in cur.fetchall()]


def wipe_tenant3(dc) -> int:
    dc.execute(
        """
        UPDATE "user" u
        SET organization_id = s.other_org
        FROM (
            SELECT uo.user_id, MIN(uo.organization_id) AS other_org
            FROM user_organization uo
            WHERE uo.organization_id <> %s
            GROUP BY uo.user_id
        ) s
        WHERE u.organization_id = %s
          AND u.id = s.user_id
        """,
        (DST_ORG, DST_ORG),
    )

    dc.execute(
        """
        SELECT u.id
        FROM "user" u
        WHERE u.organization_id = %s
          AND NOT EXISTS (
            SELECT 1 FROM user_organization uo
            WHERE uo.user_id = u.id AND uo.organization_id <> %s
          )
        """,
        (DST_ORG, DST_ORG),
    )
    org3_only = [r[0] for r in dc.fetchall()]

    if org3_only:
        if table_exists(dc, "subscription"):
            dc.execute(
                """
                DELETE FROM subscription
                WHERE user_id = ANY(%s)
                   OR payment_id IN (SELECT id FROM payment WHERE user_id = ANY(%s))
                """,
                (org3_only, org3_only),
            )
        if table_exists(dc, "discount_application"):
            dc.execute(
                """
                DELETE FROM discount_application
                WHERE user_id = ANY(%s)
                   OR (payment_id IS NOT NULL
                       AND payment_id IN (SELECT id FROM payment WHERE user_id = ANY(%s)))
                """,
                (org3_only, org3_only),
            )

    if table_exists(dc, "appointment_participant"):
        dc.execute(
            """
            DELETE FROM appointment_participant ap
            WHERE ap.appointment_id IN (
                SELECT id FROM appointment WHERE organization_id = %s
            )
            """,
            (DST_ORG,),
        )
    if table_exists(dc, "appointment"):
        dc.execute(
            "DELETE FROM appointment WHERE organization_id = %s", (DST_ORG,)
        )
    if table_exists(dc, "appointment_slot"):
        dc.execute(
            """
            DELETE FROM appointment_slot s
            WHERE NOT EXISTS (
                SELECT 1 FROM appointment a WHERE a.slot_id = s.id
            )
            AND advisor_id IN (
                SELECT ad.id FROM advisor ad
                JOIN "user" u ON u.id = ad.user_id
                WHERE u.organization_id = %s
            )
            """,
            (DST_ORG,),
        )

    for t, col in USER_FK:
        if not table_exists(dc, t) or t == "user":
            continue
        dc.execute(
            f'DELETE FROM "{t}" AS x USING "user" AS u '
            f"WHERE u.organization_id = %s AND u.id = x.\"{col}\"",
            (DST_ORG,),
        )

    for uid in org3_only:
        for t, col in USER_FK:
            if not table_exists(dc, t) or t == "user":
                continue
            dc.execute(
                f'DELETE FROM "{t}" x WHERE x.\"{col}\" = %s', (uid,)
            )
        for t, col in (
            ("social_auth", "user_id"),
            ("user_communication_preference", "user_id"),
        ):
            if not table_exists(dc, t):
                continue
            dc.execute(
                f'DELETE FROM "{t}" WHERE "{col}" = %s', (uid,)
            )

    orgs = org_id_tables_excluding_user(dc)
    for _ in range(50):
        moved = 0
        for t in orgs:
            if not table_exists(dc, t):
                continue
            # Sin SAVEPOINT, un fallo (orden FK) aborta toda la transacción.
            sp = "sp_ot"
            try:
                dc.execute(f"SAVEPOINT {sp}")
                dc.execute(
                    f'DELETE FROM "{t}" WHERE organization_id = %s', (DST_ORG,)
                )
                n = int(dc.rowcount or 0)
                if n:
                    moved += n
                dc.execute(f"RELEASE SAVEPOINT {sp}")
            except Exception:  # noqa: BLE001
                dc.execute(f"ROLLBACK TO SAVEPOINT {sp}")
        if moved == 0:
            break

    for uid in org3_only:
        for t, col in USER_FK:
            if not table_exists(dc, t):
                continue
            dc.execute(
                f'DELETE FROM "{t}" WHERE "{col}" = %s', (uid,)
            )
        if table_exists(dc, "advisor"):
            dc.execute("DELETE FROM advisor WHERE user_id = %s", (uid,))
    if org3_only:
        dc.execute(
            'DELETE FROM "user" WHERE id = ANY(%s)',
            (org3_only,),
        )
    return len(org3_only)


def insert_org_rows(
    sc, dc, table: str, src: int, dst: int, idmap: dict[int, int] | None
) -> None:
    cols = get_cols(dc, table)
    sels = ",".join(f'"{c}"' for c in cols)
    sc.execute(
        f'SELECT {sels} FROM "{table}" WHERE organization_id = %s ORDER BY id',
        (src,),
    )
    for r in sc.fetchall():
        d = {cols[i]: r[i] for i in range(len(cols))}
        old = d.get("id")
        d.pop("id", None)
        d["organization_id"] = dst
        inc = [c for c in cols if c != "id"]
        vals = [d[c] for c in inc]
        ph = ",".join(["%s"] * len(inc))
        icsv = ",".join(f'"{c}"' for c in inc)
        dc.execute(
            f'INSERT INTO "{table}" ({icsv}) VALUES ({ph}) RETURNING id', vals
        )
        n = dc.fetchone()
        if idmap is not None and n and old is not None and n[0] is not None:
            idmap[int(old)] = int(n[0])


def import_users_and_maps(sc, dc) -> dict[int, int]:
    s_cols = get_cols(sc, "user")
    d_cols = get_cols(dc, "user")
    d_set = set(d_cols)
    sc.execute(
        'SELECT * FROM "user" WHERE organization_id = %s ORDER BY id',
        (SRC_ORG,),
    )
    c_rows = [dict(zip(s_cols, t)) for t in sc.fetchall()]

    uid: dict[int, int] = {}
    for c in c_rows:
        e = (c.get("email") or "").lower().strip()
        if not e:
            continue
        dc.execute("SELECT id FROM \"user\" WHERE lower(trim(email)) = %s", (e,))
        o = dc.fetchone()
        if o:
            uid[int(c["id"])] = int(o[0])
            continue
        payload: dict[str, Any] = {}
        for k in s_cols:
            if k in d_set and k not in ("id",):
                payload[k] = c.get(k)
        payload["organization_id"] = DST_ORG
        if "last_selected_organization_id" in d_set:
            payload["last_selected_organization_id"] = DST_ORG
        k_list = [k for k in d_cols if k != "id" and k in payload]
        vals = [payload[k] for k in k_list]
        ph = ",".join(["%s"] * len(k_list))
        icsv = ",".join(f'"{c}"' for c in k_list)
        dc.execute(
            f'INSERT INTO "user" ({icsv}) VALUES ({ph}) RETURNING id', vals
        )
        n = dc.fetchone()
        uid[int(c["id"])] = int(n[0]) if n and n[0] is not None else 0

    for c_o, d_o in uid.items():
        if d_o and table_exists(dc, "user_organization"):
            dc.execute(
                """
                INSERT INTO user_organization (user_id, organization_id, role, status, created_at)
                VALUES (%s, %s, 'user', 'active', NOW())
                ON CONFLICT (user_id, organization_id) DO NOTHING
                """,
                (d_o, DST_ORG),
            )
    return uid


def _ensure_advisor(
    sc, dc, m_u: dict[int, int], m_adv: dict[int, int]
) -> None:
    sc.execute("SELECT * FROM advisor ORDER BY id")
    cols = [d[0] for d in sc.description]
    for t in sc.fetchall():
        row = {cols[i]: t[i] for i in range(len(cols))}
        aid = int(row["id"])
        c_uid = int(row["user_id"])
        if c_uid not in m_u:
            continue
        d_uid = m_u[c_uid]
        dc.execute("SELECT id FROM advisor WHERE user_id = %s", (d_uid,))
        o = dc.fetchone()
        if o:
            m_adv[aid] = int(o[0])
        else:
            dcols = get_cols(dc, "advisor")
            drow = {k: row.get(k) for k in dcols if k in row and k != "id"}
            drow["user_id"] = d_uid
            icsv = [k for k in dcols if k != "id" and k in drow]
            vls = [drow[k] for k in icsv]
            ph = ",".join(["%s"] * len(icsv))
            cnames = ",".join(f'"{c}"' for c in icsv)
            dc.execute(
                f"INSERT INTO advisor ({cnames}) VALUES ({ph}) RETURNING id",
                vls,
            )
            n0 = dc.fetchone()
            if n0 and n0[0] is not None:
                m_adv[aid] = int(n0[0])


def import_rest(
    sc,
    dc,
    m_u: dict[int, int],
) -> None:
    m_tax: dict[int, int] = {}
    m_apt: dict[int, int] = {}
    m_mpl: dict[int, int] = {}
    m_cac: dict[int, int] = {}
    m_svc: dict[int, int] = {}
    m_cep: dict[int, int] = {}
    m_adv: dict[int, int] = {}
    m_slt: dict[int, int] = {}
    m_ap: dict[int, int] = {}
    m_cat: dict[int, int] = {}

    insert_org_rows(sc, dc, "taxes", SRC_ORG, DST_ORG, m_tax)
    insert_org_rows(sc, dc, "crm_activity_type", SRC_ORG, DST_ORG, m_cac)
    insert_org_rows(sc, dc, "membership_plan", SRC_ORG, DST_ORG, m_mpl)
    insert_org_rows(sc, dc, "appointment_type", SRC_ORG, DST_ORG, m_apt)
    if table_exists(dc, "benefit"):
        insert_org_rows(sc, dc, "benefit", SRC_ORG, DST_ORG, None)
    if table_exists(dc, "service_category"):
        sc.execute(
            """
            SELECT DISTINCT c.id
            FROM service s
            JOIN service_category c ON c.id = s.category_id
            WHERE s.organization_id = %s AND s.category_id IS NOT NULL
            """,
            (SRC_ORG,),
        )
        cids = [r[0] for r in sc.fetchall()]
        ccols = get_cols(dc, "service_category")
        sels = ",".join(f'"{c}"' for c in ccols)
        for cid0 in cids:
            sc.execute(
                f"SELECT {sels} FROM service_category WHERE id = %s", (cid0,)
            )
            r0 = sc.fetchone()
            if not r0:
                continue
            row0 = {ccols[i]: r0[i] for i in range(len(ccols))}
            name = (row0.get("name") or "").strip()
            slug = (row0.get("slug") or "").strip()
            if slug:
                dc.execute(
                    "SELECT id FROM service_category WHERE slug = %s",
                    (slug,),
                )
            else:
                dc.execute("SELECT 1 FROM service_category WHERE false")
            o = dc.fetchone()
            if not o and name:
                dc.execute(
                    "SELECT id FROM service_category WHERE lower(trim(name)) = lower(trim(%s))",
                    (name,),
                )
                o = dc.fetchone()
            if o:
                m_cat[cid0] = int(o[0])
            else:
                inc0 = [c for c in ccols if c in row0 and c != "id"]
                v0 = [row0[c] for c in inc0]
                ph0 = ",".join(["%s"] * len(inc0))
                cnv = ",".join(f'"{c}"' for c in inc0)
                dc.execute(
                    f"INSERT INTO service_category ({cnv}) VALUES ({ph0}) "
                    f"RETURNING id",
                    v0,
                )
                nr = dc.fetchone()
                if nr and nr[0] is not None:
                    m_cat[cid0] = int(nr[0])
    sc.execute(
        "SELECT * FROM service WHERE organization_id = %s ORDER BY id", (SRC_ORG,)
    )
    scols = [d[0] for d in sc.description] if sc.description else []
    for t in sc.fetchall():
        row: dict[str, Any] = {scols[i]: t[i] for i in range(len(scols))}
        oid = row.get("id")
        row["organization_id"] = DST_ORG
        for col, m in (
            ("appointment_type_id", m_apt),
            ("diagnostic_appointment_type_id", m_apt),
            ("default_tax_id", m_tax),
        ):
            if row.get(col) is not None and int(row[col]) in m:
                row[col] = m[int(row[col])]
        c_id = row.get("category_id")
        if c_id is not None and int(c_id) in m_cat:
            row["category_id"] = m_cat[int(c_id)]
        row.pop("id", None)
        dcols = get_cols(dc, "service")
        inc = [c for c in dcols if c in row and c != "id"]
        vals = [row[c] for c in inc]
        ph = ",".join(["%s"] * len(inc))
        icsv = ",".join(f'"{c}"' for c in inc)
        dc.execute(
            f'INSERT INTO "service" ({icsv}) VALUES ({ph}) RETURNING id', vals
        )
        n = dc.fetchone()
        if n and n[0] and oid is not None:
            m_svc[int(oid)] = int(n[0])
    if table_exists(dc, "service_pricing_rule"):
        dcols = get_cols(dc, "service_pricing_rule")
        sc.execute(
            """
            SELECT spr.* FROM service_pricing_rule spr
            JOIN service s ON s.id = spr.service_id
            WHERE s.organization_id = %s
            """,
            (SRC_ORG,),
        )
        srules = [d[0] for d in (sc.description or ())]
        for t in sc.fetchall():
            row = {srules[i]: t[i] for i in range(len(srules))}
            s_id = int(row.get("service_id", 0) or 0)
            if s_id in m_svc:
                row["service_id"] = m_svc[s_id]
            row.pop("id", None)
            inc3 = [c for c in dcols if c in row and c != "id"]
            vls3 = [row[c] for c in inc3]
            if not inc3:
                continue
            ph = ",".join(["%s"] * len(inc3))
            cnames = ",".join(f'"{c}"' for c in inc3)
            dc.execute(
                f"INSERT INTO service_pricing_rule ({cnames}) VALUES ({ph})",
                vls3,
            )
    for tbl in (
        "email_template",
        "organization_settings",
        "workshop_process_stage_config",
    ):
        if table_exists(dc, tbl):
            insert_org_rows(sc, dc, tbl, SRC_ORG, DST_ORG, None)
    if table_exists(dc, "saas_org_module"):
        sc.execute(
            "SELECT * FROM saas_org_module WHERE organization_id = %s ORDER BY id",
            (SRC_ORG,),
        )
        smc = [d[0] for d in (sc.description or ())]
        dsm = get_cols(dc, "saas_org_module")
        for t in sc.fetchall():
            row = {smc[i]: t[i] for i in range(len(smc))}
            row["organization_id"] = DST_ORG
            row.pop("id", None)
            ins = [c for c in dsm if c in row and c != "id"]
            vms = [row[c] for c in ins]
            if not ins:
                continue
            ph = ",".join(["%s"] * len(ins))
            cna = ",".join(f'"{c}"' for c in ins)
            dc.execute(
                f"INSERT INTO saas_org_module ({cna}) VALUES ({ph}) "
                "ON CONFLICT (organization_id, module_id) DO UPDATE "
                "SET enabled = EXCLUDED.enabled, created_at = EXCLUDED.created_at",
                vms,
            )
    if table_exists(dc, "crm_stage"):
        try:
            insert_org_rows(sc, dc, "crm_stage", SRC_ORG, DST_ORG, None)
        except Exception:
            pass
    if table_exists(dc, "crm_lost_reason"):
        try:
            insert_org_rows(sc, dc, "crm_lost_reason", SRC_ORG, DST_ORG, None)
        except Exception:
            pass
    if table_exists(dc, "crm_tag"):
        try:
            insert_org_rows(sc, dc, "crm_tag", SRC_ORG, DST_ORG, None)
        except Exception:
            pass
    if table_exists(dc, "payment_config"):
        try:
            insert_org_rows(sc, dc, "payment_config", SRC_ORG, DST_ORG, None)
        except Exception:
            pass
    if table_exists(dc, "moodle_config"):
        try:
            insert_org_rows(sc, dc, "moodle_config", SRC_ORG, DST_ORG, None)
        except Exception:
            pass
    if table_exists(dc, "email_config"):
        try:
            insert_org_rows(sc, dc, "email_config", SRC_ORG, DST_ORG, None)
        except Exception:
            pass
    insert_org_rows(
        sc, dc, "certificate_events", SRC_ORG, DST_ORG, m_cep
    )
    if table_exists(dc, "quotations"):
        sc.execute(
            "SELECT * FROM quotations WHERE organization_id = %s", (SRC_ORG,)
        )
        qcol = [d[0] for d in (sc.description or ())]
        for t in sc.fetchall():
            r = {qcol[i]: t[i] for i in range(len(qcol))}
            c_id = r.get("customer_id")
            cb = r.get("created_by")
            if c_id in m_u:
                r["customer_id"] = m_u[int(c_id)]
            if cb in m_u:
                r["created_by"] = m_u[int(cb)]
            r["organization_id"] = DST_ORG
            dcols2 = get_cols(dc, "quotations")
            r.pop("id", None)
            inc2 = [c for c in dcols2 if c in r and c != "id"]
            v2 = [r[c] for c in inc2]
            ph2 = ",".join(["%s"] * len(inc2))
            qn = ",".join(f'"{c}"' for c in inc2)
            dc.execute(
                f"INSERT INTO quotations ({qn}) VALUES ({ph2})",
                v2,
            )
    _ensure_advisor(sc, dc, m_u, m_adv)
    if table_exists(dc, "certificate_templates"):
        try:
            insert_org_rows(
                sc, dc, "certificate_templates", SRC_ORG, DST_ORG, None
            )
        except Exception:
            pass
    sc.execute(
        """
        SELECT a.* FROM appointment_slot a
        WHERE a.id IN (
            SELECT slot_id FROM appointment
            WHERE organization_id = %s AND slot_id IS NOT NULL
        )
        """,
        (SRC_ORG,),
    )
    cslot = [d[0] for d in (sc.description or ())]
    for t in sc.fetchall():
        row = {cslot[i]: t[i] for i in range(len(cslot))}
        o_id = int(row.get("id", 0) or 0)
        for col, m in (
            ("appointment_type_id", m_apt),
        ):
            if row.get(col) and int(row[col] or 0) in m_apt:
                row[col] = m_apt[int(row[col] or 0)]
        a_old = int(row.get("advisor_id") or 0)
        if a_old in m_adv:
            row["advisor_id"] = m_adv[a_old]
        cby = row.get("created_by")
        if cby in m_u:
            row["created_by"] = m_u[int(cby)]
        row.pop("id", None)
        dct = get_cols(dc, "appointment_slot")
        inc2 = [c for c in dct if c in row and c != "id"]
        v2 = [row[c] for c in inc2]
        if not v2 or not inc2:
            continue
        ph2 = ",".join(["%s"] * len(inc2))
        sn = ",".join(f'"{c}"' for c in inc2)
        dc.execute(
            f"INSERT INTO appointment_slot ({sn}) VALUES ({ph2}) "
            f"RETURNING id",
            v2,
        )
        r2 = dc.fetchone()
        if o_id and r2 and r2[0]:
            m_slt[o_id] = int(r2[0])
    sc.execute(
        "SELECT * FROM appointment WHERE organization_id = %s",
        (SRC_ORG,),
    )
    acol = [d[0] for d in (sc.description or ())]
    for t in sc.fetchall():
        r = {acol[i]: t[i] for i in range(len(acol))}
        a_old = int(r.get("id", 0) or 0)
        r["organization_id"] = DST_ORG
        u_in = r.get("user_id")
        if u_in in m_u:
            r["user_id"] = m_u[int(u_in or 0)]
        if r.get("service_id") in m_svc:
            r["service_id"] = m_svc[int(r.get("service_id", 0) or 0)]
        for col, m in (("appointment_type_id", m_apt),):
            v = r.get(col)
            if v is not None and int(v) in m_apt:
                r[col] = m_apt[int(v)]
        adv_id = r.get("advisor_id")
        if adv_id in m_adv:
            r["advisor_id"] = m_adv[int(adv_id or 0)]
        slt = r.get("slot_id")
        if slt in m_slt:
            r["slot_id"] = m_slt[int(slt or 0)]
        r.pop("id", None)
        a_ct = get_cols(dc, "appointment")
        a_inc = [c for c in a_ct if c in r and c != "id"]
        a_vl = [r[c] for c in a_inc]
        ph2 = ",".join(["%s"] * len(a_inc))
        an = ",".join(f'"{c}"' for c in a_inc)
        dc.execute(
            f"INSERT INTO appointment ({an}) VALUES ({ph2}) "
            f"RETURNING id",
            a_vl,
        )
        a_n = dc.fetchone()
        if a_old and a_n and a_n[0]:
            m_ap[a_old] = int(a_n[0])
    if table_exists(dc, "certificates"):
        sc.execute(
            """
            SELECT c.* FROM certificates c
            JOIN "user" u ON u.id = c.user_id
            WHERE u.organization_id = %s
            """,
            (SRC_ORG,),
        )
        ccol = [d[0] for d in (sc.description or ())]
        for t in sc.fetchall():
            r = {ccol[i]: t[i] for i in range(len(ccol))}
            u_in = r.get("user_id")
            if u_in in m_u:
                r["user_id"] = m_u[int(u_in or 0)]
            cei = r.get("certificate_event_id")
            if cei in m_cep:
                r["certificate_event_id"] = m_cep[int(cei or 0)]
            r.pop("id", None)
            d2 = get_cols(dc, "certificates")
            inc2 = [c for c in d2 if c in r and c != "id"]
            v2 = [r[c] for c in inc2]
            if not v2:
                continue
            ph2 = ",".join(["%s"] * len(inc2))
            cn = ",".join(f'"{c}"' for c in inc2)
            try:
                dc.execute(
                    f"INSERT INTO certificates ({cn}) VALUES ({ph2})",
                    v2,
                )
            except Exception as e:  # noqa: BLE001
                print("WARN cert", e, file=sys.stderr)
    if table_exists(dc, "user_organization"):
        sc.execute(
            "SELECT * FROM user_organization WHERE organization_id = %s", (SRC_ORG,)
        )
        uo_col = [d[0] for d in (sc.description or ())]
        for t in sc.fetchall():
            r2 = {uo_col[i]: t[i] for i in range(len(uo_col))}
            if r2.get("user_id") in m_u:
                r2["user_id"] = m_u[int(r2.get("user_id", 0) or 0)]
            r2["organization_id"] = DST_ORG
            r2.pop("id", None)
            c3 = [c for c in get_cols(dc, "user_organization") if c in r2 and c != "id"]
            v3 = [r2[c] for c in c3]
            if not c3:
                continue
            ph2 = ",".join(["%s"] * len(c3))
            c3q = ",".join(f'"{c}"' for c in c3)
            try:
                dc.execute(
                    f"INSERT INTO user_organization ({c3q}) VALUES ({ph2}) "
                    f"ON CONFLICT (user_id, organization_id) DO UPDATE SET role = EXCLUDED.role",
                    v3,
                )
            except Exception:  # noqa: BLE001
                dc.execute(
                    f"INSERT INTO user_organization ({c3q}) VALUES ({ph2}) "
                    f"ON CONFLICT (user_id, organization_id) DO NOTHING",
                    v3,
                )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="Commit (sin esto, rollback)")
    args = ap.parse_args()
    dst_dsn, src_dsn = _resolve_dsns()
    dev = psycopg2.connect(dst_dsn)
    cl = psycopg2.connect(src_dsn)
    try:
        dev.autocommit = False
        cl.autocommit = True
        dc = dev.cursor()
        sc = cl.cursor()
        dc.execute("SELECT 1 FROM saas_organization WHERE id = %s", (DST_ORG,))
        if not dc.fetchone():
            print("Falta saas_organization id=3", file=sys.stderr)
            return 1
        n = wipe_tenant3(dc)
        print("Usuarios eliminados (solo-tenant-3):", n)
        m_u = import_users_and_maps(sc, dc)
        import_rest(sc, dc, m_u)
        if not args.apply:
            dev.rollback()
            print("ROLBACK: ejecutar con --apply para fijar cambios.")
        else:
            dev.commit()
            print("COMMIT hecho.")
    except Exception as e:  # noqa: BLE001
        dev.rollback()
        print("ERROR", e, file=sys.stderr)
        return 1
    finally:
        try:
            cl.close()
            dev.close()
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
