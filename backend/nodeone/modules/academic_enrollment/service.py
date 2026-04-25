"""Lógica de inscripción a programas definidos en BD (AcademicProgram)."""
from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

log = logging.getLogger(__name__)


def _org_id_for_enrollment_tenant() -> int:
    from app import default_organization_id, tenant_data_organization_id

    try:
        return int(tenant_data_organization_id())
    except Exception:
        return int(default_organization_id())


def _org_id_for_cart_user(user) -> int:
    from app import default_organization_id, _catalog_org_for_member_and_theme

    if user is None:
        return int(default_organization_id())
    try:
        return int(
            getattr(user, 'organization_id', None) or _catalog_org_for_member_and_theme() or default_organization_id()
        )
    except Exception:
        return int(default_organization_id())


def get_published_program_by_slug(organization_id: int, slug: str):
    from app import AcademicProgram

    slug = (slug or '').strip().lower()
    if not slug:
        return None
    return (
        AcademicProgram.query.filter_by(
            organization_id=int(organization_id), slug=slug, status='published'
        ).first()
    )


def find_published_academic_program_for_inscripcion(slug: str):
    """
    1) ``organization_id`` vía host (incl. mapa apps.relatic.org → relatic, etc.)
    2) Si no hay fila, un solo ``AcademicProgram`` publicado con ese ``slug`` en toda la BD.
    """
    from flask import has_request_context, request
    from app import AcademicProgram, _organization_id_from_request_host

    slug = (slug or '').strip().lower()
    if not slug or not has_request_context():
        return None
    oid = _organization_id_from_request_host(request)
    if oid is not None:
        p = get_published_program_by_slug(int(oid), slug)
        if p is not None:
            return p
    all_pub = (
        AcademicProgram.query.filter_by(slug=slug, status='published')
        .order_by(AcademicProgram.id.asc())
        .all()
    )
    if len(all_pub) == 1:
        return all_pub[0]
    return None


def list_active_plans_for_program(program) -> list:
    from app import AcademicProgramPricingPlan

    return (
        program.pricing_plans.filter_by(is_active=True)
        .order_by(AcademicProgramPricingPlan.sort_order, AcademicProgramPricingPlan.id)
        .all()
    )


def resolve_pricing_for_cart(organization_id: int, slug: str, plan_code: str) -> tuple[Any, ...] | None:
    """
    (product_id, name, desc, unit_price_cents_float, metadata) o None.
    """
    p = get_published_program_by_slug(organization_id, slug)
    if p is None:
        return None
    code = (plan_code or '').strip().lower()
    from app import AcademicProgramPricingPlan

    row = AcademicProgramPricingPlan.query.filter_by(program_id=p.id, code=code, is_active=True).first()
    if row is None:
        return None
    name = f'{p.name} — {row.name}'
    desc = (row.description or '').strip() or name
    cents = int(row.total_amount_cents)
    pid = int(hashlib.md5(f'acprog:{p.id}:plan:{row.id}'.encode()).hexdigest()[:8], 16) % 1_000_000
    meta = {
        'academic_program_id': p.id,
        'academic_pricing_plan_id': row.id,
        'plan_code': row.code,
        'program_slug': p.slug,
        'currency': (row.currency or p.currency or 'USD').upper(),
    }
    return (pid, name, desc, float(cents), meta)


def _clear_academic_program_lines_from_cart(user_id: int) -> None:
    from app import CartItem, db
    from _app.modules.payments import repository

    cart = repository.get_or_create_cart(user_id)
    CartItem.query.filter_by(cart_id=cart.id, product_type='academic_program').delete(synchronize_session=False)
    db.session.commit()


def try_add_academic_program_to_cart(user_id: int, slug: str, plan_key: str) -> tuple[bool | None, str | None]:
    """
    (True, None) éxito; (False, err) error; (None, None) delegar a IIUS legacy.
    """
    from app import AcademicProgramEnrollment, User, db
    from _app.modules.payments import repository
    from _app.modules.payments.service import clear_diplomado_lines_from_cart

    uid = int(user_id)
    user = User.query.get(uid)
    if not user:
        return False, 'Usuario no encontrado'
    oid = _org_id_for_cart_user(user)
    from app import _organization_id_from_request_host, AcademicProgram
    from flask import has_request_context, request

    host_oid = None
    if has_request_context():
        raw_h = _organization_id_from_request_host(request)
        host_oid = int(raw_h) if raw_h is not None else None
    to_try: list[int | None] = [host_oid, int(oid)]
    seen: set[int] = set()
    res = None
    for cand in to_try:
        if cand is None or cand in seen:
            continue
        seen.add(int(cand))
        res = resolve_pricing_for_cart(int(cand), slug, plan_key)
        if res is not None:
            break
    if res is None:
        cands = AcademicProgram.query.filter_by(slug=slug, status='published').all()
        if len(cands) == 1:
            res = resolve_pricing_for_cart(int(cands[0].organization_id), slug, plan_key)
    if res is None:
        p = get_published_program_by_slug(oid, slug)
        if p is None:
            return None, None
        return False, 'Plan o programa no válido'

    product_id, product_name, product_description, unit_price, metadata = res

    _clear_academic_program_lines_from_cart(uid)
    clear_diplomado_lines_from_cart(uid)

    plan_id = metadata.get('academic_pricing_plan_id')
    program_id = metadata.get('academic_program_id')
    from app import AcademicProgram

    prog = AcademicProgram.query.get(int(program_id)) if program_id else None
    enroll_org = int(prog.organization_id) if prog is not None else oid
    en = (
        AcademicProgramEnrollment.query.filter_by(
            user_id=uid, program_id=program_id, status='pending_payment'
        )
        .order_by(AcademicProgramEnrollment.id.desc())
        .first()
    )
    if en is None:
        en = AcademicProgramEnrollment(
            organization_id=enroll_org,
            program_id=program_id,
            user_id=uid,
            pricing_plan_id=plan_id,
            status='pending_payment',
            payment_status='pending',
        )
        db.session.add(en)
        db.session.flush()
    else:
        en.pricing_plan_id = plan_id
        en.organization_id = enroll_org
    metadata['enrollment_id'] = en.id

    repository.add_to_cart(
        uid,
        'academic_program',
        product_id,
        product_name,
        float(unit_price),
        1,
        product_description,
        metadata,
    )
    return True, None


def process_academic_program_items_after_payment(cart, payment) -> None:
    """Marca matrículas asociadas a ítems ``academic_program`` del carrito pagado."""
    from app import AcademicProgramEnrollment, db

    for item in cart.items:
        if item.product_type != 'academic_program' or not item.item_metadata:
            continue
        try:
            meta = json.loads(item.item_metadata) if isinstance(item.item_metadata, str) else item.item_metadata
        except Exception:
            continue
        eid = meta.get('enrollment_id')
        if not eid:
            continue
        en = AcademicProgramEnrollment.query.get(int(eid))
        if en and en.user_id == payment.user_id and en.status == 'pending_payment':
            line_free = float(getattr(item, 'unit_price', 0) or 0) == 0.0
            pay_free = int(getattr(payment, 'amount', 0) or 0) == 0
            is_free = line_free or pay_free
            if is_free:
                en.status = 'confirmed'
                en.payment_status = 'free'
            else:
                en.status = 'paid'
                en.payment_status = 'paid'
            en.payment_id = payment.id
            en.confirmed_at = payment.paid_at or en.confirmed_at
            db.session.add(en)
    # El commit lo hace ``process_cart_after_payment`` del monolito.
