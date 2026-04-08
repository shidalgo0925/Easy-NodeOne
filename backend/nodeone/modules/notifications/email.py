"""Notificaciones transaccionales para ventas/accounting."""


def send_quotation_email(quotation, customer, html_body=None):
    import app as M

    subject = f'Cotización {quotation.number}'
    body = html_body or (
        f"<h2>Cotización {quotation.number}</h2>"
        f"<p>Hola {getattr(customer, 'first_name', '')},</p>"
        f"<p>Tu cotización está lista.</p>"
        f"<p>Total: ${quotation.grand_total:.2f}</p>"
    )
    if not M.email_service:
        return False, 'email_service_unavailable'
    try:
        M.email_service.send_email(
            subject=subject,
            recipients=[customer.email],
            html_content=body,
            email_type='quotation_sent',
            related_entity_type='quotation',
            related_entity_id=quotation.id,
            recipient_id=customer.id,
            recipient_name=f"{getattr(customer, 'first_name', '')} {getattr(customer, 'last_name', '')}".strip(),
        )
        return True, None
    except Exception as e:
        return False, str(e)

