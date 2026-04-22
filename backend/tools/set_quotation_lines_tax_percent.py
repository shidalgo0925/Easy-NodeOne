#!/usr/bin/env python3
"""
Asigna un impuesto porcentual (p. ej. 7%%) a las líneas de cotización de una organización,
recalcula totales por cotización. Omite líneas de nota (descripción __NOTE__ ).

Uso desde backend/:
  ../venv/bin/python3 tools/set_quotation_lines_tax_percent.py --org 3 --rate 7
  ../venv/bin/python3 tools/set_quotation_lines_tax_percent.py --org 3 --rate 7 --dry-run
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


def _recompute_quote_totals(quotation):
    from nodeone.core.db import db
    from nodeone.modules.accounting.models import Tax
    from nodeone.modules.sales.models import QuotationLine
    from nodeone.services.tax_calculation import compute_line_amounts

    lines = QuotationLine.query.filter_by(quotation_id=quotation.id).all()
    subtotal = 0.0
    tax_total = 0.0
    grand = 0.0
    oid = quotation.organization_id
    for ln in lines:
        qty = float(ln.quantity or 0)
        pu = float(ln.price_unit or 0)
        tax = Tax.query.filter_by(id=ln.tax_id, organization_id=oid).first() if ln.tax_id else None
        s, t, tx = compute_line_amounts(qty, pu, tax)
        ln.subtotal = s
        ln.total = t
        subtotal += s
        tax_total += tx
        grand += t
    quotation.total = round(subtotal, 2)
    quotation.tax_total = round(tax_total, 2)
    quotation.grand_total = round(grand, 2)
    db.session.add(quotation)


def main() -> int:
    here = os.path.dirname(os.path.abspath(__file__))
    backend = os.path.dirname(here)
    os.chdir(backend)
    if backend not in sys.path:
        sys.path.insert(0, backend)
    try:
        from dotenv import load_dotenv

        app_dir = Path(backend).resolve().parent
        load_dotenv(app_dir / '.env')
        silo_env = app_dir.parent / '.env'
        if silo_env.is_file():
            load_dotenv(silo_env, override=True)
    except ImportError:
        pass

    parser = argparse.ArgumentParser(description='Asignar impuesto % a líneas de cotización.')
    parser.add_argument('--org', type=int, required=True, help='organization_id')
    parser.add_argument('--rate', type=float, default=7.0, help='Porcentaje (ej. 7 para 7%%)')
    parser.add_argument('--dry-run', action='store_true', help='Solo listar, no guardar')
    args = parser.parse_args()

    from sqlalchemy import func

    import app as app_module
    from nodeone.core.db import db
    from nodeone.modules.accounting.models import Tax
    from nodeone.modules.sales.models import Quotation, QuotationLine

    uri = app_module.app.config.get('SQLALCHEMY_DATABASE_URI') or ''
    safe = uri.split('@')[-1] if '@' in uri else uri
    print('DB:', safe[:120])

    org_id = int(args.org)
    rate = float(args.rate)

    with app_module.app.app_context():
        Tax.__table__.create(db.engine, checkfirst=True)
        Quotation.__table__.create(db.engine, checkfirst=True)
        QuotationLine.__table__.create(db.engine, checkfirst=True)

        tax = (
            Tax.query.filter(
                Tax.organization_id == org_id,
                Tax.computation == 'percent',
                func.abs(Tax.percentage - rate) < 0.000001,
                Tax.active.is_(True),
            )
            .order_by(Tax.id.asc())
            .first()
        )
        if tax is None:
            print(f'ERROR: No hay impuesto activo al {rate:g}% para organization_id={org_id}.')
            return 1

        print(f'Impuesto: id={tax.id} name={tax.name!r} rate={tax.percentage}% org={org_id}')

        lines = (
            QuotationLine.query.join(Quotation, QuotationLine.quotation_id == Quotation.id)
            .filter(Quotation.organization_id == org_id)
            .all()
        )

        to_update = []
        for ln in lines:
            raw = str(ln.description or '')
            if raw.startswith('__NOTE__ '):
                continue
            to_update.append(ln)

        print(f'Líneas a actualizar (excl. notas): {len(to_update)} / {len(lines)} líneas en cotizaciones org {org_id}')

        if args.dry_run:
            qids = sorted({ln.quotation_id for ln in to_update})
            print(f'Cotizaciones afectadas (dry-run): {len(qids)} → ids {qids[:20]}{"…" if len(qids) > 20 else ""}')
            return 0

        for ln in to_update:
            ln.tax_id = int(tax.id)

        qids = sorted({ln.quotation_id for ln in to_update})
        for qid in qids:
            q = db.session.get(Quotation, qid)
            if q is None:
                continue
            _recompute_quote_totals(q)

        db.session.commit()
        print(f'OK: {len(to_update)} líneas; {len(qids)} cotización(es) recalculada(s).')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
