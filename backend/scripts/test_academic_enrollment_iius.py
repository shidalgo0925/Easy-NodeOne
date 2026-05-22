#!/usr/bin/env python3
"""Smoke test inscripción académica IIUS (sin PayPal live)."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

HOST = {'Host': 'apps.internationalinstitute.us'}
SLUG = 'neuro-liderazgo-intercultural'
PLAN = 'full'


def main() -> int:
    from app import app

    fails = 0
    with app.app_context():
        with app.test_client() as c:
            r = c.get(f'/inscripcion/{SLUG}', headers=HOST)
            if r.status_code != 200:
                print('FAIL landing', r.status_code)
                fails += 1
            else:
                print('OK landing 200')

            with c.session_transaction() as sess:
                sess.clear()
            r2 = c.post(
                f'/inscripcion/{SLUG}/seleccionar-plan',
                data={'plan_code': PLAN},
                headers=HOST,
                follow_redirects=False,
            )
            if r2.status_code not in (302, 303):
                print('FAIL seleccionar-plan', r2.status_code)
                fails += 1
            else:
                loc = r2.headers.get('Location', '')
                if 'login' in loc or 'register' in loc:
                    print('OK seleccionar-plan → auth', loc[:80])
                else:
                    print('OK seleccionar-plan redirect', loc[:80])
                # Sesión puede no persistir en test_client; el funnel usa `next=` al continuar.
                ok_next = f'/continuar/{PLAN}' in loc or f'continuar/{PLAN}' in loc
                with c.session_transaction() as sess:
                    ok_sess = (
                        sess.get('pending_program_slug') == SLUG
                        and sess.get('pending_plan_code') == PLAN
                    )
                if ok_sess:
                    print('OK session pending_*')
                elif ok_next:
                    print('OK login next=continuar (sin sesión en test_client)')
                else:
                    print('FAIL pending', loc[:120])
                    fails += 1

    print('---', 'OK' if fails == 0 else f'{fails} FAIL')
    return 1 if fails else 0


if __name__ == '__main__':
    raise SystemExit(main())
