"""Onboarding (sesión) y demo request (landing)."""

from flask import Blueprint, jsonify, request, session
from flask_login import login_required

public_api_bp = Blueprint('public_api', __name__)


@public_api_bp.route('/api/onboarding/seen', methods=['POST'])
@login_required
def mark_onboarding_seen():
    """Marca el onboarding como visto."""
    session['onboarding_seen'] = True
    return jsonify({'success': True})


@public_api_bp.route('/api/public/demo-request', methods=['POST'])
def create_demo_request():
    """Recibe solicitudes de demo desde el sitio público."""
    import app as M

    try:
        payload = request.get_json(silent=True) or {}
        name = (payload.get('name') or '').strip()
        company = (payload.get('company') or '').strip()
        phone = (payload.get('phone') or '').strip()
        message = (payload.get('message') or '').strip()
        source = (payload.get('source') or 'landing').strip()[:100]

        if not name or not company or not phone or not message:
            return jsonify({'success': False, 'error': 'Completa todos los campos requeridos.'}), 400
        if len(name) > 200 or len(company) > 200 or len(phone) > 50:
            return jsonify({'success': False, 'error': 'Datos demasiado largos.'}), 400
        if len(message) > 2000:
            return jsonify({'success': False, 'error': 'El mensaje es demasiado largo.'}), 400

        demo_request = M.DemoRequest(
            name=name,
            company=company,
            phone=phone,
            message=message,
            source=source,
        )
        M.db.session.add(demo_request)
        M.db.session.commit()
        return jsonify({'success': True, 'id': demo_request.id}), 201
    except Exception:
        M.db.session.rollback()
        return jsonify({'success': False, 'error': 'No se pudo registrar la solicitud.'}), 500
