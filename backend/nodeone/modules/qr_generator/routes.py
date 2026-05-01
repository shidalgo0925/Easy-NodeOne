"""Generador QR estático (tenant + historial)."""

import os

from nodeone.modules.qr_generator.schemas import (
    ALLOWED_ERROR_LEVELS,
    ALLOWED_FORMATS,
    DEFAULT_QR_SIZE,
    MAX_QR_SIZE,
    MIN_QR_SIZE,
)


def register_qr_generator_routes(app):
    if os.environ.get('NODEONE_SKIP_QR_GENERATOR_MODULE', '').strip().lower() in ('1', 'true', 'yes', 'on'):
        return
    from flask import Response, abort, jsonify, redirect, render_template, request, url_for
    from flask_login import current_user
    from werkzeug.utils import secure_filename

    import app as M
    from app import (
        admin_data_scope_organization_id,
        admin_required,
        db,
        has_saas_module_enabled,
    )
    from models.qr_codes import QrCodeRecord
    from nodeone.modules.qr_generator import services as qr_services
    from nodeone.modules.qr_generator.utils import rate_limit_hit, validate_qr_content

    def _scope_oid():
        return int(admin_data_scope_organization_id())

    def _guard():
        if not has_saas_module_enabled(_scope_oid(), 'qr_generator'):
            return False
        return True

    @app.route('/admin/tools/qr')
    @app.route('/tools/qr')
    @admin_required
    def admin_tools_qr():
        if not _guard():
            from flask import flash

            flash('El módulo Generador QR no está activo para esta organización.', 'error')
            return redirect(url_for('dashboard'))
        return render_template('admin/tools_qr.html')

    @app.route('/api/qr/generate', methods=['POST'])
    @admin_required
    def api_qr_generate():
        if not _guard():
            return jsonify({'ok': False, 'error': 'módulo desactivado'}), 403
        if rate_limit_hit(getattr(current_user, 'id', None), request.remote_addr or ''):
            return jsonify({'ok': False, 'error': 'rate_limited'}), 429
        data = request.get_json(silent=True) or {}
        content_raw = data.get('content', '')
        fmt = (data.get('format') or 'png').lower()
        err = (data.get('error_level') or 'M').upper()
        try:
            size = int(data.get('size', DEFAULT_QR_SIZE))
        except (TypeError, ValueError):
            return jsonify({'ok': False, 'error': 'size inválido'}), 400
        size = max(MIN_QR_SIZE, min(MAX_QR_SIZE, size))
        if fmt not in ALLOWED_FORMATS:
            return jsonify({'ok': False, 'error': 'formato no permitido'}), 400
        if err not in ALLOWED_ERROR_LEVELS:
            return jsonify({'ok': False, 'error': 'error_level inválido'}), 400
        content, verr = validate_qr_content(content_raw if isinstance(content_raw, str) else '')
        if verr:
            return jsonify({'ok': False, 'error': verr}), 400
        try:
            blob, mime, fname = qr_services.generate_file(content, fmt, size, err)
        except Exception as ex:
            return jsonify({'ok': False, 'error': str(ex)}), 500
        oid = _scope_oid()
        try:
            rec = QrCodeRecord(
                organization_id=oid,
                content=content,
                format=fmt,
                size=size,
                error_level=err,
                created_by=int(getattr(current_user, 'id', 0) or 0) or None,
            )
            db.session.add(rec)
            db.session.commit()
        except Exception:
            db.session.rollback()
        safe_name = secure_filename(fname) or 'qr.dat'
        return Response(
            blob,
            mimetype=mime.split(';')[0].strip(),
            headers={
                'Content-Disposition': f'attachment; filename="{safe_name}"',
                'Cache-Control': 'no-store',
            },
        )

    @app.route('/api/qr/list', methods=['GET'])
    @admin_required
    def api_qr_list():
        if not _guard():
            return jsonify({'ok': False, 'error': 'módulo desactivado'}), 403
        oid = _scope_oid()
        rows = (
            QrCodeRecord.query.filter_by(organization_id=oid)
            .order_by(QrCodeRecord.created_at.desc())
            .limit(80)
            .all()
        )
        out = []
        for r in rows:
            prev = (r.content or '')[:120]
            out.append(
                {
                    'id': r.id,
                    'content_preview': prev + ('…' if len(r.content or '') > 120 else ''),
                    'format': r.format,
                    'size': r.size,
                    'error_level': r.error_level,
                    'created_at': r.created_at.isoformat() if r.created_at else None,
                    'created_by': r.created_by,
                }
            )
        return jsonify({'ok': True, 'items': out})

    @app.route('/api/qr/<int:rid>', methods=['DELETE'])
    @admin_required
    def api_qr_delete(rid: int):
        if not _guard():
            return jsonify({'ok': False, 'error': 'módulo desactivado'}), 403
        oid = _scope_oid()
        row = QrCodeRecord.query.filter_by(id=rid, organization_id=oid).first()
        if row is None:
            abort(404)
        try:
            db.session.delete(row)
            db.session.commit()
            return jsonify({'ok': True})
        except Exception as ex:
            db.session.rollback()
            return jsonify({'ok': False, 'error': str(ex)}), 500
