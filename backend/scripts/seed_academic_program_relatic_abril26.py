"""
Carga/actualiza programas Relatic (Abril 26) en AcademicProgram desde un JSON fijo.
Idempotente: upsert por organization_id + slug, planes por program_id + code.

Uso (desde el directorio backend, con venv y DATABASE_URL):
  python3 scripts/seed_academic_program_relatic_abril26.py <organization_id>

``total_amount`` y ``installment_amount`` de cada plan están en USD; se almacenan
centesimales en ``total_amount_cents``.

Relatic suele tener un solo plan de precio por programa; en la pantalla pública
se explica monto/cuotas; el **método** de pago (Stripe, PayPal, etc.) lo elige
el usuario en el checkout, no en ``pricing_plans`` del JSON.
"""
from __future__ import annotations

import json
import os
import sys

# Raíz: .../app/backend
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

JSON_RELPATH = os.path.join('data', 'relatic_academic_programs.json')


def _cents_from_money(value) -> int:
    if value is None:
        return 0
    return int(round(float(value) * 100))


def _bool(v, default=True) -> bool:
    if v is None:
        return default
    return bool(v)


def _upsert_plans(prog, plans_raw: list) -> tuple[int, int]:
    from app import AcademicProgramPricingPlan, db

    created, updated = 0, 0
    for raw in plans_raw or []:
        code = (raw.get('code') or '').strip().lower()
        if not code:
            continue
        row = AcademicProgramPricingPlan.query.filter_by(program_id=prog.id, code=code).first()
        name = (raw.get('name') or 'Plan').strip()
        cur = (raw.get('currency') or prog.currency or 'USD').upper()
        total_c = _cents_from_money(raw.get('total_amount'))
        inst = raw.get('installment_count')
        inst = int(inst) if inst is not None else 1
        inst_amt = float(raw.get('installment_amount') or 0)
        desc = (raw.get('description') or '').strip() or None
        active = _bool(raw.get('is_active'), True)
        sort_order = int(raw.get('sort_order', 0))

        if row is None:
            row = AcademicProgramPricingPlan(
                program_id=prog.id,
                name=name,
                code=code,
                currency=cur,
                total_amount_cents=total_c,
                installment_count=inst,
                installment_amount=inst_amt,
                description=desc,
                is_active=active,
                sort_order=sort_order,
            )
            db.session.add(row)
            created += 1
        else:
            row.name = name
            row.currency = cur
            row.total_amount_cents = total_c
            row.installment_count = inst
            row.installment_amount = inst_amt
            row.description = desc
            row.is_active = active
            row.sort_order = sort_order
            updated += 1
    return created, updated


def main() -> int:
    if len(sys.argv) < 2:
        print('Uso: python3 scripts/seed_academic_program_relatic_abril26.py <organization_id>', file=sys.stderr)
        return 2
    org_id = int(sys.argv[1])
    data_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), JSON_RELPATH)
    with open(data_path, encoding='utf-8') as f:
        programs: list[dict] = json.load(f)

    from app import app, db
    from models.academic_program import AcademicProgram
    from models.saas import SaasOrganization

    created_p, updated_p = 0, 0
    created_plans, updated_plans = 0, 0
    org_name = ''

    with app.app_context():
        org = SaasOrganization.query.get(org_id)
        if org is None:
            raise SystemExit(f'No existe organization_id={org_id} en saas_organization (SaasOrganization).')
        org_name = (org.name or '').strip()
        for raw in programs:
            slug = (raw.get('slug') or '').strip().lower()
            if not slug:
                print('Omisión: registro sin slug', file=sys.stderr)
                continue
            prog = AcademicProgram.query.filter_by(organization_id=org_id, slug=slug).first()
            name = (raw.get('name') or slug).strip()
            if prog is None:
                # name NOT NULL: no hacer flush hasta tener al menos name asignado
                prog = AcademicProgram(organization_id=org_id, slug=slug, name=name)
                db.session.add(prog)
                created_p += 1
            else:
                updated_p += 1
            status = (raw.get('status') or 'published').strip().lower()
            hours_val = raw.get('hours')
            hours_s = None
            if hours_val is not None and hours_val != '':
                hours_s = str(hours_val)

            prog.name = name
            prog.program_type = (raw.get('program_type') or 'curso').strip().lower() or 'curso'
            prog.category = (raw.get('category') or '').strip() or None
            prog.short_description = (raw.get('short_description') or '').strip() or None
            prog.long_description = (raw.get('long_description') or '').strip() or None
            prog.modality = (raw.get('modality') or '').strip() or None
            prog.duration_text = (raw.get('duration_text') or '').strip() or None
            prog.hours = hours_s
            prog.language = (raw.get('language') or 'Español').strip() or None
            img = (raw.get('image_url') or '').strip()
            prog.image_url = img or None
            flyer = (raw.get('flyer_url') or '').strip()
            prog.flyer_url = flyer or None
            pf = raw.get('price_from')
            prog.price_from = float(pf) if pf is not None else 0.0
            prog.currency = (raw.get('currency') or 'USD').strip().upper() or 'USD'
            prog.status = status if status in ('draft', 'published', 'archived') else 'published'

            db.session.flush()  # id para planes nuevos
            cadd, uadd = _upsert_plans(prog, raw.get('pricing_plans') or [])
            created_plans += cadd
            updated_plans += uadd
            db.session.commit()
            print(f"OK: org={org_id} slug={slug} program_id={prog.id}")

    print('---')
    print(f"Organización: {org_id} - {org_name}")
    print(f"Programas creados: {created_p}")
    print(f"Programas actualizados: {updated_p}")
    print(f"Planes creados: {created_plans}")
    print(f"Planes actualizados: {updated_plans}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
