"""PaymentConfig dedicado por tenant cuando falta (idempotente)."""

from __future__ import annotations

from nodeone.core.db import db
from models.payments import PaymentConfig
from nodeone.services import organization_payment_methods as opm

_COPY_ATTRS = (
    'stripe_secret_key',
    'stripe_publishable_key',
    'stripe_webhook_secret',
    'paypal_client_id',
    'paypal_client_secret',
    'paypal_mode',
    'paypal_return_url',
    'paypal_cancel_url',
    'banco_general_merchant_id',
    'banco_general_api_key',
    'banco_general_shared_secret',
    'banco_general_api_url',
    'yappy_api_key',
    'yappy_merchant_id',
    'yappy_api_url',
    'yappy_directory_name',
    'yappy_qr_image_path',
    'yappy_business_name',
    'yappy_merchant_phone',
    'yappy_manual_instructions',
    'yappy_manual_admin_emails',
    'yappy_display_name',
    'yappy_phone_or_identifier',
    'yappy_instructions',
    'yappy_requires_receipt',
    'yappy_admin_validation_required',
    'intl_wire_beneficiary_name',
    'intl_wire_bank_name',
    'intl_wire_swift',
    'intl_wire_account',
    'intl_wire_account_type',
    'intl_wire_country',
    'intl_wire_instructions',
    'banco_general_beneficiary_name',
    'banco_general_bank_name',
    'banco_general_account_number',
    'banco_general_account_type',
    'use_environment_variables',
)


def dedicated_active_config(organization_id: int) -> PaymentConfig | None:
    return (
        PaymentConfig.query.filter_by(
            organization_id=int(organization_id),
            is_active=True,
        )
        .order_by(PaymentConfig.id.asc())
        .first()
    )


def clone_config_for_org(source: PaymentConfig, target_org_id: int) -> PaymentConfig:
    PaymentConfig.query.filter_by(organization_id=int(target_org_id)).update(
        {'is_active': False}
    )
    row = PaymentConfig(organization_id=int(target_org_id), is_active=True)
    for attr in _COPY_ATTRS:
        setattr(row, attr, getattr(source, attr, None))
    row.yappy_manual_enabled = False
    row.intl_wire_enabled = False
    db.session.add(row)
    db.session.flush()
    return row


def provision_missing_payment_configs(
    *,
    source_org_id: int = 1,
    target_org_ids: tuple[int, ...] | None = None,
) -> list[int]:
    """
    Crea PaymentConfig activo en tenants sin fila dedicada.
    Por defecto: todas las orgs excepto la fuente.
    """
    from models.saas import SaasOrganization

    source = dedicated_active_config(source_org_id)
    if source is None:
        source = PaymentConfig.get_active_config(organization_id=source_org_id)
    if source is None:
        return []

    if target_org_ids is None:
        target_org_ids = tuple(
            o.id
            for o in SaasOrganization.query.order_by(SaasOrganization.id).all()
            if int(o.id) != int(source_org_id)
        )

    created: list[int] = []
    for oid in target_org_ids:
        if dedicated_active_config(oid) is not None:
            continue
        clone_config_for_org(source, oid)
        created.append(int(oid))

    if created:
        db.session.commit()
        for oid in created:
            opm.seed_organization_payment_methods(oid)
            opm.sync_legacy_payment_config_flags(oid)
    return created


def bootstrap_tenant_payment_setup() -> list[int]:
    """Matriz + configs dedicados (idempotente). Llamar en arranque del app."""
    from models.saas import SaasOrganization

    opm.ensure_organization_payment_methods_schema()
    for org in SaasOrganization.query.order_by(SaasOrganization.id).all():
        opm.seed_organization_payment_methods(int(org.id))
    db.session.commit()
    return provision_missing_payment_configs()
