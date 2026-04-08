# Lógica marketing: segmentos, campañas, plantillas, cola
import json
import random
import secrets
from datetime import datetime
from app import db
from app import (
    User, MarketingSegment, MarketingTemplate, MarketingCampaign,
    CampaignRecipient, EmailQueueItem
)
from . import repository


def _parse_rules(query_rules):
    if not query_rules:
        return {}
    try:
        return json.loads(query_rules) if isinstance(query_rules, str) else query_rules
    except Exception:
        return {}


# Lista blanca de campos permitidos en filtros (seguridad)
ALLOWED_SEGMENT_FIELDS = {
    'country', 'email', 'first_name', 'last_name', 'user_group', 'tags',
    'email_marketing_status', 'tipo_membresia'
}

# Campos filtrables en segmentos (constructor de dominios)
SEGMENT_FIELDS = [
    {'id': 'country', 'label': 'País', 'model': 'user'},
    {'id': 'email', 'label': 'Email', 'model': 'user'},
    {'id': 'first_name', 'label': 'Nombre', 'model': 'user'},
    {'id': 'last_name', 'label': 'Apellido', 'model': 'user'},
    {'id': 'user_group', 'label': 'Empresa / Grupo', 'model': 'user'},
    {'id': 'tags', 'label': 'Etiquetas', 'model': 'user'},
    {'id': 'email_marketing_status', 'label': 'Suscripción marketing', 'model': 'user'},
    {'id': 'tipo_membresia', 'label': 'Tipo de membresía', 'model': 'membership'},
]
SEGMENT_OPERATORS = [
    {'id': '=', 'label': 'es igual a'},
    {'id': '!=', 'label': 'no es igual a'},
    {'id': 'contains', 'label': 'contiene'},
    {'id': 'not_contains', 'label': 'no contiene'},
    {'id': 'is_set', 'label': 'está definido'},
    {'id': 'is_not_set', 'label': 'no está definido'},
]


def _apply_condition(q, field, op, value, User_model=User):
    """Aplica una condición al query de usuarios. q ya filtra subscribed + is_active."""
    from sqlalchemy import exists
    from app import Subscription, Membership
    val = (value or '').strip() if value is not None else ''
    if field == 'tipo_membresia':
        ex_sub = exists().where(Subscription.user_id == User_model.id, Subscription.status == 'active', Subscription.end_date >= datetime.utcnow())
        ex_mem = exists().where(Membership.user_id == User_model.id, Membership.is_active == True)
        if op in ('is_set', 'is_not_set'):
            if op == 'is_set':
                q = q.filter(db.or_(ex_sub, ex_mem))
            else:
                q = q.filter(~db.or_(ex_sub, ex_mem))
        else:
            ex_sub_t = exists().where(Subscription.user_id == User_model.id, Subscription.status == 'active', Subscription.end_date >= datetime.utcnow(), Subscription.membership_type == val)
            ex_mem_t = exists().where(Membership.user_id == User_model.id, Membership.is_active == True, Membership.membership_type == val)
            if op == '=':
                q = q.filter(db.or_(ex_sub_t, ex_mem_t))
            else:
                q = q.filter(~db.or_(ex_sub_t, ex_mem_t))
        return q
    col = getattr(User_model, field, None)
    if col is None:
        return q
    if op == '=':
        q = q.filter(col == val)
    elif op == '!=':
        q = q.filter(col != val)
    elif op == 'contains':
        q = q.filter(col.isnot(None), col.contains(val))
    elif op == 'not_contains':
        q = q.filter(db.or_(col.is_(None), ~col.contains(val)))
    elif op == 'is_set':
        q = q.filter(col.isnot(None), col != '')
    elif op == 'is_not_set':
        q = q.filter(db.or_(col.is_(None), col == ''))
    return q


def _get_members_with_domain(rules, subscribed_only=False):
    """Obtiene usuarios que cumplen rules. logic 'or' = al menos una condición; 'and' = todas. Sin condiciones = todos."""
    if not isinstance(rules, dict):
        return None
    conditions = rules.get('conditions') if 'conditions' in rules else []
    logic = (rules.get('logic') or 'and').strip().lower()
    if not conditions:
        q = User.query
        if subscribed_only:
            q = q.filter(User.is_active == True, User.email_marketing_status == 'subscribed')
        return q.distinct().all()
    if logic == 'or':
        user_ids = set()
        for c in conditions:
            field = (c.get('field') or '').strip()
            op = (c.get('op') or c.get('operator') or '=').strip()
            value = c.get('value')
            if not field or not op or field not in ALLOWED_SEGMENT_FIELDS:
                continue
            q = User.query
            if subscribed_only:
                q = q.filter(User.is_active == True, User.email_marketing_status == 'subscribed')
            q = _apply_condition(q, field, op, value)
            for u in q.distinct().all():
                user_ids.add(u.id)
        return User.query.filter(User.id.in_(user_ids)).all() if user_ids else []
    q = User.query
    if subscribed_only:
        q = q.filter(User.is_active == True, User.email_marketing_status == 'subscribed')
    for c in conditions:
        field = (c.get('field') or '').strip()
        op = (c.get('op') or c.get('operator') or '=').strip()
        value = c.get('value')
        if not field or not op or field not in ALLOWED_SEGMENT_FIELDS:
            continue
        q = _apply_condition(q, field, op, value)
    return q.distinct().all()


def get_members_from_segment(segment_id):
    """Devuelve usuarios que cumplen las reglas del segmento y email_marketing_status=subscribed."""
    seg = repository.get_segment_by_id(segment_id)
    if not seg:
        return []
    rules = _parse_rules(seg.query_rules)
    q = User.query.filter(User.email_marketing_status == 'subscribed', User.is_active == True)
    if rules.get('tipo_membresia'):
        q = q.join(User.memberships).filter(
            db.or_(
                db.and_(User.memberships.any(db.text("membership_type = :t")), False),
                False
            )
        )
        from sqlalchemy import or_
        from app import Membership, Subscription
        subq = Subscription.query.filter(
            Subscription.user_id == User.id,
            Subscription.status == 'active',
            Subscription.end_date >= datetime.utcnow(),
            Subscription.membership_type == rules['tipo_membresia']
        ).exists()
        memq = Membership.query.filter(
            Membership.user_id == User.id,
            Membership.is_active == True,
            Membership.membership_type == rules['tipo_membresia']
        ).exists()
        q = q.filter(subq | memq)
    if rules.get('pais'):
        q = q.filter(User.country == rules['pais'])
    return q.distinct().all()


def _parse_exclusion_user_ids(raw):
    """Devuelve set de user IDs a excluir desde JSON array."""
    if not raw or not str(raw).strip():
        return set()
    try:
        data = json.loads(raw) if isinstance(raw, str) else raw
        return set(int(x) for x in data if x is not None and str(x).isdigit())
    except Exception:
        return set()


def get_members_from_segment_simple(segment_id, subscribed_only=True, apply_exclusion=True):
    """Filtra por reglas. apply_exclusion=True aplica exclusion_user_ids (envío); False para listar en editor y marcar exclusiones."""
    seg = repository.get_segment_by_id(segment_id)
    if not seg:
        return []
    rules = _parse_rules(seg.query_rules)
    if isinstance(rules, dict) and 'conditions' in rules:
        users = _get_members_with_domain(rules, subscribed_only=subscribed_only) or []
    else:
        q = User.query
        if subscribed_only:
            q = q.filter(User.is_active == True, User.email_marketing_status == 'subscribed')
        if rules.get('pais'):
            q = q.filter(User.country == rules['pais'])
        users = q.all()
        if rules.get('tipo_membresia'):
            from app import Subscription, Membership
            out = []
            for u in users:
                sub = Subscription.query.filter_by(user_id=u.id, status='active').filter(
                    Subscription.end_date >= datetime.utcnow(),
                    Subscription.membership_type == rules['tipo_membresia']
                ).first()
                mem = Membership.query.filter_by(user_id=u.id, is_active=True, membership_type=rules['tipo_membresia']).first()
                if sub or mem:
                    out.append(u)
            users = out
    if apply_exclusion:
        exclusion_ids = _parse_exclusion_user_ids(getattr(seg, 'exclusion_user_ids', None))
        if exclusion_ids:
            users = [u for u in users if u.id not in exclusion_ids]
    return users


def _parse_exclusion_emails(exclusion_emails_text):
    """Devuelve set de emails en minúsculas a partir de JSON array o texto (coma/nueva línea)."""
    if not exclusion_emails_text or not (exclusion_emails_text or '').strip():
        return set()
    s = (exclusion_emails_text or '').strip()
    out = set()
    try:
        data = json.loads(s)
        if isinstance(data, list):
            for e in data:
                if isinstance(e, str) and '@' in e:
                    out.add(e.strip().lower())
        return out
    except Exception:
        pass
    for part in s.replace(',', '\n').split():
        e = part.strip()
        if e and '@' in e:
            out.add(e.lower())
    return out


def get_recipient_count(segment_id, exclusion_emails_text=None, for_editor=False):
    """Cuenta destinatarios. for_editor=True: todos los que cumplen filtros (para construir segmento); False: solo suscritos (para envío)."""
    users = get_members_from_segment_simple(segment_id, subscribed_only=not for_editor)
    exclude = _parse_exclusion_emails(exclusion_emails_text)
    if not exclude:
        return len(users)
    return sum(1 for u in users if (u.email or '').strip().lower() not in exclude)


def render_template_html(template_html, variables_json, context, base_url=None):
    """Reemplaza {{var}} con context.get(var). Incluye {{unsubscribe_url}}, {{base_url}} si hay base_url."""
    html = template_html or ''
    vars_list = []
    try:
        vars_list = json.loads(variables_json) if isinstance(variables_json, str) else (variables_json or [])
    except Exception:
        pass
    for var in vars_list:
        val = context.get(var, '')
        html = html.replace('{{' + var + '}}', str(val))
    base = (base_url or '').rstrip('/')
    if base:
        html = html.replace('{{base_url}}', base)
    if 'user_id' in context:
        unsub = base + f"/marketing/unsubscribe/{context['user_id']}" if base else ''
        html = html.replace('{{unsubscribe_url}}', unsub)
    reunion_url = (context.get('reunion_url') or context.get('meeting_url') or '').strip()
    html = html.replace('{{reunion_url}}', reunion_url).replace('{{meeting_url}}', reunion_url)
    return html


def create_campaign(name, subject, template_id, segment_id, organization_id=None):
    if organization_id is None:
        from app import get_current_organization_id
        organization_id = get_current_organization_id()
    if organization_id is None:
        raise ValueError('organization_id requerido (sesión sin organización activa)')
    c = MarketingCampaign(
        name=name,
        subject=subject,
        template_id=template_id,
        segment_id=segment_id,
        organization_id=int(organization_id),
        status='draft',
    )
    db.session.add(c)
    db.session.commit()
    return c


def start_campaign(campaign_id):
    c = repository.get_campaign_by_id(campaign_id)
    if not c or c.status not in ('draft', 'scheduled'):
        return None, 'Campaña no válida o ya enviada'
    try:
        from app import has_saas_module_enabled

        oid = int(getattr(c, 'organization_id', None) or 1)
        if not has_saas_module_enabled(oid, 'marketing_email'):
            return None, 'Módulo marketing_email desactivado para esta organización'
    except Exception:
        pass
    template = repository.get_template_by_id(c.template_id)
    if not template:
        return None, 'Plantilla no encontrada'
    users = get_members_from_segment_simple(c.segment_id)
    exclude = _parse_exclusion_emails(getattr(c, 'exclusion_emails', None))
    if exclude:
        users = [u for u in users if (u.email or '').strip().lower() not in exclude]
    c.status = 'sending'
    db.session.commit()
    base_url = None
    try:
        from flask import request
        base_url = request.host_url.rstrip('/') if request else None
    except Exception:
        pass
    body_source = (getattr(c, 'body_html', None) or '').strip()
    if not body_source:
        body_source = template.html
    subject_b = (getattr(c, 'subject_b', None) or '').strip()
    use_ab = bool(subject_b)
    for u in users:
        variant = random.choice(['A', 'B']) if use_ab else None
        subject = (subject_b if variant == 'B' else c.subject) if use_ab else c.subject
        tracking_id = secrets.token_urlsafe(24)
        rec = CampaignRecipient(
            campaign_id=c.id,
            user_id=u.id,
            tracking_id=tracking_id,
            status='pending',
            variant=variant
        )
        db.session.add(rec)
        db.session.flush()
        reunion_url = (getattr(c, 'meeting_url', None) or '').strip()
        if not reunion_url:
            reunion_url = 'https://meet.google.com/zac-wmmg-hgb'
        ctx = {
            'nombre': f"{u.first_name or ''} {u.last_name or ''}".strip() or u.email,
            'empresa': getattr(u, 'user_group', '') or '',
            'email': u.email,
            'user_id': u.id,
            'reunion_url': reunion_url,
        }
        html = render_template_html(body_source, template.variables, ctx, base_url=base_url)
        if base_url:
            html += f'<img src="{base_url}/marketing/email/open/{tracking_id}" width="1" height="1" alt="" />'
        payload = json.dumps({
            'subject': subject,
            'html': html,
            'to_email': u.email,
            'to_name': ctx['nombre'],
            'tracking_id': tracking_id,
            'recipient_id': rec.id,
            'user_id': u.id,
            'from_name': getattr(c, 'from_name', None) or None,
            'reply_to': getattr(c, 'reply_to', None) or None
        })
        eq = EmailQueueItem(
            organization_id=int(getattr(c, 'organization_id', None) or 1),
            recipient_id=rec.id,
            campaign_id=c.id,
            payload=payload,
            status='pending',
            send_after=datetime.utcnow(),
            attempts=0
        )
        db.session.add(eq)
    db.session.commit()
    c.status = 'sent'
    db.session.commit()
    return c, None


def mark_opened(tracking_id):
    rec = repository.get_recipient_by_tracking_id(tracking_id)
    if rec and not rec.opened_at:
        rec.opened_at = datetime.utcnow()
        rec.status = 'opened'
        db.session.commit()


def mark_clicked(tracking_id):
    rec = repository.get_recipient_by_tracking_id(tracking_id)
    if rec:
        rec.clicked_at = rec.clicked_at or datetime.utcnow()
        rec.status = 'clicked'
        db.session.commit()


def unsubscribe_user(user_id):
    u = User.query.get(user_id)
    if u:
        u.email_marketing_status = 'unsubscribed'
        db.session.commit()
        return True
    return False


def trigger_automation(trigger_event, user_id, base_url=None, **extra_context):
    """Encola emails de automatización para trigger_event y user_id. No bloquea si falla."""
    try:
        from app import default_organization_id

        u = User.query.get(user_id)
        if not u or getattr(u, 'email_marketing_status', 'subscribed') != 'subscribed':
            return
        oid_queue = int(getattr(u, 'organization_id', None) or default_organization_id())
        flows = repository.get_active_automation_flows_by_trigger(trigger_event)
        for flow in flows:
            template = repository.get_template_by_id(flow.template_id)
            if not template:
                continue
            ctx = {
                'nombre': f"{getattr(u, 'first_name', '') or ''} {getattr(u, 'last_name', '') or ''}".strip() or u.email,
                'empresa': getattr(u, 'user_group', '') or '',
                'email': u.email,
                'user_id': u.id,
                **extra_context
            }
            html = render_template_html(template.html, template.variables, ctx, base_url=base_url)
            subject = getattr(template, 'subject', None) or template.name or 'Notificación'
            payload = json.dumps({
                'subject': subject,
                'html': html,
                'to_email': u.email,
            })
            eq = EmailQueueItem(
                organization_id=oid_queue,
                recipient_id=None,
                campaign_id=None,
                payload=payload,
                status='pending'
            )
            db.session.add(eq)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Marketing automation trigger {trigger_event} error: {e}")
