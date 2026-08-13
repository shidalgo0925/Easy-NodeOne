"""Correo informativo al registrar un Cliente EN1 (cualquier producto o alta manual)."""

from __future__ import annotations

import html as html_module
import os
import secrets
from datetime import datetime, timedelta
from typing import Any


EMAIL_TYPE = 'customer_registration_info'
_PWD_ALPHABET = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789'


def new_temporary_password() -> str:
    """Contraseña temporal legible (12 caracteres en 3 grupos)."""
    raw = ''.join(secrets.choice(_PWD_ALPHABET) for _ in range(12))
    return f'{raw[:4]}-{raw[4:8]}-{raw[8:12]}'


def _already_sent(*, to_email: str) -> bool:
    from models.communications import EmailLog

    mail = (to_email or '').strip().lower()
    if not mail:
        return True
    return (
        EmailLog.query.filter(
            EmailLog.email_type == EMAIL_TYPE,
            EmailLog.status == 'sent',
            EmailLog.recipient_email.ilike(mail),
        ).first()
        is not None
    )


def _product_label(product_code: str | None) -> str | None:
    code = (product_code or '').strip().lower()
    if not code:
        return None
    try:
        from nodeone.core.platform.product_registry import ProductRegistry

        row = ProductRegistry.get(code)
        if row is not None:
            return (row.name or code).strip() or code
    except Exception:
        pass
    return code


def _base_url(branding: dict[str, Any] | None = None) -> str:
    from flask import has_request_context, request

    if has_request_context() and request:
        return request.url_root.rstrip('/')
    branded = ((branding or {}).get('base_url') or '').strip().rstrip('/')
    if branded:
        return branded
    return (os.getenv('BASE_URL') or 'https://appdev.easynodeone.com').strip().rstrip('/')


def ensure_email_verification_url(user: Any) -> str | None:
    """Crea o reutiliza token de verificación. None si ya está verificado o no hay user."""
    if user is None or getattr(user, 'email_verified', False):
        return None
    from nodeone.core.db import db
    from utils.validators import generate_verification_token

    token = getattr(user, 'email_verification_token', None)
    expires = getattr(user, 'email_verification_token_expires', None)
    if not token or (expires and expires < datetime.utcnow()):
        token = generate_verification_token()
        user.email_verification_token = token
        user.email_verification_token_expires = datetime.utcnow() + timedelta(hours=24)
        user.email_verification_sent_at = datetime.utcnow()
        db.session.commit()
    return f'{_base_url()}/verify-email/{token}'


def payment_method_labels(organization_id: int) -> list[str]:
    try:
        from nodeone.services.organization_payment_methods import METHOD_CATALOG, list_methods_for_org

        rows = list_methods_for_org(int(organization_id), enabled_only=True)
        labels: list[str] = []
        for row in rows:
            label = (row.label or '').strip()
            if not label:
                label = str(METHOD_CATALOG.get(row.method_key, {}).get('label') or row.method_key)
            if label:
                labels.append(label)
        return labels
    except Exception:
        return []


def send_customer_registration_info_email(
    *,
    to_email: str,
    display_name: str,
    organization_id: int,
    user: Any | None = None,
    product_code: str | None = None,
    plan_code: str | None = None,
    related_id: int | None = None,
    temporary_password: str | None = None,
    include_verification: bool = True,
    include_payment_methods: bool = True,
) -> bool:
    """Aviso de registro: validación de correo, clave temporal y formas de pago.

    Idempotente. No rompe el alta si SMTP falla.
    """
    mail = (to_email or '').strip().lower()
    if not mail or '@' not in mail:
        return False
    try:
        if _already_sent(to_email=mail):
            return True
    except Exception:
        pass

    try:
        import app as M
        from email_templates import get_email_template_base

        oid = int(organization_id)
        ok_smtp, _ = M.apply_transactional_smtp_for_organization(oid)
        if not ok_smtp or not M.email_service:
            return False

        name = (display_name or '').strip() or mail
        product = _product_label(product_code)
        plan = (plan_code or '').strip() or None
        br = M._email_branding_from_organization_id(oid)
        org = br.get('organization_name') or 'Easy NodeOne'
        base = _base_url(br)
        login_url = f'{base}/login'
        subject = f'Registro recibido — {org}'

        extra = ''
        if product:
            extra += f'<p>Producto: <strong>{html_module.escape(product)}</strong>'
            if plan:
                extra += f' · plan <code>{html_module.escape(plan)}</code>'
            extra += '</p>'

        verify_html = ''
        if include_verification and user is not None:
            verify_url = ensure_email_verification_url(user)
            if verify_url:
                verify_html = f"""
            <h3>Validá tu correo</h3>
            <p>Para activar tu cuenta, confirmá este email (el enlace vence en 24 horas):</p>
            <p style="text-align:center;">
                <a href="{html_module.escape(verify_url)}" class="button">Validar correo</a>
            </p>
            <p style="font-size:13px;color:#555;">Si el botón no funciona, copiá esta URL:<br>
            {html_module.escape(verify_url)}</p>
                """

        pwd_html = ''
        temp = (temporary_password or '').strip()
        if temp:
            pwd_html = f"""
            <h3>Contraseña de acceso</h3>
            <p>Te asignamos una contraseña temporal de seguridad. Cambiala después de ingresar.</p>
            <p style="font-size:20px;letter-spacing:0.08em;text-align:center;">
                <strong>{html_module.escape(temp)}</strong>
            </p>
            <p style="text-align:center;">
                <a href="{html_module.escape(login_url)}" class="button">Ingresar</a>
            </p>
            """

        pay_html = ''
        if include_payment_methods:
            labels = payment_method_labels(oid)
            if labels:
                items = ''.join(f'<li>{html_module.escape(x)}</li>' for x in labels)
                pay_html = f"""
            <h3>Formas de pago</h3>
            <p>Podés completar el pago con:</p>
            <ul>{items}</ul>
                """
            else:
                pay_html = """
            <h3>Formas de pago</h3>
            <p>Las formas de pago disponibles se muestran en el checkout al confirmar tu plan.</p>
                """

        content = f"""
            <h2>Registro recibido</h2>
            <p>Hola <strong>{html_module.escape(name)}</strong>,</p>
            <p>Confirmamos tu registro como Cliente en {html_module.escape(str(org))}.</p>
            {extra}
            {verify_html}
            {pwd_html}
            {pay_html}
            <p>Si necesitás ayuda, respondé a este mensaje o escribinos a
            {html_module.escape(str(br.get('contact_email') or ''))}.</p>
        """
        html = get_email_template_base(
            subject,
            content,
            **{k: br.get(k) for k in ('organization_name', 'base_url', 'contact_email', 'org_tagline')},
        )
        recipient_name = name
        if user is not None:
            recipient_name = (
                f"{getattr(user, 'first_name', '') or ''} {getattr(user, 'last_name', '') or ''}".strip()
                or name
            )
        return bool(
            M.email_service.send_email(
                subject=subject,
                recipients=[mail],
                html_content=html,
                email_type=EMAIL_TYPE,
                related_entity_type='customer' if related_id else 'contact',
                related_entity_id=int(related_id) if related_id else (int(user.id) if user is not None else None),
                recipient_id=int(user.id) if user is not None else None,
                recipient_name=recipient_name[:200],
            )
        )
    except Exception as exc:
        print(f'⚠️ customer_registration_info: {exc}')
        return False
