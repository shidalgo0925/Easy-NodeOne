"""Listado y actualización de solicitudes Office 365 (admin)."""

from datetime import datetime

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

office365_admin_bp = Blueprint('office365_admin', __name__)


@office365_admin_bp.route('/admin/office365/requests')
@login_required
def admin_office365_requests():
    """Listado de solicitudes Office 365 (solo admin)."""
    import app as M

    if not getattr(current_user, 'is_admin', False) and not (
        hasattr(current_user, 'has_permission') and current_user.has_permission('users.view')
    ):
        flash('No tienes permiso para ver esta sección.', 'error')
        return redirect(url_for('dashboard'))
    status_filter = request.args.get('status', 'all')
    scope_oid = M.admin_data_scope_organization_id()
    from nodeone.services.user_organization import user_in_org_clause

    query = (
        M.Office365Request.query
        .join(M.User, M.Office365Request.user_id == M.User.id)
        .filter(user_in_org_clause(M.User, scope_oid))
        .order_by(M.Office365Request.created_at.desc())
    )
    if status_filter and status_filter != 'all':
        query = query.filter_by(status=status_filter)
    requests_list = query.limit(200).all()
    pending_count = (
        M.Office365Request.query
        .join(M.User, M.Office365Request.user_id == M.User.id)
        .filter(user_in_org_clause(M.User, scope_oid), M.Office365Request.status == 'pending')
        .count()
    )
    return render_template(
        'admin/office365_requests.html',
        requests=requests_list,
        status_filter=status_filter,
        pending_count=pending_count,
    )


@office365_admin_bp.route('/admin/office365/requests/<int:request_id>/update', methods=['POST'])
@login_required
def admin_update_office365_request(request_id):
    """Aprobar o rechazar solicitud Office 365 y notificar al usuario por correo. Al aprobar, consume código si aplica."""
    import app as M

    if not getattr(current_user, 'is_admin', False) and not (
        hasattr(current_user, 'has_permission') and current_user.has_permission('users.view')
    ):
        return jsonify({'error': 'No autorizado'}), 403
    data = request.get_json(silent=True) or request.form
    new_status = (data.get('status') or '').strip().lower()
    admin_notes = (data.get('admin_notes') or '').strip()
    if new_status not in ('approved', 'rejected'):
        return jsonify({'error': 'Estado inválido. Use approved o rejected.'}), 400
    scope_oid = M.admin_data_scope_organization_id()
    from nodeone.services.user_organization import user_in_org_clause

    req = (
        M.Office365Request.query
        .join(M.User, M.Office365Request.user_id == M.User.id)
        .filter(M.Office365Request.id == request_id, user_in_org_clause(M.User, scope_oid))
        .first()
    )
    if not req:
        return jsonify({'error': 'No autorizado'}), 403
    try:
        if new_status == 'approved' and req.discount_code_id:
            dc = M.DiscountCode.query.get(req.discount_code_id)
            if dc:
                dc.current_uses = (dc.current_uses or 0) + 1
                app_use = M.DiscountApplication(
                    discount_code_id=dc.id,
                    user_id=req.user_id,
                    payment_id=None,
                    cart_id=None,
                    original_amount=0.0,
                    discount_amount=0.0,
                    final_amount=0.0,
                )
                M.db.session.add(app_use)
        req.status = new_status
        req.admin_notes = admin_notes or None
        req.updated_at = datetime.utcnow()
        M.db.session.commit()
    except Exception as e:
        M.db.session.rollback()
        M.app.logger.exception('Office365 request update failed: %s', e)
        return jsonify({'error': 'Error al actualizar la solicitud.'}), 500
    user_email = req.user.email if req.user else req.email
    if user_email and M.Mail and M.Message:
        subject = f'Solicitud Office 365 – {new_status.upper()}'
        body_text = f"""Tu solicitud de acceso Office 365 (ID {req.id}) ha sido {new_status}.\n\nNotas del administrador:\n{admin_notes or 'Sin observaciones.'}\n\n— RelaticPanama"""
        try:
            ok_smtp, _ = M.apply_transactional_smtp_for_organization(int(scope_oid))
            if ok_smtp and M.mail:
                msg = M.Message(subject=subject, recipients=[user_email], body=body_text)
                M.mail.send(msg)
        except Exception as e:
            M.app.logger.exception('Office365 notification mail failed for request %s: %s', req.id, e)
        finally:
            M.apply_email_config_from_db()
    return jsonify({'success': True})
