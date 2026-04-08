"""Registro de envíos en EmailLog (extraído de app.py)."""

from datetime import datetime


def log_email_sent(
    recipient_email,
    subject,
    html_content=None,
    text_content=None,
    email_type=None,
    related_entity_type=None,
    related_entity_id=None,
    recipient_id=None,
    recipient_name=None,
    status='sent',
    error_message=None,
):
    """Registrar un email enviado en EmailLog."""
    import app as M

    try:
        email_log = M.EmailLog(
            recipient_id=recipient_id,
            recipient_email=recipient_email,
            recipient_name=recipient_name or recipient_email,
            subject=subject,
            html_content=html_content[:5000] if html_content else None,
            text_content=text_content[:5000] if text_content else None,
            email_type=email_type or 'general',
            related_entity_type=related_entity_type,
            related_entity_id=related_entity_id,
            status=status,
            error_message=error_message[:1000] if error_message else None,
            sent_at=datetime.utcnow() if status == 'sent' else None,
        )
        M.db.session.add(email_log)
        M.db.session.commit()
        print(f"📧 Email registrado en log: {email_type or 'general'} → {recipient_email} ({status})")
    except Exception as e:
        print(f"❌ Error registrando email en log: {e}")
        import traceback

        traceback.print_exc()
        M.db.session.rollback()
