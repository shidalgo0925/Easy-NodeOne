# Rutas marketing: API, tracking, unsubscribe
import json
from flask import Blueprint, request, jsonify, redirect, Response, render_template_string
from flask_login import login_required, current_user

from app import db
from app import (
    MarketingSegment, MarketingTemplate, MarketingCampaign,
    CampaignRecipient, EmailQueueItem
)
from . import service

marketing_bp = Blueprint('marketing', __name__, url_prefix='/marketing')

# Pixel 1x1 transparente GIF
TRACKING_PIXEL = (
    b'GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;'
)


@marketing_bp.route('/email/open/<tracking_id>')
def email_open(tracking_id):
    service.mark_opened(tracking_id)
    return Response(TRACKING_PIXEL, mimetype='image/gif')


@marketing_bp.route('/email/click/<tracking_id>')
def email_click(tracking_id):
    service.mark_clicked(tracking_id)
    url = request.args.get('url', '')
    if url:
        return redirect(url)
    return Response('OK', status=200)


@marketing_bp.route('/unsubscribe/<int:user_id>')
def unsubscribe(user_id):
    service.unsubscribe_user(user_id)
    return render_template_string(
        '<!DOCTYPE html><html><body style="font-family:sans-serif;padding:2rem;text-align:center">'
        '<h1>Has sido removido de las campañas</h1>'
        '<p>Ya no recibirás emails de marketing.</p></body></html>'
    )


# --- API (requieren login admin o gestor; aquí simplificado login_required) ---

@marketing_bp.route('/campaign', methods=['POST'])
@login_required
def api_create_campaign():
    data = request.get_json() or {}
    name = data.get('name') or ''
    subject = data.get('subject') or ''
    template_id = data.get('template_id')
    segment_id = data.get('segment_id')
    if not name or not subject or not template_id or not segment_id:
        return jsonify({'success': False, 'error': 'Faltan name, subject, template_id, segment_id'}), 400
    try:
        c = service.create_campaign(name, subject, template_id, segment_id)
        return jsonify({'success': True, 'id': c.id})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@marketing_bp.route('/campaigns', methods=['GET'])
@login_required
def api_list_campaigns():
    campaigns = MarketingCampaign.query.order_by(MarketingCampaign.created_at.desc()).limit(100).all()
    out = []
    for c in campaigns:
        recs = CampaignRecipient.query.filter_by(campaign_id=c.id).all()
        sent = sum(1 for r in recs if r.sent_at)
        opened = sum(1 for r in recs if r.opened_at)
        clicked = sum(1 for r in recs if r.clicked_at)
        out.append({
            'id': c.id, 'name': c.name, 'subject': c.subject, 'status': c.status,
            'created_at': c.created_at.isoformat() if c.created_at else None,
            'total': len(recs), 'sent': sent,
            'open_rate': (opened / sent * 100) if sent else 0,
            'click_rate': (clicked / sent * 100) if sent else 0
        })
    return jsonify({'success': True, 'campaigns': out})


@marketing_bp.route('/campaign/<int:campaign_id>/send', methods=['POST'])
@login_required
def api_send_campaign(campaign_id):
    c, err = service.start_campaign(campaign_id)
    if err:
        return jsonify({'success': False, 'error': err}), 400
    return jsonify({'success': True, 'id': c.id})


@marketing_bp.route('/segment', methods=['POST'])
@login_required
def api_create_segment():
    data = request.get_json() or {}
    name = data.get('name') or ''
    query_rules = data.get('query_rules')
    if not name:
        return jsonify({'success': False, 'error': 'Falta name'}), 400
    try:
        rules_str = json.dumps(query_rules) if isinstance(query_rules, dict) else (query_rules or '{}')
        s = MarketingSegment(name=name, query_rules=rules_str)
        db.session.add(s)
        db.session.commit()
        return jsonify({'success': True, 'id': s.id})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@marketing_bp.route('/segments', methods=['GET'])
@login_required
def api_list_segments():
    segments = MarketingSegment.query.order_by(MarketingSegment.id).all()
    out = [{'id': s.id, 'name': s.name, 'query_rules': s.query_rules} for s in segments]
    return jsonify({'success': True, 'segments': out})


@marketing_bp.route('/segment/<int:segment_id>/count', methods=['GET'])
@login_required
def api_segment_recipient_count(segment_id):
    """Cuenta destinatarios del segmento; opcional exclusion (query param, emails separados por coma)."""
    exclusion_raw = request.args.get('exclusion', '')
    count = service.get_recipient_count(segment_id, exclusion_raw)
    return jsonify({'success': True, 'count': count})


@marketing_bp.route('/segment/preview-count', methods=['POST'])
@login_required
def api_segment_preview_count():
    """Vista previa de cuenta con reglas dinámicas (para constructor de filtros). Body: {"rules": {"logic": "and", "conditions": [...]}}."""
    data = request.get_json() or {}
    rules = data.get('rules')
    if not rules or not isinstance(rules, dict):
        return jsonify({'success': True, 'count': 0})
    users = service._get_members_with_domain(rules)
    count = len(users) if users else 0
    return jsonify({'success': True, 'count': count})


@marketing_bp.route('/template', methods=['POST'])
@login_required
def api_create_template():
    data = request.get_json() or {}
    name = data.get('name') or ''
    html = data.get('html') or ''
    variables = data.get('variables', [])
    if not name or not html:
        return jsonify({'success': False, 'error': 'Faltan name o html'}), 400
    try:
        var_str = json.dumps(variables) if isinstance(variables, list) else (variables or '[]')
        t = MarketingTemplate(name=name, html=html, variables=var_str)
        db.session.add(t)
        db.session.commit()
        return jsonify({'success': True, 'id': t.id})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@marketing_bp.route('/templates', methods=['GET'])
@login_required
def api_list_templates():
    templates = MarketingTemplate.query.order_by(MarketingTemplate.id).all()
    out = [{'id': t.id, 'name': t.name, 'variables': t.variables} for t in templates]
    return jsonify({'success': True, 'templates': out})


@marketing_bp.route('/template/<int:template_id>', methods=['GET'])
@login_required
def api_get_template(template_id):
    """Devuelve HTML y nombre de una plantilla (para el editor)."""
    t = MarketingTemplate.query.get(template_id)
    if not t:
        return jsonify({'success': False, 'error': 'No encontrada'}), 404
    return jsonify({'success': True, 'id': t.id, 'name': t.name, 'html': t.html or ''})


@marketing_bp.route('/stats', methods=['GET'])
@login_required
def api_stats():
    from sqlalchemy import func
    total_sent = db.session.query(func.count(CampaignRecipient.id)).filter(CampaignRecipient.sent_at.isnot(None)).scalar() or 0
    total_opened = db.session.query(func.count(CampaignRecipient.id)).filter(CampaignRecipient.opened_at.isnot(None)).scalar() or 0
    total_clicked = db.session.query(func.count(CampaignRecipient.id)).filter(CampaignRecipient.clicked_at.isnot(None)).scalar() or 0
    from app import User
    unsub = db.session.query(func.count(User.id)).filter(User.email_marketing_status == 'unsubscribed').scalar() or 0
    sub = db.session.query(func.count(User.id)).filter(User.email_marketing_status == 'subscribed').scalar() or 0
    return jsonify({
        'success': True,
        'emails_sent': total_sent,
        'open_rate': (total_opened / total_sent * 100) if total_sent else 0,
        'click_rate': (total_clicked / total_sent * 100) if total_sent else 0,
        'unsubscribe_count': unsub,
        'subscribed_count': sub
    })
