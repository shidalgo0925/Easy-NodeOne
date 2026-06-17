"""Métodos de pago por tenant: catálogo, semilla y contexto de checkout."""

from __future__ import annotations

from typing import Any

from nodeone.core.db import db
from models.payments import OrganizationPaymentMethod, PaymentConfig

# Claves alineadas con Payment.payment_method y payment_processors.PAYMENT_METHODS
METHOD_CATALOG: dict[str, dict[str, Any]] = {
    'paypal': {
        'label': 'PayPal',
        'display_order': 10,
        'requires_receipt': False,
        'requires_admin_approval': False,
        'auto_confirm': True,
        'is_international': True,
        'default_enabled': True,
    },
    'wire_international': {
        'label': 'Transferencia internacional (SWIFT)',
        'display_order': 30,
        'requires_receipt': True,
        'requires_admin_approval': True,
        'auto_confirm': False,
        'is_international': True,
        'default_enabled': True,
    },
    'banco_general': {
        'label': 'Banco General',
        'display_order': 40,
        'requires_receipt': True,
        'requires_admin_approval': True,
        'auto_confirm': False,
        'is_international': False,
        'default_enabled': False,
    },
    'yappy_manual': {
        'label': 'Yappy manual',
        'display_order': 20,
        'requires_receipt': True,
        'requires_admin_approval': True,
        'auto_confirm': False,
        'is_international': False,
        'default_enabled': False,
    },
    'stripe': {
        'label': 'Tarjeta (Stripe)',
        'display_order': 5,
        'requires_receipt': False,
        'requires_admin_approval': False,
        'auto_confirm': True,
        'is_international': True,
        'default_enabled': False,
    },
    'manual_payment': {
        'label': 'Pago manual / transferencia local',
        'display_order': 50,
        'requires_receipt': True,
        'requires_admin_approval': True,
        'auto_confirm': False,
        'is_international': False,
        'default_enabled': False,
    },
}

IMMEDIATE_METHOD_KEYS = frozenset({'paypal', 'stripe'})
MANUAL_VALIDATION_METHOD_KEYS = frozenset({
    'yappy_manual',
    'wire_international',
    'banco_general',
    'manual_payment',
})

# Perfiles operativos (matriz = única fuente de visibilidad en checkout).
PAYMENT_PROFILES: dict[str, dict[str, Any]] = {
    'panama': {
        'label': 'Panamá — Yappy, Banco General, PayPal opcional',
        'enabled': {
            'paypal': True,
            'yappy_manual': True,
            'banco_general': True,
            'wire_international': False,
            'stripe': False,
            'manual_payment': False,
        },
    },
    'international': {
        'label': 'Internacional (IIUS) — PayPal + SWIFT + Stripe',
        'enabled': {
            'paypal': True,
            'wire_international': True,
            'stripe': True,
            'yappy_manual': False,
            'banco_general': False,
            'manual_payment': False,
        },
    },
}


def ensure_organization_payment_methods_schema() -> None:
    OrganizationPaymentMethod.__table__.create(db.engine, checkfirst=True)


def _pcfg_for_org(organization_id: int) -> PaymentConfig | None:
    return PaymentConfig.get_active_config(organization_id=int(organization_id))


def _enabled_from_payment_config(method_key: str, pcfg: PaymentConfig | None) -> bool:
    """Solo migración inicial: lee flags legacy de PaymentConfig una vez."""
    if pcfg is None:
        return bool(METHOD_CATALOG.get(method_key, {}).get('default_enabled'))
    if method_key == 'yappy_manual':
        return bool(getattr(pcfg, 'yappy_manual_enabled', False))
    if method_key == 'wire_international':
        return bool(getattr(pcfg, 'intl_wire_enabled', True))
    if method_key == 'paypal':
        return True
    if method_key == 'stripe':
        return False
    if method_key == 'banco_general':
        return False
    if method_key == 'manual_payment':
        return False
    return bool(METHOD_CATALOG.get(method_key, {}).get('default_enabled'))


def is_known_method_key(method_key: str) -> bool:
    return (method_key or '').strip() in METHOD_CATALOG


def seed_organization_payment_methods(
    organization_id: int,
    *,
    force: bool = False,
    inherit_enabled_from_config: bool = False,
) -> int:
    """Crea filas base por org. Si force=False, solo completa métodos faltantes."""
    ensure_organization_payment_methods_schema()
    oid = int(organization_id)
    pcfg = _pcfg_for_org(oid) if inherit_enabled_from_config else None
    created = 0
    for method_key, meta in METHOD_CATALOG.items():
        existing = OrganizationPaymentMethod.query.filter_by(
            organization_id=oid, method_key=method_key
        ).first()
        if existing and not force:
            continue
        if inherit_enabled_from_config:
            enabled = _enabled_from_payment_config(method_key, pcfg)
        else:
            enabled = bool(meta.get('default_enabled'))
        instructions = ''
        if method_key == 'yappy_manual' and pcfg:
            instructions = (getattr(pcfg, 'yappy_manual_instructions', None) or '').strip()
        elif method_key == 'wire_international' and pcfg:
            instructions = (getattr(pcfg, 'intl_wire_instructions', None) or '').strip()
        elif method_key == 'manual_payment':
            instructions = ''

        if existing:
            if force:
                existing.label = meta['label']
                existing.enabled = enabled
                existing.display_order = meta['display_order']
                existing.requires_receipt = meta['requires_receipt']
                existing.requires_admin_approval = meta['requires_admin_approval']
                existing.auto_confirm = meta['auto_confirm']
                existing.is_international = meta['is_international']
                if instructions and not (existing.instructions_html or '').strip():
                    existing.instructions_html = instructions
            continue

        row = OrganizationPaymentMethod(
            organization_id=oid,
            method_key=method_key,
            label=meta['label'],
            enabled=enabled,
            display_order=meta['display_order'],
            requires_receipt=meta['requires_receipt'],
            requires_admin_approval=meta['requires_admin_approval'],
            auto_confirm=meta['auto_confirm'],
            instructions_html=instructions or None,
            is_international=meta['is_international'],
        )
        db.session.add(row)
        created += 1
    if created:
        db.session.commit()
    return created


def list_methods_for_org(organization_id: int, *, enabled_only: bool = False) -> list[OrganizationPaymentMethod]:
    ensure_organization_payment_methods_schema()
    seed_organization_payment_methods(int(organization_id))
    q = OrganizationPaymentMethod.query.filter_by(organization_id=int(organization_id))
    if enabled_only:
        q = q.filter_by(enabled=True)
    return q.order_by(
        OrganizationPaymentMethod.display_order.asc(),
        OrganizationPaymentMethod.method_key.asc(),
    ).all()


def get_method_row(organization_id: int, method_key: str) -> OrganizationPaymentMethod | None:
    seed_organization_payment_methods(int(organization_id))
    return OrganizationPaymentMethod.query.filter_by(
        organization_id=int(organization_id),
        method_key=(method_key or '').strip(),
    ).first()


def is_method_enabled(organization_id: int, method_key: str) -> bool:
    row = get_method_row(organization_id, method_key)
    return bool(row and row.enabled)


def list_payment_profile_keys() -> list[str]:
    return list(PAYMENT_PROFILES.keys())


def apply_payment_profile(organization_id: int, profile_key: str) -> tuple[list[dict[str, Any]], str]:
    """
    Aplica preset de métodos activos en la matriz del tenant.
    No modifica credenciales en PaymentConfig (solo sync legacy flags tras guardar).
    """
    key = (profile_key or '').strip().lower()
    prof = PAYMENT_PROFILES.get(key)
    if not prof:
        raise ValueError(
            f'Perfil «{profile_key}» no válido. Opciones: {", ".join(PAYMENT_PROFILES)}'
        )
    oid = int(organization_id)
    enabled_map = prof['enabled']
    seed_organization_payment_methods(oid)
    payload: list[dict[str, Any]] = []
    for row in list_methods_for_org(oid, enabled_only=False):
        d = row.to_dict()
        if row.method_key in enabled_map:
            d['enabled'] = bool(enabled_map[row.method_key])
        payload.append(d)
    saved = save_methods_payload(oid, payload)
    return saved, str(prof['label'])


def sync_legacy_payment_config_flags(
    organization_id: int,
    *,
    sync_wire_instructions: bool = True,
) -> None:
    """Espejo legacy en PaymentConfig (solo compat); el checkout usa la matriz."""
    oid = int(organization_id)
    pcfg = PaymentConfig.query.filter_by(organization_id=oid, is_active=True).order_by(
        PaymentConfig.id.asc()
    ).first()
    if not pcfg:
        return
    ym = get_method_row(int(organization_id), 'yappy_manual')
    iw = get_method_row(int(organization_id), 'wire_international')
    if ym is not None:
        pcfg.yappy_manual_enabled = bool(ym.enabled)
        if (ym.instructions_html or '').strip():
            pcfg.yappy_manual_instructions = ym.instructions_html
        pcfg.yappy_requires_receipt = bool(ym.requires_receipt)
        pcfg.yappy_admin_validation_required = bool(ym.requires_admin_approval)
    if iw is not None:
        pcfg.intl_wire_enabled = bool(iw.enabled)
        # Solo al guardar la matriz: no pisar «Notas SWIFT» del panel al guardar credenciales.
        if sync_wire_instructions and (iw.instructions_html or '').strip():
            pcfg.intl_wire_instructions = iw.instructions_html
    db.session.add(pcfg)
    db.session.commit()


def save_methods_payload(organization_id: int, methods: list[dict[str, Any]]) -> list[dict]:
    oid = int(organization_id)
    seed_organization_payment_methods(oid)
    out = []
    for item in methods:
        key = (item.get('method_key') or '').strip()
        if key not in METHOD_CATALOG:
            continue
        row = get_method_row(oid, key)
        if not row:
            continue
        row.label = (item.get('label') or row.label or METHOD_CATALOG[key]['label']).strip()[:120]
        row.enabled = bool(item.get('enabled'))
        try:
            row.display_order = int(item.get('display_order', row.display_order))
        except (TypeError, ValueError):
            pass
        row.requires_receipt = bool(item.get('requires_receipt'))
        row.requires_admin_approval = bool(item.get('requires_admin_approval'))
        row.auto_confirm = bool(item.get('auto_confirm'))
        row.instructions_html = (item.get('instructions_html') or '').strip() or None
        row.is_international = bool(item.get('is_international'))
        db.session.add(row)
        out.append(row.to_dict())
    db.session.commit()
    sync_legacy_payment_config_flags(oid)
    return out


def build_checkout_payment_context(
    organization_id: int,
    *,
    payment_config: PaymentConfig | None = None,
) -> dict[str, Any]:
    """
    Contexto para checkout.html / checkout_payment_methods.html.
    Visibilidad: únicamente organization_payment_methods.enabled=True.
    PaymentConfig aporta credenciales, cuentas e instrucciones técnicas.
    """
    from payment_processors import BANCO_GENERAL_DISPLAY_DEFAULTS, INTL_WIRE_DEFAULTS
    from nodeone.services.yappy_manual import (
        effective_yappy_display_name,
        effective_yappy_instructions_html,
        effective_yappy_phone_or_identifier,
    )

    oid = int(organization_id)
    pcfg = payment_config or _pcfg_for_org(oid)
    rows = list_methods_for_org(oid, enabled_only=True)

    payment_methods: dict[str, str] = {}
    method_rows: list[dict[str, Any]] = []
    for row in rows:
        if row.method_key not in METHOD_CATALOG:
            continue
        payment_methods[row.method_key] = row.label or METHOD_CATALOG[row.method_key]['label']
        method_rows.append(row.to_dict())

    keys = list(payment_methods.keys())
    pref = ('stripe', 'paypal', 'yappy_manual', 'wire_international', 'banco_general', 'manual_payment')
    checkout_first_method = next((k for k in pref if k in payment_methods), keys[0] if keys else None)
    checkout_has_immediate = any(k in payment_methods for k in IMMEDIATE_METHOD_KEYS)
    checkout_has_manual_validation = any(
        k in payment_methods for k in MANUAL_VALIDATION_METHOD_KEYS
    )
    checkout_other_method_keys = [k for k in keys if k not in IMMEDIATE_METHOD_KEYS | MANUAL_VALIDATION_METHOD_KEYS]

    intl_wire_display: dict[str, Any] = {}
    if 'wire_international' in payment_methods:
        intl_wire_display = dict(INTL_WIRE_DEFAULTS)
        if pcfg:
            if (getattr(pcfg, 'intl_wire_beneficiary_name', None) or '').strip():
                intl_wire_display['beneficiary_name'] = pcfg.intl_wire_beneficiary_name.strip()
            if (getattr(pcfg, 'intl_wire_bank_name', None) or '').strip():
                intl_wire_display['bank_name'] = pcfg.intl_wire_bank_name.strip()
            if (getattr(pcfg, 'intl_wire_swift', None) or '').strip():
                intl_wire_display['swift'] = pcfg.intl_wire_swift.strip()
            if (getattr(pcfg, 'intl_wire_account', None) or '').strip():
                intl_wire_display['account_number'] = pcfg.intl_wire_account.strip()
            if (getattr(pcfg, 'intl_wire_account_type', None) or '').strip():
                intl_wire_display['account_type'] = pcfg.intl_wire_account_type.strip()
            if (getattr(pcfg, 'intl_wire_country', None) or '').strip():
                intl_wire_display['country'] = pcfg.intl_wire_country.strip()
        iw_row = get_method_row(oid, 'wire_international')
        if iw_row and (iw_row.instructions_html or '').strip():
            intl_wire_display['instructions_html'] = iw_row.instructions_html

    banco_general_display: dict[str, Any] = {}
    if 'banco_general' in payment_methods:
        try:
            from payment_processors import BancoGeneralProcessor

            banco_general_display = BancoGeneralProcessor(pcfg)._display()
        except Exception:
            banco_general_display = dict(BANCO_GENERAL_DISPLAY_DEFAULTS)
        bg_row = get_method_row(oid, 'banco_general')
        if bg_row and (bg_row.instructions_html or '').strip():
            banco_general_display['instructions_html'] = bg_row.instructions_html

    yappy_checkout = None
    if 'yappy_manual' in payment_methods and pcfg:
        ym_row = get_method_row(oid, 'yappy_manual')
        instr = ''
        if ym_row:
            instr = (ym_row.instructions_html or '').strip()
        if not instr:
            instr = effective_yappy_instructions_html(pcfg)
        yappy_checkout = {
            'display_name': effective_yappy_display_name(pcfg),
            'directory_name': (getattr(pcfg, 'yappy_directory_name', None) or '').strip(),
            'phone': effective_yappy_phone_or_identifier(pcfg),
            'instructions_html': instr,
            'requires_receipt': bool(ym_row.requires_receipt) if ym_row else True,
            'currency': 'USD',
        }

    method_by_key = {r['method_key']: r for r in method_rows}
    checkout_method_order = [r['method_key'] for r in method_rows]

    return {
        'payment_methods': payment_methods,
        'method_rows': method_rows,
        'method_by_key': method_by_key,
        'checkout_method_order': checkout_method_order,
        'checkout_first_method': checkout_first_method,
        'checkout_has_immediate': checkout_has_immediate,
        'checkout_has_manual_validation': checkout_has_manual_validation,
        'checkout_other_method_keys': checkout_other_method_keys,
        'intl_wire_display': intl_wire_display,
        'banco_general_display': banco_general_display,
        'yappy_checkout': yappy_checkout,
    }

