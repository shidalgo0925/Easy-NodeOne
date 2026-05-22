#!/usr/bin/env python3
"""
Taller de ejemplo IIUS (program_type=taller) — catálogo mixto diplomados + talleres.
Idempotente por slug.

  python3 scripts/seed_academic_program_iius_sample_taller.py [organization_id]
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SLUG = 'taller-fundamentos-coaching-ejecutivo'


def main() -> int:
    org_id = int(sys.argv[1]) if len(sys.argv) > 1 else 1

    from app import app, db
    from models.academic_program import AcademicProgram, AcademicProgramPricingPlan

    with app.app_context():
        if AcademicProgram.query.filter_by(organization_id=org_id, slug=SLUG).first():
            print(f'Ya existe slug={SLUG}; skip')
            return 0
        p = AcademicProgram(
            organization_id=org_id,
            name='Taller: Fundamentos de Coaching Ejecutivo',
            slug=SLUG,
            program_type='taller',
            modality='100% online · en vivo',
            duration_text='4 semanas · 32 h',
            hours='32 h',
            language='Español',
            price_from=349.0,
            currency='USD',
            short_description='Taller introductorio. Un solo cargo al inscribirte.',
            status='published',
        )
        db.session.add(p)
        db.session.flush()
        db.session.add(
            AcademicProgramPricingPlan(
                program_id=p.id,
                name='Inscripción taller',
                code='full',
                currency='USD',
                total_amount_cents=34900,
                installment_count=None,
                discount_label='',
                description='Taller — pago único USD 349',
                is_active=True,
                sort_order=0,
            )
        )
        db.session.commit()
        print(f'OK: program id={p.id} slug={SLUG} type=taller')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
