"""Exportación admin (miembros → XLS/PDF, plantillas, vista previa)."""

import json
import os
from datetime import datetime
from io import BytesIO

from flask import Blueprint, current_app, jsonify, render_template, request, send_file
from flask_login import current_user

admin_export_bp = Blueprint('admin_export', __name__)


def _reports_export_required(f):
    import app as M

    return M.require_permission('reports.export')(f)


EXPORT_FIELD_REGISTRY = {
    'members': [
        {'key': 'id', 'label': 'ID', 'type': 'integer'},
        {'key': 'email', 'label': 'Correo electrónico', 'type': 'string'},
        {'key': 'first_name', 'label': 'Nombre', 'type': 'string'},
        {'key': 'last_name', 'label': 'Apellido', 'type': 'string'},
        {'key': 'phone', 'label': 'Teléfono', 'type': 'string'},
        {'key': 'country', 'label': 'País', 'type': 'string'},
        {'key': 'cedula_or_passport', 'label': 'Cédula / Pasaporte', 'type': 'string'},
        {'key': 'user_group', 'label': 'Grupo', 'type': 'string'},
        {'key': 'created_at', 'label': 'Fecha registro', 'type': 'date'},
        {'key': 'is_active', 'label': 'Activo', 'type': 'boolean'},
        {'key': 'is_admin', 'label': 'Admin', 'type': 'boolean'},
        {'key': 'is_advisor', 'label': 'Asesor', 'type': 'boolean'},
        {'key': 'is_salesperson', 'label': 'Vendedor', 'type': 'boolean'},
    ],
}


def _get_export_logo_path():
    """Ruta absoluta del logo para PDF (solo PNG; ReportLab no soporta SVG). None si no hay logo."""
    base = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'static'))
    for rel in (
        os.path.join('public', 'emails', 'logos', 'logo-primary.png'),
        os.path.join('images', 'logo-primary.png'),
    ):
        path = os.path.join(base, rel)
        if os.path.isfile(path):
            return path
    return None


def _get_export_fields_allowed(entity):
    """Campos permitidos para la entidad (según registry)."""
    return EXPORT_FIELD_REGISTRY.get(entity, [])


def _sanitize_report_title(raw):
    """Sanitiza nombre del reporte: trim, máx 100 caracteres, sin HTML/scripts."""
    if raw is None:
        return None
    s = (raw or '').strip()
    if not s:
        return None
    s = s[:100]
    s = ''.join(c for c in s if c.isalnum() or c in ' -_.,;:áéíóúñÁÉÍÓÚÑ')
    return s.strip() or None


def _get_report_title(entity):
    """Nombre del reporte: request (report_title o title), sanitizado; si vacío, default."""
    raw = request.args.get('report_title') or request.args.get('title')
    title = _sanitize_report_title(raw)
    if title:
        return title
    ent_label = 'Miembros' if entity == 'members' else entity
    return f'Reporte - {ent_label} - {datetime.utcnow().strftime("%d/%m/%Y %H:%M")}'


def _export_members_data(
    field_keys,
    status_filter=None,
    limit=10000,
    search=None,
    admin_filter=None,
    advisor_filter=None,
    group_filter=None,
    tag_filter=None,
    organization_id_scope=None,
):
    import app as M

    from nodeone.services.user_organization import user_in_org_clause

    allowed_keys = {f['key'] for f in _get_export_fields_allowed('members')}
    keys = [k for k in field_keys if k in allowed_keys]
    if not keys:
        return [], []
    query = M.User.query
    if organization_id_scope is not None:
        query = query.filter(user_in_org_clause(M.User, organization_id_scope))
    elif not M._admin_can_view_all_organizations():
        from sqlalchemy import false as sql_false
        query = query.filter(sql_false())
    if search:
        query = query.filter(
            M.db.or_(
                M.User.first_name.ilike(f'%{search}%'),
                M.User.last_name.ilike(f'%{search}%'),
                M.User.email.ilike(f'%{search}%'),
                M.User.phone.ilike(f'%{search}%'),
            )
        )
    if status_filter == 'active':
        query = query.filter_by(is_active=True)
    elif status_filter == 'inactive':
        query = query.filter_by(is_active=False)
    if admin_filter == 'yes':
        query = query.filter_by(is_admin=True)
    elif admin_filter == 'no':
        query = query.filter_by(is_admin=False)
    if advisor_filter == 'yes':
        query = query.filter_by(is_advisor=True)
    elif advisor_filter == 'no':
        query = query.filter_by(is_advisor=False)
    if group_filter and group_filter != 'all':
        query = query.filter_by(user_group=group_filter)
    if tag_filter:
        query = query.filter(M.User.tags.ilike(f'%{tag_filter}%'))
    query = query.order_by(M.User.created_at.desc())
    rows = query.limit(limit).all()
    labels = {f['key']: f['label'] for f in _get_export_fields_allowed('members')}
    headers = [labels.get(k, k) for k in keys]
    data = []
    for u in rows:
        row = {}
        for k in keys:
            v = getattr(u, k, None)
            if v is None:
                row[k] = ''
            elif hasattr(v, 'strftime'):
                row[k] = v.strftime('%d/%m/%Y %H:%M') if v else ''
            elif isinstance(v, bool):
                row[k] = 'Sí' if v else 'No'
            else:
                row[k] = str(v)
        data.append([row[k] for k in keys])
    return headers, data


def _export_members_organization_scope():
    import app as M

    if not M._admin_can_view_all_organizations():
        return M.admin_data_scope_organization_id()
    plat = M._platform_admin_data_scope_organization_id()
    if plat is not None:
        return int(plat)
    return M.admin_data_scope_organization_id()


def _export_request_filters():
    return {
        'status_filter': request.args.get('status', 'all'),
        'search': (request.args.get('search') or '').strip() or None,
        'admin_filter': request.args.get('admin') or None,
        'advisor_filter': request.args.get('advisor') or None,
        'group_filter': request.args.get('group') or None,
        'tag_filter': (request.args.get('tag') or '').strip() or None,
        'organization_id_scope': _export_members_organization_scope(),
    }


@admin_export_bp.route('/admin/export')
@_reports_export_required
def admin_export_page():
    """Pantalla de exportación: selector de campos, filtros, XLS/PDF."""
    return render_template('admin/export.html')


@admin_export_bp.route('/api/admin/export/fields')
@_reports_export_required
def api_export_fields():
    """Lista de campos permitidos para la entidad."""
    entity = request.args.get('entity', 'members')
    fields = _get_export_fields_allowed(entity)
    return jsonify({'fields': fields})


@admin_export_bp.route('/api/admin/export/xls')
@_reports_export_required
def api_export_xls():
    """Exportar a Excel (campos y filtros por query). Mismos filtros que listado usuarios."""
    import app as M

    entity = request.args.get('entity', 'members')
    fields_param = request.args.get('fields', '')
    field_keys = [x.strip() for x in fields_param.split(',') if x.strip()]
    if entity != 'members':
        return jsonify({'error': 'Entidad no soportada'}), 400
    if not field_keys:
        return jsonify({'error': 'Seleccione al menos un campo'}), 400
    filters = _export_request_filters()
    report_title = _get_report_title(entity)
    try:
        headers, data = _export_members_data(field_keys, limit=10000, **filters)
        from openpyxl import Workbook

        wb = Workbook()
        ws = wb.active
        sheet_name = (report_title or 'Miembros')[:31].replace(':', '-').replace('\\', '-').replace('/', '-').replace('?', '').replace('*', '').replace('[', '').replace(']', '')
        ws.title = sheet_name or 'Miembros'
        ws.append(headers)
        for row in data:
            ws.append(row)
        buf = BytesIO()
        wb.save(buf)
        buf.seek(0)
        try:
            M.ActivityLog.log_activity(
                current_user.id,
                'EXPORT_XLS',
                'export',
                None,
                f'entity=members fields={len(field_keys)} rows={len(data)}',
                request,
            )
            M.db.session.commit()
        except Exception:
            M.db.session.rollback()
        download_name = f'miembros_{datetime.utcnow().strftime("%Y%m%d_%H%M")}.xlsx'
        if report_title:
            safe = ''.join(c if c.isalnum() or c in ' -_' else '_' for c in report_title)[:80]
            download_name = f'{safe}_{datetime.utcnow().strftime("%Y%m%d_%H%M")}.xlsx'
        return send_file(
            buf,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=download_name,
        )
    except Exception as e:
        M.db.session.rollback()
        current_app.logger.exception('export xls: %s', e)
        return jsonify({'error': str(e)}), 500


@admin_export_bp.route('/api/admin/export/pdf')
@_reports_export_required
def api_export_pdf():
    """Generar PDF (misma selección que XLS, límite 1000). Mismos filtros que listado usuarios."""
    import app as M

    entity = request.args.get('entity', 'members')
    fields_param = request.args.get('fields', '')
    field_keys = [x.strip() for x in fields_param.split(',') if x.strip()]
    if entity != 'members':
        return jsonify({'error': 'Entidad no soportada'}), 400
    if not field_keys:
        return jsonify({'error': 'Seleccione al menos un campo'}), 400
    filters = _export_request_filters()
    try:
        headers, data = _export_members_data(field_keys, limit=1000, **filters)
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import Image as RlImage
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

        buf = BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
        story = []
        logo_path = _get_export_logo_path()
        if logo_path:
            try:
                img = RlImage(logo_path, width=120)
                story.append(img)
                story.append(Spacer(1, 12))
            except Exception:
                pass
        report_title = _get_report_title(entity)
        fecha = datetime.utcnow().strftime('%d/%m/%Y %H:%M')
        styles = getSampleStyleSheet()
        story.append(Paragraph(f'<b>{report_title}</b><br/>{fecha}', styles['Heading2']))
        story.append(Spacer(1, 16))
        table_data = [headers] + data
        t = Table(table_data, repeatRows=1)
        t.setStyle(
            TableStyle(
                [
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('FONTSIZE', (0, 0), (-1, -1), 8),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
                ]
            )
        )
        story.append(t)
        doc.build(story)
        buf.seek(0)
        try:
            M.ActivityLog.log_activity(
                current_user.id,
                'EXPORT_PDF',
                'export',
                None,
                f'entity=members fields={len(field_keys)} rows={len(data)}',
                request,
            )
            M.db.session.commit()
        except Exception:
            M.db.session.rollback()
        safe_pdf_name = ''.join(c if c.isalnum() or c in ' -_' else '_' for c in (report_title or ''))[:80]
        pdf_download = (
            f'{safe_pdf_name}_{datetime.utcnow().strftime("%Y%m%d_%H%M")}.pdf'
            if safe_pdf_name
            else f'miembros_{datetime.utcnow().strftime("%Y%m%d_%H%M")}.pdf'
        )
        return send_file(
            buf,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=pdf_download,
        )
    except Exception as e:
        M.db.session.rollback()
        current_app.logger.exception('export pdf: %s', e)
        return jsonify({'error': str(e)}), 500


@admin_export_bp.route('/api/admin/export/preview')
@_reports_export_required
def api_export_preview():
    """Vista previa: mismos params que export, límite 50 filas. Mismos filtros que listado."""
    import app as M

    entity = request.args.get('entity', 'members')
    fields_param = request.args.get('fields', '')
    field_keys = [x.strip() for x in fields_param.split(',') if x.strip()]
    if entity != 'members':
        return jsonify({'error': 'Entidad no soportada'}), 400
    if not field_keys:
        return jsonify({'error': 'Seleccione al menos un campo'}), 400
    filters = _export_request_filters()
    try:
        headers, data = _export_members_data(field_keys, limit=50, **filters)
        return jsonify({'headers': headers, 'rows': data})
    except Exception as e:
        M.db.session.rollback()
        return jsonify({'error': str(e)}), 500


@admin_export_bp.route('/api/admin/export/templates', methods=['GET', 'POST'])
@_reports_export_required
def api_export_templates():
    """Listar (propias + compartidas) o crear plantilla de exportación."""
    import app as M

    if request.method == 'GET':
        templates = M.ExportTemplate.query.filter(
            M.db.or_(
                M.ExportTemplate.user_id == current_user.id,
                M.ExportTemplate.visibility == 'shared',
            )
        ).order_by(M.ExportTemplate.created_at.desc()).all()
        out = []
        for t in templates:
            try:
                fields_list = json.loads(t.fields) if t.fields else []
            except Exception:
                fields_list = []
            is_own = t.user_id == current_user.id
            out.append(
                {
                    'id': t.id,
                    'name': t.name,
                    'entity': t.entity,
                    'fields': fields_list,
                    'visibility': getattr(t, 'visibility', 'own'),
                    'is_own': is_own,
                    'created_at': t.created_at.isoformat() if t.created_at else None,
                }
            )
        return jsonify({'templates': out})
    data = request.get_json() or {}
    name = (data.get('name') or '').strip()
    entity = (data.get('entity') or 'members').strip()
    fields_list = data.get('fields') or []
    visibility = (data.get('visibility') or 'own').strip()
    if visibility not in ('own', 'shared'):
        visibility = 'own'
    if not name:
        return jsonify({'error': 'Nombre requerido'}), 400
    if not isinstance(fields_list, list):
        return jsonify({'error': 'fields debe ser una lista'}), 400
    allowed = {f['key'] for f in _get_export_fields_allowed(entity)}
    fields_list = [k for k in fields_list if k in allowed]
    if not fields_list:
        return jsonify({'error': 'Seleccione al menos un campo permitido'}), 400
    try:
        t = M.ExportTemplate(
            name=name,
            entity=entity,
            fields=json.dumps(fields_list),
            visibility=visibility,
            user_id=current_user.id,
        )
        M.db.session.add(t)
        M.db.session.commit()
        return jsonify({'success': True, 'id': t.id, 'message': 'Plantilla guardada'})
    except Exception as e:
        M.db.session.rollback()
        return jsonify({'error': str(e)}), 500


@admin_export_bp.route('/api/admin/export/templates/<int:template_id>')
@_reports_export_required
def api_export_template_get(template_id):
    """Obtener una plantilla (propia o compartida)."""
    import app as M

    t = M.ExportTemplate.query.filter_by(id=template_id).first_or_404()
    if t.user_id != current_user.id and getattr(t, 'visibility', 'own') != 'shared':
        return jsonify({'error': 'No encontrado'}), 404
    try:
        fields_list = json.loads(t.fields) if t.fields else []
    except Exception:
        fields_list = []
    return jsonify({'id': t.id, 'name': t.name, 'entity': t.entity, 'fields': fields_list})
