"""
Post-login: contexto de organización (sesión) y pantalla de selección visual.
"""
from __future__ import annotations


def organizations_for_session_after_login(user):
    """
    Organizaciones activas entre las que el usuario puede operar.
    - Miembro: membresías activas (user_organization) o compat organization_id.
    - Admin plataforma: todas las activas, filtradas por EASYNODEONE_PLATFORM_VISIBLE_ORG_IDS si aplica.
    """
    import app as M

    if user is None or not getattr(user, 'is_authenticated', False):
        return []

    from nodeone.services.user_organization import active_organization_ids_for_user
    from utils.organization import platform_visible_organization_ids

    allow = platform_visible_organization_ids()

    if not getattr(user, 'is_admin', False):
        ids = active_organization_ids_for_user(user)
        if not ids:
            return []
        rows = (
            M.SaasOrganization.query.filter(
                M.SaasOrganization.id.in_(list(ids)),
                M.SaasOrganization.is_active == True,  # noqa: E712
            )
            .order_by(M.SaasOrganization.name.asc(), M.SaasOrganization.id.asc())
            .all()
        )
        return rows

    rows = (
        M.SaasOrganization.query.filter_by(is_active=True)
        .order_by(M.SaasOrganization.name.asc(), M.SaasOrganization.id.asc())
        .all()
    )
    if allow is not None:
        rows = [o for o in rows if int(o.id) in allow]
    return rows


def save_last_selected_organization(user, org_id: int) -> None:
    """Persiste última empresa elegida (admin y miembros con varias organizaciones)."""
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
    if not hasattr(u, 'last_selected_organization_id'):
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

    from nodeone.services.user_organization import active_organization_ids_for_user

    if M.single_tenant_default_only():
        M.ensure_canonical_saas_organization_usable()

    host_org_id = M._organization_id_from_request_host(req)
    try:
        host_int = int(host_org_id) if host_org_id is not None else None
    except (TypeError, ValueError):
        host_int = None

    if not getattr(user, 'is_admin', False):
        mids = active_organization_ids_for_user(user)
        if not mids:
            return 'error', 'Tu usuario no tiene organización asignada.'
        active_orgs = M.SaasOrganization.query.filter(
            M.SaasOrganization.id.in_(list(mids)),
            M.SaasOrganization.is_active == True,  # noqa: E712
        ).all()
        if not active_orgs:
            return 'error', 'La organización asignada a tu usuario no está disponible.'
        mids_active = {int(o.id) for o in active_orgs}
        # Si el host (subdominio) no coincide con ninguna membresía, no bloquear el login:
        # se trata como acceso "genérico" y se usa última org / selector (evita quedar en /login sin entrar).
        if host_int is not None and host_int not in mids_active:
            host_int = None

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
        # Varias empresas (len>1 ya garantizado aquí): anclar al subdominio/host si aplica;
        # si no hay tenant en el host (login genérico), pantalla de selección.
        if host_int is not None and any(int(o.id) == host_int for o in orgs):
            oid = host_int
            M.session['organization_id'] = oid
            M.session.pop('require_org_selection', None)
            save_last_selected_organization(user, oid)
            return 'ok', None
        if host_int is None:
            try:
                last_id = int(getattr(user, 'last_selected_organization_id', None) or 0)
            except (TypeError, ValueError):
                last_id = 0
            if last_id > 0 and any(int(o.id) == last_id for o in orgs):
                M.session['organization_id'] = last_id
                M.session.pop('require_org_selection', None)
                save_last_selected_organization(user, last_id)
                return 'ok', None
            try:
                primary = int(getattr(user, 'organization_id', None) or 0)
            except (TypeError, ValueError):
                primary = 0
            if primary > 0 and any(int(o.id) == primary for o in orgs):
                M.session['organization_id'] = primary
                M.session.pop('require_org_selection', None)
                save_last_selected_organization(user, primary)
                return 'ok', None
            M.session['require_org_selection'] = True
            M.session.pop('organization_id', None)
            return 'pick', None
        # Host distinto a las empresas elegibles: mismo criterio que arriba — elegir en pantalla.
        M.session['require_org_selection'] = True
        M.session.pop('organization_id', None)
        return 'pick', None

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
