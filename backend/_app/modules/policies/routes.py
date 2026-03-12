# Rutas públicas de políticas.
from flask import Blueprint, render_template, abort
from flask_login import login_required, current_user

from . import service as svc
from . import repository as repo

policies_bp = Blueprint('policies', __name__, url_prefix='')


@policies_bp.route('/normativas')
def index():
    """Listado público de políticas activas."""
    from app import Policy
    policies = Policy.query.filter_by(is_active=True).order_by(Policy.title).all()
    return render_template('policies/index.html', policies=policies)


@policies_bp.route('/normativas/<slug>')
def view(slug):
    """Ver una política por slug (público o con login según necesidad)."""
    policy = repo.get_policy_by_slug(slug, active_only=True)
    if not policy:
        abort(404)
    return render_template('policies/view.html', policy=policy)
