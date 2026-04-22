"""Importación / exportación del catálogo de servicios (CSV / XLSX)."""

from __future__ import annotations

import io
import math
import re
from typing import Any

import app as M
from nodeone.core.db import db

# Columnas estables para plantilla e import (mismo orden en export).
EXPORT_COLUMNS = [
    'id',
    'name',
    'description',
    'icon',
    'membership_type',
    'category_name',
    'external_link',
    'base_price',
    'is_active',
    'display_order',
    'service_type',
    'appointment_type_id',
    'requires_payment_before_appointment',
    'deposit_amount',
    'deposit_percentage',
    'requires_diagnostic_appointment',
    'diagnostic_appointment_type_id',
    'default_tax_id',
]

_SERVICE_TYPES = frozenset({'AGENDABLE', 'CONSULTIVO', 'CV_REGISTRATION', 'COURSE'})


def _membership_slugs_allowed_for_org(oid: int) -> set[str]:
    """Slugs de planes activos en ``membership_plan`` (import catálogo)."""
    rows = M.MembershipPlan.query.filter_by(organization_id=int(oid), is_active=True).all()
    return {str(r.slug or '').strip().lower() for r in rows if (r.slug or '').strip()}


def _is_blank(v: Any) -> bool:
    if v is None:
        return True
    if isinstance(v, float) and math.isnan(v):
        return True
    if isinstance(v, str) and not v.strip():
        return True
    return False


def _cell_str(v: Any) -> str:
    if _is_blank(v):
        return ''
    if isinstance(v, bool):
        return 'true' if v else 'false'
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        if isinstance(v, float) and v.is_integer():
            return str(int(v))
        return str(v).strip()
    return str(v).strip()


def _parse_bool(v: Any, *, default: bool = True) -> bool:
    s = _cell_str(v).lower()
    if not s:
        return default
    return s in ('1', 'true', 't', 'yes', 'y', 'sí', 'si', 'activo', 'active')


def _parse_optional_float(v: Any):
    s = _cell_str(v)
    if not s:
        return None
    return float(s.replace(',', '.'))


def _parse_optional_int(v: Any):
    s = _cell_str(v)
    if not s:
        return None
    return int(float(s.replace(',', '.')))


def _parse_int(v: Any, default: int = 0) -> int:
    s = _cell_str(v)
    if not s:
        return default
    return int(float(s.replace(',', '.')))


def _parse_float(v: Any, default: float = 0.0) -> float:
    s = _cell_str(v)
    if not s:
        return default
    return float(s.replace(',', '.'))


def service_to_row(service: M.Service) -> dict[str, Any]:
    cat_name = ''
    if service.category_id and service.category:
        cat_name = service.category.name or ''
    return {
        'id': service.id,
        'name': service.name or '',
        'description': service.description or '',
        'icon': service.icon or 'fas fa-cog',
        'membership_type': service.membership_type or 'basic',
        'category_name': cat_name,
        'external_link': service.external_link or '',
        'base_price': float(service.base_price) if service.base_price is not None else 0.0,
        'is_active': bool(service.is_active),
        'display_order': int(service.display_order or 0),
        'service_type': (getattr(service, 'service_type', None) or 'AGENDABLE').upper(),
        'appointment_type_id': service.appointment_type_id or '',
        'requires_payment_before_appointment': bool(
            service.requires_payment_before_appointment
            if service.requires_payment_before_appointment is not None
            else True
        ),
        'deposit_amount': service.deposit_amount if service.deposit_amount is not None else '',
        'deposit_percentage': service.deposit_percentage if service.deposit_percentage is not None else '',
        'requires_diagnostic_appointment': bool(service.requires_diagnostic_appointment or False),
        'diagnostic_appointment_type_id': service.diagnostic_appointment_type_id or '',
        'default_tax_id': service.default_tax_id or '',
    }


def _resolve_category_id(name: str) -> int | None:
    n = (name or '').strip()
    if not n:
        return None
    cat = M.ServiceCategory.query.filter(db.func.lower(M.ServiceCategory.name) == n.lower()).first()
    if cat:
        return cat.id
    slug = re.sub(r'[^a-z0-9]+', '-', n.lower()).strip('-')
    if slug:
        cat = M.ServiceCategory.query.filter_by(slug=slug).first()
        if cat:
            return cat.id
    return None


def _validate_appointment_type(aid: int | None, oid: int) -> str | None:
    if aid is None:
        return None
    at = M.AppointmentType.query.filter_by(id=aid, organization_id=oid).first()
    if not at:
        return f'Tipo de cita id={aid} no existe en esta organización'
    return None


def _validate_tax(tid: int | None, oid: int) -> str | None:
    if tid is None:
        return None
    from nodeone.modules.accounting.models import Tax

    if not Tax.query.filter_by(id=tid, organization_id=oid).first():
        return f'Impuesto id={tid} no válido para esta organización'
    return None


def rows_from_upload(file_storage) -> tuple[list[dict[str, Any]], str | None]:
    """Lee CSV o XLSX y devuelve filas como dicts (claves = EXPORT_COLUMNS)."""
    name = (file_storage.filename or '').lower()
    raw = file_storage.read()
    if not raw:
        return [], 'Archivo vacío'

    try:
        import pandas as pd
    except ImportError:
        return [], 'Falta la dependencia pandas en el servidor'

    try:
        if name.endswith('.xlsx'):
            df = pd.read_excel(io.BytesIO(raw), engine='openpyxl')
        elif name.endswith('.csv'):
            df = pd.read_csv(io.BytesIO(raw), encoding='utf-8-sig', dtype=object)
        else:
            return [], 'Formato no soportado. Usa .csv o .xlsx'
    except Exception as e:
        return [], f'No se pudo leer el archivo: {e}'

    df.columns = [str(c).strip() for c in df.columns]
    missing = [c for c in EXPORT_COLUMNS if c not in df.columns]
    if missing:
        return (
            [],
            f'Faltan columnas obligatorias en la cabecera: {", ".join(missing)}. Descargá la plantilla o un export.',
        )

    rows: list[dict[str, Any]] = []
    for _, series in df.iterrows():
        row = {col: series.get(col) for col in EXPORT_COLUMNS}
        if all(_is_blank(row.get(c)) for c in EXPORT_COLUMNS):
            continue
        rows.append(row)
    return rows, None


def validate_import_rows(rows: list[dict[str, Any]], oid: int) -> list[tuple[int, str]]:
    """Devuelve lista de (número_fila_hoja, mensaje). Vacía si todo OK."""
    errors: list[tuple[int, str]] = []
    for i, row in enumerate(rows, start=2):
        name = _cell_str(row.get('name'))
        if not name:
            errors.append((i, 'El campo name es obligatorio'))
            continue
        mt = _cell_str(row.get('membership_type')).lower() or 'personal'
        allowed_mt = _membership_slugs_allowed_for_org(oid)
        if not allowed_mt:
            allowed_mt = {'personal', 'emprendedor', 'ejecutivo'}
        if mt not in allowed_mt:
            errors.append(
                (i, f'membership_type inválido: {mt}. Slugs activos en esta org: {", ".join(sorted(allowed_mt))}')
            )
        st = (_cell_str(row.get('service_type')) or 'AGENDABLE').upper()
        if st not in _SERVICE_TYPES:
            errors.append((i, f'service_type inválido: {st}. Use AGENDABLE, CONSULTIVO, CV_REGISTRATION o COURSE'))
        cat_name = _cell_str(row.get('category_name'))
        if cat_name and _resolve_category_id(cat_name) is None:
            errors.append((i, f'Categoría no encontrada: {cat_name}'))

        if st not in ('CV_REGISTRATION', 'COURSE'):
            aid = _parse_optional_int(row.get('appointment_type_id'))
            err = _validate_appointment_type(aid, oid)
            if err:
                errors.append((i, err))

            did = _parse_optional_int(row.get('diagnostic_appointment_type_id'))
            err = _validate_appointment_type(did, oid)
            if err:
                errors.append((i, f'Diagnóstico: {err}'))

        dtid = _parse_optional_int(row.get('default_tax_id'))
        err = _validate_tax(dtid, oid)
        if err:
            errors.append((i, err))

        sid = _parse_optional_int(row.get('id'))
        if sid is not None:
            existing = M.Service.query.filter_by(id=sid, organization_id=oid).first()
            if not existing:
                errors.append((i, f'id={sid} no existe en esta organización (no se puede actualizar)'))
    return errors


def apply_import_rows(rows: list[dict[str, Any]], oid: int) -> tuple[int, int]:
    """Aplica filas validadas. Retorna (creados, actualizados)."""
    created = 0
    updated = 0
    for row in rows:
        name = _cell_str(row.get('name'))
        if not name:
            continue
        sid = _parse_optional_int(row.get('id'))
        service = None
        if sid is not None:
            service = M.Service.query.filter_by(id=sid, organization_id=oid).first()

        cat_name = _cell_str(row.get('category_name'))
        category_id = _resolve_category_id(cat_name) if cat_name else None

        membership_type = _cell_str(row.get('membership_type')).lower() or 'personal'
        service_type = (_cell_str(row.get('service_type')) or 'AGENDABLE').upper()

        payload = {
            'name': name,
            'description': _cell_str(row.get('description')),
            'icon': _cell_str(row.get('icon')) or 'fas fa-cog',
            'membership_type': membership_type,
            'category_id': category_id,
            'external_link': _cell_str(row.get('external_link')),
            'base_price': _parse_float(row.get('base_price'), 0.0),
            'is_active': _parse_bool(row.get('is_active'), default=True),
            'display_order': _parse_int(row.get('display_order'), 0),
            'service_type': service_type if service_type in _SERVICE_TYPES else 'AGENDABLE',
            'appointment_type_id': _parse_optional_int(row.get('appointment_type_id')),
            'requires_payment_before_appointment': _parse_bool(
                row.get('requires_payment_before_appointment'), default=True
            ),
            'deposit_amount': _parse_optional_float(row.get('deposit_amount')),
            'deposit_percentage': _parse_optional_float(row.get('deposit_percentage')),
            'requires_diagnostic_appointment': _parse_bool(
                row.get('requires_diagnostic_appointment'), default=False
            ),
            'diagnostic_appointment_type_id': _parse_optional_int(row.get('diagnostic_appointment_type_id')),
            'default_tax_id': _parse_optional_int(row.get('default_tax_id')),
        }
        if payload['service_type'] in ('CV_REGISTRATION', 'COURSE'):
            payload['appointment_type_id'] = None
            payload['diagnostic_appointment_type_id'] = None

        if service:
            service.name = payload['name']
            service.description = payload['description']
            service.icon = payload['icon']
            service.membership_type = payload['membership_type']
            service.category_id = payload['category_id']
            service.external_link = payload['external_link']
            service.base_price = payload['base_price']
            service.is_active = payload['is_active']
            service.display_order = payload['display_order']
            service.service_type = payload['service_type']
            service.appointment_type_id = payload['appointment_type_id']
            service.requires_payment_before_appointment = payload['requires_payment_before_appointment']
            service.deposit_amount = payload['deposit_amount']
            service.deposit_percentage = payload['deposit_percentage']
            service.requires_diagnostic_appointment = payload['requires_diagnostic_appointment']
            service.diagnostic_appointment_type_id = payload['diagnostic_appointment_type_id']
            service.default_tax_id = payload['default_tax_id']
            updated += 1
        else:
            service = M.Service(
                name=payload['name'],
                description=payload['description'],
                icon=payload['icon'],
                membership_type=payload['membership_type'],
                category_id=payload['category_id'],
                external_link=payload['external_link'],
                base_price=payload['base_price'],
                is_active=payload['is_active'],
                display_order=payload['display_order'],
                service_type=payload['service_type'],
                appointment_type_id=payload['appointment_type_id'],
                requires_payment_before_appointment=payload['requires_payment_before_appointment'],
                deposit_amount=payload['deposit_amount'],
                deposit_percentage=payload['deposit_percentage'],
                requires_diagnostic_appointment=payload['requires_diagnostic_appointment'],
                diagnostic_appointment_type_id=payload['diagnostic_appointment_type_id'],
                default_tax_id=payload['default_tax_id'],
                organization_id=oid,
            )
            M.db.session.add(service)
            created += 1

    M.db.session.commit()
    return created, updated
