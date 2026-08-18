"""API JSON: importar XLS → preview → cotización (sin emitir FE)."""

from __future__ import annotations

from flask import jsonify, request
from flask_login import current_user, login_required

from nodeone.modules.sales.xls_import.security import XlsImportSecurityError
from nodeone.modules.sales.xls_import.service import (
    XlsImportError,
    analyze_upload,
    available_profiles,
    commit_import,
    get_preview,
)


def register_xls_import_api(sales_bp) -> None:
    @sales_bp.route('/xls-import/profiles', methods=['GET'])
    @login_required
    def xls_import_profiles():
        from nodeone.modules.sales.routes import _can_sales, _ensure_tables

        _ensure_tables()
        if not _can_sales():
            return jsonify({'error': 'forbidden'}), 403
        return jsonify({'profiles': available_profiles()})

    @sales_bp.route('/xls-import/analyze', methods=['POST'])
    @login_required
    def xls_import_analyze():
        from nodeone.modules.sales.routes import _can_sales, _ensure_tables, _org_id

        _ensure_tables()
        if not _can_sales():
            return jsonify({'error': 'forbidden'}), 403
        oid = _org_id()
        f = request.files.get('file')
        if not f or not f.filename:
            return jsonify({'error': 'file_required', 'user_message': 'Seleccione un archivo .xls o .xlsx.'}), 400
        profile = (request.form.get('profile') or request.args.get('profile') or 'auto').strip()
        try:
            payload = analyze_upload(
                organization_id=oid,
                user_id=getattr(current_user, 'id', None),
                filename=f.filename,
                data=f.read() or b'',
                profile_code=profile,
            )
        except XlsImportSecurityError as exc:
            return jsonify({'error': exc.code, 'user_message': exc.user_message, 'emit_fe': False}), 400
        except XlsImportError as exc:
            status = 409 if exc.code == 'already_imported' else 400
            body = {'error': exc.code, 'user_message': exc.user_message, 'emit_fe': False}
            body.update(exc.payload)
            return jsonify(body), status
        except Exception:
            from flask import current_app as _app

            _app.logger.exception('xls-import analyze')
            return jsonify({
                'error': 'analyze_failed',
                'user_message': 'No se pudo analizar el archivo. Revise que sea .xls/.xlsx y vuelva a intentar.',
                'emit_fe': False,
            }), 500
        if payload.get('already_imported'):
            return jsonify(payload), 409
        return jsonify(payload)

    @sales_bp.route('/xls-import/<int:import_id>', methods=['GET'])
    @login_required
    def xls_import_get(import_id: int):
        from nodeone.modules.sales.routes import _can_sales, _ensure_tables, _org_id

        _ensure_tables()
        if not _can_sales():
            return jsonify({'error': 'forbidden'}), 403
        try:
            payload = get_preview(_org_id(), import_id)
        except XlsImportError as exc:
            return jsonify({'error': exc.code, 'user_message': exc.user_message}), 404 if exc.code == 'not_found' else 400
        if payload.get('already_imported'):
            return jsonify(payload), 409
        return jsonify(payload)

    @sales_bp.route('/xls-import/<int:import_id>/commit', methods=['POST'])
    @login_required
    def xls_import_commit(import_id: int):
        from nodeone.modules.sales.routes import _can_sales, _ensure_tables, _org_id

        _ensure_tables()
        if not _can_sales():
            return jsonify({'error': 'forbidden'}), 403
        data = request.get_json(silent=True) or {}
        create_customer = data.get('create_customer', True)
        if isinstance(create_customer, str):
            create_customer = create_customer.strip().lower() in ('1', 'true', 'yes', 'on')
        try:
            payload = commit_import(
                organization_id=_org_id(),
                user_id=getattr(current_user, 'id', None),
                import_id=import_id,
                create_customer=bool(create_customer),
            )
        except XlsImportError as exc:
            status = 409 if exc.code == 'already_imported' else 400
            body = {'error': exc.code, 'user_message': exc.user_message, 'emit_fe': False}
            body.update(exc.payload)
            return jsonify(body), status
        return jsonify(payload), 201
