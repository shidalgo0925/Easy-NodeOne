#!/usr/bin/env python3
"""
Crea o actualiza (upsert) el servicio de catálogo tipo CV_REGISTRATION a partir de un JSON.

Uso (desde el directorio backend, misma DB que Gunicorn):
  cd /opt/easynodeone/app/backend
  ../.venv/bin/python scripts/seed_cv_registration_service.py --config ../config/seed_cv_registration_service.json --dry-run
  ../.venv/bin/python scripts/seed_cv_registration_service.py --config ../config/seed_cv_registration_service.json

Por defecto busca la config en ../config/seed_cv_registration_service.json;
si no existe, usa ../config/seed_cv_registration_service.example.json (solo lectura de ejemplo).

Clave de upsert: organization_id + program_slug (y service_type CV_REGISTRATION).
Si ya existe un CV_REGISTRATION en la org sin program_slug, se reutiliza una única fila y se le asigna program_slug.
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
BACKEND = HERE.parent
ROOT = BACKEND.parent


def _default_db_path() -> Path:
    env = (os.environ.get("NODEONE_DATABASE_PATH") or "").strip()
    if env:
        return Path(env)
    return ROOT / "instance" / "NodeOne.db"


def _load_config(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _bool_sql(v) -> int:
    return 1 if v else 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Seed servicio CV_REGISTRATION desde JSON.")
    ap.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Ruta al JSON (defecto: config/seed_cv_registration_service.json o .example.json)",
    )
    ap.add_argument("--db", type=Path, default=None, help="Ruta a SQLite (defecto: instance/NodeOne.db)")
    ap.add_argument("--dry-run", action="store_true", help="Solo mostrar acción, sin escribir en BD")
    args = ap.parse_args()

    cfg_path = args.config
    if cfg_path is None:
        p1 = ROOT / "config" / "seed_cv_registration_service.json"
        p2 = ROOT / "config" / "seed_cv_registration_service.example.json"
        cfg_path = p1 if p1.is_file() else p2
    if not cfg_path.is_file():
        print(f"❌ No se encuentra el archivo de configuración: {cfg_path}", file=sys.stderr)
        return 1

    data = _load_config(cfg_path)
    if "_comment" in data:
        del data["_comment"]

    org_id = int(data["organization_id"])
    program_slug = (data.get("program_slug") or "").strip()
    if not program_slug:
        print("❌ program_slug es obligatorio en el JSON.", file=sys.stderr)
        return 1

    svc = data["service"]
    service_type = (svc.get("service_type") or "CV_REGISTRATION").strip().upper()
    if service_type != "CV_REGISTRATION":
        print("❌ service.service_type debe ser CV_REGISTRATION.", file=sys.stderr)
        return 1

    db_path = args.db or _default_db_path()
    if not db_path.is_file():
        print(f"❌ No existe la base de datos: {db_path}", file=sys.stderr)
        return 1

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    fields = {
        "name": svc["name"],
        "description": svc.get("description") or "",
        "icon": svc.get("icon") or "fas fa-file-alt",
        "membership_type": svc.get("membership_type") or "basic",
        "category_id": svc.get("category_id"),
        "external_link": svc.get("external_link") or "",
        "base_price": float(svc.get("base_price") or 0),
        "is_active": _bool_sql(svc.get("is_active", True)),
        "display_order": int(svc.get("display_order") or 0),
        "service_type": service_type,
        "requires_diagnostic_appointment": _bool_sql(svc.get("requires_diagnostic_appointment", False)),
        "requires_payment_before_appointment": _bool_sql(svc.get("requires_payment_before_appointment", False)),
        "program_slug": program_slug,
        "organization_id": org_id,
        "updated_at": now,
    }

    con = sqlite3.connect(str(db_path))
    cur = con.cursor()

    cur.execute(
        "SELECT id FROM service WHERE organization_id = ? AND program_slug = ?",
        (org_id, program_slug),
    )
    row = cur.fetchone()
    service_id = row[0] if row else None

    if service_id is None:
        cur.execute(
            """
            SELECT id FROM service
            WHERE organization_id = ? AND service_type = 'CV_REGISTRATION'
              AND (program_slug IS NULL OR program_slug = '')
            """,
            (org_id,),
        )
        legacy = cur.fetchall()
        if len(legacy) == 1:
            service_id = legacy[0][0]
        elif len(legacy) > 1:
            print(
                "❌ Hay más de un servicio CV_REGISTRATION sin program_slug; asigne program_slug a mano o limpie duplicados.",
                file=sys.stderr,
            )
            return 1

    if args.dry_run:
        if service_id:
            print(f"[dry-run] UPDATE service id={service_id} org={org_id} program_slug={program_slug!r}")
        else:
            print(f"[dry-run] INSERT service org={org_id} program_slug={program_slug!r}")
        print(json.dumps(fields, indent=2, ensure_ascii=False))
        return 0

    if service_id:
        cur.execute(
            """
            UPDATE service SET
              name=?, description=?, icon=?, membership_type=?, category_id=?,
              external_link=?, base_price=?, is_active=?, display_order=?,
              service_type=?, requires_diagnostic_appointment=?,
              requires_payment_before_appointment=?, program_slug=?,
              organization_id=?, updated_at=?
            WHERE id=?
            """,
            (
                fields["name"],
                fields["description"],
                fields["icon"],
                fields["membership_type"],
                fields["category_id"],
                fields["external_link"],
                fields["base_price"],
                fields["is_active"],
                fields["display_order"],
                fields["service_type"],
                fields["requires_diagnostic_appointment"],
                fields["requires_payment_before_appointment"],
                fields["program_slug"],
                fields["organization_id"],
                fields["updated_at"],
                service_id,
            ),
        )
        print(f"✅ Actualizado service id={service_id} (program_slug={program_slug}).")
    else:
        cur.execute(
            """
            INSERT INTO service (
              name, description, icon, membership_type, category_id, external_link,
              base_price, is_active, display_order, service_type,
              requires_diagnostic_appointment, diagnostic_appointment_type_id,
              appointment_type_id, requires_payment_before_appointment,
              deposit_amount, deposit_percentage, created_at, updated_at,
              organization_id, default_tax_id, program_slug
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                fields["name"],
                fields["description"],
                fields["icon"],
                fields["membership_type"],
                fields["category_id"],
                fields["external_link"],
                fields["base_price"],
                fields["is_active"],
                fields["display_order"],
                fields["service_type"],
                fields["requires_diagnostic_appointment"],
                None,
                None,
                fields["requires_payment_before_appointment"],
                None,
                None,
                now,
                now,
                fields["organization_id"],
                None,
                fields["program_slug"],
            ),
        )
        print(f"✅ Insertado service id={cur.lastrowid} (program_slug={program_slug}).")

    con.commit()
    con.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
