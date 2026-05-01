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
    from nodeone.modules.qr_generator.schemas import DEFAULT_BG, DEFAULT_FILL
    from nodeone.modules.qr_generator.utils import (
        build_style_for_generate,
        decode_style_json,
        effective_error_level,
        encode_style_json,
        normalize_hex_color,
        parse_border,
        rate_limit_hit,
        validate_logo_bytes,
        validate_qr_content,
    )

    def _scope_oid():
        return int(admin_data_scope_organization_id())

    def _guard():
        if not has_saas_module_enabled(_scope_oid(), 'qr_generator'):
            return False
        return True

    def _parse_generate_request():
        import base64

        ct = (request.content_type or '').lower()
        logo_bytes = None
        fill = None
        bg = None
        transparent = False
        border_raw = None

        if 'multipart/form-data' in ct:
            content_raw = request.form.get('content', '')
            fmt = (request.form.get('format') or 'png').lower()
            err = (request.form.get('error_level') or 'M').upper()
            size_raw = request.form.get('size', DEFAULT_QR_SIZE)
            fill = request.form.get('fill')
            bg = request.form.get('bg')
            transparent = request.form.get('transparent') in ('1', 'true', 'on', 'yes')
            border_raw = request.form.get('border')
            f = request.files.get('logo')
            if f and getattr(f, 'filename', None):
                logo_bytes = f.read()
        else:
            data = request.get_json(silent=True) or {}
            content_raw = data.get('content', '')
            fmt = (data.get('format') or 'png').lower()
            err = (data.get('error_level') or 'M').upper()
            size_raw = data.get('size', DEFAULT_QR_SIZE)
            st = data.get('style') if isinstance(data.get('style'), dict) else {}
            fill = st.get('fill')
            bg = st.get('bg')
            transparent = bool(st.get('transparent'))
            border_raw = st.get('border')
            b64 = st.get('logo_base64')
            if isinstance(b64, str) and b64.strip():
                try:
                    raw_b64 = b64
                    if 'base64,' in raw_b64:
                        raw_b64 = raw_b64.split('base64,', 1)[1]
                    logo_bytes = base64.b64decode(raw_b64)
                except Exception:
                    return None, (jsonify({'ok': False, 'error': 'logo_base64 inválido'}), 400)

        try:
            size = int(size_raw)
        except (TypeError, ValueError):
            return None, (jsonify({'ok': False, 'error': 'size inválido'}), 400)

        if logo_bytes:
            logo_bytes, lerr = validate_logo_bytes(logo_bytes)
            if lerr:
                return None, (jsonify({'ok': False, 'error': lerr}), 400)

        nfill = normalize_hex_color(fill, DEFAULT_FILL)
        nbg = normalize_hex_color(bg, DEFAULT_BG)
        border = parse_border(border_raw)
        style = build_style_for_generate(nfill, nbg, transparent, border, logo_bytes)
        err_eff = effective_error_level(err, bool(logo_bytes))

        return (
            {
                'content_raw': content_raw,
                'fmt': fmt,
                'size': size,
                'error_level': err_eff,
                'style': style,
            },
            None,
        )

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
        parsed, perr = _parse_generate_request()
        if perr:
            return perr
        assert parsed is not None
        content_raw = parsed['content_raw']
        fmt = parsed['fmt']
        err = parsed['error_level']
        size = max(MIN_QR_SIZE, min(MAX_QR_SIZE, int(parsed['size'])))
        style = parsed['style']
        if fmt not in ALLOWED_FORMATS:
            return jsonify({'ok': False, 'error': 'formato no permitido'}), 400
        if err not in ALLOWED_ERROR_LEVELS:
            return jsonify({'ok': False, 'error': 'error_level inválido'}), 400
        content, verr = validate_qr_content(content_raw if isinstance(content_raw, str) else '')
        if verr:
            return jsonify({'ok': False, 'error': verr}), 400
        try:
            blob, mime, fname = qr_services.generate_file(content, fmt, size, err, style)
        except Exception as ex:
            return jsonify({'ok': False, 'error': str(ex)}), 500
        oid = _scope_oid()
        try:
            sj = encode_style_json(style)
            rec = QrCodeRecord(
                organization_id=oid,
                content=content,
                format=fmt,
                size=size,
                error_level=err,
                style_json=sj,
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
        qraw = (request.args.get('q') or '').strip()
        qry = QrCodeRecord.query.filter_by(organization_id=oid)
        if qraw:
            qclean = (''.join(c for c in qraw if c not in '%_\\'))[:500]
            if qclean:
                qry = qry.filter(QrCodeRecord.content.ilike(f'%{qclean}%'))
        rows = qry.order_by(QrCodeRecord.created_at.desc()).limit(80).all()
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
                    'has_style': bool(getattr(r, 'style_json', None)),
                    'created_at': r.created_at.isoformat() if r.created_at else None,
                    'created_by': r.created_by,
                }
            )
        return jsonify({'ok': True, 'items': out})

    @app.route('/api/qr/<int:rid>/download', methods=['GET'])
    @admin_required
    def api_qr_download(rid: int):
        if not _guard():
            return jsonify({'ok': False, 'error': 'módulo desactivado'}), 403
        oid = _scope_oid()
        row = QrCodeRecord.query.filter_by(id=rid, organization_id=oid).first()
        if row is None:
            abort(404)
        content, verr = validate_qr_content(row.content or '')
        if verr:
            return jsonify({'ok': False, 'error': verr}), 400
        fmt = (row.format or 'png').lower()
        if fmt not in ALLOWED_FORMATS:
            return jsonify({'ok': False, 'error': 'formato inválido en historial'}), 400
        err = (row.error_level or 'M').upper()
        if err not in ALLOWED_ERROR_LEVELS:
            err = 'M'
        try:
            size = int(row.size)
        except (TypeError, ValueError):
            size = DEFAULT_QR_SIZE
        size = max(MIN_QR_SIZE, min(MAX_QR_SIZE, size))
        style = decode_style_json(getattr(row, 'style_json', None))
        try:
            blob, mime, fname = qr_services.generate_file(content, fmt, size, err, style)
        except Exception as ex:
            return jsonify({'ok': False, 'error': str(ex)}), 500
        safe_name = secure_filename(fname) or 'qr.dat'
        return Response(
            blob,
            mimetype=mime.split(';')[0].strip(),
            headers={
                'Content-Disposition': f'attachment; filename="{safe_name}"',
                'Cache-Control': 'no-store',
            },
        )

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
