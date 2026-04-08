# Rutas de auth: solo delegación a service y respuesta (redirect/render).
from flask import Blueprint, request, redirect, url_for, flash, render_template, session
from flask_login import login_user, login_required, current_user

from . import service

auth_bp = Blueprint('auth', __name__, url_prefix='')


def _organizations_for_login_form(user=None):
    """
    Compat: lista para plantilla login (ya no se usa selector en login).
    """
    from nodeone.services.post_login_organization import organizations_for_session_after_login

    if user is None:
        return []
    return organizations_for_session_after_login(user)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '')
        password = request.form.get('password', '')
        success, user, error = service.login(email, password)
        if success:
            from app import apply_session_organization_after_login

            login_user(user)
            code, org_err = apply_session_organization_after_login(user, request)
            if code == 'error':
                from flask_login import logout_user as _luo

                _luo()
                flash(org_err or 'No se pudo validar la organización.', 'error')
                return render_template('login.html', saas_organizations=[], login_email=email)
            if code == 'pick':
                next_page = service.safe_next_path(
                    request.form.get('next') or request.args.get('next')
                )
                if next_page:
                    return redirect(url_for('auth.select_organization', next=next_page))
                return redirect(url_for('auth.select_organization'))
            if bool(getattr(user, 'must_change_password', False)):
                flash('Debes cambiar tu contraseña antes de continuar.', 'warning')
                return redirect(url_for('auth.change_password'))
            try:
                from history_module import HistoryLogger

                HistoryLogger.log_user_action(
                    user_id=user.id,
                    action='Login exitoso',
                    status='success',
                    context={'app': 'web', 'screen': 'login', 'module': 'auth'},
                    request=request,
                )
            except Exception:
                pass
            try:
                from user_status_checker import UserStatusChecker
                from app import db

                user_status = UserStatusChecker.check_user_status(user.id, db.session)
                if user_status.get('summary', {}).get('total_pending_actions', 0) > 0:
                    urgent_count = user_status['summary'].get('urgent_actions', 0)
                    if urgent_count > 0:
                        flash(f'Tienes {urgent_count} acción(es) urgente(s) pendiente(s). Revisa tu panel.', 'warning')
                    else:
                        flash(f'Tienes {user_status["summary"]["total_pending_actions"]} acción(es) pendiente(s).', 'info')
                session['user_status_checked'] = True
            except Exception as e:
                print(f'⚠️ Error verificando estado del usuario al iniciar sesión: {e}')
            next_page = service.safe_next_path(request.form.get('next') or request.args.get('next'))
            return redirect(next_page) if next_page else redirect(url_for('dashboard'))
        flash(error or 'Credenciales inválidas.', 'error')
    return render_template('login.html', saas_organizations=[], login_email=None)


@auth_bp.route('/select-organization', methods=['GET'])
@login_required
def select_organization():
    from nodeone.services.post_login_organization import (
        organizations_for_session_after_login,
        resolved_logo_url_for_org_card,
    )

    orgs = organizations_for_session_after_login(current_user)
    if len(orgs) <= 1:
        session.pop('require_org_selection', None)
        return redirect(url_for('dashboard'))
    cards = [{'id': int(o.id), 'name': (o.name or '').strip() or 'Empresa', 'logo': resolved_logo_url_for_org_card(int(o.id))} for o in orgs]
    next_page = service.safe_next_path(request.args.get('next'))
    return render_template(
        'select_organization.html',
        picker_organizations=cards,
        next_url=next_page,
    )


@auth_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    must_change = bool(getattr(current_user, 'must_change_password', False))
    if request.method == 'POST':
        new_password = request.form.get('new_password', '')
        confirm = request.form.get('confirm_password', '')
        success, error = service.change_password(current_user, new_password, confirm)
        if success:
            flash('Contraseña actualizada. Ya puedes usar el sistema.', 'success')
            return redirect(url_for('dashboard'))
        flash(error, 'error')
        return render_template('change_password.html', must_change=must_change)
    return render_template('change_password.html', must_change=must_change)
