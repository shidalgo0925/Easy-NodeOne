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
    url_for,
)
from flask_login import current_user, login_required

from app import admin_data_scope_organization_id, default_organization_id
from models.saas import SaasOrganization
from nodeone.modules.contador import service as contador_svc

contador_bp = Blueprint('contador', __name__, url_prefix='/admin/contador')
contador_api_bp = Blueprint('contador_api', __name__, url_prefix='/api/contador')


def _org_id() -> int:
    try:
        oid = int(admin_data_scope_organization_id())
    except Exception:
        oid = int(default_organization_id())
    if SaasOrganization.query.get(int(oid)) is None:
        return int(default_organization_id())
    return int(oid)


def _can_admin() -> bool:
    return current_user.is_authenticated and current_user.has_permission('contador.admin')


def _can_review() -> bool:
    return current_user.is_authenticated and (
        current_user.has_permission('contador.admin') or current_user.has_permission('contador.review')
    )


def _can_capture() -> bool:
    """Captura: solo admin del módulo u operador (no supervisor solo-revisión)."""
    return current_user.is_authenticated and (
        current_user.has_permission('contador.admin')
        or current_user.has_permission('contador.capture')
    )


def _can_any_contador() -> bool:
    return current_user.is_authenticated and (
        current_user.has_permission('contador.admin')
        or current_user.has_permission('contador.review')
        or current_user.has_permission('contador.capture')
    )


def _deny_json(msg: str, code: int = 403):
    return jsonify({'error': msg}), code


def _deny_flash(msg: str):
    flash(msg, 'error')
    return redirect(url_for('dashboard'))


# --- HTML ---


@contador_bp.route('')
@login_required
def contador_index():
    if not _can_any_contador():
        return _deny_flash('No tenés permiso para el módulo Contador.')
    return render_template('admin/contador/index.html')


@contador_bp.route('/catalogo')
@login_required
def contador_catalogo():
    if not _can_any_contador():
        return _deny_flash('Sin permiso.')
    oid = _org_id()
    from models.contador import ContadorProductTemplate

    tpls = (
        ContadorProductTemplate.query.filter_by(organization_id=oid)
        .order_by(ContadorProductTemplate.name.asc())
        .all()
    )
    return render_template('admin/contador/catalogo.html', templates=tpls)


@contador_bp.route('/importar', methods=['GET', 'POST'])
@login_required
def contador_importar():
    if not _can_admin():
        return _deny_flash('Solo administradores de conteo pueden importar.')
    if request.method == 'POST':
        f = request.files.get('file')
        if not f or not f.filename:
            flash('Seleccioná un archivo.', 'error')
            return redirect(url_for('contador.contador_importar'))
        raw = f.read()
        try:
            res = contador_svc.import_xlsx_bytes(raw, f.filename, _org_id(), current_user.id)
            flash(
                f"Importación OK: +{res['templates_created']} plantillas, "
                f"+{res['variants_created']} variantes nuevas, {res['variants_updated']} actualizadas.",
                'success',
            )
        except Exception as e:
            flash(str(e), 'error')
        return redirect(url_for('contador.contador_catalogo'))
    return render_template('admin/contador/importar.html')


@contador_bp.route('/sesiones')
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


@contador_bp.route('/sesiones/new', methods=['GET', 'POST'])
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


@contador_bp.route('/sesiones/<int:session_id>/abrir', methods=['POST'])
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


@contador_bp.route('/sesiones/<int:session_id>/cerrar', methods=['POST'])
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


@contador_bp.route('/sesiones/<int:session_id>/borrar', methods=['POST'])
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


@contador_bp.route('/sesiones/<int:session_id>')
@login_required
def contador_sesion_detail(session_id: int):
    if not _can_any_contador():
        return _deny_flash('Sin permiso.')
    from models.contador import ContadorSession

    s = ContadorSession.query.filter_by(id=session_id, organization_id=_org_id()).first_or_404()
    summ = contador_svc.session_summary(session_id, _org_id())
    return render_template('admin/contador/sesion_detail.html', ses=s, summary=summ)


@contador_bp.route('/sesiones/<int:session_id>/captura', methods=['GET', 'POST'])
@login_required
def contador_sesion_captura(session_id: int):
    if not _can_capture():
        return _deny_flash('Sin permiso de captura.')
    from models.contador import ContadorSession

    s = ContadorSession.query.filter_by(id=session_id, organization_id=_org_id()).first_or_404()
    if request.method == 'POST':
        try:
            vid = int(request.form.get('variant_id') or 0)
            qty = int(request.form.get('quantity') or -1)
        except (TypeError, ValueError):
            flash('Cantidad y variante inválidas.', 'error')
            return redirect(url_for('contador.contador_sesion_captura', session_id=session_id))
        if qty < 0:
            flash('La cantidad no puede ser negativa.', 'error')
            return redirect(url_for('contador.contador_sesion_captura', session_id=session_id))
        restrict = (
            current_user.has_permission('contador.capture')
            and not current_user.has_permission('contador.admin')
        )
        try:
            contador_svc.capture_quantity(
                session_id,
                vid,
                qty,
                _org_id(),
                current_user.id,
                operator_restrict_own=restrict,
            )
            flash('Conteo guardado.', 'success')
        except PermissionError as e:
            flash(str(e), 'error')
        except Exception as e:
            flash(str(e), 'error')
        return redirect(url_for('contador.contador_sesion_captura', session_id=session_id))
    return render_template(
        'admin/contador/captura.html',
        ses=s,
        is_operator=current_user.has_permission('contador.capture')
        and not current_user.has_permission('contador.admin'),
    )


@contador_bp.route('/sesiones/<int:session_id>/revision/quick', methods=['POST'])
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
            qty_i = int(qty_raw)
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


@contador_bp.route('/sesiones/<int:session_id>/revision')
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


@contador_bp.route('/sesiones/<int:session_id>/exportar')
@login_required
def contador_sesion_exportar(session_id: int):
    if not _can_admin():
        return _deny_flash('Solo administradores pueden exportar.')
    from models.contador import ContadorSession

    s = ContadorSession.query.filter_by(id=session_id, organization_id=_org_id()).first_or_404()
    return render_template('admin/contador/exportar.html', ses=s)


@contador_bp.route('/configuracion')
@login_required
def contador_config():
    if not _can_admin():
        return _deny_flash('Sin permiso.')
    return render_template('admin/contador/configuracion.html')


# --- API ---


@contador_api_bp.route('/import-xls', methods=['POST'])
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


@contador_api_bp.route('/search-products', methods=['GET'])
@login_required
def api_search_products():
    if not _can_capture():
        return _deny_json('Forbidden', 403)
    q = (request.args.get('q') or '').strip()
    data = contador_svc.search_variants(_org_id(), q)
    return jsonify(data)


@contador_api_bp.route('/sessions', methods=['POST'])
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


@contador_api_bp.route('/sessions/<int:session_id>/open', methods=['POST'])
@login_required
def api_sessions_open(session_id: int):
    if not _can_admin():
        return _deny_json('Forbidden', 403)
    try:
        s = contador_svc.open_session(session_id, _org_id())
        return jsonify({'id': s.id, 'status': s.status, 'opened_at': s.opened_at.isoformat() if s.opened_at else None})
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@contador_api_bp.route('/sessions/<int:session_id>/close', methods=['POST'])
@login_required
def api_sessions_close(session_id: int):
    if not _can_admin():
        return _deny_json('Forbidden', 403)
    try:
        s = contador_svc.close_session(session_id, _org_id())
        return jsonify({'id': s.id, 'status': s.status})
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@contador_api_bp.route('/sessions/<int:session_id>/lines', methods=['GET'])
@login_required
def api_sessions_lines(session_id: int):
    if not _can_any_contador():
        return _deny_json('Forbidden', 403)
    rows = contador_svc.export_rows(session_id, _org_id())
    return jsonify(rows)


@contador_api_bp.route('/sessions/<int:session_id>/capture', methods=['POST'])
@login_required
def api_sessions_capture(session_id: int):
    if not _can_capture():
        return _deny_json('Forbidden', 403)
    body = request.get_json(silent=True) or {}
    try:
        vid = int(body.get('variant_id'))
        qty = int(body.get('quantity'))
    except (TypeError, ValueError):
        return _deny_json('variant_id y quantity enteros requeridos', 400)
    restrict = (
        current_user.has_permission('contador.capture')
        and not current_user.has_permission('contador.admin')
    )
    try:
        line = contador_svc.capture_quantity(
            session_id,
            vid,
            qty,
            _org_id(),
            current_user.id,
            operator_restrict_own=restrict,
        )
        return jsonify({'ok': True, 'line_id': line.id, 'counted_qty': line.counted_qty, 'status': line.status})
    except PermissionError as e:
        return jsonify({'error': str(e)}), 403
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@contador_api_bp.route('/sessions/<int:session_id>/review-line', methods=['POST'])
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
    qty_i = int(qty) if qty is not None and str(qty).strip() != '' else None
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


@contador_api_bp.route('/sessions/<int:session_id>/summary', methods=['GET'])
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


@contador_api_bp.route('/sessions/<int:session_id>/export.xlsx', methods=['GET'])
@login_required
def api_export_xlsx(session_id: int):
    return _export_response(session_id, 'xlsx')


@contador_api_bp.route('/sessions/<int:session_id>/export.csv', methods=['GET'])
@login_required
def api_export_csv(session_id: int):
    return _export_response(session_id, 'csv')


@contador_api_bp.route('/sessions/<int:session_id>/export.json', methods=['GET'])
@login_required
def api_export_json(session_id: int):
    return _export_response(session_id, 'json')


@contador_api_bp.route('/sessions/<int:session_id>', methods=['DELETE'])
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
    if 'contador' not in app.blueprints:
        app.register_blueprint(contador_bp)
    if 'contador_api' not in app.blueprints:
        app.register_blueprint(contador_api_bp)
