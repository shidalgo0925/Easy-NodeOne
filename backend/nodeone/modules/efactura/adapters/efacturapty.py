"""Adapter HTTP efacturapty."""

from __future__ import annotations

import os
from typing import Any

import requests

from models.efactura import ElectronicInvoiceDocument, ElectronicInvoiceProviderConfig
from nodeone.modules.efactura.adapters.base import EInvoiceProviderAdapter


class EFacturaPTYAdapter(EInvoiceProviderAdapter):
    DEFAULT_BASE = 'https://api.efacturapty.com'

    def __init__(self, config: ElectronicInvoiceProviderConfig) -> None:
        super().__init__(config)
        self.base_url = (config.api_base_url or self.DEFAULT_BASE).rstrip('/')

    def _token(self) -> str:
        raw = (self.config.api_token_encrypted or '').strip()
        if raw:
            return raw
        return (os.environ.get('EFACTURA_API_TOKEN') or '').strip()

    def _headers(self) -> dict[str, str]:
        token = self._token()
        if not token:
            raise ValueError('No hay token de API configurado para esta organización.')
        return {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
            'Accept-Language': os.getenv('EFACTURA_ACCEPT_LANGUAGE', 'es-PA'),
        }

    def _normalize_emit_response(self, data: dict, http_status: int) -> dict[str, Any]:
        autorizada = bool(data.get('autorizada'))
        cufe = data.get('cufe')
        protocolo = data.get('protocoloAutorizacion')
        mensajes: list[str] = []
        prot = data.get('rRetEnviFe') or {}
        ginf = ((prot.get('xProtFe') or {}).get('rProtFe') or {}).get('gInfProt') or {}
        for row in ginf.get('gResProc') or []:
            code = row.get('dCodRes')
            msg = row.get('dMsgRes')
            if code or msg:
                mensajes.append(f'{code}: {msg}'.strip(': '))
        auth_msg = '; '.join(mensajes) if mensajes else None
        return {
            'ok': http_status < 400 and autorizada,
            'autorizada': autorizada,
            'cufe': cufe,
            'protocolo': protocolo,
            'mensajes': mensajes,
            'authorization_message': auth_msg,
            'raw_response': data,
            'http_status': http_status,
        }

    def test_connection(self) -> dict[str, Any]:
        url = f'{self.base_url}/api/v1/Catalogs/countries'
        try:
            response = requests.get(url, headers=self._headers(), timeout=30)
        except requests.RequestException as exc:
            return {'ok': False, 'message': str(exc), 'http_status': None}
        if response.ok:
            return {'ok': True, 'message': 'Conexión correcta con efacturapty.', 'http_status': response.status_code}
        try:
            body = response.json()
            msg = body.get('message') or body.get('title') or response.text[:500]
        except Exception:
            msg = response.text[:500]
        return {
            'ok': False,
            'message': f'HTTP {response.status_code}: {msg}',
            'http_status': response.status_code,
        }

    def emit_invoice(self, document: ElectronicInvoiceDocument, pac_payload: dict) -> dict[str, Any]:
        url = f'{self.base_url}/api/v1/Invoices'
        params: dict[str, str] = {}
        if os.getenv('EFACTURA_INCLUDE_XML', '1').strip().lower() in ('1', 'true', 'yes'):
            params['xml'] = 'true'
        if os.getenv('EFACTURA_INCLUDE_QR', '1').strip().lower() in ('1', 'true', 'yes'):
            params['qr'] = 'true'
        try:
            response = requests.post(
                url, headers=self._headers(), params=params, json=pac_payload, timeout=90
            )
        except requests.RequestException as exc:
            return {
                'ok': False,
                'autorizada': False,
                'cufe': None,
                'protocolo': None,
                'mensajes': [],
                'authorization_message': str(exc),
                'raw_response': {'error': str(exc)},
                'http_status': None,
            }
        try:
            data = response.json()
        except Exception:
            data = {'raw_text': response.text[:8000]}
        out = self._normalize_emit_response(data if isinstance(data, dict) else {}, response.status_code)
        if not out['ok'] and not out['authorization_message']:
            out['authorization_message'] = response.text[:500] if not response.ok else None
        return out
