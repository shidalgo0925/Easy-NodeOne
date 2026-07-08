#!/usr/bin/env python3
"""
Siete programas de coaching IIUS (compra directa) — vitrina /coaching.
Idempotente por slug.

  python3 scripts/seed_iius_coaching_programs.py [organization_id]
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

COACHING_PROGRAMS: tuple[dict, ...] = (
    {
        'slug': 'coaching-de-vida',
        'name': 'Coaching de vida',
        'catalog_sort_order': 1,
        'short_description': (
            'Clarifica tu visión, define tus metas y diseña una vida con propósito y dirección.'
        ),
        'key_focuses': (
            'Enfoque personal\n'
            'Crecimiento y bienestar\n'
            'Equilibrio y plenitud\n'
            'Toma de decisiones con confianza'
        ),
    },
    {
        'slug': 'coaching-espiritual-y-de-proposito',
        'name': 'Coaching espiritual y de propósito',
        'catalog_sort_order': 2,
        'short_description': (
            'Conecta con tus valores, sentido de vida y tu propósito superior.'
        ),
        'key_focuses': (
            'Conexión interior\n'
            'Propósito y misión\n'
            'Transformación personal\n'
            'Alineación y paz interior'
        ),
    },
    {
        'slug': 'coaching-familiar',
        'name': 'Coaching familiar',
        'catalog_sort_order': 3,
        'short_description': (
            'Fortalece tus vínculos, mejora la comunicación y construye relaciones sanas y duraderas.'
        ),
        'key_focuses': (
            'Comunicación efectiva\n'
            'Resolución de conflictos\n'
            'Armonía familiar\n'
            'Valores y unidad'
        ),
    },
    {
        'slug': 'coaching-financiero',
        'name': 'Coaching financiero',
        'catalog_sort_order': 4,
        'short_description': (
            'Alcanza tu bienestar financiero, administra tus recursos y construye libertad y abundancia.'
        ),
        'key_focuses': (
            'Educación financiera\n'
            'Planificación y metas\n'
            'Manejo de recursos\n'
            'Abundancia y crecimiento'
        ),
    },
    {
        'slug': 'coaching-ejecutivo',
        'name': 'Coaching ejecutivo',
        'catalog_sort_order': 5,
        'short_description': (
            'Potencia tu liderazgo, toma decisiones estratégicas y alcanza resultados excepcionales.'
        ),
        'key_focuses': (
            'Liderazgo y toma de decisiones\n'
            'Gestión estratégica y enfoque en resultados\n'
            'Comunicación efectiva\n'
            'Inteligencia emocional\n'
            'Alta productividad y desempeño'
        ),
    },
    {
        'slug': 'coaching-individual',
        'name': 'Coaching individual',
        'catalog_sort_order': 6,
        'short_description': (
            'Descubre tu propósito, fortalece tu mentalidad y crea la vida que deseas con claridad y dirección.'
        ),
        'key_focuses': (
            'Autoconocimiento y claridad de propósito\n'
            'Desarrollo personal y mentalidad\n'
            'Gestión emocional y resiliencia\n'
            'Hábitos y disciplina\n'
            'Diseño de vida y logro de metas'
        ),
    },
    {
        'slug': 'coaching-organizacional-empresarial',
        'name': 'Coaching organizacional empresarial',
        'catalog_sort_order': 7,
        'short_description': (
            'Transforma tu empresa, fortalece tu equipo y crea una cultura de alto rendimiento y crecimiento sostenible.'
        ),
        'key_focuses': (
            'Coaching de equipos y alto rendimiento\n'
            'Cultura organizacional y liderazgo\n'
            'Comunicación y colaboración efectiva\n'
            'Gestión del cambio y transformación\n'
            'Estrategia y resultados sostenibles'
        ),
    },
)

PRICE_USD = 99.0
PLAN_CODE = 'full'


def _upsert_plan(program, db, AcademicProgramPricingPlan) -> None:
    plan = AcademicProgramPricingPlan.query.filter_by(
        program_id=program.id, code=PLAN_CODE
    ).first()
    cents = int(PRICE_USD * 100)
    if plan is None:
        db.session.add(
            AcademicProgramPricingPlan(
                program_id=program.id,
                name='Inscripción coaching',
                code=PLAN_CODE,
                currency='USD',
                total_amount_cents=cents,
                installment_count=None,
                discount_label='',
                description=f'Coaching — pago único USD {int(PRICE_USD)}',
                is_active=True,
                sort_order=0,
            )
        )
        return
    plan.name = 'Inscripción coaching'
    plan.currency = 'USD'
    plan.total_amount_cents = cents
    plan.description = f'Coaching — pago único USD {int(PRICE_USD)}'
    plan.is_active = True


def main() -> int:
    org_id = int(sys.argv[1]) if len(sys.argv) > 1 else 1

    from app import app, db
    from models.academic_program import AcademicProgram, AcademicProgramPricingPlan

    with app.app_context():
        for spec in COACHING_PROGRAMS:
            slug = spec['slug']
            program = AcademicProgram.query.filter_by(organization_id=org_id, slug=slug).first()
            if program is None:
                program = AcademicProgram(
                    organization_id=org_id,
                    slug=slug,
                    program_type='coaching',
                    category='Coaching',
                    modality='Online',
                    duration_text='Sesiones personalizadas',
                    language='Español',
                    price_from=PRICE_USD,
                    currency='USD',
                    status='published',
                    cta_label='Inscribirme',
                    cta_action='scroll_pricing',
                    requires_agenda=slug in ('coaching-individual', 'coaching-ejecutivo'),
                    ecalendar_product_id=(
                        'coaching_personal' if slug == 'coaching-individual'
                        else ('coaching_ejecutivo' if slug == 'coaching-ejecutivo' else None)
                    ),
                )
                db.session.add(program)
                db.session.flush()
                action = 'created'
            else:
                action = 'updated'

            program.name = spec['name']
            program.program_type = 'coaching'
            program.category = 'Coaching'
            program.catalog_sort_order = int(spec['catalog_sort_order'])
            program.short_description = spec['short_description']
            program.key_focuses = spec['key_focuses']
            program.modality = program.modality or 'Online'
            program.duration_text = program.duration_text or 'Sesiones personalizadas'
            program.language = program.language or 'Español'
            program.price_from = PRICE_USD
            program.currency = 'USD'
            program.status = 'published'
            program.cta_label = 'Inscribirme'
            program.cta_action = 'scroll_pricing'
            if slug in ('coaching-individual', 'coaching-ejecutivo'):
                program.requires_agenda = True
                program.ecalendar_product_id = (
                    'coaching_personal' if slug == 'coaching-individual' else 'coaching_ejecutivo'
                )
            else:
                program.requires_agenda = False
                program.ecalendar_product_id = None
            _upsert_plan(program, db, AcademicProgramPricingPlan)
            print(f'OK ({action}): id={program.id} slug={slug}')

        db.session.commit()
        print(f'Done: {len(COACHING_PROGRAMS)} coaching programs for org {org_id}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
