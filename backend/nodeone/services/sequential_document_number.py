"""Siguiente número de documento por organización (Q-0001, INV-0001).

Evita ``COUNT + 1``, que repite números si hay huecos, borrados o importaciones
y rompe la restricción ``uq_*_org_number`` en Postgres.
"""

from __future__ import annotations

import re


def next_org_document_number(prefix: str, model, organization_id: int) -> str:
    """
    Devuelve el siguiente ``{prefix}-{dddd}`` libre para ``organization_id``.

    Solo considera filas cuyo ``number`` coincide exactamente con ``^PREFIX-\\d+$``.
    """
    rx = re.compile(rf'^{re.escape(prefix)}-(\d{{1,12}})\Z')
    max_seq = 0
    q = model.query.filter_by(organization_id=organization_id).with_entities(model.number)
    for (num,) in q:
        if not num:
            continue
        m = rx.match(str(num).strip())
        if m:
            max_seq = max(max_seq, int(m.group(1)))
    return f'{prefix}-{max_seq + 1:04d}'
