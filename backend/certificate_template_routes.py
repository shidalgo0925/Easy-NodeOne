# Módulo Plantillas de Certificados (JSON tipo Canva) - CRUD API y motor render JSON -> HTML -> PDF

import json
import io
import os
import logging
from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user

logger = logging.getLogger(__name__)

certificate_templates_bp = Blueprint('certificate_templates', __name__, url_prefix='/api')


def _tpl_admin_org_id():
    from app import _catalog_org_for_admin_catalog_routes
    return _catalog_org_for_admin_catalog_routes()


def _admin_required(f):
    from functools import wraps
    @wraps(f)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated or not getattr(current_user, 'is_admin', False):
            return jsonify({'error': 'No autorizado'}), 403
        return f(*args, **kwargs)
    return wrapped


def _get_base_url():
    from flask import request as req
    if req and req.url_root:
        return req.url_root.rstrip('/')
    return os.getenv('BASE_URL', 'https://app.easynodeone.com')


def _abs_url(base, u):
    if not u:
        return ''
    u = (u or '').strip()
    if u.startswith('http'):
        return u
    if u.startswith('/'):
        return base + u
    return base + '/' + u


_VAR_DEFAULT_FONT_SIZES = {
    'participant_name': 32,
    'document_id': 14,
    'body_text': 16,
    'program_name': 24,
}


def _normalize_text_element_styles(el: dict) -> dict:
    """Compatibilidad plantillas antiguas + nombres snake_case del editor."""
    out = dict(el)
    var_name = out.get('name') or ''
    default_fs = _VAR_DEFAULT_FONT_SIZES.get(var_name, 16)
    out['font_family'] = (out.get('font_family') or out.get('fontFamily') or 'Georgia').strip()
    try:
        out['font_size'] = int(out.get('font_size') or out.get('fontSize') or default_fs)
    except (TypeError, ValueError):
        out['font_size'] = default_fs
    out['font_weight'] = (out.get('font_weight') or out.get('fontWeight') or 'normal').strip()
    out['font_style'] = (out.get('font_style') or out.get('fontStyle') or 'normal').strip()
    out['text_decoration'] = (out.get('text_decoration') or 'none').strip()
    out['color'] = (out.get('color') or '#000000').strip()
    out['text_align'] = (out.get('text_align') or out.get('align') or 'center').strip()
    try:
        out['line_height'] = float(out.get('line_height', 1.2))
    except (TypeError, ValueError):
        out['line_height'] = 1.2
    out['locked_position'] = bool(out.get('locked_position', False))
    if out.get('width') is not None:
        try:
            out['width'] = int(out['width'])
        except (TypeError, ValueError):
            pass
    if out.get('height') is not None:
        try:
            out['height'] = int(out['height'])
        except (TypeError, ValueError):
            pass
    return out


def _text_element_css(el: dict) -> str:
    st = _normalize_text_element_styles(el)
    parts = [
        'font-size: %dpx;' % st['font_size'],
        'font-family: %s;' % st['font_family'],
        'text-align: %s;' % st['text_align'],
        'color: %s;' % st['color'],
        'line-height: %s;' % st['line_height'],
    ]
    if st['font_weight'] and st['font_weight'] != 'normal':
        parts.append('font-weight: %s;' % st['font_weight'])
    if st['font_style'] and st['font_style'] != 'normal':
        parts.append('font-style: %s;' % st['font_style'])
    if st['text_decoration'] and st['text_decoration'] != 'none':
        parts.append('text-decoration: %s;' % st['text_decoration'])
    if st.get('width'):
        parts.append('width: %dpx;' % int(st['width']))
    return ' '.join(parts)


def _background_path_from_url(url, upload_dir):
    """Si url es /static/uploads/certificates/xxx, devuelve ruta absoluta al archivo."""
    if not url or '/static/uploads/certificates/' not in url:
        return None
    name = url.split('/static/uploads/certificates/')[-1].split('?')[0].strip()
    if not name:
        return None
    path = os.path.abspath(os.path.join(upload_dir, name))
    return path if os.path.isfile(path) else None


def render_html_from_json_layout(template_model, data, base_url, qr_base64=None, upload_dir=None, use_file_urls=True):
    """
    Genera HTML a partir de template (CertificateTemplate) con json_layout y data.
    data: participant_name, program_name, hours, issue_date, certificate_code, verification_url, institution, etc.
    use_file_urls: si True (PDF/WeasyPrint) usa file:// para assets locales; si False (vista previa en navegador) solo URLs HTTP.
    """
    layout_raw = template_model.json_layout
    if not layout_raw:
        return None
    try:
        layout = json.loads(layout_raw) if isinstance(layout_raw, str) else layout_raw
    except Exception:
        return None
    canvas_cfg = layout.get('canvas') or {}
    width = canvas_cfg.get('width', 1024)
    height = canvas_cfg.get('height', 768)
    elements = layout.get('elements') or []
    bg_url = (template_model.background_image or '').strip()
    if bg_url and base_url:
        bg_url = _abs_url(base_url, bg_url)
    if use_file_urls and upload_dir and template_model.background_image and '/static/uploads/certificates/' in (template_model.background_image or ''):
        bg_path = _background_path_from_url(template_model.background_image, upload_dir)
        if bg_path:
            bg_url = 'file://' + os.path.abspath(bg_path)

    html_parts = [
        '<!DOCTYPE html><html><head><meta charset="utf-8">',
        '<style>',
        '@page { size: %dpx %dpx; margin: 0; }' % (width, height),
        '* { box-sizing: border-box; }',
        'body { margin: 0; padding: 0; font-family: "Times New Roman", serif; }',
        '.cert-canvas { position: relative; width: %dpx; height: %dpx; overflow: hidden; background-color: #ffffff;' % (width, height),
        '  background-size: cover; background-position: center; background-repeat: no-repeat;' if bg_url else '',
        ('  background-image: url(%s);' % bg_url) if bg_url else '',
        '}',
        '.cert-el { position: absolute; margin: 0; white-space: pre-wrap; }',
        '.cert-border { position: absolute; box-sizing: border-box; background: transparent; }',
        '</style></head><body><div class="cert-canvas">'
    ]
    style_attr = 'left: %spx; top: %spx;'
    for el in elements:
        el_type = (el.get('type') or 'text').lower()
        x = el.get('x', 0)
        y = el.get('y', 0)
        if el_type == 'border':
            bw = el.get('lineWidth', 2)
            color = el.get('color', '#002B5C')
            bw_px = int(bw)
            w_box = el.get('width', 100)
            h_box = el.get('height', 100)
            style = (
                style_attr % (x, y)
                + ' width: %dpx; height: %dpx; border: %dpx solid %s;'
                % (w_box, h_box, bw_px, color)
            )
            html_parts.append('<div class="cert-border" style="%s"></div>' % style)
            continue
        if el_type == 'text':
            value = el.get('value', '')
            style = style_attr % (x, y) + ' ' + _text_element_css(el)
            html_parts.append('<div class="cert-el" style="%s">%s</div>' % (style, _escape(value)))
        elif el_type == 'variable':
            name = el.get('name', '')
            value = str(data.get(name, ''))
            prefix = el.get('prefix', '') or ''
            suffix = el.get('suffix', '') or ''
            value = prefix + value + suffix
            style = style_attr % (x, y) + ' ' + _text_element_css(el)
            html_parts.append('<div class="cert-el" style="%s">%s</div>' % (style, _escape(value)))
        elif el_type == 'image':
            src = el.get('src', '')
            if src and base_url and not src.startswith('data:'):
                src = _abs_url(base_url, src)
            if use_file_urls and upload_dir and src and '/static/uploads/certificates/' in src:
                bp = _background_path_from_url(src, upload_dir)
                if bp:
                    src = 'file://' + os.path.abspath(bp)
            w = el.get('width', 100)
            h = el.get('height', 100)
            style = style_attr % (x, y) + ' width: %dpx; height: %dpx;' % (w, h)
            html_parts.append('<img class="cert-el" src="%s" alt="" style="%s" />' % (_escape_attr(src), style))
        elif el_type == 'qr':
            # QR: data viene de variable (verification_url); imagen ya generada en qr_base64
            if not qr_base64:
                continue
            size = el.get('size', 120)
            style = style_attr % (x, y) + ' width: %dpx; height: %dpx;' % (size, size)
            html_parts.append('<img class="cert-el" src="data:image/png;base64,%s" alt="QR" style="%s" />' % (qr_base64, style))
    html_parts.append('</div></body></html>')
    return '\n'.join(html_parts)


def _escape(s):
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;') if s else ''


def _escape_attr(s):
    return s.replace('&', '&amp;').replace('"', '&quot;').replace("'", '&#39;') if s else ''


def render_pdf_from_json_layout(template_model, data, base_url, qr_base64, upload_dir=None):
    """Genera PDF desde plantilla JSON. Retorna bytes del PDF o None."""
    html = render_html_from_json_layout(template_model, data, base_url, qr_base64, upload_dir)
    if not html:
        return None
    try:
        from weasyprint import HTML
        return HTML(string=html).write_pdf()
    except Exception as e1:
        logger.warning("WeasyPrint PDF (template JSON) falló: %s", e1)
    try:
        import weasyprint
        return weasyprint.HTML(string=html).write_pdf()
    except Exception as e2:
        logger.warning("WeasyPrint (alt) falló: %s", e2)
    return None


# --- CRUD API ---

def _template_to_dict(t):
    from nodeone.services.event_institutional_certificate_template import (
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
        from nodeone.services.event_institutional_certificate_template import sync_event_template_link_from_template

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

    from nodeone.services.event_institutional_certificate_template import (
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

    from nodeone.services.event_institutional_certificate_template import (
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

    from nodeone.services.event_institutional_certificate_template import (
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
    coid = _tpl_admin_org_id()
    t = CertificateTemplate.query.filter_by(id=template_id, organization_id=coid).first()
    if not t:
        return jsonify({'error': 'Plantilla no encontrada'}), 404
    db.session.delete(t)
    db.session.commit()
    return jsonify({'success': True})
