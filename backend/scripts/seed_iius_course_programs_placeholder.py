#!/usr/bin/env python3
"""
Carga inicial: programas COURSE (IIUS) con convocatoria sin fecha — para landings /programs/<slug>.
Idempotente: no duplica por (organization_id, program_slug).

Ejecutar desde la raíz de la app:
  cd /opt/easynodeone/app && .venv/bin/python backend/scripts/seed_iius_course_programs_placeholder.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
os.environ.setdefault("NODEONE_ROOT", str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")


# Misma lista de slugs que enlaza WordPress (únicos; 15 enlaces → 12 programas)
PROGRAMS: list[tuple[str, str, str]] = [
    (
        "curso-en-coaching-profesional-integral",
        "Curso en Coaching Profesional Integral",
        "Bases del coaching moderno; PNL, escucha activa y ética. Prácticas y técnicas aplicadas.",
    ),
    (
        "curso-en-inteligencia-emocional-y-bienestar",
        "Curso en Inteligencia Emocional y Bienestar",
        "Neurociencia, autoconciencia, regulación emocional y resiliencia.",
    ),
    (
        "curso-en-neuroeducacion-y-programacion-neurolinguistica-pnl",
        "Curso en Neuroeducación y Programación Neurolingüística (PNL)",
        "Cómo aprende el cerebro y técnicas de PNL para hábitos y comunicación.",
    ),
    (
        "curso-de-neuroeducacion-y-neuroplasticidad",
        "Curso de Neuroeducación y Neuroplasticidad",
        "Neuroplasticidad aplicada a hábitos, liderazgo y educación.",
    ),
    (
        "diplomado-en-creatividad-y-expresion-artistica-aplicada",
        "Diplomado en Creatividad y Expresión Artística Aplicada",
        "Arte como herramienta de bienestar e innovación.",
    ),
    (
        "curso-en-liderazgo-y-gestion-de-equipos",
        "Curso en Liderazgo y Gestión de Equipos",
        "Comunicación, inteligencia emocional en liderazgo y equipos.",
    ),
    (
        "cursos-en-emprendimiento-y-desarrollo-de-negocios",
        "Cursos en Emprendimiento y Desarrollo de Negocios",
        "Planificación, marketing, ventas y mentalidad emprendedora.",
    ),
    (
        "curso-en-coaching-ejecutivo-y-liderazgo-organizacional",
        "Curso en Coaching Ejecutivo y Liderazgo Organizacional",
        "Coaching ejecutivo, casos reales y desempeño directivo.",
    ),
    (
        "curso-en-finanzas-personales-y-empresariales",
        "Curso en Finanzas Personales y Empresariales",
        "Presupuestos, inversiones y administración de recursos.",
    ),
    (
        "curso-en-mindfulness-y-reduccion-del-estres",
        "Curso en Mindfulness y Reducción del Estrés",
        "Atención plena, respiración y regulación del estrés.",
    ),
    (
        "curso-en-espiritualidad-y-crecimiento-personal",
        "Curso en Espiritualidad y Crecimiento Personal",
        "Propósito, valores y prácticas de crecimiento interior.",
    ),
    (
        "la-mujer-virtuosa-de-prov-31",
        "La Mujer Virtuosa de Prov 31",
        "Formación bíblico-práctica (contenido según programa IIUS).",
    ),
]

ORG_ID = 1
COHORT_LABEL = "Próxima edición — la fecha de inicio se anunciará pronto"
COHORT_SLUG = "proxima-edicion"


def main():
    from app import CourseCohort, Service, db

    from app import app

    with app.app_context():
        created_svc = 0
        created_coh = 0
        for slug, name, desc in PROGRAMS:
            svc = Service.query.filter_by(organization_id=ORG_ID, program_slug=slug).first()
            if svc is None:
                svc = Service(
                    name=name,
                    description=desc,
                    icon="fas fa-graduation-cap",
                    membership_type="basic",
                    category_id=None,
                    base_price=0.0,
                    is_active=True,
                    display_order=100,
                    service_type="COURSE",
                    program_slug=slug,
                    organization_id=ORG_ID,
                    requires_payment_before_appointment=False,
                )
                db.session.add(svc)
                db.session.flush()
                created_svc += 1
            else:
                # Asegurar tipo y slug
                svc.service_type = "COURSE"
                svc.program_slug = slug
                svc.is_active = True
                if not (svc.description or "").strip():
                    svc.description = desc

            ch = (
                CourseCohort.query.filter_by(organization_id=ORG_ID, service_id=svc.id)
                .filter(CourseCohort.slug == COHORT_SLUG)
                .first()
            )
            if ch is None:
                ch = CourseCohort(
                    organization_id=ORG_ID,
                    service_id=svc.id,
                    slug=COHORT_SLUG,
                    label=COHORT_LABEL,
                    start_date=None,
                    end_date=None,
                    weeks_duration=None,
                    modality="virtual",
                    capacity_total=0,
                    capacity_reserved=0,
                    price_override_cents=None,
                    is_active=True,
                    display_order=0,
                )
                db.session.add(ch)
                created_coh += 1

        db.session.commit()
        print(f"OK: servicios COURSE nuevos={created_svc}, cohortes nuevas={created_coh}, programas en lista={len(PROGRAMS)}")


if __name__ == "__main__":
    main()
