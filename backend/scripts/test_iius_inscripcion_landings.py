#!/usr/bin/env python3
"""Smoke: landings /inscripcion/* publicadas para IIUS (org 1)."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

HOST = {'Host': 'apps.internationalinstitute.us'}
DIPLOMADO_SLUGS = (
    'neuro-liderazgo-intercultural',
    'neuro-descodificacion-psicogenealogia-pnl',
    'neuro-teologia-coaching-cristiano-transgeneracional',
    'neuro-heuristica-coaching-vida',
)
OPTIONAL_SLUGS = ('taller-fundamentos-coaching-ejecutivo',)


def main() -> int:
    from app import app
    from models.academic_program import AcademicProgram

    fails = 0
    with app.app_context():
        pub_n = AcademicProgram.query.filter_by(organization_id=1, status='published').count()
        if pub_n < len(DIPLOMADO_SLUGS):
            print('FAIL published count <', len(DIPLOMADO_SLUGS))
            fails += 1
        else:
            print('OK', pub_n, 'programas published org 1')
        slugs = list(DIPLOMADO_SLUGS)
        for opt in OPTIONAL_SLUGS:
            if AcademicProgram.query.filter_by(organization_id=1, slug=opt, status='published').first():
                slugs.append(opt)
        with app.test_client() as c:
            for slug in slugs:
                r = c.get(f'/inscripcion/{slug}', headers=HOST)
                if r.status_code != 200:
                    print('FAIL', slug, r.status_code)
                    fails += 1
                    continue
                if b'pe-checkout-landing' not in r.data and b'program_enrollment' not in r.data:
                    print('WARN', slug, 'posible plantilla legacy')
                print('OK', slug, 200)
    print('---', 'OK' if fails == 0 else f'{fails} FAIL')
    return 1 if fails else 0


if __name__ == '__main__':
    raise SystemExit(main())
