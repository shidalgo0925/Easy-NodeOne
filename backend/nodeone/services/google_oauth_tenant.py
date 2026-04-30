"""Google OAuth por organización (multitenant): credenciales en BD con fallback a env."""

from __future__ import annotations

import os
import threading
from contextlib import contextmanager

_lock = threading.Lock()


def ensure_saas_organization_google_oauth_table(db, engine, printfn=None) -> None:
    from models.saas import SaasOrganizationGoogleOAuth

    SaasOrganizationGoogleOAuth.__table__.create(engine, checkfirst=True)


def get_google_oauth_client_credentials(organization_id: int) -> tuple[str | None, str | None]:
    """
    Devuelve (client_id, client_secret) para la org: fila en saas_organization_google_oauth
    si existe y está rellena; si no, GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET del entorno.
    """
    from models.saas import SaasOrganizationGoogleOAuth

    try:
        oid = int(organization_id)
    except (TypeError, ValueError):
        oid = 0
    if oid >= 1:
        row = SaasOrganizationGoogleOAuth.query.filter_by(organization_id=oid).first()
        if row:
            cid = (row.google_client_id or '').strip()
            sec = (row.google_client_secret or '').strip()
            if cid and sec:
                return cid, sec
    cid = (os.environ.get('GOOGLE_CLIENT_ID') or '').strip()
    sec = (os.environ.get('GOOGLE_CLIENT_SECRET') or '').strip()
    if cid and sec:
        return cid, sec
    return None, None


def google_oauth_configured_for_organization(organization_id: int) -> bool:
    cid, sec = get_google_oauth_client_credentials(organization_id)
    return bool(cid and sec)


@contextmanager
def apply_google_oauth_credentials_for_org(oauth_google_client, organization_id: int):
    """
    Sustituye client_id/client_secret en el cliente Authlib Google para esta petición.
    El cliente global se comparte entre workers: usar bajo lock (OAuth es corto).
    """
    cid, sec = get_google_oauth_client_credentials(organization_id)
    if not cid or not sec:
        yield False
        return
    with _lock:
        old_id = oauth_google_client.client_id
        old_sec = oauth_google_client.client_secret
        try:
            oauth_google_client.client_id = cid
            oauth_google_client.client_secret = sec
            yield True
        finally:
            oauth_google_client.client_id = old_id
            oauth_google_client.client_secret = old_sec
