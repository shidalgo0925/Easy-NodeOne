#!/usr/bin/env python3
"""
Publica en BD los diplomados IIUS (misma matriz de precios que DIPLOMADOS_IIUS).
Idempotente por slug + organization_id.

  python3 scripts/seed_academic_programs_iius_all.py [organization_id]
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Metadatos de catálogo (precios vienen de DIPLOMADOS_IIUS)
_CATALOG = {
    'neuro-liderazgo-intercultural': {
        'name': 'Neuro-Liderazgo y Coaching Ejecutivo Intercultural',
        'program_type': 'diplomado',
        'modality': '100% online',
        'duration_text': '10 meses · 240 h',
        'hours': '240 h',
        'price_from': 1949.0,
    },
    'neuro-descodificacion-psicogenealogia-pnl': {
        'name': 'Neuro-Descodificación™, Psicogenealogía y PNL',
        'program_type': 'diplomado',
        'modality': '100% online',
        'duration_text': '10 meses · 240 h',
        'hours': '240 h',
        'price_from': 1949.0,
    },
    'neuro-teologia-coaching-cristiano-transgeneracional': {
        'name': 'Neuro-Teología y Coaching Cristiano Transgeneracional',
        'program_type': 'diplomado',
        'modality': '100% online',
        'duration_text': '10 meses · 200 h',
        'hours': '200 h',
        'price_from': 1499.0,
    },
    'neuro-heuristica-coaching-vida': {
        'name': 'Neuro-Heurística™ y Coaching de Vida',
        'program_type': 'diplomado',
        'modality': '100% online',
        'duration_text': '10 meses · 200 h',
        'hours': '200 h',
        'price_from': 1499.0,
    },
}

_PLAN_LABELS = {
    'full': ('Pago completo', '20% dto. incluido'),
    '6': ('Plan 6 cuotas', ''),
    '10': ('Plan 10 cuotas', ''),
}


def main() -> int:
    org_id = int(sys.argv[1]) if len(sys.argv) > 1 else 1

    from app import app, db
    from _app.modules.payments.service import DIPLOMADOS_IIUS
    from models.academic_program import AcademicProgram, AcademicProgramPricingPlan

    created = skipped = 0
    with app.app_context():
        for slug, legacy in DIPLOMADOS_IIUS.items():
            if AcademicProgram.query.filter_by(organization_id=org_id, slug=slug).first():
                skipped += 1
                continue
            meta = _CATALOG.get(slug, {})
            label = legacy.get('label') or slug
            p = AcademicProgram(
                organization_id=org_id,
                name=meta.get('name') or label,
                slug=slug,
                program_type=meta.get('program_type', 'diplomado'),
                modality=meta.get('modality', '100% online'),
                duration_text=meta.get('duration_text', ''),
                hours=meta.get('hours', ''),
                language='Español',
                price_from=float(meta.get('price_from', 0) or 0),
                currency='USD',
                short_description=(
                    'El cargo en la pasarela corresponde al total del plan que elijas. '
                    'Tras el pago, el equipo confirma acceso al aula.'
                ),
                status='published',
            )
            db.session.add(p)
            db.session.flush()
            for so, (plan_key, row) in enumerate((legacy.get('plans') or {}).items()):
                cents, _cart_name, desc = row
                pl_name, disc = _PLAN_LABELS.get(plan_key, (f'Plan {plan_key}', ''))
                inst = None
                if plan_key == '6':
                    inst = 6
                elif plan_key == '10':
                    inst = 10
                db.session.add(
                    AcademicProgramPricingPlan(
                        program_id=p.id,
                        name=pl_name,
                        code=plan_key,
                        currency='USD',
                        total_amount_cents=int(cents),
                        installment_count=inst,
                        discount_label=disc,
                        description=desc,
                        is_active=True,
                        sort_order=so,
                    )
                )
            db.session.commit()
            created += 1
            print(f'OK created id={p.id} slug={slug}')

    print(f'Done org={org_id}: created={created} skipped={skipped}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
