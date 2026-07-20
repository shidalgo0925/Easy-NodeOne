"""Actor Back Office para Order Domain (crear/cobrar sin tablet)."""

from __future__ import annotations

from models.commercial_core import CorePosTerminal
from nodeone.core.commerce.constants import POS_TERMINAL_ACTIVE
from nodeone.core.master.constants import ORG_UNIT_TYPE_POS, ORG_UNIT_TYPE_REGISTER

BACKOFFICE_TERMINAL_REF = 'en1-backoffice'
BACKOFFICE_DEVICE_LABEL = 'Caja principal (Back Office)'


def ensure_backoffice_terminal(organization_id: int) -> CorePosTerminal:
    """Terminal sintético de la org para operaciones desde EN1 BO.

    Evita atribuir pedidos BO al primer device real/e2e (antes todos salían como caja-01
    sin distinguir origen).
    """
    from app import db
    from models.core_master import CoreOrgUnit
    from nodeone.core.master.org_unit import OrgUnitService

    oid = int(organization_id)
    row = CorePosTerminal.query.filter_by(
        organization_id=oid, terminal_ref=BACKOFFICE_TERMINAL_REF
    ).first()
    if row is not None:
        dirty = False
        if (row.device_label or '') != BACKOFFICE_DEVICE_LABEL:
            row.device_label = BACKOFFICE_DEVICE_LABEL
            dirty = True
        if str(row.status or '') != POS_TERMINAL_ACTIVE:
            row.status = POS_TERMINAL_ACTIVE
            dirty = True
        if dirty:
            db.session.commit()
        return row

    registers = OrgUnitService.list_units(
        oid, unit_type=ORG_UNIT_TYPE_REGISTER, status='active'
    )
    poses = OrgUnitService.list_units(oid, unit_type=ORG_UNIT_TYPE_POS, status='active')
    register_ref = registers[0].unit_ref if registers else 'caja-01'
    pos_ref = poses[0].unit_ref if poses else None
    branch_ref = None
    if poses:
        pos_row = CoreOrgUnit.query.filter_by(
            organization_id=oid, unit_ref=str(poses[0].unit_ref)
        ).first()
        if pos_row and pos_row.parent_id:
            br = CoreOrgUnit.query.filter_by(id=int(pos_row.parent_id)).first()
            if br is not None:
                branch_ref = br.unit_ref

    row = CorePosTerminal(
        organization_id=oid,
        terminal_ref=BACKOFFICE_TERMINAL_REF,
        register_ref=register_ref,
        pos_ref=pos_ref,
        branch_ref=branch_ref,
        status=POS_TERMINAL_ACTIVE,
        device_label=BACKOFFICE_DEVICE_LABEL,
        profile='fixed',
        platform='web',
        sync_enabled=False,
    )
    db.session.add(row)
    db.session.commit()
    return row


def is_backoffice_owner(owner_device_uuid: str | None, device_label: str | None = None) -> bool:
    ref = str(owner_device_uuid or '').strip().lower()
    label = str(device_label or '').strip().lower()
    blob = f'{ref} {label}'
    if ref == BACKOFFICE_TERMINAL_REF or 'backoffice' in blob:
        return True
    # Legado: BO usaba el primer terminal (e2e/http-check).
    if ref.startswith(('e2e-', 'diag-', 'test-', 'smoke-', 'h3-', 'bootstrap-')):
        return True
    if 'http-check' in blob or 'bootstrap-check' in blob:
        return True
    return False


def is_ops_device(device) -> bool:
    """True si el terminal es operativo (no BO sintético / e2e / smoke)."""
    return not is_backoffice_owner(
        getattr(device, 'terminal_ref', None),
        getattr(device, 'device_label', None),
    )


def order_origin_meta(
    *,
    owner_device_uuid: str | None,
    device_label: str | None = None,
    profile: str | None = None,
) -> dict[str, str]:
    """Etiqueta visible de origen del pedido (BO vs tablet/POS)."""
    if is_backoffice_owner(owner_device_uuid, device_label):
        return {
            'kind': 'bo',
            'label': 'Caja principal (BO)',
            'detail': device_label or BACKOFFICE_DEVICE_LABEL,
        }
    label = (device_label or '').strip()
    short_ref = str(owner_device_uuid or '').strip()
    if len(short_ref) > 12:
        short_ref = short_ref[:8]
    if (profile or '').lower() == 'handheld':
        return {
            'kind': 'tablet',
            'label': f'Tablet · {label or short_ref or "POS"}',
            'detail': label or short_ref,
        }
    if label:
        return {
            'kind': 'tablet',
            'label': f'Tablet · {label}',
            'detail': label,
        }
    if short_ref:
        return {'kind': 'tablet', 'label': f'Tablet · {short_ref}', 'detail': short_ref}
    return {'kind': 'unknown', 'label': '—', 'detail': ''}
