"""
Entrypoint alternativo (FASE 1).

Uso desde el directorio backend:
  python nodeone/main.py

Producción (recomendado, mismo venv):
  cd backend && ../venv/bin/gunicorn -b 127.0.0.1:9001 wsgi:application

Sigue siendo válido: python app.py
"""
import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from nodeone.core.factory import create_app

app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 9001))
    app.run(host='0.0.0.0', port=port, debug=False)
