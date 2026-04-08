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
        '.cert-canvas { position: relative; width: %dpx; height: %dpx; overflow: hidden;' % (width, height),
        '  background-size: cover; background-position: center; background-repeat: no-repeat;' if bg_url else '',
        ('  background-image: url(%s);' % bg_url) if bg_url else '',
        '}',
        '.cert-el { position: absolute; margin: 0; }',
        '</style></head><body><div class="cert-canvas">'
    ]
    style_attr = 'left: %spx; top: %spx;'
    for el in elements:
        el_type = (el.get('type') or 'text').lower()
        x = el.get('x', 0)
        y = el.get('y', 0)
        if el_type == 'text':
            value = el.get('value', '')
            fs = el.get('fontSize', 24)
            ff = el.get('fontFamily', 'Times New Roman')
            align = el.get('align', 'left')
            style = style_attr % (x, y) + ' font-size: %dpx; font-family: %s; text-align: %s;' % (fs, ff, align)
            html_parts.append('<div class="cert-el" style="%s">%s</div>' % (style, _escape(value)))
        elif el_type == 'variable':
            name = el.get('name', '')
            value = str(data.get(name, ''))
            fs = el.get('fontSize', 24)
            ff = el.get('fontFamily', 'Times New Roman')
            align = el.get('align', 'left')
            style = style_attr % (x, y) + ' font-size: %dpx; font-family: %s; text-align: %s;' % (fs, ff, align)
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
    return {
        'id': t.id,
        'organization_id': getattr(t, 'organization_id', None) or 1,
        'name': t.name,
        'width': t.width or 1024,
        'height': t.height or 768,
        'background_image': t.background_image,
        'json_layout': t.json_layout,
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
        t.json_layout = json.dumps(j) if isinstance(j, dict) else (j if isinstance(j, str) else t.json_layout)
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
