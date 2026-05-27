#!/usr/bin/env python3
"""
PASO 1 IIUS: upsert catálogo académico desde data/iius_academic_catalog.json.

Idempotente por (organization_id, slug). Actualiza metadatos y planes; no borra
image_url/flyer_url existentes si el JSON no los trae.

  python3 scripts/seed_iius_academic_catalog_paso1.py [organization_id]
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'iius_academic_catalog.json')

_PLAN_LABELS = {
    'full': ('Pago completo', '20% dto. incluido'),
    '6': ('Plan 6 cuotas', ''),
    '10': ('Plan 10 cuotas', ''),
}


def _load_catalog() -> list[dict]:
    with open(_DATA, encoding='utf-8') as f:
        data = json.load(f)
    return list(data.get('programs') or [])


def _upsert_plans_from_diplomados(program, legacy: dict, AcademicProgramPricingPlan, db) -> int:
    n = 0
    for so, (plan_key, row) in enumerate((legacy.get('plans') or {}).items()):
        cents, _cart_name, desc = row
        pl_name, disc = _PLAN_LABELS.get(plan_key, (f'Plan {plan_key}', ''))
        inst = 6 if plan_key == '6' else (10 if plan_key == '10' else None)
        existing = AcademicProgramPricingPlan.query.filter_by(program_id=program.id, code=plan_key).first()
        if existing:
            existing.name = pl_name
            existing.currency = 'USD'
            existing.total_amount_cents = int(cents)
            existing.installment_count = inst
            existing.discount_label = disc
            existing.description = desc
            existing.is_active = True
            existing.sort_order = so
        else:
            db.session.add(
                AcademicProgramPricingPlan(
                    program_id=program.id,
                    name=pl_name,
                    code=plan_key,
                    currency='USD',
                    total_amount_cents=int(cents),
                    installment_count=inst,
                    discount_label=disc,
                    description=desc,
                    is_active=True,
                    sort_order=so,
                )
            )
        n += 1
    return n


def _upsert_plans_from_json(program, plans: list[dict], AcademicProgramPricingPlan, db) -> int:
    n = 0
    for so, row in enumerate(plans):
        code = (row.get('code') or 'full').strip()
        name = (row.get('name') or 'Pago completo').strip()
        total_usd = float(row.get('total_usd') or 0)
        cents = int(round(total_usd * 100))
        desc = (row.get('description') or '').strip() or None
        existing = AcademicProgramPricingPlan.query.filter_by(program_id=program.id, code=code).first()
        if existing:
            existing.name = name
            existing.currency = 'USD'
            existing.total_amount_cents = cents
            existing.installment_count = row.get('installment_count')
            existing.discount_label = row.get('discount_label')
            existing.description = desc
            existing.is_active = True
            existing.sort_order = so
        else:
            db.session.add(
                AcademicProgramPricingPlan(
                    program_id=program.id,
                    name=name,
                    code=code,
                    currency='USD',
                    total_amount_cents=cents,
                    installment_count=row.get('installment_count'),
                    discount_label=row.get('discount_label'),
                    description=desc,
                    is_active=True,
                    sort_order=so,
                )
            )
        n += 1
    return n


def main() -> int:
    org_id = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    catalog = _load_catalog()

    from app import app, db
    from _app.modules.payments.service import DIPLOMADOS_IIUS
    from models.academic_program import AcademicProgram, AcademicProgramPricingPlan

    created = updated = 0
    with app.app_context():
        for entry in catalog:
            slug = (entry.get('slug') or '').strip()
            if not slug:
                continue
            row = AcademicProgram.query.filter_by(organization_id=org_id, slug=slug).first()
            is_new = row is None
            if is_new:
                row = AcademicProgram(organization_id=org_id, slug=slug, name=entry.get('name') or slug)
                db.session.add(row)

            row.name = (entry.get('name') or row.name or slug).strip()
            row.program_type = (entry.get('program_type') or row.program_type or 'curso').strip().lower()
            row.category = (entry.get('category') or '').strip() or None
            row.status = (entry.get('status') or 'published').strip().lower()
            row.modality = (entry.get('modality') or '').strip() or None
            row.duration_text = (entry.get('duration_text') or '').strip() or None
            row.hours = (entry.get('hours') or '').strip() or None
            row.language = (entry.get('language') or row.language or 'Español').strip() or 'Español'
            row.currency = (entry.get('currency') or 'USD').strip().upper()[:8] or 'USD'
            if entry.get('price_from') is not None:
                row.price_from = float(entry['price_from'])
            row.short_description = (entry.get('short_description') or '').strip() or None
            if entry.get('long_description'):
                row.long_description = (entry.get('long_description') or '').strip() or None
            if entry.get('image_url'):
                row.image_url = (entry.get('image_url') or '').strip() or None
            if entry.get('flyer_url'):
                row.flyer_url = (entry.get('flyer_url') or '').strip() or None

            db.session.flush()
            if entry.get('plans_from_diplomados_iius'):
                legacy = DIPLOMADOS_IIUS.get(slug)
                if not legacy:
                    print(f'WARN slug={slug}: plans_from_diplomados_iius pero no está en DIPLOMADOS_IIUS')
                else:
                    _upsert_plans_from_diplomados(row, legacy, AcademicProgramPricingPlan, db)
            elif entry.get('plans'):
                _upsert_plans_from_json(row, entry['plans'], AcademicProgramPricingPlan, db)

            db.session.commit()
            if is_new:
                created += 1
                print(f'CREATED id={row.id} slug={slug} category={row.category!r}')
            else:
                updated += 1
                print(f'UPDATED id={row.id} slug={slug} category={row.category!r} status={row.status}')

        published = (
            AcademicProgram.query.filter_by(organization_id=org_id, status='published')
            .order_by(AcademicProgram.category, AcademicProgram.slug)
            .all()
        )
        print(f'\n--- Resumen org={org_id}: created={created} updated={updated} published_total={len(published)} ---')
        by_cat: dict[str, list[str]] = {}
        for p in published:
            cat = p.category or '(sin categoría)'
            by_cat.setdefault(cat, []).append(p.slug)
        for cat in sorted(by_cat.keys()):
            print(f'  [{cat}] {len(by_cat[cat])} → {", ".join(by_cat[cat])}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
