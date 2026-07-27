"""Rutas HTML de EPayroll (app nativa — scaffold)."""

from __future__ import annotations

from flask import Blueprint, redirect, render_template, url_for
from flask_login import current_user, login_required

from nodeone.core.template_context_gates import user_can_see_tenant_admin_menu

epayroll_bp = Blueprint('epayroll', __name__, url_prefix='/admin/epayroll')


@epayroll_bp.route('/')
@login_required
def epayroll_home():
    if not user_can_see_tenant_admin_menu(current_user):
        return redirect(url_for('dashboard'))
    return render_template('epayroll/home.html')
