"""Servicio de importación XLS → cotización EN1 (sin motor FE)."""

from __future__ import annotations

import json
import logging
import os
import re
import tempfile
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy.exc import IntegrityError

from nodeone.core.db import db
from nodeone.modules.accounting.models import Invoice, Tax
from nodeone.modules.sales.models import Quotation, QuotationLine, SalesXlsImport
from nodeone.modules.sales.xls_import.detect import list_profiles, parse_grid
from nodeone.modules.sales.xls_import.security import SafeWorkbook, XlsImportSecurityError, inspect_upload
from nodeone.modules.sales.xls_import.totals import TotalsResult, recompute
from nodeone.modules.sales.xls_import.types import SalesImportData
from nodeone.modules.sales.xls_import.workbook import load_sheet_grid


_LOG = logging.getLogger(__name__)
_STORAGE_ROOT_CACHE: Path | None = None


class XlsImportError(ValueError):
    def __init__(self, code: str, message: str, payload: dict[str, Any] | None = None):
        super().__init__(message)
        self.code = code
        self.user_message = message
        self.payload = payload or {}


def available_profiles() -> list[dict[str, Any]]:
    return [{'code': 'auto', 'version': None, 'label': 'Automático'}] + list_profiles()


def analyze_upload(
    *,
    organization_id: int,
    user_id: int | None,
    filename: str,
    data: bytes,
    profile_code: str | None = None,
) -> dict[str, Any]:
    from nodeone.services.sales_xls_import_schema import ensure_sales_xls_import_schema

    ensure_sales_xls_import_schema(db, db.engine)
    oid = int(organization_id)
    wb = inspect_upload(filename=filename, data=data)
    existing = (
        SalesXlsImport.query.filter_by(organization_id=oid, file_hash=wb.sha256)
        .order_by(SalesXlsImport.id.desc())
        .first()
    )
    if existing and existing.quotation_id:
        return _already_processed_payload(oid, existing)

    grid = load_sheet_grid(wb.kind, wb.payload)
    from nodeone.core.regional_format import RegionalFormatService
    from nodeone.modules.sales.xls_import.workbook import reset_number_format, use_number_format

    nf = '1,234.56'
    try:
        nf = RegionalFormatService.get_or_create(oid).number_format
    except Exception:
        pass
    token = use_number_format(nf)
    try:
        parsed, prof, ver = parse_grid(wb.filename, grid, profile_code)
    except ValueError as exc:
        raise XlsImportError('unrecognized_format', str(exc)) from exc
    finally:
        reset_number_format(token)
    parsed.profile = prof
    parsed.profile_version = ver
    _match_catalog(oid, parsed, create_missing=False)
    totals = recompute(parsed, tax_resolver=lambda rate: _resolve_tax(oid, rate))
    _apply_tax_ids(parsed, totals)
    contact_info = _match_contact(oid, parsed)
    warnings = list(totals.warnings)
    errors = list(totals.errors)
    if not parsed.customer and not parsed.tax_id:
        errors.append('No se reconoció el cliente en el archivo.')
    if not parsed.external_number:
        warnings.append('No se encontró número de factura de origen; se usará el nombre de archivo.')
    if contact_info['status'] == 'missing':
        warnings.append('Cliente no encontrado en la organización. Se creará en Clientes al confirmar la importación.')
    elif contact_info['status'] == 'ambiguous':
        warnings.append(
            'Hay varios contactos con el mismo nombre. No se creará un duplicado; elija el cliente en Clientes o unifique el catálogo.'
        )
    unmatched = sum(1 for ln in parsed.lines if ln.product_id is None and (ln.description or '').strip())
    if unmatched:
        warnings.append(
            f'{unmatched} línea(s) sin producto en catálogo. Se crearán con código P-#### al confirmar la importación.'
        )
    if not parsed.email:
        warnings.append('El archivo no trae correo del cliente (necesario más adelante para FE).')
    if not _usable_tax_id(parsed.tax_id):
        warnings.append('El RUC del archivo está vacío o es un placeholder; se buscará el cliente por nombre.')

    stored = _store_file(oid, wb)
    payload_json = json.dumps(parsed.to_dict(), ensure_ascii=False)
    totals_json = json.dumps(totals.to_dict(), ensure_ascii=False)
    warnings_json = json.dumps(warnings, ensure_ascii=False)
    errors_json = json.dumps(errors, ensure_ascii=False)

    if existing and not existing.quotation_id:
        existing.original_filename = wb.filename
        existing.stored_path = stored
        existing.import_profile = prof
        existing.import_profile_version = int(ver)
        existing.external_reference = parsed.external_number
        existing.status = 'error' if errors else 'analyzed'
        existing.warnings_json = warnings_json
        existing.errors_json = errors_json
        existing.parser_payload_json = payload_json
        existing.totals_json = totals_json
        existing.uploaded_by_user_id = user_id
        row = existing
    else:
        row = SalesXlsImport(
            organization_id=oid,
            uploaded_by_user_id=user_id,
            original_filename=wb.filename,
            stored_path=stored,
            file_hash=wb.sha256,
            import_profile=prof,
            import_profile_version=int(ver),
            external_reference=parsed.external_number,
            status='error' if errors else 'analyzed',
            warnings_json=warnings_json,
            errors_json=errors_json,
            parser_payload_json=payload_json,
            totals_json=totals_json,
        )
        db.session.add(row)
        try:
            db.session.flush()
        except IntegrityError:
            db.session.rollback()
            again = SalesXlsImport.query.filter_by(organization_id=oid, file_hash=wb.sha256).first()
            if again and again.quotation_id:
                return _already_processed_payload(oid, again)
            raise
    db.session.commit()
    return _preview_payload(row, parsed, totals, warnings, errors, contact_info)


def commit_import(
    *,
    organization_id: int,
    user_id: int | None,
    import_id: int,
    create_customer: bool = True,
) -> dict[str, Any]:
    from nodeone.services.sales_xls_import_schema import ensure_sales_xls_import_schema

    ensure_sales_xls_import_schema(db, db.engine)
    oid = int(organization_id)
    row = SalesXlsImport.query.filter_by(id=int(import_id), organization_id=oid).first()
    if not row:
        raise XlsImportError('not_found', 'Importación no encontrada.')
    if row.quotation_id:
        return _already_processed_payload(oid, row)
    parsed = SalesImportData.from_dict(json.loads(row.parser_payload_json or '{}'))
    _match_catalog(oid, parsed, create_missing=True)
    totals = recompute(parsed, tax_resolver=lambda rate: _resolve_tax(oid, rate))
    if totals.errors:
        raise XlsImportError(
            'import_blocked',
            totals.errors[0],
            {'errors': totals.errors, 'difference': totals.difference, 'totals': totals.to_dict()},
        )
    contact = _resolve_or_create_contact(oid, parsed, allow_create=create_customer)
    quotation = _create_quotation(
        oid=oid,
        user_id=user_id,
        contact=contact,
        parsed=parsed,
        totals=totals,
        row=row,
    )
    row.quotation_id = int(quotation.id)
    row.status = 'committed'
    row.committed_at = datetime.utcnow()
    row.totals_json = json.dumps(totals.to_dict(), ensure_ascii=False)
    db.session.commit()
    return {
        'ok': True,
        'import_id': row.id,
        'quotation_id': quotation.id,
        'quotation_number': quotation.number,
        'quotation_url': f'/admin/sales/quotations/{quotation.id}',
    }


def get_preview(organization_id: int, import_id: int) -> dict[str, Any]:
    oid = int(organization_id)
    row = SalesXlsImport.query.filter_by(id=int(import_id), organization_id=oid).first()
    if not row:
        raise XlsImportError('not_found', 'Importación no encontrada.')
    if row.quotation_id:
        return _already_processed_payload(oid, row)
    parsed = SalesImportData.from_dict(json.loads(row.parser_payload_json or '{}'))
    totals = recompute(parsed, tax_resolver=lambda rate: _resolve_tax(oid, rate))
    warnings = json.loads(row.warnings_json or '[]') or list(totals.warnings)
    errors = json.loads(row.errors_json or '[]') or list(totals.errors)
    contact_info = _match_contact(oid, parsed)
    return _preview_payload(row, parsed, totals, warnings, errors, contact_info)


def _preview_payload(
    row: SalesXlsImport,
    parsed: SalesImportData,
    totals: TotalsResult,
    warnings: list[str],
    errors: list[str],
    contact_info: dict[str, Any],
) -> dict[str, Any]:
    can_create = not errors
    validation = {
        'recognized': bool(parsed.customer or parsed.tax_id or parsed.external_number),
        'lines_ok': bool(totals.lines),
        'totals_ok': totals.within_tolerance if parsed.declared_total is not None else True,
        'warnings': warnings,
        'errors': errors,
    }
    return {
        'ok': True,
        'already_imported': False,
        'import_id': row.id,
        'filename': row.original_filename,
        'file_hash': row.file_hash,
        'profile': row.import_profile,
        'profile_version': row.import_profile_version,
        'external_reference': parsed.external_number,
        'customer': parsed.customer,
        'tax_id': parsed.tax_id,
        'dv': parsed.dv,
        'date': parsed.date,
        'email': parsed.email,
        'phone': parsed.phone,
        'address': parsed.address,
        'currency': parsed.currency,
        'contact': contact_info,
        'lines': totals.to_dict()['lines'],
        'subtotal': totals.subtotal,
        'tax_total': totals.tax_total,
        'grand_total': totals.grand_total,
        'declared_subtotal': totals.declared_subtotal,
        'declared_tax': totals.declared_tax,
        'declared_total': totals.declared_total,
        'difference': totals.difference,
        'can_create': can_create,
        'validation': validation,
        'emit_fe': False,
    }


def _already_processed_payload(organization_id: int, row: SalesXlsImport) -> dict[str, Any]:
    q = Quotation.query.filter_by(id=int(row.quotation_id), organization_id=int(organization_id)).first()
    fe_info = _fe_for_quotation(organization_id, int(row.quotation_id)) if row.quotation_id else None
    msg = 'Este archivo ya fue procesado.'
    if fe_info:
        msg = 'Este archivo ya fue procesado y la cotización ya produjo una factura electrónica. No se volverá a importar.'
    return {
        'ok': False,
        'already_imported': True,
        'error': 'already_imported',
        'user_message': msg,
        'import_id': row.id,
        'quotation_id': row.quotation_id,
        'quotation_number': q.number if q else None,
        'quotation_url': f'/admin/sales/quotations/{row.quotation_id}' if row.quotation_id else None,
        'invoice_id': fe_info.get('invoice_id') if fe_info else None,
        'fe_blocked': bool(fe_info),
        'emit_fe': False,
    }


def _fe_for_quotation(organization_id: int, quotation_id: int) -> dict[str, Any] | None:
    inv = Invoice.query.filter_by(
        organization_id=int(organization_id), origin_quotation_id=int(quotation_id)
    ).first()
    if not inv:
        return None
    try:
        from models.efactura import ElectronicInvoiceDocument

        fe = (
            ElectronicInvoiceDocument.query.filter_by(
                organization_id=int(organization_id), invoice_id=int(inv.id)
            )
            .filter(ElectronicInvoiceDocument.status.notin_(('cancelled', 'rejected', 'error')))
            .first()
        )
    except Exception:
        fe = None
    if not fe:
        return {'invoice_id': inv.id, 'invoice_number': inv.number, 'fe_id': None}
    return {'invoice_id': inv.id, 'invoice_number': inv.number, 'fe_id': fe.id, 'fe_status': fe.status}


def _catalog_key(value: str | None) -> str:
    """Clave comparable: quita tildes, puntuación y espacios (G.M. HOLDING, INC → gmholdinginc)."""
    t = unicodedata.normalize('NFKD', value or '')
    t = ''.join(c for c in t if not unicodedata.combining(c))
    return re.sub(r'[^a-z0-9]+', '', t.lower())


def _usable_tax_id(tax_id: str | None) -> str:
    raw = (tax_id or '').strip()
    if not raw or raw in ('--', '-', '0'):
        return ''
    digits = re.sub(r'\D', '', raw)
    if digits and set(digits) <= {'0'}:
        return ''
    return raw


def _contact_keys(contact) -> set[str]:
    keys = set()
    for raw in (getattr(contact, 'display_name', None), getattr(contact, 'company_name', None), getattr(contact, 'commercial_name', None)):
        k = _catalog_key(raw)
        if k:
            keys.add(k)
    return keys


def _find_contacts_by_name(organization_id: int, name: str):
    from sqlalchemy import or_

    from models.contact import Contact

    key = _catalog_key(name)
    if not key:
        return []
    tokens = re.findall(r'[A-Za-z0-9]{3,}', name or '')
    token = tokens[0] if tokens else (name or '')[:8]
    like = f'%{token}%'
    candidates = (
        Contact.query.filter(
            Contact.organization_id == int(organization_id),
            Contact.active.is_(True),
            or_(
                Contact.display_name.ilike(like),
                Contact.company_name.ilike(like),
                Contact.commercial_name.ilike(like),
            ),
        )
        .limit(80)
        .all()
    )
    return [c for c in candidates if key in _contact_keys(c)]


def _find_services_by_description(organization_id: int, description: str):
    from sqlalchemy import or_

    from models.catalog import Service

    key = _catalog_key(description)
    if not key:
        return []
    tokens = re.findall(r'[A-Za-z0-9]{3,}', description or '')
    token = tokens[0] if tokens else (description or '')[:8]
    like = f'%{token}%'
    conds = [Service.name.ilike(like), Service.description.ilike(like)]
    if getattr(Service, 'sku', None) is not None:
        conds.append(Service.sku.ilike(like))
    candidates = (
        Service.query.filter(
            Service.organization_id == int(organization_id),
            Service.is_active.is_(True),
            or_(*conds),
        )
        .limit(80)
        .all()
    )
    hits = []
    for s in candidates:
        keys = {_catalog_key(s.name), _catalog_key(s.description)}
        sku = (getattr(s, 'sku', None) or '').strip()
        if sku:
            keys.add(_catalog_key(sku))
        if key in keys:
            hits.append(s)
    return hits


def _next_product_sku(organization_id: int) -> str:
    from models.catalog import Service

    rx = re.compile(r'^P-(\d{1,12})\Z', re.I)
    max_seq = 0
    q = Service.query.filter_by(organization_id=int(organization_id)).with_entities(Service.sku)
    for (sku,) in q:
        if not sku:
            continue
        m = rx.match(str(sku).strip())
        if m:
            max_seq = max(max_seq, int(m.group(1)))
    return f'P-{max_seq + 1:04d}'


def _create_imported_service(organization_id: int, ln) -> Any:
    from models.catalog import Service

    desc = (ln.description or '').strip() or 'Producto importado'
    sku = _next_product_sku(organization_id)
    svc = Service(
        name=desc[:200],
        description=desc,
        icon='fas fa-box',
        membership_type='basic',
        service_type='AGENDABLE',
        base_price=float(ln.unit_price or 0),
        is_active=True,
        organization_id=int(organization_id),
        default_tax_id=(int(ln.tax_id) if ln.tax_id else None),
        sku=sku,
    )
    db.session.add(svc)
    db.session.flush()
    try:
        from nodeone.core.master.product_bridge import ensure_from_service

        ensure_from_service(int(organization_id), svc)
    except Exception:
        pass
    return svc


def _match_catalog(organization_id: int, parsed: SalesImportData, *, create_missing: bool = False) -> dict[str, int]:
    created_by_key: dict[str, Any] = {}
    unmatched = 0
    ambiguous = 0
    created = 0
    for ln in parsed.lines:
        name = (ln.description or '').strip()
        if not name:
            continue
        if ln.product_id:
            continue
        key = _catalog_key(name)
        if key and key in created_by_key:
            ln.product_id = int(created_by_key[key].id)
            continue
        hits = _find_services_by_description(organization_id, name)
        if len(hits) == 1:
            ln.product_id = int(hits[0].id)
            if ln.tax_id is None and getattr(hits[0], 'default_tax_id', None) and ln.tax_rate is None:
                ln.tax_id = int(hits[0].default_tax_id)
            continue
        if len(hits) > 1:
            ambiguous += 1
            continue
        if create_missing:
            svc = _create_imported_service(organization_id, ln)
            created_by_key[key] = svc
            ln.product_id = int(svc.id)
            created += 1
        else:
            unmatched += 1
    return {'unmatched': unmatched, 'ambiguous': ambiguous, 'created': created}


def _resolve_tax(organization_id: int, rate: float | None) -> tuple[int | None, Any]:
    if rate is None:
        return None, None
    rows = Tax.query.filter_by(organization_id=int(organization_id), active=True).all()
    target = float(rate)
    hits = [t for t in rows if abs(float(t.percentage or 0) - target) < 0.05]
    if not hits:
        return None, None

    def _rank(t):
        name = (t.name or '').lower()
        return (0 if 'itbms' in name else 1, t.id)

    tax = sorted(hits, key=_rank)[0]
    return int(tax.id), tax


def _apply_tax_ids(parsed: SalesImportData, totals: TotalsResult) -> None:
    by_desc = {(ln.description, ln.quantity, ln.unit_price): ln for ln in totals.lines}
    for src in parsed.lines:
        hit = by_desc.get((src.description, src.quantity, src.unit_price))
        if hit:
            src.tax_id = hit.tax_id


def _match_contact(organization_id: int, parsed: SalesImportData) -> dict[str, Any]:
    from nodeone.modules.contacts import service as contact_svc

    tax_id = _usable_tax_id(parsed.tax_id)
    dv = (parsed.dv or '').strip() or None
    if tax_id:
        ident = 'ruc'
        found = contact_svc.find_fiscal_duplicate(organization_id, ident, tax_id, dv)
        if found:
            return {
                'status': 'matched',
                'contact_id': found.id,
                'display_name': found.display_name,
                'create_proposed': False,
                'match': 'tax_id',
            }
    email = (parsed.email or '').strip().lower()
    if email:
        from models.contact import Contact

        by_email = Contact.query.filter_by(organization_id=int(organization_id), email=email).first()
        if by_email:
            return {
                'status': 'matched',
                'contact_id': by_email.id,
                'display_name': by_email.display_name,
                'create_proposed': False,
                'match': 'email',
            }
    name_hits = _find_contacts_by_name(organization_id, parsed.customer or '')
    if len(name_hits) == 1:
        found = name_hits[0]
        return {
            'status': 'matched',
            'contact_id': found.id,
            'display_name': found.display_name,
            'create_proposed': False,
            'match': 'name',
        }
    if len(name_hits) > 1:
        return {
            'status': 'ambiguous',
            'contact_id': None,
            'display_name': parsed.customer,
            'create_proposed': False,
            'match': 'name',
            'matches': [{'id': c.id, 'display_name': c.display_name} for c in name_hits[:8]],
        }
    return {
        'status': 'missing',
        'contact_id': None,
        'display_name': parsed.customer,
        'create_proposed': True,
        'match': None,
    }


def _resolve_or_create_contact(organization_id: int, parsed: SalesImportData, *, allow_create: bool):
    from nodeone.modules.contacts import service as contact_svc

    info = _match_contact(organization_id, parsed)
    if info['status'] == 'matched':
        c = contact_svc.get_contact(organization_id, int(info['contact_id']))
        if c:
            return c
    if info['status'] == 'ambiguous':
        raise XlsImportError(
            'customer_ambiguous',
            'Hay varios clientes con el mismo nombre. Unifique el catálogo o elija el contacto antes de importar.',
            {'matches': info.get('matches') or []},
        )
    if not allow_create:
        raise XlsImportError(
            'customer_not_found',
            'El cliente no existe en esta organización. Indique crear cliente o cárguelo antes en Clientes.',
        )
    tax_id = _usable_tax_id(parsed.tax_id)
    name = (parsed.customer or '').strip() or f'Cliente {tax_id or parsed.external_number or "XLS"}'
    is_company = bool(tax_id) or any(x in name.lower() for x in ('s.a', 'sa', 'inc', 'corp', 'ltda'))
    payload = {
        'contact_type': 'company' if is_company else 'person',
        'display_name': name,
        'company_name': name if is_company else None,
        'first_name': None if is_company else name.split(' ', 1)[0],
        'last_name': None if is_company else (' '.join(name.split(' ')[1:]) or '.'),
        'email': parsed.email,
        'phone': parsed.phone,
        'fiscal_address': parsed.address,
        'identification_type': 'ruc' if tax_id else 'consumer_final',
        'tax_id': tax_id or None,
        'dv': parsed.dv if tax_id else None,
        'is_customer': True,
        'country': 'PA',
    }
    return contact_svc.create_contact(organization_id, payload)


def _create_quotation(
    *,
    oid: int,
    user_id: int | None,
    contact,
    parsed: SalesImportData,
    totals: TotalsResult,
    row: SalesXlsImport,
) -> Quotation:
    from nodeone.modules.contacts import invoice_integration as inv_contact_svc
    from nodeone.modules.sales.routes import _recompute_quote_totals
    from nodeone.services.sequential_document_number import next_org_document_number

    _c, uid = inv_contact_svc.resolve_invoice_customer(oid, contact_id=int(contact.id))
    q_date = datetime.utcnow()
    if parsed.date:
        try:
            q_date = datetime.fromisoformat(parsed.date[:10])
        except ValueError:
            q_date = datetime.utcnow()
    last_exc = None
    q = None
    for _ in range(8):
        try:
            with db.session.begin_nested():
                q = Quotation(
                    organization_id=oid,
                    number=next_org_document_number('Q', Quotation, oid),
                    customer_id=int(uid),
                    contact_id=int(contact.id),
                    customer_contact_id=None,
                    date=q_date,
                    status='draft',
                    created_by=user_id,
                    source='xls',
                    import_profile=row.import_profile,
                    import_profile_version=row.import_profile_version,
                    import_filename=row.original_filename,
                    import_file_hash=row.file_hash,
                    import_external_ref=parsed.external_number,
                )
                db.session.add(q)
                db.session.flush()
            last_exc = None
            break
        except IntegrityError as ex:
            last_exc = ex
            q = None
    if last_exc is not None or q is None:
        raise last_exc or XlsImportError('create_failed', 'No se pudo crear la cotización.')
    for ln in totals.lines:
        db.session.add(
            QuotationLine(
                quotation_id=q.id,
                product_id=ln.product_id,
                description=ln.description[:500],
                quantity=ln.quantity,
                price_unit=ln.unit_price,
                tax_id=ln.tax_id,
            )
        )
    _recompute_quote_totals(q)
    db.session.flush()
    return q


def _store_file(organization_id: int, wb: SafeWorkbook) -> str:
    root = _storage_root()
    path = root / f'{int(organization_id)}_{wb.sha256}.bin'
    try:
        if not path.exists():
            path.write_bytes(wb.payload)
    except OSError as exc:
        _LOG.exception('xls-import store failed path=%s errno=%s', path, getattr(exc, 'errno', None))
        raise XlsImportError(
            'storage_unavailable',
            'No se pudo guardar el archivo en el servidor. Intente de nuevo o contacte a soporte.',
        ) from exc
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def _ensure_writable(path: Path) -> bool:
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / f'.wprobe_{os.getpid()}'
        probe.write_bytes(b'ok')
        probe.unlink(missing_ok=True)
        return True
    except OSError:
        return False


def _candidate_roots() -> list[Path]:
    out: list[Path] = []
    env = (os.environ.get('NODEONE_SALES_XLS_STORAGE') or '').strip()
    if env:
        out.append(Path(env))
    try:
        from flask import current_app, has_app_context

        if has_app_context():
            cfg = getattr(current_app, 'SALES_XLS_UPLOAD_ROOT', None) or current_app.config.get(
                'SALES_XLS_UPLOAD_ROOT'
            )
            if cfg:
                out.append(Path(cfg))
            backend = Path(current_app.root_path).resolve()
            # silo/uploads (root_path = .../app/backend → parents[1] = silo)
            if len(backend.parents) >= 2:
                out.append(backend.parents[1] / 'uploads' / 'sales_xls')
            if len(backend.parents) >= 1:
                out.append(backend.parents[0] / 'uploads' / 'sales_xls')
    except Exception:
        pass
    out.append(Path(tempfile.gettempdir()) / 'en1-sales-xls')
    deduped: list[Path] = []
    seen: set[str] = set()
    for p in out:
        key = str(p)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(p)
    return deduped


def _storage_root() -> Path:
    global _STORAGE_ROOT_CACHE
    env = (os.environ.get('NODEONE_SALES_XLS_STORAGE') or '').strip()
    if env:
        root = Path(env)
        if _ensure_writable(root):
            return root
        raise XlsImportError(
            'storage_unavailable',
            'No se pudo guardar el archivo en el servidor. Intente de nuevo o contacte a soporte.',
        )
    if _STORAGE_ROOT_CACHE is not None and _ensure_writable(_STORAGE_ROOT_CACHE):
        return _STORAGE_ROOT_CACHE
    for cand in _candidate_roots():
        if _ensure_writable(cand):
            _STORAGE_ROOT_CACHE = cand
            return cand
    raise XlsImportError(
        'storage_unavailable',
        'No se pudo guardar el archivo en el servidor. Intente de nuevo o contacte a soporte.',
    )
