"""Miembro: preferencias y ayuda."""

from flask import Blueprint, render_template
from flask_login import login_required

member_pages_bp = Blueprint('member_pages', __name__)


@member_pages_bp.route('/settings')
@login_required
def settings():
    """Módulo de Configuración"""
    return render_template('settings.html')


@member_pages_bp.route('/settings/communications')
@login_required
def settings_communications():
    """Preferencias del motor unificado (evento × canal)."""
    return render_template('settings_communications.html')


@member_pages_bp.route('/help')
@login_required
def help_page():
    """Módulo de Ayuda"""
    return render_template('help.html')
