"""Decoradores compartidos para APIs admin JSON."""

from __future__ import annotations

from functools import wraps

from flask import jsonify
from flask_login import current_user


def admin_required_json(f):
    """Exige usuario autenticado con flag is_admin; responde 403 JSON si no."""

    @wraps(f)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated or not getattr(current_user, 'is_admin', False):
            return jsonify({'error': 'No autorizado'}), 403
        return f(*args, **kwargs)

    return wrapped
