"""Eliminación de usuario y dependencias (admin y scripts operativos)."""


class UserDeletionBlockedError(Exception):
    """El usuario no puede eliminarse por registros comerciales vinculados."""


def _commercial_deletion_blockers(user_id: int) -> list[str]:
    from nodeone.modules.accounting.models import Invoice
    from nodeone.modules.sales.models import Quotation
    from nodeone.modules.workshop.models import WorkshopOrder, WorkshopVehicle

    blockers: list[str] = []

    invoices = Invoice.query.filter_by(customer_id=user_id).order_by(Invoice.id).all()
    if invoices:
        sample = ', '.join(i.number for i in invoices[:5])
        extra = f' (+{len(invoices) - 5} más)' if len(invoices) > 5 else ''
        blockers.append(f'{len(invoices)} factura(s): {sample}{extra}')

    quotations = Quotation.query.filter_by(customer_id=user_id).order_by(Quotation.id).all()
    if quotations:
        sample = ', '.join(q.number for q in quotations[:5])
        extra = f' (+{len(quotations) - 5} más)' if len(quotations) > 5 else ''
        blockers.append(f'{len(quotations)} cotización(es): {sample}{extra}')

    order_count = WorkshopOrder.query.filter_by(customer_id=user_id).count()
    if order_count:
        blockers.append(f'{order_count} orden(es) de taller')

    vehicle_count = WorkshopVehicle.query.filter_by(customer_id=user_id).count()
    if vehicle_count:
        blockers.append(f'{vehicle_count} vehículo(s) de taller')

    return blockers


def _delete_commercial_data_for_user(user_id: int, *, db) -> None:
    """Elimina facturas, cotizaciones y taller del cliente (solo uso explícito / dev)."""
    from models.efactura import ElectronicInvoiceDocument, ElectronicInvoiceEventLog
    from nodeone.modules.accounting.models import Invoice
    from nodeone.modules.sales.models import Quotation
    from nodeone.modules.workshop.models import WorkshopOrder, WorkshopVehicle

    invoice_ids = [
        row.id for row in Invoice.query.filter_by(customer_id=user_id).with_entities(Invoice.id).all()
    ]
    quotation_ids = [
        row.id for row in Quotation.query.filter_by(customer_id=user_id).with_entities(Quotation.id).all()
    ]

    if invoice_ids:
        WorkshopOrder.query.filter(WorkshopOrder.invoice_id.in_(invoice_ids)).update(
            {'invoice_id': None}, synchronize_session=False
        )
    if quotation_ids:
        WorkshopOrder.query.filter(WorkshopOrder.quotation_id.in_(quotation_ids)).update(
            {'quotation_id': None}, synchronize_session=False
        )

    WorkshopOrder.query.filter_by(customer_id=user_id).delete(synchronize_session=False)
    WorkshopVehicle.query.filter_by(customer_id=user_id).delete(synchronize_session=False)

    if invoice_ids:
        doc_ids = [
            row.id
            for row in ElectronicInvoiceDocument.query.filter(
                ElectronicInvoiceDocument.invoice_id.in_(invoice_ids)
            ).with_entities(ElectronicInvoiceDocument.id).all()
        ]
        if doc_ids:
            ElectronicInvoiceEventLog.query.filter(
                ElectronicInvoiceEventLog.document_id.in_(doc_ids)
            ).delete(synchronize_session=False)
            ElectronicInvoiceDocument.query.filter(ElectronicInvoiceDocument.id.in_(doc_ids)).delete(
                synchronize_session=False
            )

    if quotation_ids:
        Invoice.query.filter(Invoice.origin_quotation_id.in_(quotation_ids)).update(
            {'origin_quotation_id': None}, synchronize_session=False
        )

    Invoice.query.filter_by(customer_id=user_id).delete(synchronize_session=False)
    Quotation.query.filter_by(customer_id=user_id).delete(synchronize_session=False)


def delete_user_and_related(user, *, db, force_commercial: bool = False) -> None:
    """Elimina un usuario y datos relacionados que bloquean el DELETE."""
    from models.academic import Student
    from models.appointments import ActivityLog, Appointment, AppointmentParticipant, Proposal
    from models.benefits import Membership
    from models.catalog import Cart, CartItem, HistoryTransaction, UserService
    from models.certificates import Certificate
    from models.communications import CampaignRecipient, EmailLog, EmailQueueItem, Notification
    from models.communication_rules import UserCommunicationPreference
    from models.email_notifications import Office365Request
    from models.events import (
        DiscountApplication,
        Event,
        EventCertificate,
        EventParticipant,
        EventRegistration,
    )
    from models.payments import Payment, Subscription
    from models.policies import PolicyAcceptance
    from models.users import SocialAuth
    from nodeone.modules.accounting.models import Invoice
    from nodeone.modules.crm_api.models import CrmLead
    from nodeone.modules.sales.models import Quotation
    from nodeone.modules.workshop.models import WorkshopOrder

    user_id = user.id

    Invoice.query.filter(
        Invoice.customer_id == user_id,
        Invoice.status.in_(('draft', 'cancelled')),
    ).delete(synchronize_session=False)
    Quotation.query.filter(
        Quotation.customer_id == user_id,
        Quotation.status.in_(('draft', 'cancelled')),
    ).delete(synchronize_session=False)

    if force_commercial:
        _delete_commercial_data_for_user(user_id, db=db)
    else:
        blockers = _commercial_deletion_blockers(user_id)
        if blockers:
            raise UserDeletionBlockedError(
                'No se puede eliminar el usuario porque tiene registros comerciales vinculados: '
                + '; '.join(blockers)
                + '. Reasigne o anule esos documentos primero.'
            )

    with db.session.no_autoflush:
        payments = Payment.query.filter_by(user_id=user_id).all()
        payment_ids = [p.id for p in payments]

        campaign_recipient_ids = [
            r.id
            for r in CampaignRecipient.query.filter_by(user_id=user_id).with_entities(CampaignRecipient.id).all()
        ]
        if campaign_recipient_ids:
            EmailQueueItem.query.filter(EmailQueueItem.recipient_id.in_(campaign_recipient_ids)).delete(
                synchronize_session=False
            )
        CampaignRecipient.query.filter_by(user_id=user_id).delete(synchronize_session=False)

        Membership.query.filter_by(user_id=user_id).delete(synchronize_session=False)

        sub_filters = [Subscription.user_id == user_id]
        if payment_ids:
            sub_filters.append(Subscription.payment_id.in_(payment_ids))
        Subscription.query.filter(db.or_(*sub_filters)).delete(synchronize_session=False)

        if payment_ids:
            Payment.query.filter(Payment.id.in_(payment_ids)).delete(synchronize_session=False)

        for registration in EventRegistration.query.filter_by(user_id=user_id).all():
            if registration.registration_status == 'confirmed':
                event = Event.query.get(registration.event_id)
                if event and event.registered_count and event.registered_count > 0:
                    event.registered_count -= 1
        EventRegistration.query.filter_by(user_id=user_id).delete(synchronize_session=False)

        participant_ids = [
            p.id
            for p in EventParticipant.query.filter_by(user_id=user_id).with_entities(EventParticipant.id).all()
        ]
        if participant_ids:
            EventCertificate.query.filter(EventCertificate.participant_id.in_(participant_ids)).delete(
                synchronize_session=False
            )
        EventCertificate.query.filter(EventCertificate.issued_by == user_id).update(
            {'issued_by': None}, synchronize_session=False
        )
        EventCertificate.query.filter(EventCertificate.revoked_by == user_id).update(
            {'revoked_by': None}, synchronize_session=False
        )
        EventParticipant.query.filter_by(user_id=user_id).delete(synchronize_session=False)

        Certificate.query.filter_by(user_id=user_id).delete(synchronize_session=False)
        Appointment.query.filter_by(user_id=user_id).delete(synchronize_session=False)
        Student.query.filter_by(user_id=user_id).delete(synchronize_session=False)
        UserService.query.filter_by(user_id=user_id).delete(synchronize_session=False)
        AppointmentParticipant.query.filter_by(user_id=user_id).delete(synchronize_session=False)
        PolicyAcceptance.query.filter_by(user_id=user_id).delete(synchronize_session=False)
        Office365Request.query.filter_by(user_id=user_id).delete(synchronize_session=False)
        UserCommunicationPreference.query.filter_by(user_id=user_id).delete(synchronize_session=False)

        if user.advisor_profile:
            db.session.delete(user.advisor_profile)

        Notification.query.filter_by(user_id=user_id).delete(synchronize_session=False)
        EmailLog.query.filter_by(recipient_id=user_id).delete(synchronize_session=False)
        ActivityLog.query.filter_by(user_id=user_id).delete(synchronize_session=False)

        cart = Cart.query.filter_by(user_id=user_id).first()
        if cart:
            CartItem.query.filter_by(cart_id=cart.id).delete(synchronize_session=False)
            db.session.delete(cart)

        SocialAuth.query.filter_by(user_id=user_id).delete(synchronize_session=False)
        DiscountApplication.query.filter_by(user_id=user_id).delete(synchronize_session=False)
        HistoryTransaction.query.filter_by(owner_user_id=user_id).update({'owner_user_id': None})
        HistoryTransaction.query.filter(HistoryTransaction.actor_id == user_id).update({'actor_id': None})

        Invoice.query.filter_by(created_by=user_id).update({'created_by': None}, synchronize_session=False)
        Invoice.query.filter_by(salesperson_user_id=user_id).update({'salesperson_user_id': None}, synchronize_session=False)
        Quotation.query.filter_by(created_by=user_id).update({'created_by': None}, synchronize_session=False)
        Quotation.query.filter_by(salesperson_user_id=user_id).update({'salesperson_user_id': None}, synchronize_session=False)
        WorkshopOrder.query.filter_by(advisor_id=user_id).update({'advisor_id': None}, synchronize_session=False)
        CrmLead.query.filter_by(user_id=user_id).update({'user_id': None}, synchronize_session=False)
        Payment.query.filter_by(validated_by_user_id=user_id).update({'validated_by_user_id': None}, synchronize_session=False)
        Proposal.query.filter_by(client_id=user_id).delete(synchronize_session=False)

        Event.query.filter_by(created_by=user_id).update({'created_by': None}, synchronize_session=False)
        Event.query.filter_by(moderator_id=user_id).update({'moderator_id': None}, synchronize_session=False)
        Event.query.filter_by(administrator_id=user_id).update({'administrator_id': None}, synchronize_session=False)
        Event.query.filter_by(speaker_id=user_id).update({'speaker_id': None}, synchronize_session=False)

        db.session.delete(user)
