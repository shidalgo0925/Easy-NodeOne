#!/usr/bin/env python3
"""
Obtener refresh token OAuth para ECalendar (Google Calendar API).

Uso (una vez por entorno / cliente OAuth):
  cd /opt/easynodeone/dev/app/backend
  export ECALENDAR_OAUTH_CLIENT_ID='....apps.googleusercontent.com'
  export ECALENDAR_OAUTH_CLIENT_SECRET='GOCSPX-...'
  /opt/easynodeone/dev/venv/bin/python3 tools/ecalendar_oauth_refresh.py

Requisitos en Google Cloud (cliente OAuth Web):
  - Redirect URI: http://localhost:8765/oauth2callback
  - Scope: https://www.googleapis.com/auth/calendar
  - Usuario de prueba en pantalla de consentimiento (modo Testing)

No commitear secretos. Pegar refresh_token en /admin/ecalendar.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer

REDIRECT_URI = 'http://localhost:8765/oauth2callback'
SCOPE = 'https://www.googleapis.com/auth/calendar'
TOKEN_URL = 'https://oauth2.googleapis.com/token'
AUTH_URL = 'https://accounts.google.com/o/oauth2/v2/auth'
PORT = 8765


def _env(name: str) -> str:
    return (os.environ.get(name) or '').strip()


def build_auth_url(client_id: str) -> str:
    params = {
        'client_id': client_id,
        'redirect_uri': REDIRECT_URI,
        'response_type': 'code',
        'scope': SCOPE,
        'access_type': 'offline',
        'prompt': 'consent',
    }
    return f'{AUTH_URL}?{urllib.parse.urlencode(params)}'


def exchange_code(client_id: str, client_secret: str, code: str) -> dict:
    body = urllib.parse.urlencode(
        {
            'code': code,
            'client_id': client_id,
            'client_secret': client_secret,
            'redirect_uri': REDIRECT_URI,
            'grant_type': 'authorization_code',
        }
    ).encode('utf-8')
    req = urllib.request.Request(
        TOKEN_URL,
        data=body,
        method='POST',
        headers={'Content-Type': 'application/x-www-form-urlencoded'},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as ex:
        detail = ex.read().decode('utf-8', errors='replace')
        raise SystemExit(f'Error HTTP {ex.code} al intercambiar code:\n{detail}') from ex


class _CallbackHandler(BaseHTTPRequestHandler):
    auth_code: str | None = None
    error: str | None = None

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return

    def do_GET(self) -> None:  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path != '/oauth2callback':
            self.send_error(404)
            return
        qs = urllib.parse.parse_qs(parsed.query)
        if 'error' in qs:
            _CallbackHandler.error = qs['error'][0]
            body = b'<h1>Error OAuth</h1><p>Cerra esta pesta\xc3\xb1a.</p>'
            self.send_response(400)
        elif 'code' in qs:
            _CallbackHandler.auth_code = qs['code'][0]
            body = b'<h1>OK</h1><p>Refresh token obtenido. Volv\xc3\xa9 a la terminal.</p>'
            self.send_response(200)
        else:
            body = b'<h1>Sin code</h1>'
            self.send_response(400)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(body)


def main() -> int:
    client_id = _env('ECALENDAR_OAUTH_CLIENT_ID')
    client_secret = _env('ECALENDAR_OAUTH_CLIENT_SECRET')
    if not client_id or not client_secret:
        print(
            'Define ECALENDAR_OAUTH_CLIENT_ID y ECALENDAR_OAUTH_CLIENT_SECRET en el entorno.',
            file=sys.stderr,
        )
        return 1

    url = build_auth_url(client_id)
    print('1) Abriendo navegador para autorizar (cuenta del calendario EasyTech)...')
    print(f'   Si no abre: {url}\n')
    webbrowser.open(url)

    print(f'2) Esperando callback en {REDIRECT_URI} ...')
    server = HTTPServer(('127.0.0.1', PORT), _CallbackHandler)
    server.handle_request()

    if _CallbackHandler.error:
        print(f'OAuth error: {_CallbackHandler.error}', file=sys.stderr)
        return 1
    if not _CallbackHandler.auth_code:
        print('No se recibió code en el callback.', file=sys.stderr)
        return 1

    print('3) Intercambiando code por tokens...')
    data = exchange_code(client_id, client_secret, _CallbackHandler.auth_code)

    refresh = (data.get('refresh_token') or '').strip()
    if not refresh:
        print(
            'Respuesta sin refresh_token. Revocá la app en myaccount.google.com/permissions '
            'y repetí con prompt=consent.',
            file=sys.stderr,
        )
        print(json.dumps({k: v for k, v in data.items() if k != 'access_token'}, indent=2))
        return 1

    print('\n=== REFRESH TOKEN (guardar en /admin/ecalendar) ===\n')
    print(refresh)
    print('\n=== Siguiente ===')
    print('  - https://appdev.easynodeone.com/admin/ecalendar')
    print('  - Client ID, secret, refresh token → Guardar → Probar OAuth')
    print('  - curl -s https://appdev.easynodeone.com/api/ecalendar/health')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
