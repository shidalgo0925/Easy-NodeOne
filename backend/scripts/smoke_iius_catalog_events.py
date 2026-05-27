#!/usr/bin/env python3
"""Smoke funcional: vitrina /programas, API catálogo, eventos y redirects legacy slugs."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

HOST = {'Host': 'apps.internationalinstitute.us', 'User-Agent': 'Mozilla/5.0'}
ORG_ID = 1
DIPLOMADO_SLUGS = (
    'neuro-liderazgo-intercultural',
    'neuro-descodificacion-psicogenealogia-pnl',
    'neuro-teologia-coaching-cristiano-transgeneracional',
    'neuro-heuristica-coaching-vida',
)
LEGACY_REDIRECTS = (
    ('diplomado-en-creatividad-y-expresion-artistica-aplicada', 'taller-de-creatividad-e-innovacion'),
    ('taller-fundamentos-coaching-ejecutivo', 'taller-de-aprendizaje-practico'),
    ('curso-en-aprendizaje-practico', 'curso-en-arte-collage-mapas-mentales'),
)


def main() -> int:
    from app import app
    from models.academic_program import AcademicProgram
    from models.events import Event

    fails: list[str] = []
    oks: list[str] = []

    def ok(msg: str):
        oks.append(msg)
        print(f'  OK  {msg}')

    def fail(msg: str):
        fails.append(msg)
        print(f' FAIL {msg}')

    with app.app_context():
        pub_n = AcademicProgram.query.filter_by(organization_id=ORG_ID, status='published').count()
        if pub_n < 20:
            fail(f'pocos programas published: {pub_n}')
        else:
            ok(f'{pub_n} programas published org {ORG_ID}')

        draft_events = Event.query.filter_by(publish_status='draft').count()
        published_events = Event.query.filter_by(publish_status='published').count()

        with app.test_client() as c:
            r = c.get('/programas', headers=HOST)
            if r.status_code == 200 and b'ap-catalog' in r.data:
                ok('/programas vitrina 200')
            else:
                fail(f'/programas status={r.status_code}')

            r = c.get('/api/public/academic-programs', headers=HOST)
            data = r.get_json() if r.status_code == 200 else {}
            count = int((data or {}).get('count') or 0)
            if r.status_code == 200 and count >= len(DIPLOMADO_SLUGS):
                ok(f'/api/public/academic-programs count={count}')
            else:
                fail(f'API programs status={r.status_code} count={count}')

            for slug in DIPLOMADO_SLUGS:
                r = c.get(f'/inscripcion/{slug}', headers=HOST)
                if r.status_code == 200:
                    ok(f'/inscripcion/{slug} 200')
                else:
                    fail(f'/inscripcion/{slug} status={r.status_code}')

            r = c.get('/api/events/', headers=HOST)
            evs = (r.get_json() or {}).get('events') or []
            if r.status_code == 200 and len(evs) == published_events and draft_events == 0 or (
                r.status_code == 200 and len(evs) == published_events
            ):
                ok(f'/api/events/ publicados={len(evs)} (draft en BD={draft_events}, no listados)')
            else:
                fail(f'/api/events/ status={r.status_code} count={len(evs)} published_db={published_events}')

            if draft_events:
                draft_slug = (
                    Event.query.filter_by(publish_status='draft').order_by(Event.id.asc()).first().slug
                )
                r = c.get(f'/api/events/{draft_slug}', headers=HOST)
                if r.status_code in (401, 403, 404):
                    ok(f'draft event API no público ({r.status_code})')
                else:
                    fail(f'draft event API accesible status={r.status_code}')

            for legacy, canonical in LEGACY_REDIRECTS:
                if not AcademicProgram.query.filter_by(
                    organization_id=ORG_ID, slug=canonical, status='published'
                ).first():
                    fail(f'canonical missing for redirect {legacy} -> {canonical}')
                    continue
                r = c.get(f'/programs/{legacy}', headers=HOST, follow_redirects=False)
                loc = (r.headers.get('Location') or '').lower()
                if r.status_code in (301, 302) and f'/inscripcion/{canonical}' in loc:
                    ok(f'/programs/{legacy} -> inscripcion/{canonical}')
                else:
                    fail(f'/programs/{legacy} redirect status={r.status_code} loc={loc[:90]}')

    print(f'\nResumen: {len(oks)} OK, {len(fails)} FAIL')
    for f in fails:
        print(f'  - {f}')
    return 1 if fails else 0


if __name__ == '__main__':
    raise SystemExit(main())
