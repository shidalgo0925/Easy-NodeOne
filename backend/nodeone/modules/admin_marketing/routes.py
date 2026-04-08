"""Registro de rutas admin marketing masivas (HTML + API email-config)."""

import json

import app as ap


def register_admin_marketing_routes(app):
    """Mismos endpoints que el monolito (url_for compatible)."""
    from flask import flash, jsonify, redirect, render_template, request, url_for

    from app import (
        admin_data_scope_organization_id,
        admin_required,
        CampaignRecipient,
        db,
        EmailConfig,
        EmailQueueItem,
        MarketingCampaign,
        MarketingSegment,
        MarketingTemplate,
        User,
    )

    def _scope_query_by_org(query, model, scope_oid):
        if hasattr(model, 'organization_id'):
            return query.filter(model.organization_id == scope_oid)
        return query

    @app.route('/admin/marketing/email-settings')
    @admin_required
    def admin_marketing_email_settings():
        """Configuración de correo para envíos masivos: listar cuentas y designar cuál usar en campañas."""
        scope_oid = admin_data_scope_organization_id()
        q = _scope_query_by_org(EmailConfig.query, EmailConfig, scope_oid)
        configs = [c.to_dict() for c in q.order_by(EmailConfig.id).all()]
        return render_template('admin/marketing_email_settings.html', configs=configs)


    @app.route('/api/admin/marketing/email-config/set-marketing', methods=['POST'])
    @admin_required
    def api_marketing_email_config_set_marketing():
        """Designar una configuración como la que se usa para envíos masivos (campañas)."""
        data = request.get_json() or {}
        config_id = data.get('config_id')
        if config_id is None:
            return jsonify({'success': False, 'error': 'Falta config_id'}), 400
        scope_oid = admin_data_scope_organization_id()
        cfg = EmailConfig.query.get(config_id)
        if not cfg:
            return jsonify({'success': False, 'error': 'Configuración no encontrada'}), 404
        if hasattr(EmailConfig, 'organization_id') and int(getattr(cfg, 'organization_id', 0) or 0) != int(scope_oid):
            return jsonify({'success': False, 'error': 'No autorizado'}), 403
        try:
            cfg_query = _scope_query_by_org(EmailConfig.query, EmailConfig, scope_oid)
            for c in cfg_query.all():
                c.use_for_marketing = (c.id == cfg.id)
            db.session.commit()
            return jsonify({'success': True, 'message': 'Configuración designada para correos masivos.', 'config': cfg.to_dict()})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': str(e)}), 500


    @app.route('/api/admin/marketing/email-config/create', methods=['POST'])
    @admin_required
    def api_marketing_email_config_create():
        """Crear una nueva configuración SMTP (para poder usarla en marketing sin tocar la institucional)."""
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No se recibieron datos JSON'}), 400
        try:
            config = EmailConfig(
                mail_server=(data.get('mail_server') or 'smtp.gmail.com').strip(),
                mail_port=int(data.get('mail_port', 587)),
                mail_use_tls=bool(data.get('mail_use_tls', True)),
                mail_use_ssl=bool(data.get('mail_use_ssl', False)),
                mail_username=(data.get('mail_username') or '').strip(),
                mail_password=(data.get('mail_password') or '').strip() or None,
                mail_default_sender=(data.get('mail_default_sender') or 'noreply@relaticpanama.org').strip(),
                use_environment_variables=bool(data.get('use_environment_variables', False)),
                is_active=False,
                use_for_marketing=False,
            )
            db.session.add(config)
            db.session.commit()
            return jsonify({'success': True, 'message': 'Configuración creada. Puedes designarla para marketing.', 'config': config.to_dict()})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': str(e)}), 500


    @app.route('/admin/marketing')
    @admin_required
    def admin_marketing():
        """Panel de Email Marketing: campañas, segmentos, plantillas y estadísticas."""
        from sqlalchemy import func
        scope_oid = admin_data_scope_organization_id()
        campaigns = _scope_query_by_org(MarketingCampaign.query, MarketingCampaign, scope_oid).order_by(MarketingCampaign.created_at.desc()).limit(100).all()
        campaign_list = []
        for c in campaigns:
            recs = CampaignRecipient.query.filter_by(campaign_id=c.id).all()
            sent = sum(1 for r in recs if r.sent_at)
            opened = sum(1 for r in recs if r.opened_at)
            clicked = sum(1 for r in recs if r.clicked_at)
            item = {
                'id': c.id, 'name': c.name, 'subject': c.subject, 'status': c.status,
                'created_at': c.created_at,
                'total': len(recs), 'sent': sent,
                'open_rate': (opened / sent * 100) if sent else 0,
                'click_rate': (clicked / sent * 100) if sent else 0,
                'subject_b': getattr(c, 'subject_b', None) or None
            }
            if item['subject_b']:
                recs_a = [r for r in recs if r.variant == 'A']
                recs_b = [r for r in recs if r.variant == 'B']
                sent_a = sum(1 for r in recs_a if r.sent_at)
                sent_b = sum(1 for r in recs_b if r.sent_at)
                opened_a = sum(1 for r in recs_a if r.opened_at)
                opened_b = sum(1 for r in recs_b if r.opened_at)
                clicked_a = sum(1 for r in recs_a if r.clicked_at)
                clicked_b = sum(1 for r in recs_b if r.clicked_at)
                item['open_rate_a'] = (opened_a / sent_a * 100) if sent_a else 0
                item['click_rate_a'] = (clicked_a / sent_a * 100) if sent_a else 0
                item['open_rate_b'] = (opened_b / sent_b * 100) if sent_b else 0
                item['click_rate_b'] = (clicked_b / sent_b * 100) if sent_b else 0
                item['sent_a'] = sent_a
                item['sent_b'] = sent_b
            campaign_list.append(item)
        segments = _scope_query_by_org(MarketingSegment.query, MarketingSegment, scope_oid).order_by(MarketingSegment.id).all()
        templates = _scope_query_by_org(MarketingTemplate.query, MarketingTemplate, scope_oid).order_by(MarketingTemplate.id).all()
        total_sent = db.session.query(func.count(CampaignRecipient.id)).join(User, CampaignRecipient.user_id == User.id).filter(User.organization_id == scope_oid, CampaignRecipient.sent_at.isnot(None)).scalar() or 0
        total_opened = db.session.query(func.count(CampaignRecipient.id)).join(User, CampaignRecipient.user_id == User.id).filter(User.organization_id == scope_oid, CampaignRecipient.opened_at.isnot(None)).scalar() or 0
        total_clicked = db.session.query(func.count(CampaignRecipient.id)).join(User, CampaignRecipient.user_id == User.id).filter(User.organization_id == scope_oid, CampaignRecipient.clicked_at.isnot(None)).scalar() or 0
        unsub_count = db.session.query(func.count(User.id)).filter(User.organization_id == scope_oid, User.email_marketing_status == 'unsubscribed').scalar() or 0
        sub_count = db.session.query(func.count(User.id)).filter(User.organization_id == scope_oid, User.email_marketing_status == 'subscribed').scalar() or 0
        stats = {
            'emails_sent': total_sent,
            'open_rate': (total_opened / total_sent * 100) if total_sent else 0,
            'click_rate': (total_clicked / total_sent * 100) if total_sent else 0,
            'unsubscribe_count': unsub_count,
            'subscribed_count': sub_count,
            'segments_count': len(segments)
        }
        from _app.modules.marketing.service import SEGMENT_FIELDS, SEGMENT_OPERATORS
        return render_template('admin/marketing.html',
                             campaigns=campaign_list,
                             segments=segments,
                             templates=templates,
                             stats=stats,
                             segment_fields=SEGMENT_FIELDS,
                             segment_operators=SEGMENT_OPERATORS)


    @app.route('/admin/marketing/campaign/new')
    @admin_required
    def admin_marketing_campaign_new():
        """Editor de campaña: galería de plantillas + bloques."""
        scope_oid = admin_data_scope_organization_id()
        segments = _scope_query_by_org(MarketingSegment.query, MarketingSegment, scope_oid).order_by(MarketingSegment.id).all()
        templates = _scope_query_by_org(MarketingTemplate.query, MarketingTemplate, scope_oid).order_by(MarketingTemplate.id).all()
        if not templates:
            flash('Crea al menos una plantilla (abajo) antes de usar el editor.', 'warning')
            return redirect(url_for('admin_marketing'))
        if not segments:
            flash('Crea al menos un segmento (abajo) antes de crear una campaña.', 'warning')
            return redirect(url_for('admin_marketing'))
        default_template = templates[0]
        return render_template('admin/marketing_editor.html',
                             campaign=None,
                             segments=segments,
                             templates=templates,
                             default_template=default_template)


    @app.route('/admin/marketing/campaign/<int:campaign_id>/edit')
    @admin_required
    def admin_marketing_campaign_edit(campaign_id):
        """Editar campaña en borrador."""
        scope_oid = admin_data_scope_organization_id()
        c = MarketingCampaign.query.get_or_404(campaign_id)
        if hasattr(MarketingCampaign, 'organization_id') and int(getattr(c, 'organization_id', 0) or 0) != int(scope_oid):
            flash('No autorizado.', 'danger')
            return redirect(url_for('admin_marketing'))
        if c.status not in ('draft', 'scheduled'):
            flash('Solo se pueden editar campañas en borrador o programadas.', 'warning')
            return redirect(url_for('admin_marketing'))
        segments = _scope_query_by_org(MarketingSegment.query, MarketingSegment, scope_oid).order_by(MarketingSegment.id).all()
        templates = _scope_query_by_org(MarketingTemplate.query, MarketingTemplate, scope_oid).order_by(MarketingTemplate.id).all()
        return render_template('admin/marketing_editor.html',
                             campaign=c,
                             segments=segments,
                             templates=templates,
                             default_template=c.template)


    @app.route('/admin/marketing/campaign/save', methods=['POST'])
    @admin_required
    def admin_marketing_campaign_save():
        """Guardar borrador (crear o actualizar). Acepta action=schedule y scheduled_at para programar."""
        from _app.modules.marketing.service import create_campaign
        from datetime import datetime as dt
        campaign_id = request.form.get('campaign_id', type=int)
        name = (request.form.get('name') or '').strip()
        subject = (request.form.get('subject') or '').strip()
        segment_id = request.form.get('segment_id', type=int)
        template_id = request.form.get('template_id', type=int)
        body_html = request.form.get('body_html') or ''
        exclusion_emails = (request.form.get('exclusion_emails') or '').strip() or None
        from_name = (request.form.get('from_name') or '').strip() or None
        reply_to = (request.form.get('reply_to') or '').strip() or None
        subject_b = (request.form.get('subject_b') or '').strip() or None
        meeting_url = (request.form.get('meeting_url') or '').strip() or None
        action = request.form.get('action', 'save')
        scheduled_at_raw = (request.form.get('scheduled_at') or '').strip()
        if not name or not subject or not segment_id or not template_id:
            flash('Faltan nombre, asunto, segmento o plantilla.', 'warning')
            return redirect(url_for('admin_marketing_campaign_new')) if not campaign_id else redirect(url_for('admin_marketing_campaign_edit', campaign_id=campaign_id))
        scheduled_at = None
        if action == 'schedule' and scheduled_at_raw:
            try:
                scheduled_at = dt.fromisoformat(scheduled_at_raw.replace('Z', '+00:00'))
                if scheduled_at.tzinfo:
                    scheduled_at = scheduled_at.replace(tzinfo=None)
            except Exception:
                flash('Fecha/hora de programación no válida.', 'warning')
        if campaign_id:
            c = MarketingCampaign.query.get_or_404(campaign_id)
            if c.status not in ('draft', 'scheduled'):
                flash('Campaña no editable.', 'danger')
                return redirect(url_for('admin_marketing'))
            c.name = name
            c.subject = subject
            c.segment_id = segment_id
            c.template_id = template_id
            c.body_html = body_html.strip() or None
            c.exclusion_emails = exclusion_emails
            c.from_name = from_name
            c.reply_to = reply_to
            c.subject_b = subject_b
            if hasattr(c, 'meeting_url'):
                c.meeting_url = meeting_url
            if action == 'schedule' and scheduled_at:
                c.status = 'scheduled'
                c.scheduled_at = scheduled_at
                flash(f'Campaña programada para {scheduled_at.strftime("%d/%m/%Y %H:%M")}.', 'success')
            else:
                flash('Borrador actualizado.', 'success')
            db.session.commit()
            return redirect(url_for('admin_marketing_campaign_edit', campaign_id=c.id))
        c = create_campaign(name, subject, template_id, segment_id)
        c.body_html = body_html.strip() or None
        c.exclusion_emails = exclusion_emails
        c.from_name = from_name
        c.reply_to = reply_to
        c.subject_b = subject_b
        if hasattr(c, 'meeting_url'):
            c.meeting_url = meeting_url
        if action == 'schedule' and scheduled_at:
            c.status = 'scheduled'
            c.scheduled_at = scheduled_at
            db.session.commit()
            flash(f'Campaña programada para {scheduled_at.strftime("%d/%m/%Y %H:%M")}.', 'success')
        else:
            db.session.commit()
            flash('Campaña creada en borrador.', 'success')
        return redirect(url_for('admin_marketing_campaign_edit', campaign_id=c.id))


    @app.route('/admin/marketing/campaign/<int:campaign_id>/send', methods=['POST'])
    @admin_required
    def admin_marketing_campaign_send(campaign_id):
        """Enviar campaña."""
        from _app.modules.marketing.service import start_campaign
        c, err = start_campaign(campaign_id)
        if err:
            flash(err, 'danger')
        else:
            flash('Campaña enviada.', 'success')
        return redirect(url_for('admin_marketing'))


    @app.route('/admin/marketing/campaign/<int:campaign_id>/save-as-template', methods=['POST'])
    @admin_required
    def admin_marketing_save_as_template(campaign_id):
        """Guarda el cuerpo actual de la campaña como nueva plantilla."""
        c = MarketingCampaign.query.get_or_404(campaign_id)
        name = (request.form.get('template_name') or request.form.get('name') or '').strip()
        if not name:
            flash('Indica el nombre de la plantilla.', 'warning')
            return redirect(url_for('admin_marketing_campaign_edit', campaign_id=c.id))
        body = (getattr(c, 'body_html', None) or '').strip()
        if not body and c.template_id:
            t = MarketingTemplate.query.get(c.template_id)
            body = (t.html or '') if t else ''
        if not body:
            flash('No hay contenido para guardar como plantilla.', 'warning')
            return redirect(url_for('admin_marketing_campaign_edit', campaign_id=c.id))
        t = MarketingTemplate(name=name, html=body, variables='[]')
        db.session.add(t)
        db.session.commit()
        flash(f'Plantilla "{name}" creada. Ya puedes usarla en nuevas campañas.', 'success')
        return redirect(url_for('admin_marketing_campaign_edit', campaign_id=c.id))


    @app.route('/admin/marketing/campaign/<int:campaign_id>/test', methods=['POST'])
    @admin_required
    def admin_marketing_campaign_test(campaign_id):
        """Enviar correo de prueba al email indicado."""
        c = MarketingCampaign.query.get_or_404(campaign_id)
        test_email = (request.form.get('test_email') or request.form.get('email') or '').strip().lower()
        if not test_email or '@' not in test_email:
            flash('Indica un email válido para la prueba.', 'warning')
            return redirect(url_for('admin_marketing_campaign_edit', campaign_id=c.id))
        from _app.modules.marketing.service import render_template_html
        template = MarketingTemplate.query.get(c.template_id)
        body_source = (getattr(c, 'body_html', None) or '').strip() or (template.html if template else '')
        base_url = request.host_url.rstrip('/') if request else ''
        ctx = {'nombre': 'Prueba', 'email': test_email, 'user_id': None}
        html = render_template_html(body_source, getattr(template, 'variables', '[]') if template else '[]', ctx, base_url=base_url)
        oid_c = int(getattr(c, 'organization_id', None) or ap.default_organization_id())
        try:
            ok_smtp, _cfg_id = ap.apply_marketing_smtp_for_organization(oid_c)
            if not ok_smtp:
                flash(
                    'No hay SMTP (marketing o institucional) o Mail/EmailService no disponible para esta organización.',
                    'danger',
                )
            else:
                ok = ap.email_service.send_email(
                    subject=c.subject,
                    recipients=[test_email],
                    html_content=html,
                    email_type='marketing_test',
                    sender=getattr(c, 'from_name', None) or None,
                    reply_to=getattr(c, 'reply_to', None) or None,
                )
                if ok:
                    flash(f'Prueba enviada a {test_email}.', 'success')
                else:
                    flash('El envío falló. Revisa la configuración SMTP del tenant.', 'danger')
        except Exception as e:
            flash(f'Error: {e}', 'danger')
        finally:
            ap.apply_email_config_from_db()
        return redirect(url_for('admin_marketing_campaign_edit', campaign_id=c.id))


    @app.route('/admin/marketing/process-scheduled')
    @admin_required
    def admin_marketing_process_scheduled():
        """Ejecuta el envío de campañas programadas cuya fecha ya pasó. Llamar por cron o manualmente."""
        from datetime import datetime
        from _app.modules.marketing.service import start_campaign
        now = datetime.utcnow()
        pending = MarketingCampaign.query.filter(
            MarketingCampaign.status == 'scheduled',
            MarketingCampaign.scheduled_at.isnot(None),
            MarketingCampaign.scheduled_at <= now
        ).all()
        sent = 0
        for c in pending:
            _, err = start_campaign(c.id)
            if not err:
                sent += 1
        flash(f'Procesadas {len(pending)} campañas programadas; enviadas: {sent}.', 'info')
        return redirect(url_for('admin_marketing'))


    @app.route('/admin/marketing/process-queue', methods=['GET', 'POST'])
    @admin_required
    def admin_marketing_process_queue():
        """Procesa la cola email_queue: hasta 50 pendientes; SMTP por organización de la campaña."""
        from datetime import datetime as dt

        ap.initialize_email_config()
        scope_oid = admin_data_scope_organization_id()
        now = dt.utcnow()
        q = EmailQueueItem.query.filter(
            EmailQueueItem.status == 'pending',
            db.or_(
                EmailQueueItem.send_after.is_(None),
                EmailQueueItem.send_after <= now,
            ),
        )
        if not ap._admin_can_view_all_organizations():
            scope = int(scope_oid)
            q = q.outerjoin(MarketingCampaign, EmailQueueItem.campaign_id == MarketingCampaign.id).filter(
                db.or_(
                    EmailQueueItem.organization_id == scope,
                    MarketingCampaign.organization_id == scope,
                )
            )
        items = q.order_by(EmailQueueItem.id).limit(50).all()

        def _item_org_id(item):
            oi = getattr(item, 'organization_id', None)
            if oi is not None:
                return int(oi)
            if item.campaign_id:
                c = MarketingCampaign.query.get(item.campaign_id)
                if c is not None:
                    return int(c.organization_id or ap.default_organization_id())
            if not ap._admin_can_view_all_organizations():
                return int(scope_oid)
            return int(ap.default_organization_id())

        last_cfg_id = None
        sent, failed = 0, 0
        for item in items:
            item.status = 'processing'
            if getattr(item, 'attempts', None) is not None:
                item.attempts = (item.attempts or 0) + 1
            db.session.commit()
            try:
                oid_send = _item_org_id(item)
                ok_smtp, cfg_id = ap.apply_marketing_smtp_for_organization(
                    oid_send, skip_if_config_id=last_cfg_id
                )
                if ok_smtp:
                    last_cfg_id = cfg_id
                if not ok_smtp:
                    item.status = 'failed'
                    if getattr(item, 'error_message', None) is not None:
                        item.error_message = 'Sin SMTP/marketing para esta organización'
                    db.session.commit()
                    failed += 1
                    continue
                payload = json.loads(item.payload) if item.payload else {}
                subject = payload.get('subject', '')
                html = payload.get('html', '')
                to_email = payload.get('to_email', '')
                if not to_email:
                    item.status = 'failed'
                    if getattr(item, 'error_message', None) is not None:
                        item.error_message = 'to_email vacío'
                    db.session.commit()
                    failed += 1
                    continue
                is_campaign = bool(item.campaign_id)
                ok = ap.email_service.send_email(
                    subject=subject,
                    recipients=[to_email],
                    html_content=html,
                    sender=payload.get('from_name') or None,
                    reply_to=payload.get('reply_to') or None,
                    email_type='marketing_campaign' if is_campaign else 'marketing_automation',
                    related_entity_type='campaign' if is_campaign else 'marketing_automation',
                    related_entity_id=item.campaign_id,
                )
                if ok:
                    item.status = 'sent'
                    if item.recipient_id:
                        rec = CampaignRecipient.query.get(item.recipient_id)
                        if rec:
                            rec.sent_at = now
                            rec.status = 'sent'
                    sent += 1
                else:
                    item.status = 'failed'
                    if getattr(item, 'error_message', None) is not None:
                        item.error_message = 'send_email devolvió False'
                    failed += 1
                db.session.commit()
            except Exception as e:
                item.status = 'failed'
                if getattr(item, 'error_message', None) is not None:
                    item.error_message = str(e)[:500]
                db.session.rollback()
                db.session.commit()
                failed += 1
        ap.apply_email_config_from_db()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 'application/json' in (request.headers.get('Accept') or ''):
            return jsonify({'success': True, 'processed': len(items), 'sent': sent, 'failed': failed})
        flash(f'Cola: {len(items)} procesados ({sent} enviados, {failed} fallos).', 'info')
        return redirect(url_for('admin_marketing'))


    @app.route('/admin/marketing/queue')
    @admin_required
    def admin_marketing_queue():
        """Lista cola de envío (pendientes y recientes)."""
        pending = EmailQueueItem.query.filter_by(status='pending').order_by(EmailQueueItem.id.desc()).limit(200).all()
        recent = EmailQueueItem.query.filter(EmailQueueItem.status.in_(['sent', 'failed'])).order_by(EmailQueueItem.id.desc()).limit(100).all()
        return render_template('admin/marketing_queue.html', pending=pending, recent=recent)


    @app.route('/admin/marketing/send', methods=['POST'])
    @admin_required
    def admin_marketing_send():
        """Crea una campaña y la envía (form POST desde el panel)."""
        from _app.modules.marketing.service import create_campaign, start_campaign
        name = (request.form.get('name') or '').strip()
        subject = (request.form.get('subject') or '').strip()
        template_id = request.form.get('template_id', type=int)
        segment_id = request.form.get('segment_id', type=int)
        meeting_url = (request.form.get('meeting_url') or '').strip() or None
        if not name or not subject or not template_id or not segment_id:
            flash('Faltan nombre, asunto, plantilla o segmento.', 'warning')
            return redirect(url_for('admin_marketing'))
        try:
            c = create_campaign(name, subject, template_id, segment_id)
            if hasattr(c, 'meeting_url') and meeting_url:
                c.meeting_url = meeting_url
                db.session.commit()
            _, err = start_campaign(c.id)
            if err:
                flash(f'Campaña creada pero error al enviar: {err}', 'warning')
            else:
                flash('Campaña creada y envío iniciado.', 'success')
        except Exception as e:
            flash(f'Error: {e}', 'danger')
        return redirect(url_for('admin_marketing'))


    @app.route('/admin/marketing/segments/preview', methods=['POST'])
    @admin_required
    def admin_marketing_segments_preview():
        """Vista previa: cuenta miembros que cumplen los filtros. Body: {"filters": {"conditions": [...]}}."""
        from _app.modules.marketing.service import _get_members_with_domain
        data = request.get_json() or {}
        filters = data.get('filters') or data.get('rules') or {}
        if not isinstance(filters, dict):
            filters = {}
        conditions = filters.get('conditions') or []
        if not isinstance(conditions, list):
            conditions = []
        logic = (filters.get('logic') or 'and').strip().lower()
        if logic not in ('and', 'or'):
            logic = 'and'
        rules = {'logic': logic, 'conditions': conditions}
        users = _get_members_with_domain(rules, subscribed_only=False) or []
        return jsonify({'success': True, 'total_members': len(users)})


    @app.route('/admin/marketing/segments/create', methods=['GET', 'POST'])
    @admin_required
    def admin_marketing_segments_create():
        """Crear segmento: definir filtros → previsualizar cantidad → Guardar segmento (no se guardan miembros)."""
        from _app.modules.marketing.service import SEGMENT_FIELDS, SEGMENT_OPERATORS, _get_members_with_domain
        if request.method == 'POST':
            name = (request.form.get('name') or '').strip()
            if not name:
                flash('Escribe el nombre del segmento.', 'warning')
                return redirect(url_for('admin_marketing_segments_create'))
            query_rules_raw = (request.form.get('query_rules') or '').strip()
            query_rules = '{}'
            if query_rules_raw:
                try:
                    data = json.loads(query_rules_raw)
                    if isinstance(data, dict) and data.get('conditions') is not None:
                        query_rules = json.dumps(data)
                except Exception:
                    pass
            description = (request.form.get('description') or '').strip() or None
            try:
                s = MarketingSegment(name=name, description=description, query_rules=query_rules, is_dynamic=True)
                db.session.add(s)
                db.session.commit()
                flash(f'Segmento "{name}" creado. Los destinatarios se calculan al enviar la campaña.', 'success')
                return redirect(url_for('admin_marketing'))
            except Exception as e:
                flash(f'Error al crear segmento: {e}', 'danger')
                return redirect(url_for('admin_marketing_segments_create'))
        rules = {'logic': 'and', 'conditions': []}
        count = 0
        if request.args.get('preview'):
            try:
                qr = request.args.get('query_rules', '{}')
                r = json.loads(qr) if isinstance(qr, str) else qr
                if isinstance(r, dict) and r.get('conditions'):
                    users = _get_members_with_domain(r, subscribed_only=False) or []
                    count = len(users)
            except Exception:
                pass
        return render_template('admin/marketing_segment_create.html',
                             segment_fields=SEGMENT_FIELDS,
                             segment_operators=SEGMENT_OPERATORS,
                             rules=rules,
                             recipient_count=count)


    @app.route('/admin/marketing/segment', methods=['POST'])
    @admin_required
    def admin_marketing_create_segment():
        """Crear segmento desde el panel (form POST). Acepta query_rules JSON para filtros."""
        name = (request.form.get('name') or '').strip()
        if not name:
            flash('Escribe el nombre del segmento.', 'warning')
            return redirect(url_for('admin_marketing'))
        query_rules_raw = (request.form.get('query_rules') or '').strip()
        query_rules = '{}'
        if query_rules_raw:
            try:
                data = json.loads(query_rules_raw)
                if isinstance(data, dict) and data.get('conditions'):
                    query_rules = json.dumps(data)
            except Exception:
                pass
        try:
            s = MarketingSegment(name=name, query_rules=query_rules, is_dynamic=True)
            db.session.add(s)
            db.session.commit()
            flash(f'Segmento "{name}" creado.', 'success')
        except Exception as e:
            flash(f'Error al crear segmento: {e}', 'danger')
        return redirect(url_for('admin_marketing'))


    @app.route('/admin/marketing/segment/<int:segment_id>/edit', methods=['GET', 'POST'])
    @admin_required
    def admin_marketing_segment_edit(segment_id):
        """Editar segmento: nombre y filtros (constructor de dominios)."""
        from _app.modules.marketing.service import SEGMENT_FIELDS, SEGMENT_OPERATORS, get_recipient_count, get_members_from_segment_simple
        s = MarketingSegment.query.get_or_404(segment_id)
        if request.method == 'POST':
            name = (request.form.get('name') or '').strip()
            if not name:
                flash('El nombre es obligatorio.', 'warning')
                return redirect(url_for('admin_marketing_segment_edit', segment_id=s.id))
            query_rules_raw = (request.form.get('query_rules') or '').strip()
            query_rules = '{}'
            if query_rules_raw:
                try:
                    data = json.loads(query_rules_raw)
                    if isinstance(data, dict) and data.get('conditions') is not None:
                        query_rules = json.dumps(data)
                except Exception:
                    pass
            preview_ids_raw = (request.form.get('preview_member_ids') or '').strip()
            include_ids = request.form.getlist('include_user_ids')
            try:
                preview_ids = set(int(x) for x in preview_ids_raw.split(',') if str(x).strip().isdigit())
                include_set = set(int(x) for x in include_ids if str(x).strip().isdigit())
                exclusion_user_ids = json.dumps(list(preview_ids - include_set))
            except Exception:
                exclusion_user_ids = '[]'
            s.name = name
            s.description = (request.form.get('description') or '').strip() or None
            s.query_rules = query_rules
            if hasattr(s, 'exclusion_user_ids'):
                s.exclusion_user_ids = exclusion_user_ids
            db.session.commit()
            flash('Segmento actualizado.', 'success')
            return redirect(url_for('admin_marketing'))
        rules = {}
        try:
            rules = json.loads(s.query_rules) if s.query_rules else {}
        except Exception:
            pass
        if not isinstance(rules, dict):
            rules = {}
        if 'conditions' not in rules and (rules.get('pais') or rules.get('tipo_membresia')):
            conditions = []
            if rules.get('pais'):
                conditions.append({'field': 'country', 'op': '=', 'value': rules['pais']})
            if rules.get('tipo_membresia'):
                conditions.append({'field': 'tipo_membresia', 'op': '=', 'value': rules['tipo_membresia']})
            rules = {'logic': 'and', 'conditions': conditions}
        count = get_recipient_count(s.id, None, for_editor=True) if s.id else 0
        members_preview = get_members_from_segment_simple(s.id, subscribed_only=False, apply_exclusion=False)[:200] if s.id else []
        exclusion_ids = set()
        if getattr(s, 'exclusion_user_ids', None):
            try:
                exclusion_ids = set(json.loads(s.exclusion_user_ids)) if isinstance(s.exclusion_user_ids, str) else set(s.exclusion_user_ids or [])
            except Exception:
                pass
        return render_template('admin/marketing_segment_edit.html',
                             segment=s,
                             rules=rules,
                             segment_fields=SEGMENT_FIELDS,
                             segment_operators=SEGMENT_OPERATORS,
                             recipient_count=count,
                             members_preview=members_preview,
                             exclusion_ids=exclusion_ids)


    @app.route('/admin/marketing/segment/<int:segment_id>/delete', methods=['POST'])
    @admin_required
    def admin_marketing_segment_delete(segment_id):
        """Eliminar segmento si no está en uso por ninguna campaña."""
        s = MarketingSegment.query.get_or_404(segment_id)
        used = MarketingCampaign.query.filter_by(segment_id=segment_id).limit(1).first()
        if used:
            flash('No se puede eliminar: hay campañas que usan este segmento.', 'danger')
            return redirect(url_for('admin_marketing'))
        db.session.delete(s)
        db.session.commit()
        flash('Segmento eliminado.', 'success')
        return redirect(url_for('admin_marketing'))


    @app.route('/admin/marketing/templates/create', methods=['GET', 'POST'])
    @admin_required
    def admin_marketing_templates_create():
        """Crear plantilla: pantalla con selector de modelo (plantillas base)."""
        from _app.modules.marketing.template_models import TEMPLATE_MODELS
        if request.method == 'POST':
            name = (request.form.get('name') or '').strip()
            html = request.form.get('html') or ''
            if not name:
                flash('Escribe el nombre de la plantilla.', 'warning')
                return redirect(url_for('admin_marketing_templates_create'))
            if not html.strip():
                flash('El contenido HTML no puede estar vacío.', 'warning')
                return redirect(url_for('admin_marketing_templates_create'))
            try:
                t = MarketingTemplate(name=name, html=html, variables='[]')
                db.session.add(t)
                db.session.commit()
                flash(f'Plantilla "{name}" creada.', 'success')
                return redirect(url_for('admin_marketing'))
            except Exception as e:
                flash(f'Error al crear plantilla: {e}', 'danger')
                return redirect(url_for('admin_marketing_templates_create'))
        return render_template('admin/marketing_template_create.html', template_models=TEMPLATE_MODELS)


    @app.route('/admin/marketing/template', methods=['POST'])
    @admin_required
    def admin_marketing_create_template():
        """Crear plantilla desde el panel (form POST, creación rápida)."""
        name = (request.form.get('name') or '').strip()
        html = request.form.get('html') or ''
        if not name:
            flash('Escribe el nombre de la plantilla.', 'warning')
            return redirect(url_for('admin_marketing'))
        if not html.strip():
            flash('El contenido HTML no puede estar vacío.', 'warning')
            return redirect(url_for('admin_marketing'))
        try:
            t = MarketingTemplate(name=name, html=html, variables='[]')
            db.session.add(t)
            db.session.commit()
            flash(f'Plantilla "{name}" creada.', 'success')
        except Exception as e:
            flash(f'Error al crear plantilla: {e}', 'danger')
        return redirect(url_for('admin_marketing'))


    @app.route('/admin/marketing/template/preview', methods=['POST'])
    @admin_required
    def admin_marketing_template_preview():
        """Vista previa de plantilla: reemplaza variables con datos de ejemplo y devuelve HTML."""
        html = request.form.get('html') or (request.get_json(silent=True) or {}).get('html') or ''
        # URL base absoluta para que las imágenes (ej. flyer) carguen en el iframe
        if request:
            base_url = (request.host_url or request.url_root or '').rstrip('/')
            if not base_url and request.url:
                from urllib.parse import urlparse
                p = urlparse(request.url)
                base_url = f"{p.scheme}://{p.netloc}"
        else:
            base_url = ''
        from _app.modules.marketing.service import render_template_html
        ctx = {
            'nombre': 'Usuario de ejemplo',
            'email': 'ejemplo@email.com',
            'user_id': 0,
            'reunion_url': 'https://meet.google.com/zac-wmmg-hgb',
        }
        rendered = render_template_html(html, '[]', ctx, base_url=base_url)
        # Inyectar <base href="..."> para que /static/... resuelva bien en el iframe
        if base_url and '<head>' in rendered.lower():
            import re
            rendered = re.sub(r'(<head[^>]*>)', r'\1<base href="' + base_url + '/">', rendered, count=1, flags=re.I)
        elif base_url and '<html' in rendered.lower() and '<head>' not in rendered.lower():
            rendered = rendered.replace('<html', '<html><head><base href="' + base_url + '/"></head>', 1)
        return jsonify({'html': rendered})


    @app.route('/admin/marketing/template/<int:template_id>/edit', methods=['GET', 'POST'])
    @admin_required
    def admin_marketing_template_edit(template_id):
        """Editar plantilla: nombre y HTML."""
        t = MarketingTemplate.query.get_or_404(template_id)
        if request.method == 'POST':
            name = (request.form.get('name') or '').strip()
            html = request.form.get('html') or ''
            if not name:
                flash('El nombre es obligatorio.', 'warning')
                return redirect(url_for('admin_marketing_template_edit', template_id=t.id))
            if not html.strip():
                flash('El contenido HTML no puede estar vacío.', 'warning')
                return redirect(url_for('admin_marketing_template_edit', template_id=t.id))
            t.name = name
            t.html = html
            db.session.commit()
            flash('Plantilla actualizada.', 'success')
            return redirect(url_for('admin_marketing'))
        return render_template('admin/marketing_template_edit.html', template=t)


    @app.route('/admin/marketing/template/<int:template_id>/delete', methods=['POST'])
    @admin_required
    def admin_marketing_template_delete(template_id):
        """Eliminar plantilla si no está en uso por ninguna campaña."""
        t = MarketingTemplate.query.get_or_404(template_id)
        used = MarketingCampaign.query.filter_by(template_id=template_id).limit(1).first()
        if used:
            flash('No se puede eliminar: hay campañas que usan esta plantilla.', 'danger')
            return redirect(url_for('admin_marketing'))
        db.session.delete(t)
        db.session.commit()
        flash('Plantilla eliminada.', 'success')
        return redirect(url_for('admin_marketing'))
