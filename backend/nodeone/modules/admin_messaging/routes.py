"""Registro de rutas admin messaging en app (endpoints legacy)."""

import app as ap


def register_admin_messaging_routes(app):
    from datetime import datetime, timedelta

    from flask import flash, jsonify, redirect, render_template, request, url_for
    from sqlalchemy import func

    from app import db, EmailLog, Notification, require_permission

    @app.route('/admin/messaging')
    @require_permission('reports.view')
    def admin_messaging():
        """Lista de todos los emails enviados"""
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 10, type=int), 100)
        email_type = request.args.get('type', 'all')
        status = request.args.get('status', 'all')
        search = request.args.get('search', '')

        query = EmailLog.query
        if email_type != 'all':
            query = query.filter_by(email_type=email_type)
        if status != 'all':
            query = query.filter_by(status=status)
        if search:
            query = query.filter(
                db.or_(
                    EmailLog.recipient_email.ilike(f'%{search}%'),
                    EmailLog.subject.ilike(f'%{search}%'),
                    EmailLog.recipient_name.ilike(f'%{search}%'),
                )
            )
        query = query.order_by(EmailLog.created_at.desc())

        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        emails = pagination.items

        total_emails = EmailLog.query.count()
        sent_emails = EmailLog.query.filter_by(status='sent').count()
        failed_emails = EmailLog.query.filter_by(status='failed').count()
        email_types = db.session.query(EmailLog.email_type).distinct().all()
        email_types = [t[0] for t in email_types if t[0]]
        notifications_without_email = Notification.query.filter_by(email_sent=False).order_by(Notification.created_at.desc()).limit(10).all()

        return render_template(
            'admin/messaging.html',
            emails=emails,
            pagination=pagination,
            total_emails=total_emails,
            sent_emails=sent_emails,
            failed_emails=failed_emails,
            email_types=email_types,
            current_type=email_type,
            current_status=status,
            search=search,
            notifications_without_email=notifications_without_email,
        )

    @app.route('/admin/messaging/<int:email_id>')
    @require_permission('reports.view')
    def admin_messaging_detail(email_id):
        """Detalle de un email específico"""
        email_log = EmailLog.query.get_or_404(email_id)
        return render_template('admin/messaging_detail.html', email_log=email_log)

    @app.route('/admin/messaging/<int:email_id>/resend', methods=['POST'])
    @require_permission('reports.view')
    def admin_messaging_resend(email_id):
        """Reenviar un email que falló"""
        email_log = EmailLog.query.get_or_404(email_id)

        if email_log.status == 'sent':
            flash('Este email ya fue enviado exitosamente.', 'info')
            return redirect(url_for('admin_messaging_detail', email_id=email_id))

        try:
            if ap.email_service:
                success = ap.email_service.send_email(
                    subject=email_log.subject,
                    recipients=[email_log.recipient_email],
                    html_content=email_log.html_content or '',
                    text_content=email_log.text_content,
                    email_type=email_log.email_type,
                    related_entity_type=email_log.related_entity_type,
                    related_entity_id=email_log.related_entity_id,
                    recipient_id=email_log.recipient_id,
                    recipient_name=email_log.recipient_name,
                )

                if success:
                    email_log.status = 'sent'
                    email_log.sent_at = datetime.utcnow()
                    email_log.error_message = None
                    db.session.commit()
                    flash('Email reenviado exitosamente.', 'success')
                else:
                    email_log.status = 'failed'
                    email_log.retry_count += 1
                    db.session.commit()
                    flash('Error al reenviar el email. Verifica la configuración del servidor de correo.', 'error')
            else:
                flash('Servicio de email no disponible.', 'error')
        except Exception as e:
            db.session.rollback()
            flash(f'Error al reenviar: {str(e)}', 'error')

        return redirect(url_for('admin_messaging_detail', email_id=email_id))

    @app.route('/admin/messaging/<int:email_id>/delete', methods=['POST'])
    @require_permission('reports.view')
    def admin_messaging_delete(email_id):
        """Eliminar un registro de email"""
        email_log = EmailLog.query.get_or_404(email_id)
        try:
            db.session.delete(email_log)
            db.session.commit()
            flash('Registro de email eliminado.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error al eliminar: {str(e)}', 'error')
        return redirect(url_for('admin_messaging'))

    @app.route('/api/admin/messaging/stats')
    @require_permission('reports.view')
    def api_messaging_stats():
        """API para obtener estadísticas de mensajería"""
        total = EmailLog.query.count()
        sent = EmailLog.query.filter_by(status='sent').count()
        failed = EmailLog.query.filter_by(status='failed').count()

        stats_by_type = db.session.query(EmailLog.email_type, func.count(EmailLog.id).label('count')).group_by(EmailLog.email_type).all()
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        stats_by_day = db.session.query(func.date(EmailLog.created_at).label('date'), func.count(EmailLog.id).label('count')).filter(EmailLog.created_at >= thirty_days_ago).group_by(func.date(EmailLog.created_at)).all()

        return jsonify(
            {
                'total': total,
                'sent': sent,
                'failed': failed,
                'by_type': {t[0]: t[1] for t in stats_by_type},
                'by_day': [{'date': str(d[0]), 'count': d[1]} for d in stats_by_day],
            }
        )
