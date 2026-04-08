#!/usr/bin/env python3
"""
Esquema inicial / parches DDL (equivalente al bloque previo de `python app.py` sin levantar Flask).

Uso: desde `backend/`
  python3 bootstrap_nodeone.py

systemd puede llamarlo en ExecStartPre antes de gunicorn.
"""
import os
import sys

if __name__ == '__main__':
    here = os.path.dirname(os.path.abspath(__file__))
    os.chdir(here)
    if here not in sys.path:
        sys.path.insert(0, here)
    import app as app_module

    app_module.bootstrap_nodeone_schema()
