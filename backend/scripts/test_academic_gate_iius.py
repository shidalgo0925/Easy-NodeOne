#!/usr/bin/env python3
"""Smoke: campus académico cerrado (org 1) y ruta /mi-campus."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

HOST = {'Host': 'apps.internationalinstitute.us'}


def main() -> int:
    from app import app, db
    from models.users import User
    from nodeone.services.academic_access import has_active_enrollment, member_needs_academic_enrollment

    fails = 0
    with app.app_context():
        u1 = User.query.get(1)
        u2 = User.query.get(2)
        if u1 is None or u2 is None:
            print('FAIL users missing')
            return 1
        if not has_active_enrollment(1, 1):
            print('FAIL user1 sin matrícula activa')
            fails += 1
        else:
            print('OK user1 matrícula activa (campus desbloqueado)')
        if not member_needs_academic_enrollment(u2, 1):
            print('FAIL user2 debería estar bajo gate')
            fails += 1
        else:
            print('OK user2 bajo gate (sin matrícula)')

        with app.test_client() as c:
            r = c.get('/mi-campus', headers=HOST, follow_redirects=False)
            if r.status_code in (302, 303) and 'login' in (r.headers.get('Location') or '').lower():
                print('OK /mi-campus anónimo → login')
            else:
                print('FAIL /mi-campus anon', r.status_code, r.headers.get('Location'))
                fails += 1

    print('---', 'OK' if fails == 0 else f'{fails} FAIL')
    return 1 if fails else 0


if __name__ == '__main__':
    raise SystemExit(main())
