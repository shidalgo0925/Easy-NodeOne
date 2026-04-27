#!/usr/bin/env python3
r"""
Muestra por qué /inscripcion/<slug> no encuentra programa (misma lógica que en producción).

Uso (desde app/backend, con la **misma** DATABASE_URL que el proceso de apps.relatic.org):

  python3 scripts/diagnose_inscripcion_relatic.py
  python3 scripts/diagnose_inscripcion_relatic.py curso-redaccion-cientifica-publicacion-revistas
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DEFAULT_SLUG = "curso-redaccion-cientifica-publicacion-revistas"


def main() -> int:
    slug = (sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SLUG).strip().lower()
    if not slug:
        return 2

    from app import _organization_id_from_request_host, AcademicProgram, app, db
    from models.saas import SaasOrganization
    from nodeone.modules.academic_enrollment import service as aes

    with app.app_context():
        dbs = (os.environ.get("DATABASE_URL") or os.environ.get("SQLALCHEMY_DATABASE_URI") or "").strip()
        dbs = dbs[:50] + ("…" if len(dbs) > 50 else "")
        print(f"DATABASE (truncada): {dbs or '(no en env: revisa .env)'}")
        print()

        print("=== saas_organization (id, subdomain, activa) ===")
        rows = SaasOrganization.query.order_by(SaasOrganization.id.asc()).all()
        for o in rows:
            d = o.subdomain or ""
            a = bool(getattr(o, "is_active", True))
            print(f"  id={o.id}  subdomain={d!r}  active={a!r}  name={(o.name or '')[:48]!r}")
        if not any((o.subdomain or "").lower() == "relatic" for o in rows):
            print("\n  (!) No hay subdomain exacto 'relatic' — apps.relatic.org no puede resolver organization_id.\n")
        else:
            print("\n  (OK) Existe subdomain 'relatic'.\n")

        sub_env = (os.environ.get("EASYNODEONE_APPS_ORG_SUBDOMAIN") or "").strip()
        if sub_env:
            print(
                f"(!) EASYNODEONE_APPS_ORG_SUBDOMAIN={sub_env!r}\n"
                f"     Si el mapa explícito (relatic) no encuentra org, el host apps.* se puede resolver a OTRO tenant.\n"
            )

        print("=== resolución de org como con Host: apps.relatic.org ===")
        with app.test_request_context(
            f"/inscripcion/{slug}", base_url="https://apps.relatic.org", headers=[("Host", "apps.relatic.org")]
        ):
            from flask import request

            oid = _organization_id_from_request_host(request)
            found = aes.find_published_academic_program_for_inscripcion(slug)
            print(f"  _organization_id_from_request_host  ->  {oid}")
            print(f"  find_published_academic_program_for_inscripcion  ->  {found}")
        print()

        print(f"=== todas las filas academic_program con slug={slug!r} (cualquier estado) ===")
        aps = AcademicProgram.query.filter_by(slug=slug).all()
        if not aps:
            print("  (ninguna)  — no está cargado en esta base o el slug no coincide.")
        for p in aps:
            print(
                f"  program_id={p.id}  organization_id={p.organization_id}  status={p.status!r}  name={(p.name or '')[:50]!r}"
            )
        print()

        pub = AcademicProgram.query.filter_by(slug=slug, status="published").all()
        print(
            f"=== publicados con este slug: {len(pub)} (el fallback global solo aplica si hay **exactamente 1**) ==="
        )
        for p in pub:
            print(f"  id={p.id}  organization_id={p.organization_id}")
        if len(pub) > 1:
            print("  (!) Más de uno publicado con el mismo slug → el código no elige; devuelve None (404).")
        print()

        if oid is not None:
            p = aes.get_published_program_by_slug(int(oid), slug)
            print(f"=== get_published_program_by_slug(organization_id={oid}, slug)  ->  {p}")
        else:
            print("=== get_published_program_by_slug: org_id resuelto es None; no aplica 1) ===")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
