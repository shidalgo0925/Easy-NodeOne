#!/usr/bin/env python3
"""
Coaching personal IIUS (program_type=taller) — enlaces /inscripcion/<slug>.
Idempotente por slug + organization_id.

  python3 scripts/seed_academic_programs_iius_coaching_personal.py [organization_id]
  python3 scripts/seed_academic_programs_iius_coaching_personal.py [organization_id] coaching-de-vida
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PRICE_USD = 99.0
PRICE_CENTS = 9900

COACHING_CATALOG = {
    'coaching-de-vida': {
        'name': 'Coaching de Vida',
        'short_description': (
            'Clarifica tu visión, define tus metas y diseña una vida con propósito y dirección.'
        ),
    },
    'coaching-espiritual-y-proposito': {
        'name': 'Coaching Espiritual y de Propósito',
        'short_description': (
            'Conecta con tus valores, sentido de vida y tu propósito superior.'
        ),
    },
    'coaching-familiar': {
        'name': 'Coaching Familiar',
        'short_description': (
            'Fortalece tus vínculos, mejora la comunicación y construye relaciones sanas y duraderas.'
        ),
    },
    'coaching-financiero': {
        'name': 'Coaching Financiero',
        'short_description': (
            'Alcanza tu bienestar financiero, administra tus recursos y construye libertad y abundancia.'
        ),
    },
}


def _seed_one(org_id: int, slug: str, meta: dict) -> str:
    from app import db
    from models.academic_program import AcademicProgram, AcademicProgramPricingPlan

    if AcademicProgram.query.filter_by(organization_id=org_id, slug=slug).first():
        return f'skip slug={slug} (ya existe)'

    p = AcademicProgram(
        organization_id=org_id,
        name=meta['name'],
        slug=slug,
        program_type='taller',
        category='Coaching Personal',
        modality='Coaching personal · sesión',
        duration_text='1 sesión',
        language='Español',
        price_from=PRICE_USD,
        currency='USD',
        short_description=meta['short_description'],
        status='published',
    )
    db.session.add(p)
    db.session.flush()
    db.session.add(
        AcademicProgramPricingPlan(
            program_id=p.id,
            name='Inscripción coaching',
            code='full',
            currency='USD',
            total_amount_cents=PRICE_CENTS,
            installment_count=None,
            discount_label='',
            description=f'Coaching — pago único USD {PRICE_USD:.2f}',
            is_active=True,
            sort_order=0,
        )
    )
    db.session.commit()
    return f'OK program id={p.id} slug={slug}'


def main() -> int:
    org_id = 1
    only_slug = None
    args = sys.argv[1:]
    if args and args[0].isdigit():
        org_id = int(args.pop(0))
    if args:
        only_slug = args[0].strip().lower()
        if only_slug not in COACHING_CATALOG:
            print(f'Slug desconocido: {only_slug}')
            print('Válidos:', ', '.join(COACHING_CATALOG))
            return 1

    from app import app

    with app.app_context():
        items = (
            [(only_slug, COACHING_CATALOG[only_slug])]
            if only_slug
            else list(COACHING_CATALOG.items())
        )
        for slug, meta in items:
            print(_seed_one(org_id, slug, meta))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
