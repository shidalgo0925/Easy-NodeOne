"""Rutas HTML y API del módulo Contador."""

from __future__ import annotations

import json
import os
from datetime import datetime

from flask import (
    Blueprint,
    Response,
    abort,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

from app import admin_data_scope_organization_id, default_organization_id
from models.saas import SaasOrganization
from nodeone.modules.contador import service as contador_svc

contador_bp = Blueprint('contador', __name__, url_prefix='/admin/contador')
contador_api_bp = Blueprint('contador_api', __name__, url_prefix='/api/contador')


@contador_bp.app_template_filter('contador_sesion_name')
def contador_sesion_name_filter(value):
    return contador_svc.format_sesion_display_name(value)


def _org_id() -> int:
    try:
        oid = int(admin_data_scope_organization_id())
    except Exception:
        oid = int(default_organization_id())
    if SaasOrganization.query.get(int(oid)) is None:
        return int(default_organization_id())
    return int(oid)


def _platform_admin() -> bool:
    """Mismo criterio que nav_can / menú: is_admin de plataforma pasa sin permisos RBAC explícitos."""
    return bool(
        current_user.is_authenticated and getattr(current_user, 'is_admin', False)
    )


def _can_admin() -> bool:
    return current_user.is_authenticated and (
        _platform_admin() or current_user.has_permission('contador.admin')
    )


def _can_review() -> bool:
    return current_user.is_authenticated and (
        _platform_admin()
        or current_user.has_permission('contador.admin')
        or current_user.has_permission('contador.review')
    )


def _can_capture() -> bool:
    """Captura: solo admin del módulo u operador (no supervisor solo-revisión)."""
    return current_user.is_authenticated and (
        _platform_admin()
        or current_user.has_permission('contador.admin')
        or current_user.has_permission('contador.capture')
    )


def _can_any_contador() -> bool:
    return current_user.is_authenticated and (
        _platform_admin()
        or current_user.has_permission('contador.admin')
        or current_user.has_permission('contador.review')
        or current_user.has_permission('contador.capture')
    )


def _is_contador_operator_only() -> bool:
    """UI/API operador puro (COP): no aplica a admin de plataforma ni contador.admin."""
    if not current_user.is_authenticated:
        return False
    if _platform_admin() or current_user.has_permission('contador.admin'):
        return False
    return bool(current_user.has_permission('contador.capture'))


def _deny_json(msg: str, code: int = 403):
    return jsonify({'error': msg}), code


def _deny_flash(msg: str):
    flash(msg, 'error')
    return redirect(url_for('dashboard'))


# --- HTML ---


@contador_bp.route('', strict_slashes=False)
@login_required
def contador_index():
    if not _can_any_contador():
        return _deny_flash('No tenés permiso para el módulo Contador.')
    return render_template('admin/contador/index.html')


@contador_bp.route('/catalogo', strict_slashes=False)
@login_required
def contador_catalogo():
    if not _can_any_contador():
        return _deny_flash('Sin permiso.')
    oid = _org_id()
    from models.contador import ContadorProductTemplate

    page = request.args.get('page', 1, type=int) or 1
    raw_per = request.args.get('per_page', 25, type=int) or 25
    search = (request.args.get('q') or '').strip()
    per_page = max(1, min(int(raw_per), 100))
    if page < 1:
        page = 1

    q = ContadorProductTemplate.query.filter_by(organization_id=oid)
    if search:
        like = f'%{search}%'
        q = q.filter(
            (ContadorProductTemplate.name.ilike(like))
            | (ContadorProductTemplate.category.ilike(like))
            | (ContadorProductTemplate.subcategory.ilike(like))
            | (ContadorProductTemplate.product_class.ilike(like))
        )
    q = q.order_by(
        ContadorProductTemplate.name.asc()
    )
    pagination = q.paginate(page=page, per_page=per_page, error_out=False)
    return render_template(
        'admin/contador/catalogo.html',
        templates=pagination.items,
        pagination=pagination,
        per_page=per_page,
        search=search,
    )


@contador_bp.route('/catalogo/nuevo', methods=['GET', 'POST'], strict_slashes=False)
@login_required
def contador_catalogo_nuevo():
    if not _can_admin():
        return _deny_flash('Solo administradores de conteo pueden crear productos.')
    if request.method == 'POST':
        try:
            res = contador_svc.create_catalog_variant_manual(
                _org_id(),
                product_name=request.form.get('product_name'),
                presentation=request.form.get('presentation'),
                category=request.form.get('category'),
                subcategory=request.form.get('subcategory'),
                product_class=request.form.get('product_class'),
                internal_code=request.form.get('internal_code'),
                barcode=request.form.get('barcode'),
            )
            msg = 'Producto creado correctamente.'
            if res.get('template_created'):
                msg += ' (nueva plantilla)'
            flash(msg, 'success')
            return redirect(url_for('contador.contador_catalogo'))
        except Exception as e:
            flash(str(e), 'error')
    return render_template('admin/contador/catalogo_nuevo.html')


def _form_opt_int(name: str) -> int | None:
    raw = (request.form.get(name) or '').strip()
    if raw == '':
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def _form_req_int(name: str) -> int | None:
    raw = (request.form.get(name) or '').strip()
    try:
        return int(raw)
    except ValueError:
        return None


def _handle_importar_wizard_upload():
    """Paso 1 del asistente: guarda el XLSX y redirige al mapeo."""
    f = request.files.get('file')
    if not f or not f.filename:
        flash('Seleccioná un archivo.', 'error')
        return redirect(url_for('contador.contador_importar'))
    raw = f.read()
    if len(raw) > 25 * 1024 * 1024:
        flash('El archivo supera el límite de 25 MB.', 'error')
        return redirect(url_for('contador.contador_importar'))
    try:
        token = contador_svc.wizard_save_upload(raw, current_user.id)
    except Exception as e:
        flash(str(e), 'error')
        return redirect(url_for('contador.contador_importar'))
    session['contador_wizard_token'] = token
    session['contador_wizard_filename'] = secure_filename(f.filename) or 'catalogo.xlsx'
    return redirect(url_for('contador.contador_importar_mapear'))


def _handle_importar_automatico():
    """Importación en un paso con detección automática."""
    f = request.files.get('file')
    if not f or not f.filename:
        flash('Seleccioná un archivo.', 'error')
        return redirect(url_for('contador.contador_importar'))
    raw = f.read()
    try:
        res = contador_svc.import_xlsx_bytes(raw, f.filename, _org_id(), current_user.id)
        sk = int(res.get('rows_skipped') or 0)
        tail = f' Filas omitidas (instrucciones o no válidas): {sk}.' if sk else ''
        flash(
            f"Importación OK: +{res['templates_created']} plantillas, "
            f"+{res['variants_created']} variantes nuevas, {res['variants_updated']} actualizadas.{tail}",
            'success',
        )
    except Exception as e:
        flash(str(e), 'error')
    return redirect(url_for('contador.contador_catalogo'))


@contador_bp.route('/importar', methods=['GET', 'POST'], strict_slashes=False)
@login_required
def contador_importar():
    """GET: página de importación. POST: campo oculto import_mode = wizard | automatic (evita url_for a rutas no cargadas)."""
    if not _can_admin():
        return _deny_flash('Solo administradores de conteo pueden importar.')
    if request.method == 'POST':
        mode = (request.form.get('import_mode') or '').strip().lower()
        if mode == 'wizard':
            return _handle_importar_wizard_upload()
        if mode == 'automatic':
            return _handle_importar_automatico()
        flash('Modo de importación no reconocido.', 'error')
        return redirect(url_for('contador.contador_importar'))
    return render_template('admin/contador/importar.html')


@contador_bp.route('/importar/subir', methods=['POST'], strict_slashes=False)
@login_required
def contador_importar_subir():
    """Alias POST del asistente (compatibilidad)."""
    if not _can_admin():
        return _deny_flash('Solo administradores de conteo pueden importar.')
    return _handle_importar_wizard_upload()


@contador_bp.route('/importar/automatico', methods=['POST'], strict_slashes=False)
@login_required
def contador_importar_automatico():
    """Alias POST import automático (compatibilidad)."""
    if not _can_admin():
        return _deny_flash('Solo administradores de conteo pueden importar.')
    return _handle_importar_automatico()


@contador_bp.route('/importar/mapear', methods=['GET', 'POST'], strict_slashes=False)
@login_required
def contador_importar_mapear():
    """Paso 2: vista previa + mapeo tipo Odoo."""
    if not _can_admin():
        return _deny_flash('Solo administradores de conteo pueden importar.')

    token = session.get('contador_wizard_token')
    path = contador_svc.wizard_load_path(token)
    meta = contador_svc.wizard_meta(token)
    if (
        not path
        or not meta
        or int(meta.get('user_id') or 0) != int(current_user.id)
    ):
        flash('Subí de nuevo el archivo (sesión caducada o inválida).', 'error')
        return redirect(url_for('contador.contador_importar'))

    raw = path.read_bytes()
    filename = session.get('contador_wizard_filename') or 'catalogo.xlsx'

    def _render_mapear(preview: dict, has_header_flag: bool):
        return render_template(
            'admin/contador/importar_mapear.html',
            preview=preview,
            filename=filename,
            sel_sheet=preview['sheet'],
            has_header=has_header_flag,
        )

    if request.method == 'POST':
        sheet = (request.form.get('sheet') or '').strip()
        has_header = request.form.get('has_header') == '1'

        if request.form.get('preview_only'):
            preview = contador_svc.build_import_preview(
                raw,
                sheet_name=sheet or None,
                has_header=has_header,
            )
            return _render_mapear(preview, has_header)

        ni = _form_req_int('col_name')
        pi = _form_req_int('col_presentation')
        if ni is None or pi is None:
            flash('Elegí columnas obligatorias: nombre del producto y presentación.', 'error')
            preview = contador_svc.build_import_preview(
                raw,
                sheet_name=sheet or None,
                has_header=has_header,
            )
            return _render_mapear(preview, has_header)
        try:
            res = contador_svc.import_xlsx_bytes_mapped(
                raw,
                filename,
                _org_id(),
                current_user.id,
                sheet_name=sheet,
                has_header=has_header,
                col_name=ni,
                col_pres=pi,
                col_cat=_form_opt_int('col_category'),
                col_sub=_form_opt_int('col_subcategory'),
                col_cls=_form_opt_int('col_product_class'),
                col_code=_form_opt_int('col_code'),
                col_bc=_form_opt_int('col_barcode'),
            )
            sk = int(res.get('rows_skipped') or 0)
            tail = f' Filas omitidas: {sk}.' if sk else ''
            flash(
                f"Asistente: +{res['templates_created']} plantillas, "
                f"+{res['variants_created']} variantes nuevas, {res['variants_updated']} actualizadas.{tail}",
                'success',
            )
        except Exception as e:
            flash(str(e), 'error')
            preview = contador_svc.build_import_preview(
                raw,
                sheet_name=sheet or None,
                has_header=has_header,
            )
            return _render_mapear(preview, has_header)
        contador_svc.wizard_delete_upload(token)
        session.pop('contador_wizard_token', None)
        session.pop('contador_wizard_filename', None)
        return redirect(url_for('contador.contador_catalogo'))

    sheet_q = request.args.get('sheet')
    has_header = request.args.get('has_header', '1') not in ('0', 'false', '')
    preview = contador_svc.build_import_preview(
        raw,
        sheet_name=sheet_q if sheet_q else None,
        has_header=has_header,
    )
    return _render_mapear(preview, has_header)


@contador_bp.route('/sesiones', strict_slashes=False)
@login_required
def contador_sesiones():
    if not _can_any_contador():
        return _deny_flash('Sin permiso.')
    from models.contador import ContadorSession

    ses = (
        ContadorSession.query.filter_by(organization_id=_org_id())
        .order_by(ContadorSession.created_at.desc())
        .limit(200)
        .all()
    )
    return render_template('admin/contador/sesiones.html', sesiones=ses)


@contador_bp.route('/sesiones/new', methods=['GET', 'POST'], strict_slashes=False)
@login_required
def contador_sesion_new():
    if not _can_admin():
        return _deny_flash('Solo administradores pueden crear sesiones.')
    if request.method == 'POST':
        name = (request.form.get('name') or '').strip()
        desc = (request.form.get('description') or '').strip()
        if not name:
            flash('El nombre es obligatorio.', 'error')
            return redirect(url_for('contador.contador_sesion_new'))
        s = contador_svc.create_session(_org_id(), name, desc, current_user.id)
        flash('Sesión creada en borrador.', 'success')
        return redirect(url_for('contador.contador_sesion_detail', session_id=s.id))
    return render_template('admin/contador/sesion_new.html')


@contador_bp.route('/sesiones/<int:session_id>/abrir', methods=['POST'], strict_slashes=False)
@login_required
def contador_sesion_abrir(session_id: int):
    if not _can_admin():
        return _deny_flash('Sin permiso.')
    try:
        contador_svc.open_session(session_id, _org_id())
        flash('Sesión abierta: líneas generadas por cada variante activa.', 'success')
    except Exception as e:
        flash(str(e), 'error')
    return redirect(url_for('contador.contador_sesion_detail', session_id=session_id))


@contador_bp.route('/sesiones/<int:session_id>/cerrar', methods=['POST'], strict_slashes=False)
@login_required
def contador_sesion_cerrar(session_id: int):
    if not _can_admin():
        return _deny_flash('Sin permiso.')
    try:
        contador_svc.close_session(session_id, _org_id())
        flash('Sesión cerrada.', 'success')
    except Exception as e:
        flash(str(e), 'error')
    return redirect(url_for('contador.contador_sesion_detail', session_id=session_id))


@contador_bp.route('/sesiones/<int:session_id>/borrar', methods=['POST'], strict_slashes=False)
@login_required
def contador_sesion_borrar(session_id: int):
    if not _can_admin():
        return _deny_flash('Sin permiso.')
    try:
        contador_svc.delete_session_if_draft(session_id, _org_id())
        flash('Sesión borrada.', 'success')
        return redirect(url_for('contador.contador_sesiones'))
    except Exception as e:
        flash(str(e), 'error')
        return redirect(url_for('contador.contador_sesion_detail', session_id=session_id))


@contador_bp.route('/sesiones/<int:session_id>', strict_slashes=False)
@login_required
def contador_sesion_detail(session_id: int):
    if not _can_any_contador():
        return _deny_flash('Sin permiso.')
    from models.contador import ContadorSession

    s = ContadorSession.query.filter_by(id=session_id, organization_id=_org_id()).first_or_404()
    summ = contador_svc.session_summary(session_id, _org_id())
    line_rows = contador_svc.session_lines_for_detail(session_id, _org_id())
    return render_template(
        'admin/contador/sesion_detail.html',
        ses=s,
        summary=summ,
        line_rows=line_rows,
    )


@contador_bp.route('/sesiones/<int:session_id>/line/<int:line_id>/historial', strict_slashes=False)
@login_required
def contador_line_historial(session_id: int, line_id: int):
    if not _can_any_contador():
        return _deny_flash('Sin permiso.')
    from models.contador import ContadorCaptureLog, ContadorCountLine, ContadorSession

    s = ContadorSession.query.filter_by(id=session_id, organization_id=_org_id()).first_or_404()
    if (
        ContadorCountLine.query.filter_by(
            id=line_id, session_id=session_id, organization_id=_org_id()
        ).first()
        is None
    ):
        abort(404)
    logs = (
        ContadorCaptureLog.query.filter_by(session_id=session_id, line_id=line_id)
        .order_by(ContadorCaptureLog.created_at.desc())
        .all()
    )
    return render_template(
        'admin/contador/line_historial.html',
        ses=s,
        line_id=line_id,
        logs=logs,
    )


@contador_bp.route('/sesiones/<int:session_id>/captura', methods=['GET', 'POST'], strict_slashes=False)
@login_required
def contador_sesion_captura(session_id: int):
    if not _can_capture():
        return _deny_flash('Sin permiso de captura.')
    from models.contador import ContadorSession

    s = ContadorSession.query.filter_by(id=session_id, organization_id=_org_id()).first_or_404()
    if request.method == 'POST':
        try:
            vid = int(request.form.get('variant_id') or 0)
            qty = float(request.form.get('quantity') or -1)
        except (TypeError, ValueError):
            flash('Cantidad y variante inválidas.', 'error')
            return redirect(
                url_for('contador.contador_sesion_captura', session_id=session_id, **dict(request.args))
            )
        if qty < 0:
            flash('La cantidad no puede ser negativa.', 'error')
            return redirect(
                url_for('contador.contador_sesion_captura', session_id=session_id, **dict(request.args))
            )
        try:
            contador_svc.capture_quantity(
                session_id,
                vid,
                qty,
                _org_id(),
                current_user.id,
                operator_restrict_own=_is_contador_operator_only(),
            )
            flash('Conteo guardado.', 'success')
        except PermissionError as e:
            flash(str(e), 'error')
        except Exception as e:
            flash(str(e), 'error')
        rq = (request.form.get('captura_ret_q') or '').strip()
        rf = (request.form.get('captura_ret_filtro') or 'all').strip().lower()
        if rf not in ('all', 'pend', 'done'):
            rf = 'all'
        try:
            rp = int(request.form.get('captura_ret_page') or 1)
        except (TypeError, ValueError):
            rp = 1
        try:
            rpp = int(request.form.get('captura_ret_per_page') or 10)
        except (TypeError, ValueError):
            rpp = 10
        return redirect(
            url_for(
                'contador.contador_sesion_captura',
                session_id=session_id,
                q=rq or None,
                filtro=rf,
                page=max(1, rp),
                per_page=max(1, min(rpp, 100)),
            )
        )
    page = request.args.get('page', 1, type=int) or 1
    per_page = request.args.get('per_page', 10, type=int) or 10
    q_arg = (request.args.get('q') or '').strip()
    filtro = (request.args.get('filtro') or 'all').strip().lower()
    if filtro not in ('all', 'pend', 'done'):
        filtro = 'all'
    if s.status == 'open':
        try:
            contador_svc.sync_session_lines_with_catalog(session_id, _org_id())
        except Exception:
            pass
    capture_rows, _ses, cap_total = contador_svc.list_session_lines_for_capture(
        session_id,
        _org_id(),
        page=max(1, page),
        per_page=max(1, min(per_page, 100)),
        q=q_arg or None,
        filtro=filtro,
    )
    pp = max(1, min(per_page, 100))
    pg = max(1, page)
    cap_pages = max(1, (cap_total + pp - 1) // pp) if cap_total else 1
    summ = contador_svc.session_summary(session_id, _org_id())
    return render_template(
        'admin/contador/captura.html',
        ses=s,
        summary=summ,
        last_capture_label=contador_svc.format_last_capture_label(summ),
        capture_lines=capture_rows,
        capture_total=cap_total,
        capture_page=pg,
        capture_pages=cap_pages,
        capture_per_page=pp,
        capture_q=q_arg,
        capture_filtro=filtro,
        is_operator=_is_contador_operator_only(),
    )


@contador_bp.route('/sesiones/<int:session_id>/revision/quick', methods=['POST'], strict_slashes=False)
@login_required
def contador_revision_quick(session_id: int):
    if not _can_review():
        return _deny_flash('Sin permiso de revisión.')
    from models.contador import ContadorCountLine

    line_id = request.form.get('line_id', type=int)
    if not line_id:
        flash('Línea inválida.', 'error')
        return redirect(url_for('contador.contador_sesiones'))
    line = ContadorCountLine.query.filter_by(
        id=line_id, session_id=session_id, organization_id=_org_id()
    ).first_or_404()
    action = (request.form.get('action') or '').strip()
    qty_raw = request.form.get('quantity')
    qty_i = None
    if qty_raw is not None and str(qty_raw).strip() != '':
        try:
            qty_i = float(qty_raw)
        except ValueError:
            flash('Cantidad inválida.', 'error')
            return redirect(url_for('contador.contador_sesion_revision', session_id=session_id))
    try:
        if action == 'review':
            contador_svc.review_line(
                session_id,
                line.variant_id,
                qty_i,
                True,
                None,
                _org_id(),
                current_user.id,
            )
            flash('Marcado como revisado.', 'success')
        else:
            if qty_i is None:
                flash('Indicá cantidad.', 'error')
                return redirect(url_for('contador.contador_sesion_revision', session_id=session_id))
            contador_svc.review_line(
                session_id,
                line.variant_id,
                qty_i,
                False,
                None,
                _org_id(),
                current_user.id,
            )
            flash('Cantidad actualizada.', 'success')
    except Exception as e:
        flash(str(e), 'error')
    return redirect(url_for('contador.contador_sesion_revision', session_id=session_id))


@contador_bp.route('/sesiones/<int:session_id>/revision', strict_slashes=False)
@login_required
def contador_sesion_revision(session_id: int):
    if not _can_review():
        return _deny_flash('Sin permiso de revisión.')
    from models.contador import ContadorCountLine, ContadorSession

    s = ContadorSession.query.filter_by(id=session_id, organization_id=_org_id()).first_or_404()
    lines = (
        ContadorCountLine.query.filter_by(session_id=session_id)
        .order_by(ContadorCountLine.id.asc())
        .all()
    )
    summ = contador_svc.session_summary(session_id, _org_id())
    return render_template('admin/contador/revision.html', ses=s, lines=lines, summary=summ)


@contador_bp.route('/sesiones/<int:session_id>/exportar', strict_slashes=False)
@login_required
def contador_sesion_exportar(session_id: int):
    if not _can_admin():
        return _deny_flash('Solo administradores pueden exportar.')
    from models.contador import ContadorSession

    s = ContadorSession.query.filter_by(id=session_id, organization_id=_org_id()).first_or_404()
    return render_template('admin/contador/exportar.html', ses=s)


@contador_bp.route('/configuracion', strict_slashes=False)
@login_required
def contador_config():
    if not _can_admin():
        return _deny_flash('Sin permiso.')
    return render_template('admin/contador/configuracion.html')


@contador_bp.route('/purgar-datos', methods=['POST'], strict_slashes=False)
@login_required
def contador_purgar_datos():
    """Elimina sesiones, líneas y catálogo Contador de la organización actual (irreversible)."""
    if not _can_admin():
        return _deny_flash('Sin permiso.')
    if (request.form.get('confirmar') or '').strip() != 'BORRAR':
        flash('Escribí exactamente BORRAR en el campo de confirmación.', 'error')
        return redirect(url_for('contador.contador_config'))
    try:
        stats = contador_svc.purge_organization_contador_data(_org_id())
        flash(
            'Contador vaciado: '
            f"{stats['sessions']} sesión(es), {stats['lines']} línea(s), "
            f"{stats['templates']} plantilla(s), {stats['variants']} variante(s).",
            'success',
        )
    except Exception as e:
        flash(str(e), 'error')
    return redirect(url_for('contador.contador_catalogo'))


# --- API ---


@contador_api_bp.route('/import-xls', methods=['POST'], strict_slashes=False)
@login_required
def api_import_xls():
    if not _can_admin():
        return _deny_json('Forbidden', 403)
    f = request.files.get('file')
    if not f:
        return _deny_json('Falta archivo', 400)
    raw = f.read()
    try:
        res = contador_svc.import_xlsx_bytes(raw, f.filename, _org_id(), current_user.id)
        return jsonify({'success': True, **res})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400


@contador_api_bp.route('/search-products', methods=['GET'], strict_slashes=False)
@login_required
def api_search_products():
    if not _can_capture():
        return _deny_json('Forbidden', 403)
    q = (request.args.get('q') or '').strip()
    limit = request.args.get('limit', default=12, type=int) or 12
    offset = request.args.get('offset', default=0, type=int) or 0
    data = contador_svc.search_variants(_org_id(), q, limit=limit, offset=offset)
    return jsonify(data)


@contador_api_bp.route('/sessions', methods=['POST'], strict_slashes=False)
@login_required
def api_sessions_create():
    if not _can_admin():
        return _deny_json('Forbidden', 403)
    body = request.get_json(silent=True) or {}
    name = (body.get('name') or '').strip()
    if not name:
        return _deny_json('name obligatorio', 400)
    desc = (body.get('description') or '').strip()
    s = contador_svc.create_session(_org_id(), name, desc, current_user.id)
    return jsonify({'id': s.id, 'name': s.name, 'status': s.status})


@contador_api_bp.route('/sessions/<int:session_id>/open', methods=['POST'], strict_slashes=False)
@login_required
def api_sessions_open(session_id: int):
    if not _can_admin():
        return _deny_json('Forbidden', 403)
    try:
        s = contador_svc.open_session(session_id, _org_id())
        return jsonify({'id': s.id, 'status': s.status, 'opened_at': s.opened_at.isoformat() if s.opened_at else None})
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@contador_api_bp.route('/sessions/<int:session_id>/close', methods=['POST'], strict_slashes=False)
@login_required
def api_sessions_close(session_id: int):
    if not _can_admin():
        return _deny_json('Forbidden', 403)
    try:
        s = contador_svc.close_session(session_id, _org_id())
        return jsonify({'id': s.id, 'status': s.status})
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@contador_api_bp.route('/sessions/<int:session_id>/lines', methods=['GET'], strict_slashes=False)
@login_required
def api_sessions_lines(session_id: int):
    if not _can_any_contador():
        return _deny_json('Forbidden', 403)
    rows = contador_svc.export_rows(session_id, _org_id())
    return jsonify(rows)


@contador_api_bp.route('/sessions/<int:session_id>/capture', methods=['POST'], strict_slashes=False)
@login_required
def api_sessions_capture(session_id: int):
    if not _can_capture():
        return _deny_json('Forbidden', 403)
    body = request.get_json(silent=True) or {}
    try:
        vid = int(body.get('variant_id'))
        qty = float(body.get('quantity'))
    except (TypeError, ValueError):
        return _deny_json('variant_id y quantity requeridos', 400)
    try:
        line = contador_svc.capture_quantity(
            session_id,
            vid,
            qty,
            _org_id(),
            current_user.id,
            operator_restrict_own=_is_contador_operator_only(),
        )
        return jsonify({'ok': True, 'line_id': line.id, 'counted_qty': line.counted_qty, 'status': line.status})
    except PermissionError as e:
        return jsonify({'error': str(e)}), 403
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@contador_api_bp.route('/sessions/<int:session_id>/capture-bulk', methods=['POST'], strict_slashes=False)
@login_required
def api_sessions_capture_bulk(session_id: int):
    if not _can_capture():
        return _deny_json('Forbidden', 403)
    body = request.get_json(silent=True) or {}
    lines = body.get('lines')
    if not isinstance(lines, list):
        return _deny_json('lines debe ser un array', 400)
    try:
        n = contador_svc.capture_bulk(
            session_id,
            _org_id(),
            current_user.id,
            lines,
            operator_restrict_own=_is_contador_operator_only(),
        )
        return jsonify({'ok': True, 'updated': n})
    except PermissionError as e:
        return jsonify({'ok': False, 'error': str(e)}), 403
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 400


@contador_api_bp.route('/sessions/<int:session_id>/review-line', methods=['POST'], strict_slashes=False)
@login_required
def api_sessions_review_line(session_id: int):
    if not _can_review():
        return _deny_json('Forbidden', 403)
    body = request.get_json(silent=True) or {}
    try:
        vid = int(body.get('variant_id'))
    except (TypeError, ValueError):
        return _deny_json('variant_id requerido', 400)
    qty = body.get('quantity')
    qty_i = float(qty) if qty is not None and str(qty).strip() != '' else None
    mark = bool(body.get('mark_reviewed'))
    notes = body.get('notes')
    try:
        line = contador_svc.review_line(
            session_id,
            vid,
            qty_i,
            mark,
            notes,
            _org_id(),
            current_user.id,
        )
        return jsonify({'ok': True, 'line_id': line.id, 'status': line.status})
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@contador_api_bp.route('/sessions/<int:session_id>/summary', methods=['GET'], strict_slashes=False)
@login_required
def api_sessions_summary(session_id: int):
    if not _can_any_contador():
        return _deny_json('Forbidden', 403)
    try:
        return jsonify(contador_svc.session_summary(session_id, _org_id()))
    except Exception:
        abort(404)


def _export_response(session_id: int, fmt: str):
    if not _can_admin():
        return _deny_json('Forbidden', 403)
    oid = _org_id()
    rows = contador_svc.export_rows(session_id, oid)
    fname_base = f'conteo_{session_id}_{datetime.utcnow().strftime("%Y%m%d_%H%M")}'
    try:
        if fmt == 'xlsx':
            raw = contador_svc.build_export_xlsx(rows)
            contador_svc.log_export(oid, session_id, 'xlsx', fname_base + '.xlsx', 'ok', None, current_user.id)
            return Response(
                raw,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                headers={'Content-Disposition': f'attachment; filename={fname_base}.xlsx'},
            )
        if fmt == 'csv':
            raw = contador_svc.build_export_csv(rows)
            contador_svc.log_export(oid, session_id, 'csv', fname_base + '.csv', 'ok', None, current_user.id)
            return Response(
                raw,
                mimetype='text/csv; charset=utf-8',
                headers={'Content-Disposition': f'attachment; filename={fname_base}.csv'},
            )
        if fmt == 'json':
            raw = json.dumps(rows, ensure_ascii=False, indent=2).encode('utf-8')
            contador_svc.log_export(oid, session_id, 'json', fname_base + '.json', 'ok', None, current_user.id)
            return Response(
                raw,
                mimetype='application/json; charset=utf-8',
                headers={'Content-Disposition': f'attachment; filename={fname_base}.json'},
            )
    except Exception as e:
        contador_svc.log_export(oid, session_id, fmt, None, 'error', str(e), current_user.id)
        return jsonify({'error': str(e)}), 500
    return _deny_json('formato inválido', 400)


@contador_api_bp.route('/sessions/<int:session_id>/export.xlsx', methods=['GET'], strict_slashes=False)
@login_required
def api_export_xlsx(session_id: int):
    return _export_response(session_id, 'xlsx')


@contador_api_bp.route('/sessions/<int:session_id>/export.csv', methods=['GET'], strict_slashes=False)
@login_required
def api_export_csv(session_id: int):
    return _export_response(session_id, 'csv')


@contador_api_bp.route('/sessions/<int:session_id>/export.json', methods=['GET'], strict_slashes=False)
@login_required
def api_export_json(session_id: int):
    return _export_response(session_id, 'json')


@contador_api_bp.route('/sessions/<int:session_id>', methods=['DELETE'], strict_slashes=False)
@login_required
def api_sessions_delete(session_id: int):
    if not _can_admin():
        return _deny_json('Forbidden', 403)
    try:
        contador_svc.delete_session_if_draft(session_id, _org_id())
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 400


def register_contador_blueprints(app):
    if os.environ.get('NODEONE_SKIP_CONTADOR_MODULE', '').strip().lower() in ('1', 'true', 'yes'):
        return
    from saas_features import register_simple_saas_guard

    if 'contador' not in app.blueprints:
        register_simple_saas_guard(contador_bp, 'contador')
        app.register_blueprint(contador_bp)
    if 'contador_api' not in app.blueprints:
        register_simple_saas_guard(contador_api_bp, 'contador')
        app.register_blueprint(contador_api_bp)
