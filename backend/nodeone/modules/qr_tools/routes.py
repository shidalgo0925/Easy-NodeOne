"""QR simple: solo URL https → PNG. Sin DB."""

from __future__ import annotations

import os
from io import BytesIO

from flask import Blueprint, Response, jsonify, render_template, request

qr_bp = Blueprint('qr_tools', __name__, url_prefix='/api/tools/qr')

MAX_URL_LEN = 500


@qr_bp.route('/generate', methods=['POST'])
def generate_qr():
    data = request.get_json(silent=True) or {}
    url = (data.get('url') or '').strip()
    if not url:
        return jsonify({'error': 'URL requerida'}), 400
    if len(url) > MAX_URL_LEN:
        return jsonify({'error': 'URL demasiado larga'}), 400
    if not url.startswith('https://'):
        return jsonify({'error': 'Solo se permiten URLs https://'}), 400

    import qrcode

    img = qrcode.make(url)
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    body = buffer.getvalue()
    return Response(
        body,
        mimetype='image/png',
        headers={
            'Content-Disposition': 'attachment; filename="qr.png"',
            'Cache-Control': 'no-store',
        },
    )


def register_qr_tools_routes(app):
    if os.environ.get('NODEONE_SKIP_QR_TOOLS_MODULE', '').strip().lower() in ('1', 'true', 'yes', 'on'):
        return
    app.register_blueprint(qr_bp)

    from flask_login import login_required

    @app.route('/tools/qr/simple')
    @login_required
    def tools_qr_simple_page():
        return render_template('tools_qr_simple.html')
