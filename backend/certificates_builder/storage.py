"""Almacenamiento JSON de plantillas del editor. No toca BD ni certificate_routes."""
import json
import os

def _storage_dir():
    d = os.path.join(os.path.dirname(os.path.dirname(__file__)), '..', 'instance', 'certificates_builder')
    os.makedirs(d, exist_ok=True)
    return d

def _storage_path():
    return os.path.join(_storage_dir(), 'templates.json')

def _load_all():
    path = _storage_path()
    if not os.path.isfile(path):
        return []
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return []

def _save_all(items):
    with open(_storage_path(), 'w', encoding='utf-8') as f:
        json.dump(items, f, ensure_ascii=False, indent=2)

def list_templates():
    return _load_all()

def get_template(template_id):
    items = _load_all()
    for t in items:
        if t.get('id') == template_id:
            return t
    return None

def create_template(name, width=842, height=595, background='', elements=None):
    items = _load_all()
    next_id = max([t.get('id', 0) for t in items], default=0) + 1
    doc = {
        'id': next_id,
        'name': name or 'Sin nombre',
        'width': width,
        'height': height,
        'background': background or '',
        'elements': elements if elements is not None else [],
    }
    items.append(doc)
    _save_all(items)
    return doc

def update_template(template_id, **kwargs):
    items = _load_all()
    for t in items:
        if t.get('id') == template_id:
            if kwargs.get('name') is not None:
                t['name'] = kwargs['name']
            if kwargs.get('width') is not None:
                t['width'] = int(kwargs['width'])
            if kwargs.get('height') is not None:
                t['height'] = int(kwargs['height'])
            if kwargs.get('background') is not None:
                t['background'] = kwargs['background']
            if 'elements' in kwargs:
                t['elements'] = kwargs['elements'] if kwargs['elements'] is not None else []
            _save_all(items)
            return t
    return None

def delete_template(template_id):
    items = _load_all()
    new_items = [t for t in items if t.get('id') != template_id]
    if len(new_items) == len(items):
        return False
    _save_all(new_items)
    return True
