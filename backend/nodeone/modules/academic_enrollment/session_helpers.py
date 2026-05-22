"""Sesión para retomar inscripción tras registro/login."""
from __future__ import annotations

from flask import session, url_for


def capture_utm_from_request(req) -> None:
    for key in ('utm_source', 'utm_campaign', 'utm_medium'):
        val = (req.args.get(key) or '').strip()[:120]
        if val:
            session[key] = val


def set_pending_inscription(
    slug: str,
    plan_code: str,
    organization_id: int | None = None,
    *,
    return_url: str | None = None,
) -> None:
    slug = (slug or '').strip().lower()
    plan_code = (plan_code or '').strip().lower()
    if not slug or not plan_code:
        return
    session['pending_program_slug'] = slug
    session['pending_plan_code'] = plan_code
    if organization_id is not None:
        session['pending_organization_id'] = int(organization_id)
    session['pending_return_url'] = return_url or url_for(
        'payments.diplomado_continuar', slug=slug, plan=plan_code
    )
    session.modified = True


def clear_pending_inscription() -> None:
    for key in (
        'pending_program_slug',
        'pending_plan_code',
        'pending_organization_id',
        'pending_return_url',
    ):
        session.pop(key, None)


def pending_continuar_url() -> str | None:
    slug = (session.get('pending_program_slug') or '').strip().lower()
    plan = (session.get('pending_plan_code') or '').strip().lower()
    if not slug or not plan:
        return None
    return url_for('payments.diplomado_continuar', slug=slug, plan=plan)
