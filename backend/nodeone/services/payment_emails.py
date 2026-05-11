"""Emails de confirmación de pago / membresía (extraído de app.py)."""

from nodeone.services.email_log import log_email_sent


def send_payment_confirmation_email(user, payment, subscription):
    """Enviar email de confirmación de pago (plantilla BD del tenant + SMTP transaccional)."""
    import app as M

    oid_mail = int(getattr(user, 'organization_id', None) or M._infra_org_id_for_runtime())
    try:
        ok_smtp, _ = M.apply_transactional_smtp_for_organization(oid_mail)
        if not ok_smtp or not M.email_service:
            raise RuntimeError('SMTP transaccional no disponible para la organización del usuario')
        html_content, subj_mail = M.render_membership_payment_email_for_org(
            user, payment, subscription, oid_mail, strict_tenant_logo=False
        )
        M.email_service.send_email(
            subject=subj_mail,
            recipients=[user.email],
            html_content=html_content,
            email_type='membership_payment',
            related_entity_type='payment',
            related_entity_id=payment.id,
            recipient_id=user.id,
            recipient_name=f'{user.first_name} {user.last_name}',
        )
    except Exception as e:
        print(f'Error sending email: {e}')
        log_email_sent(
            recipient_email=user.email,
            subject='Confirmación de Pago - Easy NodeOne',
            html_content='',
            email_type='membership_payment',
            related_entity_type='payment',
            related_entity_id=payment.id,
            recipient_id=user.id,
            recipient_name=f'{user.first_name} {user.last_name}',
            status='failed',
            error_message=str(e),
        )
    finally:
        M.apply_email_config_from_db()
