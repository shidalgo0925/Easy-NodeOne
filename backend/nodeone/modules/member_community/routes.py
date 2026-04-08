"""Miembro: foros y grupos (páginas placeholder con chequeo de membresía)."""

from flask import Blueprint, flash, redirect, render_template, url_for
from flask_login import current_user, login_required

member_community_bp = Blueprint('member_community', __name__)


@member_community_bp.route('/foros')
@login_required
def foros():
    """Módulo de Foros para miembros"""
    active_membership = current_user.get_active_membership()
    if not active_membership:
        flash('Necesitas una membresía activa para acceder a los Foros.', 'warning')
        return redirect(url_for('membership'))
    return render_template('foros.html', membership=active_membership)


@member_community_bp.route('/grupos')
@login_required
def grupos():
    """Módulo de Grupos para miembros"""
    active_membership = current_user.get_active_membership()
    if not active_membership:
        flash('Necesitas una membresía activa para acceder a los Grupos.', 'warning')
        return redirect(url_for('membership'))
    return render_template('grupos.html', membership=active_membership)
