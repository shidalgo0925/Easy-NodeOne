"""Admin: reglas del motor unificado de comunicaciones (CommunicationRule)."""

from functools import wraps

from flask import Blueprint, jsonify, render_template, request
from flask_login import current_user, login_required
from sqlalchemy import or_

admin_communications_bp = Blueprint('admin_communications', __name__)


def _admin_required_lazy(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        import app as M
        from flask import flash, redirect, url_for

        if bool(getattr(current_user, 'must_change_password', False)):
            flash('Debes cambiar tu contraseña antes de continuar.', 'warning')
            return redirect(url_for('auth.change_password'))
        if not current_user.is_admin and not M._user_has_any_admin_permission(current_user):
            flash('No tienes permisos para acceder a esta página.', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)

    return decorated_function


def _can_edit_rule(M, rule) -> bool:
    oid = int(M.admin_data_scope_organization_id())
    if rule.organization_id is not None:
        return int(rule.organization_id) == oid
    return bool(getattr(M.current_user, 'is_admin', False))


def _rule_to_dict(M, rule, event):
    return {
        'id': rule.id,
        'event_id': rule.event_id,
        'event_code': event.code,
        'event_name': event.name,
        'organization_id': rule.organization_id,
        'channel': rule.channel,
        'marketing_template_id': rule.marketing_template_id,
        'enabled': rule.enabled,
        'delay_minutes': rule.delay_minutes,
        'is_marketing': rule.is_marketing,
        'respect_user_prefs': rule.respect_user_prefs,
        'priority': rule.priority,
        'can_edit': _can_edit_rule(M, rule),
    }


@admin_communications_bp.route('/admin/communications/settings')
@_admin_required_lazy
def admin_communications_settings():
    return render_template(
        'admin/communications_settings.html',
        show_global_rule=bool(getattr(current_user, 'is_admin', False)),
    )


@admin_communications_bp.route('/api/admin/communications/events', methods=['GET'])
@_admin_required_lazy
def api_communication_events_list():
    import app as M
    from models.communication_rules import CommunicationEvent

    rows = CommunicationEvent.query.order_by(CommunicationEvent.code.asc()).all()
    return jsonify(
        {
            'events': [
                {
                    'id': e.id,
                    'code': e.code,
                    'name': e.name,
                    'description': e.description,
                    'category': e.category,
                }
                for e in rows
            ]
        }
    )


@admin_communications_bp.route('/api/admin/communications/marketing-templates', methods=['GET'])
@_admin_required_lazy
def api_communication_marketing_templates():
    import app as M

    rows = M.MarketingTemplate.query.order_by(M.MarketingTemplate.name.asc()).limit(300).all()
    return jsonify({'templates': [{'id': t.id, 'name': t.name} for t in rows]})


@admin_communications_bp.route('/api/admin/communications/rules', methods=['GET'])
@_admin_required_lazy
def api_communication_rules_list():
    import app as M
    from models.communication_rules import CommunicationEvent, CommunicationRule

    oid = int(M.admin_data_scope_organization_id())
    q = (
        M.db.session.query(CommunicationRule, CommunicationEvent)
        .join(CommunicationEvent, CommunicationRule.event_id == CommunicationEvent.id)
        .filter(
            or_(
                CommunicationRule.organization_id.is_(None),
                CommunicationRule.organization_id == oid,
            )
        )
        .order_by(CommunicationEvent.code.asc(), CommunicationRule.priority.asc(), CommunicationRule.id.asc())
    )
    out = []
    for rule, event in q.all():
        out.append(_rule_to_dict(M, rule, event))
    return jsonify({'rules': out})


@admin_communications_bp.route('/api/admin/communications/rules', methods=['POST'])
@_admin_required_lazy
def api_communication_rules_create():
    import app as M
    from models.communication_rules import CommunicationEvent, CommunicationRule

    data = request.get_json() or {}
    event_id = data.get('event_id')
    channel = (data.get('channel') or '').strip().lower()
    if not event_id or channel not in ('email', 'in_app', 'sms'):
        return jsonify({'success': False, 'error': 'event_id y channel (email|in_app|sms) requeridos'}), 400

    ev = CommunicationEvent.query.get(int(event_id))
    if not ev:
        return jsonify({'success': False, 'error': 'Evento no encontrado'}), 404

    oid_scope = int(M.admin_data_scope_organization_id())
    org_raw = data.get('organization_id', oid_scope)
    if org_raw is None or org_raw == '' or str(org_raw).lower() == 'null':
        if not getattr(M.current_user, 'is_admin', False):
            return jsonify({'success': False, 'error': 'Solo administrador de plataforma puede crear reglas globales'}), 403
        new_org_id = None
    else:
        new_org_id = int(org_raw)
        if new_org_id != oid_scope and not getattr(M.current_user, 'is_admin', False):
            return jsonify({'success': False, 'error': 'organization_id no permitido'}), 403

    mt_id = data.get('marketing_template_id')
    if mt_id in (None, '', 'null'):
        mt_id = None
    else:
        mt_id = int(mt_id)

    rule = CommunicationRule(
        event_id=int(event_id),
        organization_id=new_org_id,
        channel=channel,
        marketing_template_id=mt_id,
        enabled=bool(data.get('enabled', True)),
        delay_minutes=int(data.get('delay_minutes', 0) or 0),
        is_marketing=bool(data.get('is_marketing', False)),
        respect_user_prefs=bool(data.get('respect_user_prefs', True)),
        priority=int(data.get('priority', 10) or 10),
    )
    M.db.session.add(rule)
    M.db.session.commit()
    try:
        from nodeone.services.notification_settings_sync import sync_event_rules_to_notification_settings

        sync_event_rules_to_notification_settings(rule.event_id)
    except Exception:
        pass
    return jsonify({'success': True, 'rule': _rule_to_dict(M, rule, ev)})


@admin_communications_bp.route('/api/admin/communications/rules/<int:rule_id>', methods=['PUT'])
@_admin_required_lazy
def api_communication_rules_update(rule_id):
    import app as M
    from models.communication_rules import CommunicationEvent, CommunicationRule

    rule = CommunicationRule.query.get_or_404(rule_id)
    event = CommunicationEvent.query.get(rule.event_id)
    if not event:
        return jsonify({'success': False, 'error': 'Evento asociado no existe'}), 404
    if not _can_edit_rule(M, rule):
        return jsonify({'success': False, 'error': 'Sin permiso para editar esta regla'}), 403

    data = request.get_json() or {}
    if 'channel' in data:
        ch = (data.get('channel') or '').strip().lower()
        if ch not in ('email', 'in_app', 'sms'):
            return jsonify({'success': False, 'error': 'channel inválido'}), 400
        rule.channel = ch
    if 'enabled' in data:
        rule.enabled = bool(data['enabled'])
    if 'delay_minutes' in data:
        rule.delay_minutes = int(data['delay_minutes'] or 0)
    if 'is_marketing' in data:
        rule.is_marketing = bool(data['is_marketing'])
    if 'respect_user_prefs' in data:
        rule.respect_user_prefs = bool(data['respect_user_prefs'])
    if 'priority' in data:
        rule.priority = int(data['priority'] or 10)
    if 'marketing_template_id' in data:
        mt = data['marketing_template_id']
        rule.marketing_template_id = None if mt in (None, '', 'null') else int(mt)

    M.db.session.commit()
    try:
        from nodeone.services.notification_settings_sync import sync_event_rules_to_notification_settings

        sync_event_rules_to_notification_settings(rule.event_id)
    except Exception:
        pass
    return jsonify({'success': True, 'rule': _rule_to_dict(M, rule, event)})


@admin_communications_bp.route('/api/admin/communications/rules/<int:rule_id>', methods=['DELETE'])
@_admin_required_lazy
def api_communication_rules_delete(rule_id):
    import app as M
    from models.communication_rules import CommunicationRule

    rule = CommunicationRule.query.get_or_404(rule_id)
    if not _can_edit_rule(M, rule):
        return jsonify({'success': False, 'error': 'Sin permiso para eliminar esta regla'}), 403
    eid = int(rule.event_id)
    M.db.session.delete(rule)
    M.db.session.commit()
    try:
        from nodeone.services.notification_settings_sync import sync_event_rules_to_notification_settings

        sync_event_rules_to_notification_settings(eid)
    except Exception:
        pass
    return jsonify({'success': True})
