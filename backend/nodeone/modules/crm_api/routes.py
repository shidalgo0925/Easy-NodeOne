from datetime import datetime, timedelta

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from nodeone.core.db import db
from nodeone.modules.crm_api.models import (
    CrmActivity,
    CrmLead,
    CrmLeadLog,
    CrmLeadTag,
    CrmLostReason,
    CrmStage,
    CrmTag,
)

crm_api_bp = Blueprint('crm_api', __name__, url_prefix='/crm')


def _ensure_tables():
    CrmStage.__table__.create(db.engine, checkfirst=True)
    CrmLostReason.__table__.create(db.engine, checkfirst=True)
    CrmLead.__table__.create(db.engine, checkfirst=True)
    CrmTag.__table__.create(db.engine, checkfirst=True)
    CrmLeadTag.__table__.create(db.engine, checkfirst=True)
    CrmActivity.__table__.create(db.engine, checkfirst=True)
    CrmLeadLog.__table__.create(db.engine, checkfirst=True)


def _parse_dt(value):
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value).replace('Z', '+00:00')).replace(tzinfo=None)
    except Exception:
        return None


def _can_view_all():
    if bool(getattr(current_user, 'is_admin', False)):
        return True
    try:
        return bool(current_user.has_permission('users.view'))
    except Exception:
        return False


def _org_id_from_request():
    from app import get_current_organization_id

    oid = get_current_organization_id()
    if oid is None:
        return None
    try:
        return int(oid)
    except (TypeError, ValueError):
        return None


def _serialize_stage(s):
    return {
        'id': s.id,
        'name': s.name,
        'sequence': s.sequence,
        'probability_default': float(s.probability_default or 0),
        'is_won': bool(s.is_won),
        'is_lost': bool(s.is_lost),
    }


def _serialize_activity(a):
    now = datetime.utcnow()
    status = a.status
    if status == 'pending' and a.due_date and a.due_date < now:
        status = 'overdue'
    return {
        'id': a.id,
        'lead_id': a.lead_id,
        'type': a.type,
        'summary': a.summary,
        'due_date': a.due_date.isoformat() if a.due_date else None,
        'assigned_to': a.assigned_to,
        'status': status,
    }


def _serialize_lead(lead):
    return {
        'id': lead.id,
        'name': lead.name,
        'type': lead.lead_type,
        'contact_name': lead.contact_name,
        'company_name': lead.company_name,
        'email': lead.email,
        'phone': lead.phone,
        'stage_id': lead.stage_id,
        'stage_name': lead.stage.name if lead.stage else None,
        'user_id': lead.user_id,
        'expected_revenue': float(lead.expected_revenue or 0),
        'probability': float(lead.probability or 0),
        'priority': lead.priority,
        'source': lead.source,
        'description': lead.description,
        'create_date': lead.create_date.isoformat() if lead.create_date else None,
        'close_date': lead.close_date.isoformat() if lead.close_date else None,
        'lost_reason_id': lead.lost_reason_id,
        'active': bool(lead.active),
    }


def _ensure_default_stages(org_id):
    if CrmStage.query.filter_by(organization_id=org_id).count() > 0:
        return
    defaults = [
        {'name': 'Nuevo', 'sequence': 10, 'probability_default': 10, 'is_won': False, 'is_lost': False},
        {'name': 'Contactado', 'sequence': 20, 'probability_default': 30, 'is_won': False, 'is_lost': False},
        {'name': 'Propuesta', 'sequence': 30, 'probability_default': 60, 'is_won': False, 'is_lost': False},
        {'name': 'Ganado', 'sequence': 40, 'probability_default': 100, 'is_won': True, 'is_lost': False},
        {'name': 'Perdido', 'sequence': 50, 'probability_default': 0, 'is_won': False, 'is_lost': True},
    ]
    for row in defaults:
        db.session.add(CrmStage(organization_id=org_id, **row))
    db.session.commit()


def _lead_query_in_scope(org_id):
    q = CrmLead.query.filter_by(organization_id=org_id)
    if not _can_view_all():
        q = q.filter(CrmLead.user_id == int(getattr(current_user, 'id', 0) or 0))
    return q


def _activity_query_in_scope(org_id):
    q = CrmActivity.query.filter_by(organization_id=org_id)
    if not _can_view_all():
        q = q.filter(CrmActivity.assigned_to == int(getattr(current_user, 'id', 0) or 0))
    return q


def _assign_round_robin(org_id):
    from app import User

    from nodeone.services.user_organization import user_in_org_clause

    candidates = User.query.filter(user_in_org_clause(User, org_id), User.is_active.is_(True)).all()
    if not candidates:
        return int(getattr(current_user, 'id', 0) or 0)
    scored = []
    for u in candidates:
        if bool(getattr(u, 'is_admin', False)):
            continue
        open_count = CrmLead.query.filter_by(organization_id=org_id, user_id=u.id, active=True).count()
        scored.append((open_count, u.id))
    if not scored:
        return int(getattr(current_user, 'id', 0) or 0)
    scored.sort(key=lambda x: (x[0], x[1]))
    return scored[0][1]


def _require_lead_or_404(org_id, lead_id):
    lead = _lead_query_in_scope(org_id).filter_by(id=lead_id).first()
    if lead is None:
        return None, (jsonify({'success': False, 'error': 'Lead no encontrado'}), 404)
    return lead, None


@crm_api_bp.route('/stages', methods=['GET'])
@login_required
def crm_stages_get():
    _ensure_tables()
    org_id = _org_id_from_request()
    if org_id is None:
        return jsonify({'success': False, 'error': 'Organización no definida'}), 400
    _ensure_default_stages(org_id)
    rows = CrmStage.query.filter_by(organization_id=org_id, active=True).order_by(CrmStage.sequence.asc()).all()
    return jsonify({'success': True, 'items': [_serialize_stage(x) for x in rows]})


@crm_api_bp.route('/stages', methods=['POST'])
@login_required
def crm_stages_post():
    _ensure_tables()
    org_id = _org_id_from_request()
    if org_id is None:
        return jsonify({'success': False, 'error': 'Organización no definida'}), 400
    data = request.get_json(silent=True) or {}
    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({'success': False, 'error': 'name es obligatorio'}), 400
    row = CrmStage(
        organization_id=org_id,
        name=name,
        sequence=int(data.get('sequence') or 10),
        probability_default=float(data.get('probability_default') or 0),
        is_won=bool(data.get('is_won', False)),
        is_lost=bool(data.get('is_lost', False)),
    )
    db.session.add(row)
    db.session.commit()
    return jsonify({'success': True, 'item': _serialize_stage(row)}), 201


@crm_api_bp.route('/tags', methods=['POST'])
@login_required
def crm_tags_post():
    _ensure_tables()
    org_id = _org_id_from_request()
    if org_id is None:
        return jsonify({'success': False, 'error': 'Organización no definida'}), 400
    data = request.get_json(silent=True) or {}
    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({'success': False, 'error': 'name es obligatorio'}), 400
    row = CrmTag(organization_id=org_id, name=name, color=(data.get('color') or 'blue'))
    db.session.add(row)
    db.session.commit()
    return jsonify({'success': True, 'item': {'id': row.id, 'name': row.name, 'color': row.color}}), 201


@crm_api_bp.route('/leads', methods=['GET'])
@login_required
def crm_leads_get():
    _ensure_tables()
    org_id = _org_id_from_request()
    if org_id is None:
        return jsonify({'success': False, 'error': 'Organización no definida'}), 400
    q = _lead_query_in_scope(org_id).filter_by(active=True)
    stage_id = request.args.get('stage', type=int)
    user_id = request.args.get('user', type=int)
    source = (request.args.get('source') or '').strip()
    if stage_id:
        q = q.filter(CrmLead.stage_id == stage_id)
    if user_id:
        q = q.filter(CrmLead.user_id == user_id)
    if source:
        q = q.filter(CrmLead.source == source)
    if request.args.get('from'):
        d = _parse_dt(request.args.get('from'))
        if d:
            q = q.filter(CrmLead.create_date >= d)
    if request.args.get('to'):
        d = _parse_dt(request.args.get('to'))
        if d:
            q = q.filter(CrmLead.create_date <= d + timedelta(days=1))
    rows = q.order_by(CrmLead.create_date.desc()).limit(500).all()
    return jsonify({'success': True, 'items': [_serialize_lead(x) for x in rows]})


@crm_api_bp.route('/leads', methods=['POST'])
@login_required
def crm_leads_post():
    _ensure_tables()
    org_id = _org_id_from_request()
    if org_id is None:
        return jsonify({'success': False, 'error': 'Organización no definida'}), 400
    _ensure_default_stages(org_id)
    data = request.get_json(silent=True) or {}
    name = (data.get('name') or '').strip()
    email = (data.get('email') or '').strip().lower()
    phone = (data.get('phone') or '').strip()
    if not name:
        return jsonify({'success': False, 'error': 'name es obligatorio'}), 400
    if not email and not phone:
        return jsonify({'success': False, 'error': 'email o phone es obligatorio'}), 400

    stage = None
    if data.get('stage_id'):
        stage = CrmStage.query.filter_by(organization_id=org_id, id=int(data.get('stage_id'))).first()
    if stage is None:
        stage = CrmStage.query.filter_by(organization_id=org_id, is_won=False, is_lost=False).order_by(CrmStage.sequence.asc()).first()
    if stage is None:
        return jsonify({'success': False, 'error': 'No hay etapas configuradas'}), 400

    assign_mode = (data.get('assign_mode') or '').strip().lower()
    user_id = data.get('user_id')
    if user_id is None:
        if assign_mode == 'round_robin':
            user_id = _assign_round_robin(org_id)
        else:
            user_id = int(getattr(current_user, 'id', 0) or 0)

    row = CrmLead(
        organization_id=org_id,
        lead_type=(data.get('type') or 'lead'),
        name=name,
        contact_name=(data.get('contact_name') or '').strip() or None,
        company_name=(data.get('company_name') or '').strip() or None,
        email=email or None,
        phone=phone or None,
        stage_id=stage.id,
        user_id=int(user_id) if user_id else None,
        expected_revenue=float(data.get('expected_revenue') or 0),
        probability=float(data.get('probability') if data.get('probability') is not None else stage.probability_default),
        priority=(data.get('priority') or 'low'),
        source=(data.get('source') or 'web'),
        description=(data.get('description') or '').strip() or None,
    )
    db.session.add(row)
    db.session.commit()
    return jsonify({'success': True, 'item': _serialize_lead(row)}), 201


@crm_api_bp.route('/leads/<int:lead_id>', methods=['GET'])
@login_required
def crm_lead_get(lead_id):
    _ensure_tables()
    org_id = _org_id_from_request()
    if org_id is None:
        return jsonify({'success': False, 'error': 'Organización no definida'}), 400
    lead, err = _require_lead_or_404(org_id, lead_id)
    if err:
        return err
    activities = CrmActivity.query.filter_by(organization_id=org_id, lead_id=lead.id).order_by(CrmActivity.due_date.asc()).all()
    logs = CrmLeadLog.query.filter_by(organization_id=org_id, lead_id=lead.id).order_by(CrmLeadLog.created_at.desc()).all()
    tags = (
        db.session.query(CrmTag.id, CrmTag.name, CrmTag.color)
        .join(CrmLeadTag, CrmLeadTag.tag_id == CrmTag.id)
        .filter(CrmLeadTag.lead_id == lead.id, CrmTag.organization_id == org_id)
        .all()
    )
    return jsonify({
        'success': True,
        'item': _serialize_lead(lead),
        'activities': [_serialize_activity(x) for x in activities],
        'logs': [
            {
                'id': l.id,
                'type': l.log_type,
                'message': l.message,
                'created_by': l.created_by,
                'created_at': l.created_at.isoformat() if l.created_at else None,
            }
            for l in logs
        ],
        'tags': [{'id': t.id, 'name': t.name, 'color': t.color} for t in tags],
    })


@crm_api_bp.route('/leads/<int:lead_id>', methods=['PATCH'])
@login_required
def crm_lead_patch(lead_id):
    _ensure_tables()
    org_id = _org_id_from_request()
    if org_id is None:
        return jsonify({'success': False, 'error': 'Organización no definida'}), 400
    lead, err = _require_lead_or_404(org_id, lead_id)
    if err:
        return err
    data = request.get_json(silent=True) or {}

    if data.get('stage_id'):
        stage = CrmStage.query.filter_by(organization_id=org_id, id=int(data.get('stage_id'))).first()
        if stage is None:
            return jsonify({'success': False, 'error': 'Etapa no válida'}), 400
        if stage.is_lost and not (data.get('lost_reason_id') or lead.lost_reason_id):
            return jsonify({'success': False, 'error': 'lost_reason_id es obligatorio para etapa perdida'}), 400
        lead.stage_id = stage.id
        lead.probability = float(stage.probability_default)
        if stage.is_won:
            lead.probability = 100.0
            lead.close_date = datetime.utcnow()
        if stage.is_lost:
            lead.probability = 0.0
            lead.close_date = datetime.utcnow()

    for f in ('name', 'contact_name', 'company_name', 'email', 'phone', 'source', 'description'):
        if f in data:
            setattr(lead, f, data.get(f))
    if 'expected_revenue' in data:
        lead.expected_revenue = float(data.get('expected_revenue') or 0)
    if 'probability' in data:
        lead.probability = float(data.get('probability') or 0)
    if 'priority' in data:
        lead.priority = str(data.get('priority') or 'low')
    if 'user_id' in data and (_can_view_all() or int(getattr(current_user, 'id', 0) or 0) == int(data.get('user_id') or 0)):
        lead.user_id = int(data.get('user_id')) if data.get('user_id') else None
    if 'type' in data:
        lead.lead_type = str(data.get('type') or 'lead')
    if 'lost_reason_id' in data:
        lead.lost_reason_id = int(data.get('lost_reason_id')) if data.get('lost_reason_id') else None

    db.session.commit()
    return jsonify({'success': True, 'item': _serialize_lead(lead)})


@crm_api_bp.route('/leads/<int:lead_id>', methods=['DELETE'])
@login_required
def crm_lead_delete(lead_id):
    _ensure_tables()
    org_id = _org_id_from_request()
    if org_id is None:
        return jsonify({'success': False, 'error': 'Organización no definida'}), 400
    lead, err = _require_lead_or_404(org_id, lead_id)
    if err:
        return err
    lead.active = False
    db.session.commit()
    return jsonify({'success': True})


@crm_api_bp.route('/leads/<int:lead_id>/convert', methods=['POST'])
@login_required
def crm_lead_convert(lead_id):
    _ensure_tables()
    org_id = _org_id_from_request()
    if org_id is None:
        return jsonify({'success': False, 'error': 'Organización no definida'}), 400
    lead, err = _require_lead_or_404(org_id, lead_id)
    if err:
        return err
    lead.lead_type = 'opportunity'
    db.session.add(CrmLeadLog(
        organization_id=org_id,
        lead_id=lead.id,
        log_type='system',
        message='Lead convertido a oportunidad',
        created_by=int(getattr(current_user, 'id', 0) or 0),
    ))
    db.session.commit()
    return jsonify({'success': True, 'item': _serialize_lead(lead)})


@crm_api_bp.route('/leads/<int:lead_id>/lost', methods=['POST'])
@login_required
def crm_lead_lost(lead_id):
    _ensure_tables()
    org_id = _org_id_from_request()
    if org_id is None:
        return jsonify({'success': False, 'error': 'Organización no definida'}), 400
    lead, err = _require_lead_or_404(org_id, lead_id)
    if err:
        return err
    data = request.get_json(silent=True) or {}
    reason_name = (data.get('reason') or '').strip()
    reason_id = data.get('lost_reason_id')
    reason = None
    if reason_id:
        reason = CrmLostReason.query.filter_by(organization_id=org_id, id=int(reason_id)).first()
    elif reason_name:
        reason = CrmLostReason.query.filter_by(organization_id=org_id, name=reason_name).first()
        if reason is None:
            reason = CrmLostReason(organization_id=org_id, name=reason_name)
            db.session.add(reason)
            db.session.flush()
    if reason is None:
        return jsonify({'success': False, 'error': 'Razón de pérdida obligatoria'}), 400

    lost_stage = CrmStage.query.filter_by(organization_id=org_id, is_lost=True).order_by(CrmStage.sequence.asc()).first()
    if lost_stage:
        lead.stage_id = lost_stage.id
    lead.lost_reason_id = reason.id
    lead.probability = 0.0
    lead.close_date = datetime.utcnow()
    db.session.add(CrmLeadLog(
        organization_id=org_id,
        lead_id=lead.id,
        log_type='system',
        message=f"Oportunidad marcada como perdida: {reason.name}",
        created_by=int(getattr(current_user, 'id', 0) or 0),
    ))
    db.session.commit()
    return jsonify({'success': True, 'item': _serialize_lead(lead)})


def _create_activity(org_id, lead_id, data):
    a_type = (data.get('type') or '').strip().lower()
    if a_type not in ('call', 'meeting', 'email', 'task'):
        return None, 'type inválido'
    summary = (data.get('summary') or '').strip()
    due = _parse_dt(data.get('due_date'))
    if not summary or due is None:
        return None, 'summary y due_date son obligatorios'
    assigned_to = int(data.get('assigned_to') or getattr(current_user, 'id', 0) or 0)
    row = CrmActivity(
        organization_id=org_id,
        lead_id=lead_id,
        type=a_type,
        summary=summary,
        due_date=due,
        assigned_to=assigned_to,
        status='pending',
    )
    db.session.add(row)
    db.session.commit()
    _send_activity_email_alert_now(org_id, row)
    return row, None


def _send_activity_email_alert_now(org_id, activity):
    """Envío inmediato de alerta al asignado al crear actividad (sin esperar cron)."""
    try:
        import app as app_module
        from app import EmailLog, User
        from email_templates import _default_base_url, get_crm_activity_assigned_email
        from nodeone.services.crm_email import (
            build_crm_activity_assigned_email,
            crm_email_context_assigned_plain_esc,
        )

        apply_cfg = getattr(app_module, 'apply_email_config_from_db', None)
        if callable(apply_cfg):
            apply_cfg()
        email_service = getattr(app_module, 'email_service', None)
        if not email_service:
            return

        user = User.query.get(int(activity.assigned_to or 0))
        if not user or not getattr(user, 'email', None):
            return

        lead = CrmLead.query.filter_by(organization_id=org_id, id=int(activity.lead_id)).first()
        lead_name = lead.name if lead else f'Lead #{activity.lead_id}'
        now = datetime.utcnow()

        # dedupe: mismo usuario+actividad en última hora
        exists = EmailLog.query.filter(
            EmailLog.recipient_id == user.id,
            EmailLog.email_type == 'crm_activity_alert_assigned',
            EmailLog.related_entity_type == 'crm_activity',
            EmailLog.related_entity_id == int(activity.id),
            EmailLog.status == 'sent',
            EmailLog.created_at >= now - timedelta(hours=1),
        ).first()
        if exists:
            return

        due = activity.due_date
        due_text = due.strftime('%Y-%m-%d %H:%M UTC') if due else 'sin vencimiento'
        crm_url = f"{_default_base_url().rstrip('/')}/admin/crm"
        assignee_name = f"{getattr(user, 'first_name', '')} {getattr(user, 'last_name', '')}".strip() or user.email
        plain, esc = crm_email_context_assigned_plain_esc(
            lead_name=lead_name,
            activity_summary=activity.summary,
            activity_type=activity.type,
            due_text=due_text,
            crm_url=crm_url,
            assignee_name=assignee_name,
        )
        default_subject = f"[CRM] Nueva actividad asignada: {activity.summary}"
        default_html = get_crm_activity_assigned_email(
            lead_name,
            activity.summary,
            activity.type,
            due_text,
            crm_url,
        )
        default_text = (
            f"Nueva actividad asignada | Lead: {lead_name} | Actividad: {activity.summary} | Vence: {due_text}"
        )
        subject, html, text = build_crm_activity_assigned_email(
            org_id,
            plain,
            esc,
            default_subject=default_subject,
            default_html=default_html,
            default_text=default_text,
        )
        email_service.send_email(
            subject=subject,
            recipients=[user.email],
            html_content=html,
            text_content=text,
            email_type='crm_activity_alert_assigned',
            related_entity_type='crm_activity',
            related_entity_id=int(activity.id),
            recipient_id=user.id,
            recipient_name=assignee_name,
        )
    except Exception:
        # nunca romper alta de actividad por falla de email
        pass


@crm_api_bp.route('/activities', methods=['POST'])
@login_required
def crm_activities_post():
    _ensure_tables()
    org_id = _org_id_from_request()
    data = request.get_json(silent=True) or {}
    lead_id = int(data.get('lead_id') or 0)
    if org_id is None or lead_id < 1:
        return jsonify({'success': False, 'error': 'organization/lead inválido'}), 400
    lead, err = _require_lead_or_404(org_id, lead_id)
    if err:
        return err
    row, error = _create_activity(org_id, lead.id, data)
    if error:
        return jsonify({'success': False, 'error': error}), 400
    return jsonify({'success': True, 'item': _serialize_activity(row)}), 201


@crm_api_bp.route('/leads/<int:lead_id>/activities', methods=['POST'])
@login_required
def crm_lead_activities_post(lead_id):
    _ensure_tables()
    org_id = _org_id_from_request()
    if org_id is None:
        return jsonify({'success': False, 'error': 'Organización no definida'}), 400
    lead, err = _require_lead_or_404(org_id, lead_id)
    if err:
        return err
    row, error = _create_activity(org_id, lead.id, request.get_json(silent=True) or {})
    if error:
        return jsonify({'success': False, 'error': error}), 400
    return jsonify({'success': True, 'item': _serialize_activity(row)}), 201


@crm_api_bp.route('/leads/<int:lead_id>/log', methods=['POST'])
@login_required
def crm_lead_log_post(lead_id):
    _ensure_tables()
    org_id = _org_id_from_request()
    if org_id is None:
        return jsonify({'success': False, 'error': 'Organización no definida'}), 400
    lead, err = _require_lead_or_404(org_id, lead_id)
    if err:
        return err
    data = request.get_json(silent=True) or {}
    log_type = (data.get('type') or '').strip().lower()
    message = (data.get('message') or '').strip()
    if log_type not in ('email', 'call', 'note', 'system'):
        return jsonify({'success': False, 'error': 'type inválido'}), 400
    if not message:
        return jsonify({'success': False, 'error': 'message es obligatorio'}), 400
    row = CrmLeadLog(
        organization_id=org_id,
        lead_id=lead.id,
        log_type=log_type,
        message=message,
        created_by=int(getattr(current_user, 'id', 0) or 0),
    )
    db.session.add(row)
    db.session.commit()
    return jsonify({'success': True, 'item': {'id': row.id, 'type': row.log_type, 'message': row.message}}), 201


@crm_api_bp.route('/reports', methods=['GET'])
@login_required
def crm_reports_get():
    _ensure_tables()
    org_id = _org_id_from_request()
    if org_id is None:
        return jsonify({'success': False, 'error': 'Organización no definida'}), 400
    q = _lead_query_in_scope(org_id).filter_by(active=True)
    leads = q.all()
    total = len(leads)
    won = sum(1 for l in leads if l.stage and l.stage.is_won)
    conversion_rate = (won / total * 100.0) if total else 0.0
    forecast = sum(float(l.expected_revenue or 0) * (float(l.probability or 0) / 100.0) for l in leads)
    by_source = {}
    by_user = {}
    for l in leads:
        by_source[l.source or 'unknown'] = by_source.get(l.source or 'unknown', 0) + 1
        k = str(l.user_id or 0)
        by_user[k] = by_user.get(k, 0.0) + float(l.expected_revenue or 0)
    return jsonify({
        'success': True,
        'forecast': forecast,
        'kpis': {
            'total_leads': total,
            'won': won,
            'conversion_rate': conversion_rate,
            'leads_by_source': by_source,
            'sales_by_user': by_user,
        },
    })


@crm_api_bp.route('/activities/alerts', methods=['GET'])
@login_required
def crm_activities_alerts_get():
    _ensure_tables()
    org_id = _org_id_from_request()
    if org_id is None:
        return jsonify({'success': False, 'error': 'Organización no definida'}), 400
    now = datetime.utcnow()
    next_24h = now + timedelta(hours=24)
    q = _activity_query_in_scope(org_id).filter(CrmActivity.status.in_(('pending', 'overdue')))
    rows = q.order_by(CrmActivity.due_date.asc()).limit(500).all()
    overdue = []
    due_today = []
    due_soon = []
    for a in rows:
        item = _serialize_activity(a)
        due = a.due_date
        if due is None:
            continue
        if due < now:
            overdue.append(item)
        elif due.date() == now.date():
            due_today.append(item)
        elif due <= next_24h:
            due_soon.append(item)
    return jsonify({
        'success': True,
        'alerts': {
            'overdue': overdue,
            'due_today': due_today,
            'due_soon': due_soon,
            'totals': {
                'overdue': len(overdue),
                'due_today': len(due_today),
                'due_soon': len(due_soon),
            },
        },
    })
