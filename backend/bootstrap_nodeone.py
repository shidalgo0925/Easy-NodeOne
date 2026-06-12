#!/usr/bin/env python3
"""
Esquema inicial / parches DDL (equivalente al bloque previo de `python app.py` sin levantar Flask).

Uso: desde `backend/`
  python3 bootstrap_nodeone.py

systemd puede llamarlo en ExecStartPre antes de gunicorn.
"""
import os
import sys
from pathlib import Path

if __name__ == '__main__':
    here = os.path.dirname(os.path.abspath(__file__))
    try:
        from dotenv import load_dotenv

        app_root = Path(here).resolve().parent
        # systemd usa /opt/easynodeone/dev/.env (DATABASE_URL PG); app/.env suele no tenerla.
        load_dotenv(app_root.parent / '.env')
        load_dotenv(app_root / '.env')
    except ImportError:
        pass
    os.chdir(here)
    if here not in sys.path:
        sys.path.insert(0, here)
    import app as app_module

    app_module.bootstrap_nodeone_schema()
