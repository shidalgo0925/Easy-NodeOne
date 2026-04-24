"""
Crea un AcademicProgram de ejemplo (Neuro-Liderazgo) con planes alineados a DIPLOMADOS_IIUS.
Uso (desde directorio backend con venv y DATABASE_URL en entorno):
  python3 scripts/seed_academic_program_iius_neuro.py [organization_id]
"""
from __future__ import annotations

import os
import sys

# Raíz: .../app/backend
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main() -> int:
    org_id = int(sys.argv[1]) if len(sys.argv) > 1 else 1

    from app import app, db
    from models.academic_program import AcademicProgram, AcademicProgramPricingPlan

    with app.app_context():
        existing = AcademicProgram.query.filter_by(organization_id=org_id, slug='neuro-liderazgo-intercultural').first()
        if existing:
            print('Ya existe academic_program para ese slug; no se duplica.')
            return 0
        p = AcademicProgram(
            organization_id=org_id,
            name='Neuro-Liderazgo y Coaching Ejecutivo Intercultural',
            slug='neuro-liderazgo-intercultural',
            program_type='diplomado',
            modality='100% online',
            duration_text='10 meses · 240 h',
            hours='240 h',
            language='Español',
            price_from=1949.0,
            currency='USD',
            short_description='El cargo en la pasarela corresponde al total del plan que elijas. Tras el pago, el equipo confirma acceso al aula.',
            status='published',
        )
        db.session.add(p)
        db.session.flush()
        plans = [
            ('Pago completo', 'full', 194900, None, '20% dto. incluido · un solo cargo', 'Diplomado — pago completo (un cargo)'),
            ('Plan 6 cuotas', '6', 230000, 6, 'Total programa', '6 × USD 383 referencia; un cargo por el total hoy'),
            ('Plan 10 cuotas', '10', 269000, 10, 'Total programa', '10 × USD 269 referencia; un cargo por el total hoy'),
        ]
        for so, (name, code, cents, inst, disc, desc) in enumerate(plans):
            db.session.add(
                AcademicProgramPricingPlan(
                    program_id=p.id,
                    name=name,
                    code=code,
                    currency='USD',
                    total_amount_cents=cents,
                    installment_count=inst,
                    discount_label=disc,
                    description=desc,
                    is_active=True,
                    sort_order=so,
                )
            )
        db.session.commit()
        print(f'OK: academic_program id={p.id} org={org_id} slug=neuro-liderazgo-intercultural')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
