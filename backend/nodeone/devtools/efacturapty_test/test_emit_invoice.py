#!/usr/bin/env python3
"""
Prueba aislada: emisión FE vía efacturapty (sin integrar EN1).

Uso:
  cd /opt/easynodeone/dev/app/backend/nodeone/devtools/efacturapty_test
  export EFACTURA_API_TOKEN="..."
  export EFACTURA_API_BASE_URL="https://api.efacturapty.com"   # opcional
  ../../../../../venv/bin/python test_emit_invoice.py

Salida: consola + archivos en ./captures/
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

BASE_URL = (os.getenv('EFACTURA_API_BASE_URL') or 'https://api.efacturapty.com').rstrip('/')

TOKEN = os.getenv('EFACTURA_API_TOKEN')
HERE = Path(__file__).resolve().parent
PAYLOAD_FILE = HERE / 'factura_prueba.json'
CAPTURES = HERE / 'captures'


def _headers() -> dict[str, str]:
    if not TOKEN:
        raise SystemExit('Falta EFACTURA_API_TOKEN en el entorno.')
    return {
        'Authorization': f'Bearer {TOKEN}',
        'Content-Type': 'application/json',
        'Accept-Language': os.getenv('EFACTURA_ACCEPT_LANGUAGE', 'es-PA'),
    }


def _load_payload() -> dict:
    raw = json.loads(PAYLOAD_FILE.read_text(encoding='utf-8'))
    now = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    dg = raw.setdefault('datosGenerales', {})
    if dg.get('fechaEmision') in (None, '', 'REEMPLAZAR_ISO8601_UTC'):
        dg['fechaEmision'] = now
    return raw


def _save_capture(stem: str, payload: dict, response: requests.Response, elapsed: float) -> Path:
    CAPTURES.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    out = CAPTURES / f'{stem}_{ts}.json'
    body: object
    try:
        body = response.json()
    except Exception:
        body = response.text
    out.write_text(
        json.dumps(
            {
                'request': {
                    'method': 'POST',
                    'url': response.request.url if response.request else None,
                    'headers': {
                        k: v
                        for k, v in (response.request.headers if response.request else {}).items()
                        if k.lower() != 'authorization'
                    },
                    'payload': payload,
                },
                'response': {
                    'status_code': response.status_code,
                    'headers': dict(response.headers),
                    'elapsed_seconds': round(elapsed, 3),
                    'body': body,
                },
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding='utf-8',
    )
    return out


def main() -> int:
    payload = _load_payload()
    url = f'{BASE_URL}/api/v1/Invoices'
    params = {}
    if os.getenv('EFACTURA_INCLUDE_XML', '1').strip().lower() in ('1', 'true', 'yes'):
        params['xml'] = 'true'
    if os.getenv('EFACTURA_INCLUDE_QR', '1').strip().lower() in ('1', 'true', 'yes'):
        params['qr'] = 'true'

    t0 = time.perf_counter()
    response = requests.post(url, headers=_headers(), params=params, json=payload, timeout=90)
    elapsed = time.perf_counter() - t0

    print('BASE_URL:', BASE_URL)
    print('STATUS:', response.status_code)
    print('ELAPSED:', f'{elapsed:.3f}s')

    capture_path = _save_capture('emit_invoice', payload, response, elapsed)
    print('CAPTURE:', capture_path)

    try:
        data = response.json()
        print(json.dumps(data, indent=2, ensure_ascii=False))
        print('---')
        print('autorizada:', data.get('autorizada'))
        print('cufe:', data.get('cufe'))
        print('protocoloAutorizacion:', data.get('protocoloAutorizacion'))
        prot = data.get('rRetEnviFe') or {}
        ginf = ((prot.get('xProtFe') or {}).get('rProtFe') or {}).get('gInfProt') or {}
        gres = ginf.get('gResProc') or []
        if gres:
            print('mensajes PAC:')
            for row in gres:
                print(' ', row.get('dCodRes'), '-', row.get('dMsgRes'))
    except Exception:
        print(response.text[:8000])

    return 0 if response.ok else 1


if __name__ == '__main__':
    sys.exit(main())
