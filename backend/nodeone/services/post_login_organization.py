"""
Post-login: contexto de organización (sesión) y pantalla de selección visual.
"""
from __future__ import annotations


def organizations_for_session_after_login(user):
    """
    Organizaciones activas entre las que el usuario puede operar.
    - Miembro: solo su organization_id si está activa.
    - Admin plataforma: todas las activas, filtradas por EASYNODEONE_PLATFORM_VISIBLE_ORG_IDS si aplica.
    """
    import app as M

    if user is None or not getattr(user, 'is_authenticated', False):
        return []

    from utils.organization import platform_visible_organization_ids

    allow = platform_visible_organization_ids()

    if not getattr(user, 'is_admin', False):
        try:
            oid = int(getattr(user, 'organization_id', 0) or 0)
        except (TypeError, ValueError):
            oid = 0
        if oid < 1:
            return []
        org = M.SaasOrganization.query.filter_by(id=oid, is_active=True).first()
        return [org] if org is not None else []

    rows = (
        M.SaasOrganization.query.filter_by(is_active=True)
        .order_by(M.SaasOrganization.name.asc(), M.SaasOrganization.id.asc())
        .all()
    )
    if allow is not None:
        rows = [o for o in rows if int(o.id) in allow]
    return rows


def save_last_selected_organization(user, org_id: int) -> None:
    """Persiste última empresa elegida (admin multi-tenant)."""
    import app as M

    try:
        oid = int(org_id)
    except (TypeError, ValueError):
        return
    if oid < 1:
        return
    u = M.User.query.get(getattr(user, 'id', None))
    if u is None:
        return
    if not getattr(u, 'is_admin', False):
        return
    if getattr(u, 'last_selected_organization_id', None) == oid:
        return
    u.last_selected_organization_id = oid
    try:
        M.db.session.commit()
    except Exception:
        M.db.session.rollback()


def resolved_logo_url_for_org_card(org_id: int) -> str:
    """URL final para <img> en selector (requiere request context para url_for)."""
    from flask import url_for

    raw = organization_logo_url_for_picker(org_id)
    if not raw or not str(raw).strip():
        return url_for('static', filename='images/logo-easy-nodeone.svg')
    raw = str(raw).strip()
    if raw.startswith(('http://', 'https://')):
        return raw
    fn = raw.lstrip('/')
    if fn.startswith('static/'):
        fn = fn[7:]
    return url_for('static', filename=fn)


def organization_logo_url_for_picker(org_id: int) -> str | None:
    """Ruta relativa tipo static/... o URL absoluta guardada en settings; None = usar default en template."""
    import app as M

    try:
        oid = int(org_id)
    except (TypeError, ValueError):
        return None
    row = M.OrganizationSettings.query.filter_by(organization_id=oid).first()
    if row is None:
        return None
    url = (getattr(row, 'logo_url', None) or '').strip()
    return url or None


def finalize_post_login_organization(user, req):
    """
    Tras credenciales válidas: fija session['organization_id'] o marca require_org_selection.

    Returns
    -------
    tuple[str, str | None]
        ('ok', None) | ('pick', None) | ('error', mensaje)
    """
    import app as M

    if M.single_tenant_default_only():
        M.ensure_canonical_saas_organization_usable()

    host_org_id = M._organization_id_from_request_host(req)
    user_org_raw = getattr(user, 'organization_id', None)
    try:
        user_org_id = int(user_org_raw) if user_org_raw is not None else 0
    except (TypeError, ValueError):
        user_org_id = 0

    if not getattr(user, 'is_admin', False):
        if user_org_id < 1:
            return 'error', 'Tu usuario no tiene organización asignada.'
        user_org = M.SaasOrganization.query.get(user_org_id)
        if user_org is None or not getattr(user_org, 'is_active', True):
            return 'error', 'La organización asignada a tu usuario no está disponible.'
        if host_org_id is not None and host_org_id != user_org_id:
            return 'error', 'No tienes acceso a esta organización.'

    orgs = organizations_for_session_after_login(user)
    if not orgs:
        return 'error', 'No hay empresas activas disponibles para tu cuenta.'

    raw_pick = (req.form.get('organization_id') or req.form.get('saas_organization_id') or '').strip()
    if raw_pick and getattr(user, 'is_admin', False):
        try:
            cand = int(raw_pick)
        except (TypeError, ValueError):
            return 'error', 'Organización no válida.'
        org = M.SaasOrganization.query.get(cand)
        if org is None or not getattr(org, 'is_active', True):
            return 'error', 'Organización no disponible.'
        if not M.user_has_access_to_organization(user, cand):
            return 'error', 'No tienes acceso a esa organización.'
        if not any(int(o.id) == cand for o in orgs):
            return 'error', 'No tienes acceso a esa organización.'
        M.session['organization_id'] = cand
        M.session.pop('require_org_selection', None)
        save_last_selected_organization(user, cand)
        return 'ok', None

    if len(orgs) == 1:
        oid = int(orgs[0].id)
        M.session['organization_id'] = oid
        M.session.pop('require_org_selection', None)
        save_last_selected_organization(user, oid)
        return 'ok', None

    if not getattr(user, 'is_admin', False):
        oid = int(orgs[0].id)
        M.session['organization_id'] = oid
        M.session.pop('require_org_selection', None)
        return 'ok', None

    last_raw = getattr(user, 'last_selected_organization_id', None)
    try:
        last_id = int(last_raw) if last_raw is not None else None
    except (TypeError, ValueError):
        last_id = None
    if last_id is not None and any(int(o.id) == last_id for o in orgs):
        M.session['organization_id'] = last_id
        M.session.pop('require_org_selection', None)
        return 'ok', None

    M.session['require_org_selection'] = True
    M.session.pop('organization_id', None)
    return 'pick', None
