"""Lógica de invitaciones a organización (token + email)."""
from __future__ import annotations

import secrets
from datetime import datetime, timedelta

from nodeone.services.user_organization import ensure_membership


def normalize_invite_email(email: str | None) -> str:
    return (email or '').strip().lower()


def default_invite_expiry_hours() -> int:
    return 168  # 7 días


def create_invite_record(
    organization_id: int,
    email: str,
    invited_by_user_id: int | None,
    role: str = 'user',
    expires_hours: int | None = None,
):
    """Crea fila pending; revoca otros pending del mismo org+email."""
    from nodeone.core.db import db
    from models.organization_invite import OrganizationInvite

    oid = int(organization_id)
    em = normalize_invite_email(email)
    if not em or '@' not in em:
        raise ValueError('email inválido')
    hrs = int(expires_hours) if expires_hours is not None else default_invite_expiry_hours()
    revoke_pending_invites_session(oid, em)
    token = secrets.token_urlsafe(32)[:48]
    row = OrganizationInvite(
        organization_id=oid,
        email=em,
        token=token,
        role=(role or 'user').strip() or 'user',
        status='pending',
        invited_by_user_id=invited_by_user_id,
        expires_at=datetime.utcnow() + timedelta(hours=hrs),
    )
    db.session.add(row)
    db.session.flush()
    return row


def revoke_pending_invites_session(organization_id: int, email: str) -> int:
    """Marca pending como revoked en la sesión actual (sin commit)."""
    from models.organization_invite import OrganizationInvite

    em = normalize_invite_email(email)
    n = (
        OrganizationInvite.query.filter_by(
            organization_id=int(organization_id),
            email=em,
            status='pending',
        ).update({'status': 'revoked'}, synchronize_session=False)
    )
    return int(n or 0)


def get_valid_invite_by_token(token: str | None):
    """Invitación pending y no expirada, o None."""
    from models.organization_invite import OrganizationInvite

    if not token or not str(token).strip():
        return None
    row = OrganizationInvite.query.filter_by(token=str(token).strip(), status='pending').first()
    if row is None:
        return None
    if row.expires_at and row.expires_at < datetime.utcnow():
        return None
    return row


def accept_invite_for_user(invite, user) -> None:
    """Vincula usuario a la org de la invitación y marca accepted."""
    from nodeone.core.db import db

    if invite.status != 'pending':
        return
    uid = int(getattr(user, 'id', 0) or 0)
    oid = int(invite.organization_id)
    ensure_membership(uid, oid, role=getattr(invite, 'role', None) or 'user')
    invite.status = 'accepted'
    invite.accepted_at = datetime.utcnow()
    invite.accepted_user_id = uid
    db.session.add(invite)


def send_invite_email(invite) -> tuple[bool, str | None]:
    """Envía correo con enlace /accept-invite/<token>."""
    import os

    import app as M

    from models.saas import SaasOrganization

    org = SaasOrganization.query.get(invite.organization_id)
    org_name = (getattr(org, 'name', None) or 'la organización').strip() or 'la organización'
    if not getattr(M, 'email_service', None):
        return False, 'email_service no configurado'

    base = ''
    try:
        if M.has_request_context() and M.request:
            base = M.request.url_root.rstrip('/')
    except Exception:
        pass
    if not base:
        base = (os.getenv('BASE_URL') or '').strip().rstrip('/') or 'https://app.example.com'
    link = f"{base}/accept-invite/{invite.token}"
    subject = f'Invitación a {org_name}'
    html = f"""<!DOCTYPE html><html><body style="font-family:system-ui,sans-serif;">
<p>Hola,</p>
<p>Has sido invitado a unirte a <strong>{org_name}</strong> en la plataforma.</p>
<p><a href="{link}">Aceptar invitación</a></p>
<p>Si el enlace no funciona, copia y pega en el navegador:<br><span style="word-break:break-all;">{link}</span></p>
<p>Este enlace caduca en varios días.</p>
</body></html>"""
    try:
        M.apply_email_config_from_db()
        ok = M.email_service.send_email(
            subject=subject,
            recipients=[invite.email],
            html_content=html,
            email_type='org_invite',
            related_entity_type='organization_invite',
            related_entity_id=invite.id,
        )
        return bool(ok), None if ok else 'send_email devolvió False'
    except Exception as e:
        return False, str(e)[:500]
