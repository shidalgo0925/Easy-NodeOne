"""Lógica de negocio del módulo Contador."""

from __future__ import annotations

import csv
import io
import json
import re
from datetime import datetime
from typing import Any

from sqlalchemy import func, or_

from nodeone.core.db import db
from models.contador import (
    ContadorCaptureLog,
    ContadorCountLine,
    ContadorExportLog,
    ContadorProductTemplate,
    ContadorProductVariant,
    ContadorSession,
)


def normalize_text(value: str | None) -> str:
    if value is None:
        return ''
    s = str(value).strip().upper()
    s = re.sub(r'\s+', ' ', s)
    return s


def _next_variant_code(organization_id: int) -> str:
    rows = (
        db.session.query(ContadorProductVariant.code)
        .filter(ContadorProductVariant.organization_id == int(organization_id))
        .all()
    )
    mx = 0
    for (code,) in rows:
        if not code:
            continue
        m = re.match(r'^CNT-(\d+)$', str(code).strip())
        if m:
            mx = max(mx, int(m.group(1)))
    return f'CNT-{mx + 1:06d}'


def import_xlsx_bytes(raw: bytes, filename: str, organization_id: int, user_id: int | None) -> dict[str, Any]:
    """Importa catálogo desde XLS/XLSX (columnas A–E)."""
    try:
        import pandas as pd
    except ImportError as e:
        raise RuntimeError('pandas es requerido para importar') from e

    bio = io.BytesIO(raw)
    df = pd.read_excel(bio, engine='openpyxl', header=None)
    templates_created = 0
    variants_created = 0
    variants_updated = 0

    for _, row in df.iterrows():
        if row.isna().all():
            continue
        cat = normalize_text(row.iloc[0] if len(row) > 0 else '')
        sub = normalize_text(row.iloc[1] if len(row) > 1 else '')
        cls = normalize_text(row.iloc[2] if len(row) > 2 else '')
        name_raw = row.iloc[3] if len(row) > 3 else ''
        attr_raw = row.iloc[4] if len(row) > 4 else ''
        name_n = normalize_text(str(name_raw) if name_raw is not None and not (isinstance(name_raw, float) and str(name_raw) == 'nan') else '')
        attr_stripped = str(attr_raw).strip() if attr_raw is not None and str(attr_raw) != 'nan' else ''
        attr_n = normalize_text(attr_stripped)
        if not name_n or not attr_n:
            continue

        tpl = ContadorProductTemplate.query.filter_by(
            organization_id=organization_id,
            category=cat,
            subcategory=sub,
            product_class=cls,
            name_normalized=name_n,
        ).first()
        if not tpl:
            tpl = ContadorProductTemplate(
                organization_id=organization_id,
                name=str(name_raw).strip(),
                name_normalized=name_n,
                category=cat,
                subcategory=sub,
                product_class=cls,
                is_active=True,
            )
            db.session.add(tpl)
            db.session.flush()
            templates_created += 1

        display = f'{str(name_raw).strip()} - {attr_stripped}'
        existing_v = ContadorProductVariant.query.filter_by(
            template_id=tpl.id,
            attribute_value_normalized=attr_n,
        ).first()
        if existing_v:
            existing_v.display_name = display[:400]
            existing_v.attribute_value = attr_stripped[:200]
            existing_v.is_active = True
            variants_updated += 1
            continue

        code = _next_variant_code(organization_id)
        v = ContadorProductVariant(
            organization_id=organization_id,
            template_id=tpl.id,
            attribute_name='PRESENTACIÓN',
            attribute_value=attr_stripped[:200],
            attribute_value_normalized=attr_n,
            display_name=display[:400],
            code=code,
            barcode=None,
            is_active=True,
        )
        db.session.add(v)
        variants_created += 1

    db.session.commit()
    return {
        'filename': filename,
        'templates_created': templates_created,
        'variants_created': variants_created,
        'variants_updated': variants_updated,
    }


def search_variants(organization_id: int, q: str, limit: int = 50) -> list[dict[str, Any]]:
    term = (q or '').strip()
    if len(term) < 2:
        return []
    like = f'%{term}%'

    qry = (
        db.session.query(ContadorProductVariant, ContadorProductTemplate)
        .join(ContadorProductTemplate, ContadorProductTemplate.id == ContadorProductVariant.template_id)
        .filter(ContadorProductVariant.organization_id == organization_id)
        .filter(ContadorProductVariant.is_active.is_(True))
        .filter(
            or_(
                ContadorProductTemplate.name.ilike(like),
                ContadorProductVariant.attribute_value.ilike(like),
                ContadorProductVariant.display_name.ilike(like),
                ContadorProductVariant.code.ilike(like),
                func.coalesce(ContadorProductVariant.barcode, '').ilike(like),
                ContadorProductTemplate.category.ilike(like),
                ContadorProductTemplate.subcategory.ilike(like),
                ContadorProductTemplate.product_class.ilike(like),
            )
        )
        .order_by(ContadorProductVariant.display_name.asc())
        .limit(limit)
    )

    out: list[dict[str, Any]] = []
    for v, t in qry.all():
        out.append(
            {
                'variant_id': v.id,
                'code': v.code,
                'template_name': t.name,
                'attribute_name': v.attribute_name,
                'attribute_value': v.attribute_value,
                'display_name': v.display_name,
                'category': t.category,
                'subcategory': t.subcategory,
                'product_class': t.product_class,
            }
        )
    return out


def create_session(
    organization_id: int, name: str, description: str | None, user_id: int | None
) -> ContadorSession:
    s = ContadorSession(
        organization_id=organization_id,
        name=name.strip()[:200],
        description=(description or '').strip() or None,
        status='draft',
        created_by=user_id,
    )
    db.session.add(s)
    db.session.commit()
    return s


def open_session(session_id: int, organization_id: int) -> ContadorSession:
    s = ContadorSession.query.filter_by(id=session_id, organization_id=organization_id).first_or_404()
    if s.status != 'draft':
        raise ValueError('Solo se puede abrir una sesión en borrador')
    variants = ContadorProductVariant.query.filter_by(organization_id=organization_id, is_active=True).all()
    if not variants:
        raise ValueError('No hay variantes activas en el catálogo; importá un XLS primero')
    existing_ids = {lid for (lid,) in db.session.query(ContadorCountLine.variant_id).filter_by(session_id=s.id).all()}
    for v in variants:
        if v.id in existing_ids:
            continue
        db.session.add(
            ContadorCountLine(
                organization_id=organization_id,
                session_id=s.id,
                variant_id=v.id,
                counted_qty=None,
                status='pending',
            )
        )
    s.status = 'open'
    s.opened_at = datetime.utcnow()
    db.session.commit()
    return s


def close_session(session_id: int, organization_id: int) -> ContadorSession:
    s = ContadorSession.query.filter_by(id=session_id, organization_id=organization_id).first_or_404()
    if s.status != 'open':
        raise ValueError('Solo se puede cerrar una sesión abierta')
    s.status = 'closed'
    s.closed_at = datetime.utcnow()
    db.session.commit()
    return s


def delete_session_if_draft(session_id: int, organization_id: int) -> None:
    s = ContadorSession.query.filter_by(id=session_id, organization_id=organization_id).first_or_404()
    if s.status != 'draft':
        raise ValueError('Solo se pueden eliminar sesiones en borrador')
    db.session.delete(s)
    db.session.commit()


def _append_log(
    organization_id: int,
    session_id: int,
    line_id: int,
    variant_id: int,
    old_qty: int | None,
    new_qty: int | None,
    action: str,
    user_id: int | None,
) -> None:
    db.session.add(
        ContadorCaptureLog(
            organization_id=organization_id,
            session_id=session_id,
            line_id=line_id,
            variant_id=variant_id,
            old_qty=old_qty,
            new_qty=new_qty,
            action=action,
            user_id=user_id,
        )
    )


def capture_quantity(
    session_id: int,
    variant_id: int,
    qty: int,
    organization_id: int,
    user_id: int | None,
    *,
    operator_restrict_own: bool = False,
) -> ContadorCountLine:
    if qty < 0:
        raise ValueError('La cantidad no puede ser negativa')
    s = ContadorSession.query.filter_by(id=session_id, organization_id=organization_id).first_or_404()
    if s.status != 'open':
        raise ValueError('La sesión no está abierta para captura')

    line = ContadorCountLine.query.filter_by(session_id=session_id, variant_id=variant_id).first_or_404()

    if operator_restrict_own and line.counted_by is not None and line.counted_by != user_id:
        raise PermissionError('Solo podés editar tus propios conteos')

    old = line.counted_qty
    action = 'update' if old is not None else 'create'
    line.counted_qty = qty
    line.counted_by = user_id
    line.counted_at = datetime.utcnow()
    line.status = 'counted'

    _append_log(organization_id, session_id, line.id, variant_id, old, qty, action, user_id)
    db.session.commit()
    return line


def review_line(
    session_id: int,
    variant_id: int,
    qty: int | None,
    mark_reviewed: bool,
    notes: str | None,
    organization_id: int,
    user_id: int | None,
) -> ContadorCountLine:
    s = ContadorSession.query.filter_by(id=session_id, organization_id=organization_id).first_or_404()
    if s.status not in ('open', 'closed'):
        raise ValueError('Sesión no válida para revisión')

    line = ContadorCountLine.query.filter_by(session_id=session_id, variant_id=variant_id).first_or_404()
    old = line.counted_qty
    if qty is not None:
        if qty < 0:
            raise ValueError('La cantidad no puede ser negativa')
        line.counted_qty = qty
        _append_log(organization_id, session_id, line.id, variant_id, old, qty, 'review', user_id)
        if not mark_reviewed:
            line.status = 'counted'
    if mark_reviewed:
        line.status = 'reviewed'
        line.reviewed_by = user_id
        line.reviewed_at = datetime.utcnow()
    if notes is not None:
        line.notes = notes[:2000]
    db.session.commit()
    return line


def session_summary(session_id: int, organization_id: int) -> dict[str, Any]:
    s = ContadorSession.query.filter_by(id=session_id, organization_id=organization_id).first_or_404()
    total = ContadorCountLine.query.filter_by(session_id=session_id).count()
    pending = ContadorCountLine.query.filter_by(session_id=session_id, status='pending').count()
    counted = ContadorCountLine.query.filter_by(session_id=session_id, status='counted').count()
    reviewed = ContadorCountLine.query.filter_by(session_id=session_id, status='reviewed').count()
    void = ContadorCountLine.query.filter_by(session_id=session_id, status='void').count()
    done = (
        ContadorCountLine.query.filter(
            ContadorCountLine.session_id == session_id,
            ContadorCountLine.status.in_(('counted', 'reviewed')),
        ).count()
    )
    last = (
        db.session.query(func.max(ContadorCountLine.counted_at))
        .filter(ContadorCountLine.session_id == session_id)
        .scalar()
    )
    ops = (
        db.session.query(func.count(func.distinct(ContadorCountLine.counted_by)))
        .filter(ContadorCountLine.session_id == session_id, ContadorCountLine.counted_by.isnot(None))
        .scalar()
    )
    pct = round(done * 100.0 / total, 1) if total else 0.0
    return {
        'session_id': s.id,
        'status': s.status,
        'total_lines': total,
        'pending': pending,
        'counted': counted,
        'reviewed': reviewed,
        'void': void,
        'progress_pct': pct,
        'last_capture_at': last.isoformat() if last else None,
        'distinct_operators': int(ops or 0),
    }


def export_rows(session_id: int, organization_id: int) -> list[dict[str, Any]]:
    s = ContadorSession.query.filter_by(id=session_id, organization_id=organization_id).first_or_404()
    rows = db.session.query(ContadorCountLine, ContadorProductVariant, ContadorProductTemplate).join(
        ContadorProductVariant, ContadorProductVariant.id == ContadorCountLine.variant_id
    ).join(
        ContadorProductTemplate, ContadorProductTemplate.id == ContadorProductVariant.template_id
    ).filter(ContadorCountLine.session_id == session_id).order_by(ContadorProductVariant.display_name.asc()).all()

    from models.users import User

    out = []
    for line, v, t in rows:
        cu = User.query.get(line.counted_by) if line.counted_by else None
        ru = User.query.get(line.reviewed_by) if line.reviewed_by else None
        out.append(
            {
                'session_name': s.name,
                'code': v.code,
                'barcode': v.barcode or '',
                'category': t.category,
                'subcategory': t.subcategory,
                'product_class': t.product_class,
                'product_name': t.name,
                'attribute_name': v.attribute_name,
                'attribute_value': v.attribute_value,
                'display_name': v.display_name,
                'counted_qty': line.counted_qty,
                'status': line.status,
                'counted_by_email': (cu.email if cu else ''),
                'counted_at': line.counted_at.strftime('%Y-%m-%d %H:%M') if line.counted_at else '',
                'reviewed_by_email': (ru.email if ru else ''),
                'reviewed_at': line.reviewed_at.strftime('%Y-%m-%d %H:%M') if line.reviewed_at else '',
                'notes': line.notes or '',
            }
        )
    return out


def build_export_xlsx(rows: list[dict[str, Any]]) -> bytes:
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.title = 'conteo'
    headers = list(rows[0].keys()) if rows else [
        'session_name',
        'code',
        'barcode',
        'category',
        'subcategory',
        'product_class',
        'product_name',
        'attribute_name',
        'attribute_value',
        'display_name',
        'counted_qty',
        'status',
        'counted_by_email',
        'counted_at',
        'reviewed_by_email',
        'reviewed_at',
        'notes',
    ]
    ws.append(headers)
    for r in rows:
        ws.append([r.get(h, '') for h in headers])
    bio = io.BytesIO()
    wb.save(bio)
    return bio.getvalue()


def build_export_csv(rows: list[dict[str, Any]]) -> bytes:
    if not rows:
        headers = [
            'session_name',
            'code',
            'barcode',
            'category',
            'subcategory',
            'product_class',
            'product_name',
            'attribute_name',
            'attribute_value',
            'display_name',
            'counted_qty',
            'status',
            'counted_by_email',
            'counted_at',
            'reviewed_by_email',
            'reviewed_at',
            'notes',
        ]
    else:
        headers = list(rows[0].keys())
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=headers)
    w.writeheader()
    for r in rows:
        w.writerow({k: r.get(k, '') for k in headers})
    return buf.getvalue().encode('utf-8-sig')


def log_export(
    organization_id: int,
    session_id: int,
    export_type: str,
    filename: str | None,
    status: str,
    message: str | None,
    user_id: int | None,
) -> None:
    db.session.add(
        ContadorExportLog(
            organization_id=organization_id,
            session_id=session_id,
            export_type=export_type,
            filename=filename,
            target_name=None,
            status=status,
            message=message,
            created_by=user_id,
        )
    )
    db.session.commit()
