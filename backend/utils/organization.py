"""
Multi-tenant: organización activa = sesión.
Anónimos: sin organization_id (None) — no usar DEFAULT_ORGANIZATION_ID en request web.
"""
import os

from flask import has_request_context, session
from flask_login import current_user
from sqlalchemy import false as sql_false

# Valores del selector "volver a mi organización" (no usar literales sueltos)
ORG_HOME = '__home__'
ORG_NONE = '__none__'


def _clamp_org_id(value):
    """
    PK en saas_organization es 1, 2, … (SQLite/autoincrement). No existe id 0.
    Si DEFAULT_ORGANIZATION_ID=0 en env o sesión corrupta, se fuerza ≥ 1.
    """
    try:
        oid = int(value)
    except (TypeError, ValueError):
        return 1
    return oid if oid >= 1 else 1


def single_tenant_default_only():
    """
    Modo alineación: una sola empresa activa (id 1).
    Por defecto ACTIVO salvo NODEONE_SINGLE_TENANT_ONLY=0|false|no.
    """
    v = (os.environ.get('NODEONE_SINGLE_TENANT_ONLY') or '1').strip().lower()
    return v not in ('0', 'false', 'no', 'off')


def default_organization_id():
    """
    Org canónica del runtime.
    En modo single-tenant siempre es 1 (primera empresa en BD), ignorando
    DEFAULT_ORGANIZATION_ID en env (evita quedar pegados a cia 2 por .env viejo).
    Nunca devuelve 0: no hay tenant «cero» en este esquema.
    """
    if single_tenant_default_only():
        return 1
    return _clamp_org_id(os.environ.get('DEFAULT_ORGANIZATION_ID', '1') or '1')


def get_user_home_organization_id(user=None):
    """
    Solo para: valor inicial al login / botón «mi organización».
    No usar para filtrar datos operativos.
    """
    u = user if user is not None else current_user
    if single_tenant_default_only():
        if u is not None and getattr(u, 'is_authenticated', False):
            return _clamp_org_id(getattr(u, 'organization_id', None) or 1)
        return default_organization_id()
    if u is None or not getattr(u, 'is_authenticated', False):
        return _clamp_org_id(os.environ.get('DEFAULT_ORGANIZATION_ID', '1') or '1')
    return _clamp_org_id(getattr(u, 'organization_id', None) or 1)


def get_current_organization_id():
    """
    Organización activa (sesión). Operativo: queries, APIs, vistas autenticadas.
    - Sin contexto de request (workers/scripts): DEFAULT_ORGANIZATION_ID.
    - Modo single-tenant: is_admin → sesión (selector); resto → user.organization_id (misma app, varias empresas).
    - Anónimo en request web: None (sin fuga por tenant por defecto).
    - Multi-tenant completo: sesión obligatoria (RuntimeError si falta).
    """
    if not has_request_context():
        return default_organization_id()
    if not getattr(current_user, 'is_authenticated', False):
        return None
    if single_tenant_default_only():
        if getattr(current_user, 'is_admin', False):
            raw = session.get('organization_id')
            if raw is None:
                return default_organization_id()
            return _clamp_org_id(raw)
        return _clamp_org_id(getattr(current_user, 'organization_id', None) or default_organization_id())
    raw = session.get('organization_id')
    if raw is None:
        raise RuntimeError('Authenticated user without organization_id in session')
    return _clamp_org_id(raw)


def user_has_access_to_organization(user, org_id):
    """Admin plataforma: cualquier org. Resto: solo su organization_id en BD."""
    if user is None or not getattr(user, 'is_authenticated', False):
        return False
    try:
        oid = int(org_id)
    except (TypeError, ValueError):
        return False
    if getattr(user, 'is_admin', False):
        return True
    if single_tenant_default_only():
        return oid == int(getattr(user, 'organization_id', None) or default_organization_id())
    return int(getattr(user, 'organization_id', None) or 1) == oid


def scoped_query(model):
    """
    Query base filtrada por organization_id de sesión.
    Anónimo / sin org activa → conjunto vacío (no filas).
    """
    if not hasattr(model, 'organization_id'):
        raise TypeError('scoped_query: el modelo no tiene organization_id: %s' % model)
    oid = get_current_organization_id()
    if oid is None:
        return model.query.filter(sql_false())
    return model.query.filter_by(organization_id=oid)


def payment_organization_id_for_user_id(user_id):
    """
    Tenant para PaymentConfig en workers/scripts: organization_id del usuario.
    Sin usuario o usuario inexistente → default_organization_id().
    """
    if not user_id:
        return default_organization_id()
    from models.users import User

    u = User.query.get(int(user_id))
    if u is None:
        return default_organization_id()
    return _clamp_org_id(getattr(u, 'organization_id', None) or default_organization_id())


def platform_visible_organization_ids():
    """
    Lista blanca opcional de tenants visibles en admin (selector lateral, empresas, módulos SaaS).

    EASYNODEONE_PLATFORM_VISIBLE_ORG_IDS=1,2 → solo esas filas; el resto se oculta en UI y,
    en bootstrap, se desactiva y se reasignan usuarios a la org por defecto.

    Vacío o ausente → sin filtro (comportamiento anterior).
    """
    raw = (os.environ.get('EASYNODEONE_PLATFORM_VISIBLE_ORG_IDS') or '').strip()
    if not raw:
        return None
    out = set()
    for part in raw.split(','):
        part = part.strip()
        if not part:
            continue
        try:
            out.add(int(part))
        except ValueError:
            continue
    return out or None


def payment_organization_id_for_request():
    """
    Org para checkout web autenticado: sesión operativa o, si falta (p. ej. RuntimeError),
    organización «home» del usuario — misma idea que datos del carrito por tenant.
    """
    if not has_request_context():
        return default_organization_id()
    if not getattr(current_user, 'is_authenticated', False):
        return default_organization_id()
    try:
        return _clamp_org_id(get_current_organization_id())
    except RuntimeError:
        return _clamp_org_id(get_user_home_organization_id())
