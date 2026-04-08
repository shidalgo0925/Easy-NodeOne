"""Rutas del módulo certificates_builder. Prefijo /api/certificates-builder y página editor."""
import json
import os
import uuid
from flask import Blueprint, jsonify, request, render_template
from flask_login import login_required, current_user

from . import storage

def _upload_dir():
    d = os.path.join(os.path.dirname(os.path.dirname(__file__)), '..', 'static', 'uploads', 'certificates')
    os.makedirs(d, exist_ok=True)
    return d

certificates_builder_bp = Blueprint('certificates_builder', __name__, url_prefix='/api/certificates-builder')
certificates_builder_page_bp = Blueprint('certificates_builder_page', __name__)


def _cb_admin_org_id():
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


@certificates_builder_bp.route('/templates', methods=['GET'])
@login_required
@_admin_required
def list_templates():
    items = storage.list_templates()
    return jsonify({'items': items})


@certificates_builder_bp.route('/templates', methods=['POST'])
@login_required
@_admin_required
def create_template():
    data = request.get_json() or {}
    name = (data.get('name') or '').strip() or 'Sin nombre'
    doc = storage.create_template(
        name=name,
        width=int(data.get('width', 842)),
        height=int(data.get('height', 595)),
        background=data.get('background') or '',
        elements=data.get('elements'),
    )
    return jsonify({'success': True, 'item': doc}), 201


@certificates_builder_bp.route('/templates/<int:template_id>', methods=['GET'])
@login_required
@_admin_required
def get_template(template_id):
    t = storage.get_template(template_id)
    if not t:
        return jsonify({'error': 'Plantilla no encontrada'}), 404
    return jsonify({'item': t})


@certificates_builder_bp.route('/templates/<int:template_id>', methods=['PUT', 'PATCH'])
@login_required
@_admin_required
def update_template(template_id):
    data = request.get_json() or {}
    t = storage.update_template(
        template_id,
        name=data.get('name'),
        width=data.get('width'),
        height=data.get('height'),
        background=data.get('background'),
        elements=data.get('elements'),
    )
    if not t:
        return jsonify({'error': 'Plantilla no encontrada'}), 404
    return jsonify({'success': True, 'item': t})


@certificates_builder_bp.route('/upload-image', methods=['POST'])
@login_required
@_admin_required
def upload_image():
    """Sube imagen para usar en el editor (fondo o elemento). Guarda en static/uploads/certificates."""
    f = request.files.get('file') or request.files.get('image')
    if not f or not f.filename:
        return jsonify({'error': 'Falta el archivo'}), 400
    ext = (os.path.splitext(f.filename)[1] or '.png').lower()
    if ext not in ('.png', '.jpg', '.jpeg', '.gif', '.webp'):
        return jsonify({'error': 'Formato no permitido'}), 400
    name = 'builder_' + uuid.uuid4().hex[:12] + ext
    path = os.path.join(_upload_dir(), name)
    f.save(path)
    url = '/static/uploads/certificates/' + name
    return jsonify({'success': True, 'url': url})


def _builder_doc_to_certificate_template_fields(doc):
    """Convierte JSON del editor visual al formato CertificateTemplate (json_layout con canvas + elements)."""
    if not isinstance(doc, dict):
        return None
    name = (doc.get('name') or 'Sin nombre').strip()[:200] or 'Sin nombre'
    w = int(doc.get('width') or 842)
    h = int(doc.get('height') or 595)
    bg = (doc.get('background') or '').strip() or None
    raw_els = doc.get('elements') or []
    clean = []
    for el in raw_els:
        if not isinstance(el, dict):
            continue
        clean.append({k: v for k, v in el.items() if not str(k).startswith('_')})
    layout = {'canvas': {'width': w, 'height': h}, 'elements': clean}
    return name, w, h, bg, json.dumps(layout, ensure_ascii=False)


@certificates_builder_bp.route('/publish-to-engine', methods=['POST'])
@login_required
@_admin_required
def publish_to_engine():
    """
    Copia diseño del builder a CertificateTemplate (BD) para que el motor de emisión lo use.
    Body JSON:
      - document: { name, width, height, background, elements }  (lo mismo que guardás en el editor)
      - builder_template_id: opcional, si no mandás document lee del JSON del builder
      - certificate_template_id: opcional; si viene, actualiza esa fila; si no, crea una nueva
    """
    data = request.get_json() or {}
    cert_tid = data.get('certificate_template_id')
    try:
        cert_tid = int(cert_tid) if cert_tid not in (None, '') else None
    except (TypeError, ValueError):
        return jsonify({'error': 'certificate_template_id inválido'}), 400

    doc = None
    if isinstance(data.get('document'), dict):
        doc = data['document']
    elif data.get('builder_template_id') is not None:
        try:
            bid = int(data['builder_template_id'])
        except (TypeError, ValueError):
            return jsonify({'error': 'builder_template_id inválido'}), 400
        doc = storage.get_template(bid)
        if not doc:
            return jsonify({'error': 'Plantilla del builder no encontrada'}), 404
    else:
        return jsonify({'error': 'Mandá document (JSON del canvas) o builder_template_id'}), 400

    parsed = _builder_doc_to_certificate_template_fields(doc)
    if not parsed:
        return jsonify({'error': 'Documento inválido'}), 400
    name, w, h, bg, json_layout = parsed

    from app import CertificateTemplate, db

    if cert_tid is not None:
        coid = _cb_admin_org_id()
        t = CertificateTemplate.query.filter_by(id=cert_tid, organization_id=coid).first()
        if not t:
            return jsonify({'error': 'Plantilla en BD no encontrada'}), 404
        t.name = name
        t.width = w
        t.height = h
        t.background_image = bg
        t.json_layout = json_layout
        db.session.commit()
        return jsonify({'success': True, 'certificate_template_id': t.id, 'updated': True})

    t = CertificateTemplate(
        organization_id=_cb_admin_org_id(),
        name=name,
        width=w,
        height=h,
        background_image=bg,
        json_layout=json_layout,
    )
    db.session.add(t)
    db.session.commit()
    return jsonify({'success': True, 'certificate_template_id': t.id, 'updated': False}), 201


@certificates_builder_page_bp.route('/admin/certificates-builder')
@login_required
@_admin_required
def editor_page():
    """Página del editor visual. No modifica rutas existentes de certificados."""
    template_id = request.args.get('id', type=int)
    return render_template('certificates_builder/editor.html', template_id=template_id)
