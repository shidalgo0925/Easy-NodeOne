"""Invitaciones a organización: API admin + aceptación pública."""
from datetime import datetime


def register_org_invite_routes(app):
    from flask import current_app, flash, jsonify, redirect, request, session, url_for
    from flask_login import current_user, login_required

    from nodeone.services.organization_invites import (
        accept_invite_for_user,
        create_invite_record,
        get_valid_invite_by_token,
        normalize_invite_email,
        send_invite_email,
    )
    from nodeone.services.user_organization import user_has_active_membership

    from app import admin_data_scope_organization_id, db, require_permission

    from models.organization_invite import OrganizationInvite

    @app.route('/api/admin/organization-invites', methods=['GET', 'POST'])
    @login_required
    @require_permission('users.update')
    def api_admin_organization_invites():
        scope_oid = int(admin_data_scope_organization_id())

        if request.method == 'GET':
            status_filter = (request.args.get('status') or 'pending').strip().lower()
            try:
                limit = int(request.args.get('limit', 100))
            except (TypeError, ValueError):
                limit = 100
            limit = max(1, min(limit, 200))

            q = OrganizationInvite.query.filter_by(organization_id=scope_oid)
            if status_filter in ('pending', 'accepted', 'revoked'):
                q = q.filter_by(status=status_filter)
            elif status_filter == 'all':
                pass
            else:
                q = q.filter_by(status='pending')
                status_filter = 'pending'

            rows = q.order_by(OrganizationInvite.created_at.desc()).limit(limit).all()
            invites = []
            for r in rows:
                invites.append(
                    {
                        'id': r.id,
                        'email': r.email,
                        'role': r.role,
                        'status': r.status,
                        'created_at': r.created_at.isoformat() + 'Z' if r.created_at else None,
                        'expires_at': r.expires_at.isoformat() + 'Z' if r.expires_at else None,
                        'accepted_at': r.accepted_at.isoformat() + 'Z' if r.accepted_at else None,
                    }
                )
            return jsonify({'success': True, 'invites': invites, 'filter': status_filter})

        data = request.get_json(silent=True) or {}
        email = (data.get('email') or '').strip()
        role = (data.get('role') or 'user').strip() or 'user'
        if not email:
            return jsonify({'success': False, 'error': 'Falta email'}), 400
        try:
            inv = create_invite_record(
                scope_oid,
                email,
                int(getattr(current_user, 'id', 0) or 0) or None,
                role=role,
            )
            db.session.commit()
        except ValueError as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': str(e)}), 400
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': str(e)}), 500
        ok_mail, err_mail = send_invite_email(inv)
        payload = {
            'success': True,
            'invite_id': inv.id,
            'email_sent': ok_mail,
            'email_error': err_mail,
        }
        if current_app.debug or current_app.config.get('ORG_INVITE_API_INCLUDE_TOKEN'):
            payload['token'] = inv.token
        return jsonify(payload)

    @app.route('/api/admin/organization-invites/<int:invite_id>', methods=['DELETE'])
    @login_required
    @require_permission('users.update')
    def api_admin_revoke_organization_invite(invite_id):
        scope_oid = int(admin_data_scope_organization_id())
        inv = OrganizationInvite.query.filter_by(id=invite_id, organization_id=scope_oid).first()
        if inv is None:
            return jsonify({'success': False, 'error': 'Invitación no encontrada'}), 404
        if inv.status != 'pending':
            return jsonify({'success': False, 'error': 'Solo se pueden anular invitaciones pendientes'}), 400
        inv.status = 'revoked'
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': str(e)}), 500
        return jsonify({'success': True})

    @app.route('/accept-invite/<token>')
    def accept_invite(token):
        inv = get_valid_invite_by_token(token)
        if inv is None:
            flash('La invitación no es válida o ha caducado.', 'error')
            return redirect(url_for('index'))
        if getattr(current_user, 'is_authenticated', False):
            if normalize_invite_email(current_user.email) != inv.email:
                flash('Inicia sesión con el correo al que se envió la invitación.', 'error')
                return redirect(url_for('auth.login', next=request.path))
            if user_has_active_membership(current_user, int(inv.organization_id)):
                inv.status = 'accepted'
                inv.accepted_at = datetime.utcnow()
                inv.accepted_user_id = int(current_user.id)
                try:
                    db.session.commit()
                except Exception:
                    db.session.rollback()
                flash('Ya formas parte de esta organización.', 'info')
                return redirect(url_for('dashboard'))
            try:
                accept_invite_for_user(inv, current_user)
                db.session.commit()
            except Exception:
                db.session.rollback()
                flash('No se pudo aceptar la invitación.', 'error')
                return redirect(url_for('dashboard'))
            flash('Invitación aceptada.', 'success')
            return redirect(url_for('dashboard'))
        session['pending_invite_token'] = token
        return redirect(url_for('register', invite=token))
