#!/usr/bin/env python3
"""Comandos de operación (compat: ``python manage.py check_service_integrity``)."""
import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
os.chdir(_ROOT)
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def main() -> int:
    if len(sys.argv) < 2:
        print('Uso: python manage.py check_service_integrity')
        return 2
    cmd = sys.argv[1].strip().lower()
    if cmd == 'check_service_integrity':
        from app import app
        from nodeone.services.service_request_integrity import run_integrity_check

        with app.app_context():
            return run_integrity_check()
    print('Comando desconocido:', cmd)
    return 2


if __name__ == '__main__':
    raise SystemExit(main())
