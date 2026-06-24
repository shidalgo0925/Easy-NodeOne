# Módulo Plantillas de Certificados (JSON tipo Canva) - CRUD API y motor render JSON -> HTML -> PDF

import json
import io
import os
import logging
from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user

from nodeone.core.admin_api import admin_required_json as _admin_required
from nodeone.services.certificate_http import certificate_base_url as _get_base_url
from nodeone.services.certificate_render import (
    render_html_from_json_layout,
    render_pdf_from_json_layout,
)

logger = logging.getLogger(__name__)

certificate_templates_bp = Blueprint('certificate_templates', __name__, url_prefix='/api')


def _tpl_admin_org_id():
    from app import _catalog_org_for_admin_catalog_routes
    return _catalog_org_for_admin_catalog_routes()


# --- CRUD API ---

def _template_to_dict(t):
    from nodeone.services.certificate_visual_templates import (
        event_id_from_visual_template,
        is_institutional_template,
        parse_institutional_meta,
    )

    event_id = event_id_from_visual_template(t)
    institutional = is_institutional_template(t)
    kind = 'institutional_event' if institutional else 'visual'
    edit_path = f'/admin/certificate-templates/editor/{t.id}'
    kind_label = 'Evento (visual)' if event_id else ('Institucional' if institutional else 'Visual (Canva)')
    return {
        'id': t.id,
        'organization_id': getattr(t, 'organization_id', None) or 1,
        'name': t.name,
        'kind': kind,
        'kind_label': kind_label,
        'event_id': event_id,
        'width': t.width or 1024,
        'height': t.height or 768,
        'background_image': t.background_image,
        'json_layout': t.json_layout,
        'edit_path': edit_path,
        'created_at': t.created_at.isoformat() if t.created_at else None,
        'updated_at': t.updated_at.isoformat() if t.updated_at else None,
    }


@certificate_templates_bp.route('/templates', methods=['GET'])
@login_required
@_admin_required
def list_templates():
    from app import CertificateTemplate
    coid = _tpl_admin_org_id()
    items = CertificateTemplate.query.filter_by(organization_id=coid).order_by(
        CertificateTemplate.updated_at.desc()
    ).all()
    return jsonify({'items': [_template_to_dict(t) for t in items]})


@certificate_templates_bp.route('/templates', methods=['POST'])
@login_required
@_admin_required
def create_template():
    from app import db, CertificateTemplate
    data = request.get_json() or {}
    name = data.get('name')
    if not name:
        return jsonify({'error': 'name es obligatorio'}), 400
    json_layout = data.get('json_layout')
    if isinstance(json_layout, dict):
        json_layout = json.dumps(json_layout)
    t = CertificateTemplate(
        organization_id=_tpl_admin_org_id(),
        name=name.strip(),
        width=int(data.get('width', 1024)),
        height=int(data.get('height', 768)),
        background_image=data.get('background_image') or None,
        json_layout=json_layout,
    )
    db.session.add(t)
    db.session.commit()
    return jsonify({'success': True, 'item': _template_to_dict(t)}), 201


@certificate_templates_bp.route('/templates/<int:template_id>', methods=['GET'])
@login_required
@_admin_required
def get_template(template_id):
    from app import CertificateTemplate
    coid = _tpl_admin_org_id()
    t = CertificateTemplate.query.filter_by(id=template_id, organization_id=coid).first()
    if not t:
        return jsonify({'error': 'Plantilla no encontrada'}), 404
    return jsonify({'item': _template_to_dict(t)})


@certificate_templates_bp.route('/templates/<int:template_id>/duplicate', methods=['POST'])
@login_required
@_admin_required
def duplicate_template(template_id):
    from app import db, CertificateTemplate

    coid = _tpl_admin_org_id()
    source = CertificateTemplate.query.filter_by(id=template_id, organization_id=coid).first()
    if not source:
        return jsonify({'error': 'Plantilla no encontrada'}), 404

    layout_raw = source.json_layout
    if layout_raw:
        try:
            layout = json.loads(layout_raw) if isinstance(layout_raw, str) else layout_raw
            if isinstance(layout, dict) and isinstance(layout.get('meta'), dict):
                meta = dict(layout['meta'])
                meta.pop('event_id', None)
                if meta:
                    layout['meta'] = meta
                else:
                    layout.pop('meta', None)
                layout_raw = json.dumps(layout, ensure_ascii=False)
        except Exception:
            pass

    base_name = (source.name or 'Plantilla').strip()[:180]
    copy_name = f'{base_name} (copia)'[:200]
    existing_names = {
        (n or '').strip()
        for (n,) in CertificateTemplate.query.filter_by(organization_id=coid).with_entities(CertificateTemplate.name).all()
    }
    if copy_name in existing_names:
        n = 2
        while f'{base_name} (copia {n})'[:200] in existing_names:
            n += 1
        copy_name = f'{base_name} (copia {n})'[:200]

    copy = CertificateTemplate(
        organization_id=coid,
        name=copy_name,
        width=int(source.width or 1024),
        height=int(source.height or 768),
        background_image=source.background_image,
        json_layout=layout_raw,
    )
    db.session.add(copy)
    db.session.commit()
    return jsonify({'success': True, 'item': _template_to_dict(copy)}), 201


@certificate_templates_bp.route('/templates/<int:template_id>', methods=['PUT', 'PATCH'])
@login_required
@_admin_required
def update_template(template_id):
    from app import db, CertificateTemplate
    coid = _tpl_admin_org_id()
    t = CertificateTemplate.query.filter_by(id=template_id, organization_id=coid).first()
    if not t:
        return jsonify({'error': 'Plantilla no encontrada'}), 404
    data = request.get_json() or {}
    if data.get('name') is not None:
        t.name = (data.get('name') or '').strip() or t.name
    if 'width' in data:
        t.width = int(data.get('width', 1024))
    if 'height' in data:
        t.height = int(data.get('height', 768))
    if 'background_image' in data:
        t.background_image = data.get('background_image') or None
    if 'json_layout' in data:
        j = data.get('json_layout')
        if isinstance(j, dict):
            try:
                old = json.loads(t.json_layout) if isinstance(t.json_layout, str) else (t.json_layout or {})
                if isinstance(old, dict) and old.get('meta') and 'meta' not in j:
                    j['meta'] = old['meta']
            except Exception:
                pass
            t.json_layout = json.dumps(j)
        else:
            t.json_layout = j if isinstance(j, str) else t.json_layout
    db.session.commit()
    try:
        from nodeone.services.certificate_visual_templates import sync_event_template_link_from_template

        sync_event_template_link_from_template(db, t)
        db.session.refresh(t)
    except Exception as exc:
        logger.warning('sync_event_template_link_from_template: %s', exc)
    return jsonify({'success': True, 'item': _template_to_dict(t)})


@certificate_templates_bp.route('/templates/<int:template_id>/link-event', methods=['POST'])
@login_required
@_admin_required
def link_template_to_event(template_id):
    from app import CertificateTemplate, Event, db

    from nodeone.services.certificate_visual_templates import (
        is_visual_template,
        link_visual_template_to_event,
        parse_visual_layout,
    )

    coid = _tpl_admin_org_id()
    t = CertificateTemplate.query.filter_by(id=template_id, organization_id=coid).first()
    if not t or not is_visual_template(t):
        return jsonify({'error': 'Plantilla visual no encontrada'}), 404
    data = request.get_json() or {}
    event_id = data.get('event_id')
    if not event_id:
        return jsonify({'error': 'event_id es obligatorio'}), 400
    event = Event.query.get(int(event_id))
    if not event:
        return jsonify({'error': 'Evento no encontrado'}), 404

    layout = parse_visual_layout(t.json_layout) or {'canvas': {'width': t.width, 'height': t.height}, 'elements': []}
    meta = dict(layout.get('meta') or {})
    meta['event_id'] = int(event.id)
    layout['meta'] = meta
    t.json_layout = json.dumps(layout, ensure_ascii=False)
    link_visual_template_to_event(event, int(t.id))
    db.session.commit()
    return jsonify({'success': True, 'item': _template_to_dict(t), 'event_id': int(event.id)})


@certificate_templates_bp.route('/templates/<int:template_id>/institutional-layout', methods=['GET'])
@login_required
@_admin_required
def get_institutional_layout(template_id):
    from app import CertificateTemplate, Event

    from nodeone.services.certificate_visual_templates import (
        is_institutional_template,
        layout_from_template,
        merged_layout_for_event,
        parse_institutional_meta,
    )

    coid = _tpl_admin_org_id()
    t = CertificateTemplate.query.filter_by(id=template_id, organization_id=coid).first()
    if not t or not is_institutional_template(t):
        return jsonify({'error': 'Plantilla institucional no encontrada'}), 404
    meta = parse_institutional_meta(t.json_layout) or {}
    event_id = int(meta.get('event_id') or 0)
    layout = layout_from_template(t)
    if not layout and event_id:
        event = Event.query.get(event_id)
        if event:
            layout = merged_layout_for_event(event, coid)
    return jsonify({'success': True, 'event_id': event_id, 'layout': layout})


@certificate_templates_bp.route('/templates/<int:template_id>/institutional-layout', methods=['PUT', 'PATCH'])
@login_required
@_admin_required
def update_institutional_layout(template_id):
    from app import CertificateTemplate, Event, db

    from nodeone.services.certificate_visual_templates import (
        build_institutional_json_layout,
        is_institutional_template,
        parse_institutional_meta,
        sync_layout_to_event,
    )

    coid = _tpl_admin_org_id()
    t = CertificateTemplate.query.filter_by(id=template_id, organization_id=coid).first()
    if not t or not is_institutional_template(t):
        return jsonify({'error': 'Plantilla institucional no encontrada'}), 404
    data = request.get_json() or {}
    layout = data.get('layout')
    if not isinstance(layout, dict):
        return jsonify({'error': 'layout es obligatorio (objeto JSON)'}), 400
    meta = parse_institutional_meta(t.json_layout) or {}
    event_id = int(meta.get('event_id') or 0)
    t.json_layout = build_institutional_json_layout(event_id=event_id, layout=layout)
    if event_id:
        event = Event.query.get(event_id)
        if event:
            sync_layout_to_event(event, layout)
    db.session.commit()
    return jsonify({'success': True, 'item': _template_to_dict(t)})


@certificate_templates_bp.route('/templates/<int:template_id>', methods=['DELETE'])
@login_required
@_admin_required
def delete_template(template_id):
    from app import db, CertificateTemplate
    from nodeone.services.certificate_assets import certificate_template_delete_blocked

    coid = _tpl_admin_org_id()
    t = CertificateTemplate.query.filter_by(id=template_id, organization_id=coid).first()
    if not t:
        return jsonify({'error': 'Plantilla no encontrada'}), 404
    blocked = certificate_template_delete_blocked(t)
    if blocked:
        return jsonify({'error': blocked}), 400
    db.session.delete(t)
    db.session.commit()
    return jsonify({'success': True})
