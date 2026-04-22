"""
Entrada WSGI en la raíz del proyecto.

Gunicorn (systemd):
  WorkingDirectory=/var/www/nodeone
  ExecStart=.../gunicorn -w 3 -b 127.0.0.1:8000 wsgi:app
"""
from pathlib import Path
import os
import sys

ROOT = Path(__file__).resolve().parent
os.environ.setdefault('NODEONE_ROOT', str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / '.env')

BACKEND = ROOT / 'backend'
sys.path.insert(0, str(BACKEND))

from app import create_app

app = create_app()
application = app
