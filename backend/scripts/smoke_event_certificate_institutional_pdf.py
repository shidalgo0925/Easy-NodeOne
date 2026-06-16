#!/usr/bin/env python3
"""Smoke Nivel 2A: PDF institucional de certificados de evento (sin BD)."""
from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
os.environ.setdefault('NODEONE_ROOT', str(ROOT))

from nodeone.services.certificate_institutional_pdf import (  # noqa: E402
    CertificateRenderContext,
    build_context_from_event_participant,
    render_institutional_pdf,
)

OUT = ROOT / 'backend' / 'tmp' / 'certificate_smoke'
OUT.mkdir(parents=True, exist_ok=True)


def _write(name: str, data: bytes) -> str:
    p = OUT / name
    p.write_bytes(data)
    return str(p)


class _P:
    def __init__(self, **kw):
        self.__dict__.update(kw)


class _E:
    def __init__(self, **kw):
        self.__dict__.update(kw)


def main() -> int:
    verify = 'https://apps.relatic.org/certificates/verify/EN1-2026-SMOKE01'
    issued = datetime(2026, 6, 8, 12, 0, 0)
    start = datetime(2026, 5, 10, 9, 0, 0)
    end = datetime(2026, 5, 24, 18, 0, 0)

    event = _E(
        title='Diplomado en Neuro-Liderazgo Intercultural con Nombre Extremadamente Largo para Probar Ajuste',
        start_date=start,
        end_date=end,
        university='',
        certificate_template='',
    )
    participant = _P(
        full_name='María Fernanda López García de los Ángeles',
        document_id='8-888-8888',
        participant_type='external',
    )
    ctx = build_context_from_event_participant(
        event=event,
        participant=participant,
        certificate_code='EN1-2026-SMOKE01',
        verify_url=verify,
        issued_at=issued,
        app_root=str(ROOT / 'backend'),
        org_id=1,
    )
    p1 = _write('smoke_participation.pdf', render_institutional_pdf(ctx))
    print('OK participation', p1, os.path.getsize(p1))

    rev = _P(full_name='Dr. Revisor Académico', document_id='', participant_type='reviewer')
    ctx_rev = build_context_from_event_participant(
        event=_E(title='Seminario de Publicación Científica', start_date=start, end_date=end, certificate_template=''),
        participant=rev,
        certificate_code='REV-2026-SMOKE02',
        verify_url='https://apps.relatic.org/certificates/verify/REV-2026-SMOKE02',
        issued_at=issued,
        app_root=str(ROOT / 'backend'),
        org_id=1,
    )
    p2 = _write('smoke_reviewer.pdf', render_institutional_pdf(ctx_rev))
    print('OK reviewer', p2, os.path.getsize(p2))

    from nodeone.services.certificate_institutional_pdf import qr_png_base64

    verify3 = 'https://apps.relatic.org/certificates/verify/EN1-2026-SMOKE03'
    ctx_no_id = CertificateRenderContext(
        participant_name='Participante Sin Documento',
        document_id='No registrado',
        program_name='Webinar Introductorio',
        certificate_code='EN1-2026-SMOKE03',
        verify_url=verify3,
        issued_at=issued,
        activity_type='Seminario',
        event_start=start,
        event_end=end,
        header_text='LA UNIVERSIDAD JOSÉ MARTÍ DE LATINOAMÉRICA Y LA FUNDACIÓN RELATIC PANAMÁ',
        convenio_text='Según convenio vigente No. 100-001 del 20 de octubre de 2025',
        qr_base64=qr_png_base64(verify3),
    )
    p3 = _write('smoke_no_id.pdf', render_institutional_pdf(ctx_no_id))
    print('OK no_id', p3, os.path.getsize(p3))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
