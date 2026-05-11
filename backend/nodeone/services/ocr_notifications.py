"""Notificaciones cuando un pago OCR requiere revisión manual."""


def send_ocr_review_notifications(payment, user, ocr_extracted_data):
    """Enviar notificaciones cuando OCR necesita revisión manual."""
    import app as M

    last_smtp = [None]
    try:
        admins = M.User.query.filter_by(is_admin=True, is_active=True).all()
        if not admins:
            print("⚠️ No hay administradores para notificar")
            return

        expected_amount = payment.amount / 100.0
        extracted_amount = ocr_extracted_data.get('amount') if ocr_extracted_data else None

        user_html = f"""
            <h2>Revisión de Pago Requerida</h2>
            <p>Hola {user.first_name},</p>
            <p>Hemos recibido tu comprobante de pago, pero necesitamos verificar algunos datos:</p>
            <ul>
                <li><strong>Monto esperado:</strong> ${expected_amount:.2f}</li>
                <li><strong>Monto en comprobante:</strong> ${extracted_amount:.2f} {'(detectado)' if extracted_amount else '(no detectado)'}</li>
                <li><strong>Método de pago:</strong> {payment.payment_method.title()}</li>
            </ul>
            <p>Nuestro equipo revisará tu comprobante y te notificará cuando se apruebe tu membresía.</p>
            <p>Saludos,<br>Equipo Easy NodeOne</p>
            """
        if M.email_service:
            oid_u = M.NotificationEngine._coerce_org_id(
                getattr(user, 'organization_id', None), M._infra_org_id_for_runtime()
            )
            if M.NotificationEngine._smtp_ready(oid_u, last_smtp):
                M.email_service.send_email(
                    subject='Revisión de Pago - Easy NodeOne',
                    recipients=[user.email],
                    html_content=user_html,
                    email_type='payment_review',
                    related_entity_type='payment',
                    related_entity_id=payment.id,
                    recipient_id=user.id,
                    recipient_name=f"{user.first_name} {user.last_name}",
                )

        admin_html = f"""
        <h2>Revisión de Pago Requerida</h2>
        <p>Se requiere revisión manual de un pago:</p>
        <ul>
            <li><strong>Usuario:</strong> {user.first_name} {user.last_name} ({user.email})</li>
            <li><strong>ID de Pago:</strong> {payment.id}</li>
            <li><strong>Monto esperado:</strong> ${expected_amount:.2f}</li>
            <li><strong>Monto detectado:</strong> ${extracted_amount:.2f} {'(detectado)' if extracted_amount else '(no detectado)'}</li>
            <li><strong>Método:</strong> {payment.payment_method.title()}</li>
            <li><strong>Referencia:</strong> {ocr_extracted_data.get('reference', 'N/A') if ocr_extracted_data else 'N/A'}</li>
            <li><strong>Fecha detectada:</strong> {ocr_extracted_data.get('date', 'N/A') if ocr_extracted_data else 'N/A'}</li>
            <li><strong>Banco detectado:</strong> {ocr_extracted_data.get('bank', 'N/A') if ocr_extracted_data else 'N/A'}</li>
        </ul>
        <p><a href="/admin/payments/review/{payment.id}">Revisar Pago</a></p>
        """
        if M.email_service:
            for admin in admins:
                oid_a = M.NotificationEngine._coerce_org_id(
                    getattr(admin, 'organization_id', None),
                    getattr(user, 'organization_id', None),
                    M._infra_org_id_for_runtime(),
                )
                if M.NotificationEngine._smtp_ready(oid_a, last_smtp):
                    M.email_service.send_email(
                        subject=f'Revisión de Pago Requerida - Pago #{payment.id}',
                        recipients=[admin.email],
                        html_content=admin_html,
                        email_type='payment_review_admin',
                        related_entity_type='payment',
                        related_entity_id=payment.id,
                        recipient_id=admin.id,
                        recipient_name=f"{admin.first_name} {admin.last_name}",
                    )

        print(f"✅ Notificaciones OCR enviadas para Payment ID: {payment.id}")
    except Exception as e:
        print(f"⚠️ Error enviando notificaciones OCR: {e}")
        import traceback

        traceback.print_exc()
    finally:
        M.apply_email_config_from_db()
