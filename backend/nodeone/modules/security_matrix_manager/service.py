"""Lógica de catálogo, validación, preview y estados del import."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from nodeone.core.db import db
from nodeone.integrations.odoo.catalog_client import (
    OdooCatalogError,
    catalog_summary,
    fetch_security_catalog,
    normalize_security_catalog,
)
from nodeone.modules.security_matrix_manager.xls_parser import (
    _pick,
    normalize_mapeo_action,
    parse_workbook_bytes,
)
from models.security_matrix import (
    SecurityMatrixCatalogSnapshot,
    SecurityMatrixChangePreview,
    SecurityMatrixImport,
    SecurityMatrixRow,
)
from models.users import Permission, Role, role_permission_table
from sqlalchemy import insert, select

PERM_CODE = 'security_matrix.admin'
ROLE_CODES = ('SA', 'AD')


_schema_ready = False


def ensure_security_matrix_schema() -> None:
    global _schema_ready
    if _schema_ready:
        return
    for model in (
        SecurityMatrixCatalogSnapshot,
        SecurityMatrixImport,
        SecurityMatrixRow,
        SecurityMatrixChangePreview,
    ):
        model.__table__.create(db.engine, checkfirst=True)
    _ensure_permission()
    _schema_ready = True


def _ensure_permission() -> None:
    p = Permission.query.filter_by(code=PERM_CODE).first()
    if p is None:
        p = Permission(code=PERM_CODE, name='Matriz de permisos Odoo (admin)')
        db.session.add(p)
        db.session.flush()
    pid = p.id
    for rcode in ROLE_CODES:
        role = Role.query.filter_by(code=rcode).first()
        if not role:
            continue
        existing = {
            row[0]
            for row in db.session.execute(
                select(role_permission_table.c.permission_id).where(
                    role_permission_table.c.role_id == role.id
                )
            )
        }
        if pid not in existing:
            db.session.execute(
                insert(role_permission_table).values(role_id=role.id, permission_id=pid)
            )
    db.session.commit()


def _json_loads(text: str | None, default: Any = None) -> Any:
    if not text:
        return default
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return default


def _json_dumps(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False)


def latest_catalog_snapshot(organization_id: int) -> SecurityMatrixCatalogSnapshot | None:
    return (
        SecurityMatrixCatalogSnapshot.query.filter_by(organization_id=organization_id)
        .order_by(SecurityMatrixCatalogSnapshot.synced_at.desc())
        .first()
    )


def catalog_payload(snapshot: SecurityMatrixCatalogSnapshot | None) -> dict[str, Any]:
    if not snapshot:
        return {}
    raw = _json_loads(snapshot.payload_json, {})
    return normalize_security_catalog(raw) if raw else {}


def sync_catalog_from_odoo(organization_id: int, user_id: int | None) -> SecurityMatrixCatalogSnapshot:
    data = normalize_security_catalog(fetch_security_catalog())
    meta = data.get('meta') or {}
    snap = SecurityMatrixCatalogSnapshot(
        organization_id=organization_id,
        payload_json=_json_dumps(data),
        database_name=str(meta.get('database') or ''),
        odoo_version=str(meta.get('odoo_version') or ''),
        user_count=len(data.get('users') or []),
        group_count=len(data.get('groups') or []),
        membership_count=len(data.get('memberships') or []),
        synced_by_user_id=user_id,
        synced_at=datetime.utcnow(),
    )
    db.session.add(snap)
    db.session.commit()
    return snap


def _catalog_indexes(catalog: dict[str, Any]) -> dict[str, Any]:
    users_by_login = {}
    for u in catalog.get('users') or []:
        login = (u.get('login') or '').strip().lower()
        if login:
            users_by_login[login] = u

    groups_by_xml = {}
    groups_by_name = {}
    for g in catalog.get('groups') or []:
        xml_id = (g.get('xml_id') or '').strip()
        name = (g.get('name') or '').strip().lower()
        if xml_id:
            groups_by_xml[xml_id] = g
        if name:
            groups_by_name[name] = g

    membership_pairs: set[tuple[str, str]] = set()
    for m in catalog.get('memberships') or []:
        login = (m.get('user_login') or '').strip().lower()
        xml_id = (m.get('group_xml_id') or '').strip()
        if login and xml_id:
            membership_pairs.add((login, xml_id))

    critical_xml = {
        (c.get('xml_id') or '').strip()
        for c in (catalog.get('critical_groups') or [])
        if (c.get('xml_id') or '').strip()
    }

    return {
        'users_by_login': users_by_login,
        'groups_by_xml': groups_by_xml,
        'groups_by_name': groups_by_name,
        'membership_pairs': membership_pairs,
        'critical_xml': critical_xml,
    }


def _resolve_group(ref: str, idx: dict[str, Any]) -> tuple[str | None, str | None]:
    ref = (ref or '').strip()
    if not ref:
        return None, None
    if ref in idx['groups_by_xml']:
        g = idx['groups_by_xml'][ref]
        return ref, g.get('name')
    low = ref.lower()
    if low in idx['groups_by_name']:
        g = idx['groups_by_name'][low]
        return (g.get('xml_id') or '').strip() or None, g.get('name')
    return None, None


def create_import_from_xlsx(
    organization_id: int,
    filename: str,
    file_bytes: bytes,
    user_id: int | None,
) -> SecurityMatrixImport:
    snap = latest_catalog_snapshot(organization_id)
    if not snap:
        raise ValueError('Sincronizá el catálogo Odoo antes de subir la matriz.')

    parsed = parse_workbook_bytes(file_bytes)
    imp = SecurityMatrixImport(
        organization_id=organization_id,
        catalog_snapshot_id=snap.id,
        filename=filename or 'matriz.xlsx',
        uploaded_by_user_id=user_id,
        status='draft',
        created_at=datetime.utcnow(),
    )
    db.session.add(imp)
    db.session.flush()

    for sheet, rows in parsed.items():
        for row in rows:
            db.session.add(
                SecurityMatrixRow(
                    organization_id=organization_id,
                    import_id=imp.id,
                    sheet_name=sheet,
                    row_number=int(row.get('_row_number') or 0),
                    area=_pick(row, 'area', 'área'),
                    module=_pick(row, 'modulo', 'módulo', 'module'),
                    screen=_pick(row, 'pantalla', 'screen'),
                    odoo_group=_pick(row, 'grupo_odoo_xml_id', 'grupo_xml_id', 'xml_id', 'grupo', 'group'),
                    username=_pick(row, 'login', 'usuario', 'user', 'email'),
                    permission_read=_bool_cell(row.get('lectura') or row.get('read')),
                    permission_create=_bool_cell(row.get('crear') or row.get('create')),
                    permission_write=_bool_cell(row.get('escritura') or row.get('write')),
                    permission_unlink=_bool_cell(row.get('borrar') or row.get('unlink')),
                    risk_level=_pick(row, 'nivel_riesgo', 'risk', 'riesgo'),
                    raw_json=_json_dumps(row),
                )
            )
    db.session.commit()
    validate_import(imp.id, organization_id)
    return SecurityMatrixImport.query.get(imp.id)


def _bool_cell(v: Any) -> bool | None:
    if v is None or str(v).strip() == '':
        return None
    s = str(v).strip().lower()
    if s in ('1', 'si', 'sí', 'yes', 'true', 'x'):
        return True
    if s in ('0', 'no', 'false'):
        return False
    return None


def validate_import(import_id: int, organization_id: int) -> dict[str, Any]:
    imp = SecurityMatrixImport.query.filter_by(id=import_id, organization_id=organization_id).first()
    if not imp:
        raise ValueError('Import no encontrado')

    snap = imp.catalog_snapshot or latest_catalog_snapshot(organization_id)
    catalog = catalog_payload(snap)
    if not catalog:
        raise ValueError('Catálogo Odoo no disponible')

    idx = _catalog_indexes(catalog)
    errors: list[dict[str, Any]] = []
    warnings: list[str] = []
    critical_count = 0

    SecurityMatrixChangePreview.query.filter_by(import_id=imp.id).delete()
    db.session.flush()

    mapeo_rows = SecurityMatrixRow.query.filter_by(
        import_id=imp.id, sheet_name='MAPEO_FINAL'
    ).all()

    for row in SecurityMatrixRow.query.filter_by(import_id=imp.id).all():
        row.validation_errors_json = None
        row.validation_status = 'ok'
        row_errors: list[str] = []

        if row.sheet_name == 'MAPEO_FINAL':
            login = (row.username or '').strip().lower()
            group_ref = (row.odoo_group or '').strip()
            action_raw = _pick(_json_loads(row.raw_json, {}), 'accion', 'action', 'acción')
            action = normalize_mapeo_action(action_raw)

            if not login:
                row_errors.append('Falta login de usuario')
            elif login not in idx['users_by_login']:
                row_errors.append(f'Usuario no existe en catálogo: {login}')
            xml_id, gname = _resolve_group(group_ref, idx)
            if not xml_id:
                row_errors.append(f'Grupo no reconocido: {group_ref}')
            if not action:
                row_errors.append(f'Acción inválida: {action_raw}')

            if row_errors:
                row.validation_status = 'error'
                row.validation_errors_json = _json_dumps(row_errors)
                errors.append({'row_id': row.id, 'sheet': row.sheet_name, 'errors': row_errors})
                if any('no existe' in e or 'no reconocido' in e for e in row_errors):
                    critical_count += 1
            elif xml_id and login and action:
                pair = (login, xml_id)
                has = pair in idx['membership_pairs']
                needs_change = (action == 'add' and not has) or (action == 'remove' and has)
                if needs_change:
                    risk = 'critical' if xml_id in idx['critical_xml'] else 'medium'
                    if risk == 'critical':
                        critical_count += 1
                    db.session.add(
                        SecurityMatrixChangePreview(
                            organization_id=organization_id,
                            import_id=imp.id,
                            odoo_user=login,
                            odoo_group=gname or group_ref,
                            group_xml_id=xml_id,
                            action=action,
                            risk_level=risk,
                            reason=f'Propuesta matriz: {action} grupo {xml_id}',
                        )
                    )

        elif row.sheet_name == 'USUARIOS' and row.username:
            login = row.username.strip().lower()
            if login not in idx['users_by_login']:
                row.validation_status = 'warning'
                row_errors.append('Usuario no está en catálogo Odoo')
                warnings.append(f'USUARIOS fila {row.row_number}: {login}')

        if row_errors and row.validation_status != 'error':
            row.validation_errors_json = _json_dumps(row_errors)

    preview_count = SecurityMatrixChangePreview.query.filter_by(import_id=imp.id).count()
    summary = {
        'validated_at': datetime.utcnow().isoformat() + 'Z',
        'catalog_summary': catalog_summary(catalog) if catalog else '',
        'row_errors': len(errors),
        'warnings': warnings,
        'preview_changes': preview_count,
        'critical_issues': critical_count,
        'can_approve': critical_count == 0 and preview_count >= 0,
    }

    imp.has_critical_errors = critical_count > 0
    imp.validation_summary_json = _json_dumps(summary)
    imp.status = 'validated' if critical_count == 0 else 'draft'
    db.session.commit()
    return summary


def approve_import(import_id: int, organization_id: int, user_id: int) -> SecurityMatrixImport:
    imp = SecurityMatrixImport.query.filter_by(id=import_id, organization_id=organization_id).first()
    if not imp:
        raise ValueError('Import no encontrado')
    if imp.has_critical_errors:
        raise ValueError('No se puede aprobar: hay errores críticos de validación')
    if imp.status != 'validated':
        raise ValueError('Solo se aprueba en estado validated (sin errores críticos)')

    imp.status = 'approved'
    imp.approved_by_user_id = user_id
    imp.approved_at = datetime.utcnow()
    for prev in SecurityMatrixChangePreview.query.filter_by(import_id=imp.id):
        prev.approved = True
    db.session.commit()
    return imp


def reject_import(import_id: int, organization_id: int, user_id: int) -> SecurityMatrixImport:
    imp = SecurityMatrixImport.query.filter_by(id=import_id, organization_id=organization_id).first()
    if not imp:
        raise ValueError('Import no encontrado')
    imp.status = 'rejected'
    imp.rejected_by_user_id = user_id
    imp.rejected_at = datetime.utcnow()
    db.session.commit()
    return imp


def run_ai_for_import(import_id: int, organization_id: int, user_id: int) -> dict[str, Any]:
    from nodeone.modules.security_matrix_manager.ai_analyzer import run_ai_analysis

    imp = SecurityMatrixImport.query.filter_by(id=import_id, organization_id=organization_id).first()
    if not imp:
        raise ValueError('Import no encontrado')

    catalog = catalog_payload(imp.catalog_snapshot)
    previews = SecurityMatrixChangePreview.query.filter_by(import_id=imp.id).limit(50).all()
    preview_sample = [
        {
            'user': p.odoo_user,
            'group_xml_id': p.group_xml_id,
            'action': p.action,
            'risk_level': p.risk_level,
        }
        for p in previews
    ]
    validation_summary = _json_loads(imp.validation_summary_json, {})
    ai_result, err = run_ai_analysis(
        validation_summary,
        preview_sample,
        catalog.get('critical_groups') or [],
        session_id=f'security-matrix-{imp.id}-u{user_id}',
        organization_id=organization_id,
    )
    if err:
        raise ValueError(err)
    imp.ai_summary_json = _json_dumps(ai_result)
    db.session.commit()
    return ai_result


def import_report_data(import_id: int, organization_id: int) -> dict[str, Any]:
    imp = SecurityMatrixImport.query.filter_by(id=import_id, organization_id=organization_id).first()
    if not imp:
        raise ValueError('Import no encontrado')
    rows_err = SecurityMatrixRow.query.filter_by(import_id=imp.id, validation_status='error').all()
    previews = SecurityMatrixChangePreview.query.filter_by(import_id=imp.id).all()
    return {
        'import': {
            'id': imp.id,
            'filename': imp.filename,
            'status': imp.status,
            'has_critical_errors': imp.has_critical_errors,
            'created_at': imp.created_at.isoformat() if imp.created_at else None,
            'approved_at': imp.approved_at.isoformat() if imp.approved_at else None,
        },
        'validation': _json_loads(imp.validation_summary_json, {}),
        'ai': _json_loads(imp.ai_summary_json, {}),
        'error_rows': [
            {
                'sheet': r.sheet_name,
                'row': r.row_number,
                'errors': _json_loads(r.validation_errors_json, []),
            }
            for r in rows_err
        ],
        'preview': [
            {
                'user': p.odoo_user,
                'group': p.odoo_group,
                'group_xml_id': p.group_xml_id,
                'action': p.action,
                'risk_level': p.risk_level,
                'reason': p.reason,
            }
            for p in previews
        ],
    }


def toggle_matriz_cell(
    import_id: int,
    organization_id: int,
    *,
    module: str,
    area: str,
    screen: str,
    group_xml_id: str,
    checked: bool,
) -> SecurityMatrixImport:
    """Activa/desactiva una celda de MATRIZ_GENERAL (pantalla × grupo)."""
    imp = SecurityMatrixImport.query.filter_by(id=import_id, organization_id=organization_id).first()
    if not imp:
        raise ValueError('Import no encontrado')
    if imp.status not in ('draft', 'validated'):
        raise ValueError('La matriz no se puede editar: el import ya fue aprobado o cerrado')

    area_s = (area or '').strip()
    module_s = (module or '').strip()
    screen_s = (screen or '').strip()
    group_s = (group_xml_id or '').strip()
    if not module_s or not screen_s or not group_s:
        raise ValueError('Faltan módulo, pantalla o grupo')

    existing = SecurityMatrixRow.query.filter_by(
        import_id=import_id,
        sheet_name='MATRIZ_GENERAL',
        area=area_s,
        module=module_s,
        screen=screen_s,
        odoo_group=group_s,
    ).first()

    if checked:
        if not existing:
            max_row = (
                db.session.query(db.func.max(SecurityMatrixRow.row_number))
                .filter_by(import_id=import_id, sheet_name='MATRIZ_GENERAL')
                .scalar()
                or 1
            )
            db.session.add(
                SecurityMatrixRow(
                    organization_id=organization_id,
                    import_id=import_id,
                    sheet_name='MATRIZ_GENERAL',
                    row_number=int(max_row) + 1,
                    area=area_s,
                    module=module_s,
                    screen=screen_s,
                    odoo_group=group_s,
                    validation_status='ok',
                )
            )
    elif existing:
        db.session.delete(existing)

    db.session.commit()
    validate_import(import_id, organization_id)
    return SecurityMatrixImport.query.get(import_id)


def list_imports(organization_id: int, limit: int = 30) -> list[SecurityMatrixImport]:
    return (
        SecurityMatrixImport.query.filter_by(organization_id=organization_id)
        .order_by(SecurityMatrixImport.created_at.desc())
        .limit(limit)
        .all()
    )
