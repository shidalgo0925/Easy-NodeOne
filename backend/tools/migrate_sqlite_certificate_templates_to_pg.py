#!/usr/bin/env python3
"""
Migración SQLite → PostgreSQL: plantillas de certificado (certificate_templates)
y eventos de certificado (certificate_events).

El script principal migrate_sqlite_members_events_to_pg.py NO migra estas tablas;
Relatic (y otros) pueden ejecutar este script después del principal.

Uso (desde backend/):
  python3 tools/migrate_sqlite_certificate_templates_to_pg.py \\
    --sqlite /ruta/backup.db \\
    --dotenv /opt/easynodeone/relatic/.env \\
    --organization-id 1

Sin --apply: solo conteos SQLite vs PG.

Archivos: json_layout y background_image suelen referenciar
  /static/uploads/certificates/<archivo>
Esos binarios NO están en el .db: copiarlos desde el origen al static del despliegue
(ver mensaje al final con --apply).

No usa Flask; solo SQLAlchemy + sqlite3 + dotenv.
"""
from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from pathlib import Path

from sqlalchemy import create_engine, text


def _load_dotenv(path: Path) -> None:
    try:
        from dotenv import load_dotenv

        load_dotenv(path, override=True)
    except ImportError:
        pass


def _sqlite_table(slc: sqlite3.Connection, names: tuple[str, ...]) -> str | None:
    for n in names:
        r = slc.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=? LIMIT 1",
            (n,),
        ).fetchone()
        if r:
            return n
    return None


def _sync_sequence(conn, table: str, pk: str = "id") -> None:
    seq = conn.execute(
        text("SELECT pg_get_serial_sequence(:tbl, :pk)"),
        {"tbl": table, "pk": pk},
    ).scalar()
    if not seq:
        return
    mx = conn.execute(text(f'SELECT COALESCE(MAX("{pk}"), 1) FROM "{table}"')).scalar()
    conn.execute(text("SELECT setval(:seq, :mx, true)"), {"seq": seq, "mx": int(mx)})


def _fk_int(conn, table: str, idv: int | None) -> int | None:
    if idv is None:
        return None
    try:
        i = int(idv)
    except (TypeError, ValueError):
        return None
    r = conn.execute(text(f'SELECT 1 FROM "{table}" WHERE id = :id LIMIT 1'), {"id": i}).fetchone()
    return i if r else None


def print_summary(sqlite_path: Path, database_url: str) -> None:
    sl = sqlite3.connect(str(sqlite_path))
    eng = create_engine(database_url, future=True)
    pairs = [
        ("certificate_templates", "certificate_templates"),
        ("certificate_events", "certificate_events"),
    ]
    print("\n--- Certificados: filas SQLite vs PG ---")
    print(f"{'Tabla':<32} {'SQLite':>10} {'PG':>10}")
    with eng.connect() as c:
        for sl_t, pg_t in pairs:
            tname = _sqlite_table(sl, (sl_t,))
            try:
                s_n = int(sl.execute(f'SELECT COUNT(*) FROM "{tname}"').fetchone()[0]) if tname else 0
            except sqlite3.Error:
                s_n = -1
            try:
                p_n = int(c.execute(text(f'SELECT COUNT(*) FROM "{pg_t}"')).scalar() or 0)
            except Exception:
                p_n = -1
            print(f"{sl_t or '(ausente)':<32} {s_n:>10} {p_n:>10}")
    sl.close()


def migrate_templates(slc: sqlite3.Connection, conn, org_id: int) -> int:
    t = _sqlite_table(slc, ("certificate_templates",))
    if not t:
        print("SQLite: sin tabla certificate_templates; nada que migrar.")
        return 0
    cur = slc.execute(f'SELECT * FROM "{t}" ORDER BY id')
    cols = [d[0] for d in cur.description]
    n = 0
    for row in cur.fetchall():
        d = dict(zip(cols, row))
        tid = int(d["id"])
        name = (d.get("name") or f"Plantilla {tid}")[:200]
        width = int(d.get("width") or 1200)
        height = int(d.get("height") or 900)
        bg = d.get("background_image")
        if bg is not None:
            bg = str(bg)[:500]
        jl = d.get("json_layout")
        if jl is not None and not isinstance(jl, str):
            jl = str(jl)
        conn.execute(
            text(
                """
                INSERT INTO certificate_templates (
                    id, organization_id, name, width, height, background_image, json_layout,
                    created_at, updated_at
                ) VALUES (
                    :id, :oid, :name, :w, :h, :bg, :jl,
                    COALESCE(:ca, NOW()), COALESCE(:ua, NOW())
                )
                ON CONFLICT (id) DO UPDATE SET
                    organization_id = EXCLUDED.organization_id,
                    name = EXCLUDED.name,
                    width = EXCLUDED.width,
                    height = EXCLUDED.height,
                    background_image = EXCLUDED.background_image,
                    json_layout = EXCLUDED.json_layout,
                    updated_at = EXCLUDED.updated_at
                """
            ),
            {
                "id": tid,
                "oid": org_id,
                "name": name,
                "w": width,
                "h": height,
                "bg": bg,
                "jl": jl,
                "ca": d.get("created_at"),
                "ua": d.get("updated_at"),
            },
        )
        n += 1
    _sync_sequence(conn, "certificate_templates")
    print(f"certificate_templates: {n} filas upsert.")
    return n


def migrate_events(slc: sqlite3.Connection, conn, org_id: int) -> int:
    t = _sqlite_table(slc, ("certificate_events",))
    if not t:
        print("SQLite: sin tabla certificate_events; omitido.")
        return 0
    cur = slc.execute(f'SELECT * FROM "{t}" ORDER BY id')
    cols = [d[0] for d in cur.description]
    n = 0
    for row in cur.fetchall():
        d = dict(zip(cols, row))
        eid = int(d["id"])
        tpl_raw = d.get("template_id")
        tpl_id = int(tpl_raw) if tpl_raw is not None else None
        if tpl_id is not None:
            r = conn.execute(
                text("SELECT 1 FROM certificate_templates WHERE id = :id LIMIT 1"),
                {"id": tpl_id},
            ).fetchone()
            if not r:
                tpl_id = None

        mem_id = _fk_int(conn, "membership_plan", d.get("membership_required_id"))
        ev_id = _fk_int(conn, "event", d.get("event_required_id"))

        conn.execute(
            text(
                """
                INSERT INTO certificate_events (
                    id, organization_id, name, start_date, end_date, duration_hours,
                    institution, convenio, rector_name, academic_director_name, partner_organization,
                    logo_left_url, logo_right_url, seal_url, background_url,
                    membership_required_id, event_required_id, template_html, template_id,
                    is_active, verification_enabled, code_prefix, created_at
                ) VALUES (
                    :id, :oid, :name, :sd, :ed, :dh,
                    :inst, :conv, :rec, :adir, :partner,
                    :ll, :lr, :seal, :bgu,
                    :mem, :evr, :thtml, :tid,
                    COALESCE(:act, true), COALESCE(:ver, true), COALESCE(:pref, 'REL'), COALESCE(:ca, NOW())
                )
                ON CONFLICT (id) DO UPDATE SET
                    organization_id = EXCLUDED.organization_id,
                    name = EXCLUDED.name,
                    start_date = EXCLUDED.start_date,
                    end_date = EXCLUDED.end_date,
                    duration_hours = EXCLUDED.duration_hours,
                    institution = EXCLUDED.institution,
                    convenio = EXCLUDED.convenio,
                    rector_name = EXCLUDED.rector_name,
                    academic_director_name = EXCLUDED.academic_director_name,
                    partner_organization = EXCLUDED.partner_organization,
                    logo_left_url = EXCLUDED.logo_left_url,
                    logo_right_url = EXCLUDED.logo_right_url,
                    seal_url = EXCLUDED.seal_url,
                    background_url = EXCLUDED.background_url,
                    membership_required_id = EXCLUDED.membership_required_id,
                    event_required_id = EXCLUDED.event_required_id,
                    template_html = EXCLUDED.template_html,
                    template_id = EXCLUDED.template_id,
                    is_active = EXCLUDED.is_active,
                    verification_enabled = EXCLUDED.verification_enabled,
                    code_prefix = EXCLUDED.code_prefix
                """
            ),
            {
                "id": eid,
                "oid": org_id,
                "name": (d.get("name") or f"Evento {eid}")[:200],
                "sd": d.get("start_date"),
                "ed": d.get("end_date"),
                "dh": d.get("duration_hours"),
                "inst": (d.get("institution") or None),
                "conv": (d.get("convenio") or None),
                "rec": (d.get("rector_name") or None),
                "adir": (d.get("academic_director_name") or None),
                "partner": (d.get("partner_organization") or None),
                "ll": (str(d.get("logo_left_url"))[:500] if d.get("logo_left_url") else None),
                "lr": (str(d.get("logo_right_url"))[:500] if d.get("logo_right_url") else None),
                "seal": (str(d.get("seal_url"))[:500] if d.get("seal_url") else None),
                "bgu": (str(d.get("background_url"))[:500] if d.get("background_url") else None),
                "mem": mem_id,
                "evr": ev_id,
                "thtml": d.get("template_html"),
                "tid": tpl_id,
                "act": d.get("is_active"),
                "ver": d.get("verification_enabled"),
                "pref": (str(d.get("code_prefix") or "REL")[:20]),
                "ca": d.get("created_at"),
            },
        )
        n += 1
    _sync_sequence(conn, "certificate_events")
    print(f"certificate_events: {n} filas upsert (FKs event/plan ausentes en PG → NULL).")
    return n


def main() -> int:
    ap = argparse.ArgumentParser(description="Migrar plantillas y eventos de certificado SQLite → PG.")
    ap.add_argument("--sqlite", required=True, type=Path, help="Ruta al .db SQLite (backup).")
    ap.add_argument("--dotenv", type=Path, help="Cargar DATABASE_URL (p. ej. /opt/easynodeone/relatic/.env).")
    ap.add_argument("--organization-id", type=int, default=1, help="saas_organization.id en PG para las filas.")
    ap.add_argument("--apply", action="store_true", help="Escribir en PostgreSQL.")
    args = ap.parse_args()

    if not args.sqlite.is_file():
        print(f"No existe: {args.sqlite}", file=sys.stderr)
        return 1

    if args.dotenv:
        _load_dotenv(args.dotenv)
    else:
        _load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

    url = os.environ.get("DATABASE_URL")
    if not url:
        print("DATABASE_URL no definido.", file=sys.stderr)
        return 1

    if not args.apply:
        print_summary(args.sqlite, url)
        print("\nPara aplicar: mismo comando con --apply (tras backup de PG).")
        return 0

    org_id = int(args.organization_id)
    sl = sqlite3.connect(str(args.sqlite))
    eng = create_engine(url, future=True)
    with eng.begin() as conn:
        migrate_templates(sl, conn, org_id)
        migrate_events(sl, conn, org_id)
    sl.close()

    print(
        "\nArchivos: copiá al servidor Relatic los ficheros bajo static/uploads/certificates/ "
        "referenciados en background_image / URLs de los eventos, si existían en el entorno origen.\n"
        "Ej.: rsync -av ORIGEN/static/uploads/certificates/ /opt/easynodeone/relatic/app/static/uploads/certificates/"
    )
    print("OK.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
