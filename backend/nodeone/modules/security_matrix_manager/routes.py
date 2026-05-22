"""Rutas admin — matriz de permisos Odoo (Fase 1)."""

from __future__ import annotations

import json
import os

from flask import (
    Blueprint,
    Response,
    abort,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

from models.saas import SaasOrganization
from nodeone.integrations.odoo.catalog_client import OdooCatalogError
from nodeone.modules.security_matrix_manager import service as sm_svc
from nodeone.modules.security_matrix_manager.matriz_grid import (
    DEFAULT_MATRIZ_ROWS,
    build_module_matrix_view,
    module_tab_id,
    matriz_entries_from_import_rows,
)
from nodeone.modules.security_matrix_manager.permissions_view import (
    build_group_summary_rows,
    build_import_stats,
    build_matriz_design_rows,
    build_user_permission_rows,
)
from nodeone.modules.security_matrix_manager.xls_parser import build_template_bytes

security_matrix_bp = Blueprint('security_matrix', __name__, url_prefix='/admin/security-matrix')


@security_matrix_bp.before_request
def _ensure_schema():
    sm_svc.ensure_security_matrix_schema()


def _org_id() -> int:
    from app import admin_data_scope_organization_id, default_organization_id

    try:
        oid = int(admin_data_scope_organization_id())
    except Exception:
        oid = int(default_organization_id())
    if SaasOrganization.query.get(int(oid)) is None:
        return int(default_organization_id())
    return int(oid)


def _platform_admin() -> bool:
    return bool(current_user.is_authenticated and getattr(current_user, 'is_admin', False))


def _can_admin() -> bool:
    return current_user.is_authenticated and (
        _platform_admin() or current_user.has_permission('security_matrix.admin')
    )


def _deny():
    abort(403)


@security_matrix_bp.route('/')
@login_required
def security_matrix_index():
    if not _can_admin():
        _deny()
    oid = _org_id()
    catalog = sm_svc.latest_catalog_snapshot(oid)
    imports = sm_svc.list_imports(oid)
    return render_template(
        'admin/security_matrix/index.html',
        catalog=catalog,
        imports=imports,
        catalog_configured=bool((os.environ.get('ODOO_CATALOG_API_KEY') or '').strip()),
    )


@security_matrix_bp.route('/catalog')
@login_required
def security_matrix_catalog_view():
    """Permisos actuales en Odoo (snapshot sincronizado) — vista visual."""
    if not _can_admin():
        _deny()
    oid = _org_id()
    snap = sm_svc.latest_catalog_snapshot(oid)
    if not snap:
        flash('Sincronizá el catálogo Odoo primero.', 'warning')
        return redirect(url_for('security_matrix.security_matrix_index'))
    catalog = sm_svc.catalog_payload(snap)
    q = (request.args.get('q') or '').strip()
    tab = (request.args.get('tab') or 'users').strip()
    return render_template(
        'admin/security_matrix/catalog.html',
        snap=snap,
        catalog=catalog,
        tab=tab,
        search=q,
        user_rows=build_user_permission_rows(catalog, search=q),
        group_rows=build_group_summary_rows(catalog, search=q),
        critical_groups=catalog.get('critical_groups') or [],
    )


def _matriz_view_context(oid: int, catalog: dict, import_id: int | None, active_module: str | None):
    from models.security_matrix import SecurityMatrixImport, SecurityMatrixRow

    imp = None
    entries = list(DEFAULT_MATRIZ_ROWS)
    source = 'plantilla'
    editable = False

    if import_id:
        imp = SecurityMatrixImport.query.filter_by(id=import_id, organization_id=oid).first()
        if imp:
            rows = SecurityMatrixRow.query.filter_by(import_id=imp.id).all()
            imported = matriz_entries_from_import_rows(rows)
            if imported:
                entries = imported
                source = f'import #{imp.id}'
            editable = imp.status in ('draft', 'validated')

    active = active_module or request.args.get('module') or None
    grid = build_module_matrix_view(catalog, entries, active_module=active)
    return imp, grid, source, editable


@security_matrix_bp.route('/matriz')
@login_required
def security_matrix_matriz_view():
    """Matriz diseño: módulos (pestañas) × pantallas × grupos Odoo."""
    if not _can_admin():
        _deny()
    oid = _org_id()
    snap = sm_svc.latest_catalog_snapshot(oid)
    if not snap:
        flash('Sincronizá el catálogo Odoo primero.', 'warning')
        return redirect(url_for('security_matrix.security_matrix_index'))

    catalog = sm_svc.catalog_payload(snap)
    import_id = request.args.get('import_id', type=int)
    active_module = (request.args.get('module') or '').strip() or None
    imp, grid, source, editable = _matriz_view_context(oid, catalog, import_id, active_module)

    return render_template(
        'admin/security_matrix/matriz.html',
        snap=snap,
        imp=imp,
        grid=grid,
        source=source,
        editable=editable,
        import_id=import_id,
    )


@security_matrix_bp.route('/imports/<int:import_id>/matriz-cell', methods=['POST'])
@login_required
def security_matrix_matriz_cell(import_id: int):
    if not _can_admin():
        _deny()
    module = (request.form.get('module') or '').strip()
    area = (request.form.get('area') or '').strip()
    screen = (request.form.get('screen') or '').strip()
    group_xml_id = (request.form.get('group_xml_id') or '').strip()
    checked = request.form.get('checked') in ('1', 'on', 'true', 'yes')
    active_module = module_tab_id(module) if module else (request.form.get('active_module') or '')
    try:
        sm_svc.toggle_matriz_cell(
            import_id,
            _org_id(),
            module=module,
            area=area,
            screen=screen,
            group_xml_id=group_xml_id,
            checked=checked,
        )
        flash('Matriz actualizada.', 'success')
    except Exception as e:
        flash(str(e), 'error')
    return redirect(
        url_for(
            'security_matrix.security_matrix_matriz_view',
            import_id=import_id,
            module=active_module,
        )
    )


@security_matrix_bp.route('/sync-catalog', methods=['POST'])
@login_required
def security_matrix_sync_catalog():
    if not _can_admin():
        _deny()
    try:
        snap = sm_svc.sync_catalog_from_odoo(_org_id(), current_user.id)
        flash(
            f'Catálogo sincronizado: {snap.user_count} usuarios, {snap.group_count} grupos.',
            'success',
        )
    except OdooCatalogError as e:
        flash(f'Error catálogo Odoo: {e}', 'error')
    except Exception as e:
        flash(f'Error: {e}', 'error')
    return redirect(url_for('security_matrix.security_matrix_index'))


@security_matrix_bp.route('/template')
@login_required
def security_matrix_template():
    if not _can_admin():
        _deny()
    oid = _org_id()
    snap = sm_svc.latest_catalog_snapshot(oid)
    if not snap:
        flash('Sincronizá el catálogo Odoo antes de descargar la plantilla.', 'warning')
        return redirect(url_for('security_matrix.security_matrix_index'))
    catalog = sm_svc.catalog_payload(snap)
    data = build_template_bytes(catalog)
    return Response(
        data,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={'Content-Disposition': 'attachment; filename=matriz_permisos_en1.xlsx'},
    )


@security_matrix_bp.route('/upload', methods=['POST'])
@login_required
def security_matrix_upload():
    if not _can_admin():
        _deny()
    f = request.files.get('matrix_file')
    if not f or not f.filename:
        flash('Seleccioná un archivo .xlsx', 'error')
        return redirect(url_for('security_matrix.security_matrix_index'))
    fn = secure_filename(f.filename)
    if not fn.lower().endswith(('.xlsx', '.xlsm')):
        flash('Solo archivos .xlsx', 'error')
        return redirect(url_for('security_matrix.security_matrix_index'))
    try:
        imp = sm_svc.create_import_from_xlsx(_org_id(), fn, f.read(), current_user.id)
        flash(f'Matriz cargada (import #{imp.id}). Estado: {imp.status}.', 'success')
        return redirect(url_for('security_matrix.security_matrix_import_detail', import_id=imp.id))
    except Exception as e:
        flash(str(e), 'error')
        return redirect(url_for('security_matrix.security_matrix_index'))


@security_matrix_bp.route('/imports/<int:import_id>')
@login_required
def security_matrix_import_detail(import_id: int):
    if not _can_admin():
        _deny()
    from models.security_matrix import SecurityMatrixChangePreview, SecurityMatrixImport, SecurityMatrixRow

    imp = SecurityMatrixImport.query.filter_by(id=import_id, organization_id=_org_id()).first_or_404()
    previews = SecurityMatrixChangePreview.query.filter_by(import_id=imp.id).all()
    all_rows = SecurityMatrixRow.query.filter_by(import_id=imp.id).all()
    error_rows = [r for r in all_rows if r.validation_status == 'error'][:50]
    validation = json.loads(imp.validation_summary_json) if imp.validation_summary_json else {}
    ai = json.loads(imp.ai_summary_json) if imp.ai_summary_json else {}
    catalog = sm_svc.catalog_payload(imp.catalog_snapshot) if imp.catalog_snapshot_id else {}
    q = (request.args.get('q') or '').strip()
    visual_tab = (request.args.get('tab') or 'changes').strip()
    return render_template(
        'admin/security_matrix/import_detail.html',
        imp=imp,
        previews=previews,
        error_rows=error_rows,
        validation=validation,
        ai=ai,
        catalog=catalog,
        visual_tab=visual_tab,
        search=q,
        stats=build_import_stats(previews),
        user_rows=build_user_permission_rows(
            catalog, previews, only_with_changes=(visual_tab == 'changes'), search=q
        )
        if catalog
        else [],
        user_rows_all=build_user_permission_rows(catalog, previews, search=q) if catalog else [],
        group_rows=build_group_summary_rows(catalog, search=q) if catalog else [],
        matriz_rows=build_matriz_design_rows(all_rows),
    )


@security_matrix_bp.route('/imports/<int:import_id>/analyze-ai', methods=['POST'])
@login_required
def security_matrix_analyze_ai(import_id: int):
    if not _can_admin():
        _deny()
    try:
        sm_svc.run_ai_for_import(import_id, _org_id(), current_user.id)
        flash('Análisis IA guardado.', 'success')
    except Exception as e:
        flash(f'IA: {e}', 'error')
    return redirect(url_for('security_matrix.security_matrix_import_detail', import_id=import_id))


@security_matrix_bp.route('/imports/<int:import_id>/approve', methods=['POST'])
@login_required
def security_matrix_approve(import_id: int):
    if not _can_admin():
        _deny()
    try:
        sm_svc.approve_import(import_id, _org_id(), current_user.id)
        flash('Importación aprobada (sin ejecutar en Odoo — Fase 1).', 'success')
    except Exception as e:
        flash(str(e), 'error')
    return redirect(url_for('security_matrix.security_matrix_import_detail', import_id=import_id))


@security_matrix_bp.route('/imports/<int:import_id>/reject', methods=['POST'])
@login_required
def security_matrix_reject(import_id: int):
    if not _can_admin():
        _deny()
    try:
        sm_svc.reject_import(import_id, _org_id(), current_user.id)
        flash('Importación rechazada.', 'info')
    except Exception as e:
        flash(str(e), 'error')
    return redirect(url_for('security_matrix.security_matrix_import_detail', import_id=import_id))


@security_matrix_bp.route('/imports/<int:import_id>/execute', methods=['POST'])
@login_required
def security_matrix_execute(import_id: int):
    if not _can_admin():
        _deny()
    if request.accept_mimetypes.best == 'application/json' or request.is_json:
        return jsonify({
            'ok': False,
            'error': 'Fase 1: ejecución en Odoo deshabilitada hasta Fase 2 (en1_connector apply).',
            'code': 'phase1_execute_blocked',
        }), 501
    flash('Fase 1: ejecutar cambios en Odoo está bloqueado hasta Fase 2.', 'warning')
    return redirect(url_for('security_matrix.security_matrix_import_detail', import_id=import_id))


@security_matrix_bp.route('/imports/<int:import_id>/report')
@login_required
def security_matrix_report(import_id: int):
    if not _can_admin():
        _deny()
    if request.args.get('format') == 'json':
        try:
            return jsonify(sm_svc.import_report_data(import_id, _org_id()))
        except Exception as e:
            return jsonify({'error': str(e)}), 404
    try:
        report = sm_svc.import_report_data(import_id, _org_id())
    except Exception as e:
        flash(str(e), 'error')
        return redirect(url_for('security_matrix.security_matrix_index'))
    return render_template('admin/security_matrix/report.html', report=report)


def register_security_matrix_manager_blueprints(app):
    """Registrado desde nodeone.core.features (evitar import circular con `app`)."""
    if os.environ.get('NODEONE_SKIP_SECURITY_MATRIX_MODULE', '').strip().lower() in (
        '1',
        'true',
        'yes',
    ):
        return
    if 'security_matrix' not in app.blueprints:
        app.register_blueprint(security_matrix_bp)
