#!/usr/bin/env python3
"""
Importa plantillas desde una o más bases SQLite (otras instancias / backups / legado)
hacia la base NodeOne configurada en la app (SQLALCHEMY_DATABASE_URI o instance/NodeOne.db).

Tablas soportadas si existen en el origen:
  - email_template
  - appointment_email_template  (requiere tipos de cita equivalentes por nombre en el org destino)
  - marketing_email_templates
  - certificate_templates

Uso:
  python3 import_templates_from_sqlite.py /ruta/backup.db [/otra.db ...]
  python3 import_templates_from_sqlite.py --sources /a.db,/b.db --to-org 1 --overwrite
  NODEONE_TEMPLATE_SOURCES=/a.db,/b.db python3 import_templates_from_sqlite.py --dry-run

  --preserve-org   Usa organization_id del origen solo si existe en saas_organization destino;
                   si no, aplica --to-org (default 1).
  --to-org N       organization_id destino cuando no se preserva (default 1).
"""
from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def _table_exists(conn: sqlite3.Connection, name: str) -> bool:
    r = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1", (name,)
    ).fetchone()
    return r is not None


def _resolve_org_id(
    dest_org_ids: set[int],
    source_org_id: int,
    to_org: int,
    preserve_org: bool,
) -> int | None:
    if preserve_org and source_org_id in dest_org_ids:
        return int(source_org_id)
    if preserve_org and source_org_id not in dest_org_ids:
        return int(to_org)
    return int(to_org)


def _map_appointment_type(
    src: sqlite3.Connection,
    src_org: int,
    dst_org: int,
    src_type_id: int,
    AppointmentType,
) -> int | None:
    row = src.execute(
        "SELECT name FROM appointment_type WHERE id = ? AND organization_id = ?",
        (int(src_type_id), int(src_org)),
    ).fetchone()
    if not row:
        return None
    name = row[0]
    at = AppointmentType.query.filter_by(organization_id=int(dst_org), name=name).first()
    return int(at.id) if at else None


def run_import(
    source_paths: list[str],
    *,
    to_org: int,
    preserve_org: bool,
    overwrite: bool,
    dry_run: bool,
    skip_appointment: bool,
) -> int:
    from app import (
        AppointmentEmailTemplate,
        AppointmentType,
        CertificateTemplate,
        EmailTemplate,
        MarketingTemplate,
        SaasOrganization,
        app,
        db,
    )

    source_paths = [p for p in source_paths if p.strip()]
    if not source_paths:
        print("Indicá al menos una ruta .db (argumentos o NODEONE_TEMPLATE_SOURCES).", file=sys.stderr)
        return 1

    for p in source_paths:
        if not os.path.isfile(p):
            print(f"No existe el archivo: {p}", file=sys.stderr)
            return 1

    with app.app_context():
        dest_org_ids = {int(r.id) for r in SaasOrganization.query.with_entities(SaasOrganization.id).all()}
        if to_org not in dest_org_ids:
            print(f"--to-org {to_org} no existe en saas_organization destino.", file=sys.stderr)
            return 1

        stats = {
            "email_template": {"inserted": 0, "updated": 0, "skipped": 0},
            "appointment_email_template": {"inserted": 0, "updated": 0, "skipped": 0},
            "marketing_email_templates": {"inserted": 0, "updated": 0, "skipped": 0},
            "certificate_templates": {"inserted": 0, "updated": 0, "skipped": 0},
        }

        for src_path in source_paths:
            print(f"\n=== Origen: {src_path} ===")
            src = sqlite3.connect(f"file:{src_path}?mode=ro", uri=True)
            src.row_factory = sqlite3.Row

            if _table_exists(src, "email_template"):
                rows = src.execute("SELECT * FROM email_template").fetchall()
                for r in rows:
                    d = dict(r)
                    src_oid = int(d.get("organization_id") or to_org)
                    oid = _resolve_org_id(dest_org_ids, src_oid, to_org, preserve_org)
                    if oid not in dest_org_ids:
                        print(f"  skip email_template key={d.get('template_key')}: org {oid} inválido")
                        stats["email_template"]["skipped"] += 1
                        continue
                    key = (d.get("template_key") or "").strip() or None
                    if not key:
                        stats["email_template"]["skipped"] += 1
                        continue
                    existing = EmailTemplate.query.filter_by(
                        organization_id=oid, template_key=key
                    ).first()
                    if existing:
                        if not overwrite:
                            stats["email_template"]["skipped"] += 1
                            continue
                        if dry_run:
                            stats["email_template"]["updated"] += 1
                            continue
                        existing.name = d.get("name") or existing.name
                        existing.subject = d.get("subject") or existing.subject
                        existing.html_content = d.get("html_content") or ""
                        existing.text_content = d.get("text_content")
                        existing.category = d.get("category")
                        existing.is_custom = bool(d.get("is_custom"))
                        existing.variables = d.get("variables")
                        existing.updated_at = datetime.utcnow()
                        stats["email_template"]["updated"] += 1
                    else:
                        if dry_run:
                            stats["email_template"]["inserted"] += 1
                            continue
                        db.session.add(
                            EmailTemplate(
                                organization_id=oid,
                                template_key=key,
                                name=d.get("name") or key,
                                subject=d.get("subject") or "",
                                html_content=d.get("html_content") or "",
                                text_content=d.get("text_content"),
                                category=d.get("category"),
                                is_custom=bool(d.get("is_custom")),
                                variables=d.get("variables"),
                            )
                        )
                        stats["email_template"]["inserted"] += 1
                print(f"  email_template: {len(rows)} filas leídas")
            else:
                print("  (sin tabla email_template)")

            if not skip_appointment and _table_exists(src, "appointment_email_template"):
                rows = src.execute("SELECT * FROM appointment_email_template").fetchall()
                for r in rows:
                    d = dict(r)
                    src_oid = int(d.get("organization_id") or to_org)
                    oid = _resolve_org_id(dest_org_ids, src_oid, to_org, preserve_org)
                    src_at = int(d["appointment_type_id"])
                    dst_at = _map_appointment_type(src, src_oid, oid, src_at, AppointmentType)
                    if dst_at is None:
                        stats["appointment_email_template"]["skipped"] += 1
                        continue
                    key = (d.get("template_key") or "").strip()
                    if not key:
                        stats["appointment_email_template"]["skipped"] += 1
                        continue
                    ex = AppointmentEmailTemplate.query.filter_by(
                        organization_id=oid,
                        appointment_type_id=dst_at,
                        template_key=key,
                    ).first()
                    if ex:
                        if not overwrite:
                            stats["appointment_email_template"]["skipped"] += 1
                            continue
                        if dry_run:
                            stats["appointment_email_template"]["updated"] += 1
                            continue
                        ex.name = d.get("name")
                        ex.subject = d.get("subject") or ex.subject
                        ex.html_content = d.get("html_content") or ""
                        ex.is_custom = bool(d.get("is_custom"))
                        ex.updated_at = datetime.utcnow()
                        stats["appointment_email_template"]["updated"] += 1
                    else:
                        if dry_run:
                            stats["appointment_email_template"]["inserted"] += 1
                            continue
                        db.session.add(
                            AppointmentEmailTemplate(
                                organization_id=oid,
                                appointment_type_id=dst_at,
                                template_key=key,
                                name=d.get("name"),
                                subject=d.get("subject") or "",
                                html_content=d.get("html_content") or "",
                                is_custom=bool(d.get("is_custom")),
                            )
                        )
                        stats["appointment_email_template"]["inserted"] += 1
                print(f"  appointment_email_template: {len(rows)} filas leídas")
            elif not skip_appointment:
                print("  (sin tabla appointment_email_template)")

            if _table_exists(src, "marketing_email_templates"):
                rows = src.execute("SELECT * FROM marketing_email_templates").fetchall()
                for r in rows:
                    d = dict(r)
                    name = (d.get("name") or "").strip() or "importado"
                    html = d.get("html") or ""
                    ex = MarketingTemplate.query.filter_by(name=name).first()
                    if ex:
                        if not overwrite:
                            stats["marketing_email_templates"]["skipped"] += 1
                            continue
                        if dry_run:
                            stats["marketing_email_templates"]["updated"] += 1
                            continue
                        ex.html = html
                        ex.variables = d.get("variables")
                        stats["marketing_email_templates"]["updated"] += 1
                    else:
                        if dry_run:
                            stats["marketing_email_templates"]["inserted"] += 1
                            continue
                        db.session.add(
                            MarketingTemplate(
                                name=name,
                                html=html,
                                variables=d.get("variables"),
                            )
                        )
                        stats["marketing_email_templates"]["inserted"] += 1
                print(f"  marketing_email_templates: {len(rows)} filas leídas")
            else:
                print("  (sin tabla marketing_email_templates)")

            if _table_exists(src, "certificate_templates"):
                rows = src.execute("SELECT * FROM certificate_templates").fetchall()
                for r in rows:
                    d = dict(r)
                    src_oid = int(d.get("organization_id") or to_org)
                    oid = _resolve_org_id(dest_org_ids, src_oid, to_org, preserve_org)
                    if oid not in dest_org_ids:
                        stats["certificate_templates"]["skipped"] += 1
                        continue
                    cname = (d.get("name") or "").strip() or "certificado"
                    ex = CertificateTemplate.query.filter_by(organization_id=oid, name=cname).first()
                    if ex:
                        if not overwrite:
                            stats["certificate_templates"]["skipped"] += 1
                            continue
                        if dry_run:
                            stats["certificate_templates"]["updated"] += 1
                            continue
                        ex.width = int(d.get("width") or ex.width)
                        ex.height = int(d.get("height") or ex.height)
                        ex.background_image = d.get("background_image")
                        ex.json_layout = d.get("json_layout")
                        ex.updated_at = datetime.utcnow()
                        stats["certificate_templates"]["updated"] += 1
                    else:
                        if dry_run:
                            stats["certificate_templates"]["inserted"] += 1
                            continue
                        db.session.add(
                            CertificateTemplate(
                                organization_id=oid,
                                name=cname,
                                width=int(d.get("width") or 1200),
                                height=int(d.get("height") or 900),
                                background_image=d.get("background_image"),
                                json_layout=d.get("json_layout"),
                            )
                        )
                        stats["certificate_templates"]["inserted"] += 1
                print(f"  certificate_templates: {len(rows)} filas leídas")
            else:
                print("  (sin tabla certificate_templates)")

            src.close()

        if dry_run:
            db.session.rollback()
            print("\n[DRY-RUN] sin commit")
        else:
            db.session.commit()
            print("\n✅ Commit aplicado")

        print("\nResumen:")
        for t, s in stats.items():
            if sum(s.values()):
                print(f"  {t}: {s}")

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Importar plantillas desde SQLite(s) a NodeOne.")
    parser.add_argument(
        "paths",
        nargs="*",
        help="Rutas a archivos .db origen",
    )
    parser.add_argument(
        "--sources",
        default="",
        help="Lista separada por comas (alternativa a paths)",
    )
    parser.add_argument("--to-org", type=int, default=1, help="organization_id destino (default 1)")
    parser.add_argument(
        "--preserve-org",
        action="store_true",
        help="Mantener organization_id del origen si existe en destino; si no, usar --to-org",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Sobrescribir filas que chocan por clave única / nombre",
    )
    parser.add_argument("--dry-run", action="store_true", help="No escribe en la BD")
    parser.add_argument(
        "--skip-appointment",
        action="store_true",
        help="No importar appointment_email_template",
    )
    args = parser.parse_args()

    env_src = (os.environ.get("NODEONE_TEMPLATE_SOURCES") or "").strip()
    paths = list(args.paths)
    if args.sources.strip():
        paths.extend([x.strip() for x in args.sources.split(",") if x.strip()])
    if env_src:
        paths.extend([x.strip() for x in env_src.split(",") if x.strip()])

    return run_import(
        paths,
        to_org=args.to_org,
        preserve_org=args.preserve_org,
        overwrite=args.overwrite,
        dry_run=args.dry_run,
        skip_appointment=args.skip_appointment,
    )


if __name__ == "__main__":
    raise SystemExit(main())
