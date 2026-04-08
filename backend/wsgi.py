"""
Entrada WSGI para producción con Gunicorn (+ Nginx como reverse proxy).

Requisitos:
  - WorkingDirectory = este directorio (`backend/`), para que `import app` resuelva `app.py`.
  - venv del proyecto NodeOne (no mezclar con otros proyectos).

Ejemplo:
  cd /ruta/a/NodeOne/backend
  ../venv/bin/gunicorn --workers 2 --bind 127.0.0.1:9001 --timeout 120 wsgi:application

En desarrollo no uses Gunicorn para iterar rápido; usa `python app.py` solo en local.
"""
from app import create_app

application = create_app()
app = application
