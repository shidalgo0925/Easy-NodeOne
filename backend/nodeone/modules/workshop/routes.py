"""API JSON taller + registro admin HTML."""

from __future__ import annotations

import os
import re
import secrets
import uuid
from datetime import datetime

from flask import Blueprint, current_app, jsonify, render_template, request
from flask_login import current_user, login_required
from sqlalchemy import or_
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename

from sqlalchemy.exc import IntegrityError

from nodeone.core.db import db
from models.catalog import Service
from models.users import User
from nodeone.services.user_organization import ensure_membership, user_has_active_membership, user_in_org_clause
from nodeone.modules.accounting.models import Invoice, Tax
from nodeone.modules.sales.models import Quotation
from nodeone.modules.workshop.models import (
    VehicleInspectionPhoto,
    VehicleInspectionPoint,
    VehicleZone,
    WorkshopChecklistItem,
    WorkshopInspection,
    WorkshopLine,
    WorkshopOrder,
    WorkshopOrderProcessLog,
    WorkshopPhoto,
    WorkshopProcessStageConfig,
    WorkshopServiceProcessConfig,
    WorkshopVehicle,
)
from nodeone.modules.workshop import service as workshop_svc
from nodeone.modules.workshop import sla_service as workshop_sla

workshop_api_bp = Blueprint('workshop_api', __name__, url_prefix='/api/workshop')


def register_workshop_saas_default_org_link(bp):
    """
    Debe registrarse ANTES del guard SaaS del blueprint.
    Si no hay fila saas_org_module para workshop en la org actual, crea enabled=True
    (evita 403 y desbloquea API tras despliegues sin ensure_saas_catalog_full).
    No modifica vínculos existentes (respeta taller apagado explícitamente).
    """

    @bp.before_request
    def _workshop_saas_default_org_link():
        from flask_login import current_user

        if not current_user.is_authenticated:
            return None
        if getattr(current_user, 'is_admin', False):
            return None
        try:
            oid = int(_org_id())
        except Exception:
            return None
        try:
            from app import SaasModule, SaasOrgModule

            m = SaasModule.query.filter_by(code='workshop').first()
            if m is None:
                return None
            if SaasOrgModule.query.filter_by(organization_id=oid, module_id=m.id).first() is not None:
                return None
            db.session.add(SaasOrgModule(organization_id=oid, module_id=m.id, enabled=True))
            db.session.commit()
        except IntegrityError:
            try:
                db.session.rollback()
            except Exception:
                pass
        except Exception:
            try:
                db.session.rollback()
            except Exception:
                pass
        return None


# Misma lógica de tenant que enforce_saas_module_or_response (tenant_data_organization_id).
_EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+$')


def _org_id():
    from app import admin_data_scope_organization_id, default_organization_id, tenant_data_organization_id

    try:
        return int(tenant_data_organization_id())
    except Exception:
        pass
    try:
        return int(admin_data_scope_organization_id())
    except Exception:
        return int(default_organization_id())


_WORKSHOP_BODY_MAP_ZONES = (
    ('hood', 'Capó'),
    ('roof', 'Techo'),
    ('trunk', 'Maletero'),
    ('front_bumper', 'Parachoques delantero'),
    ('rear_bumper', 'Parachoques trasero'),
    ('door_left', 'Puerta izquierda'),
    ('door_right', 'Puerta derecha'),
    ('fender_left', 'Salpicadera izquierda'),
    ('fender_right', 'Salpicadera derecha'),
    ('mirror_left', 'Espejo izquierdo'),
    ('mirror_right', 'Espejo derecho'),
    # Interior (nuevo mapa cabina)
    ('dashboard', 'Tablero'),
    ('steering_wheel', 'Volante'),
    ('center_console', 'Consola central'),
    ('front_left_seat', 'Asiento delantero izquierdo'),
    ('front_right_seat', 'Asiento delantero derecho'),
    ('rear_left_seat', 'Asiento trasero izquierdo'),
    ('rear_right_seat', 'Asiento trasero derecho'),
    ('rear_center_seat', 'Asiento trasero central'),
    ('door_panel_left', 'Panel puerta izquierda'),
    ('door_panel_right', 'Panel puerta derecha'),
    ('headliner', 'Techo interior'),
    ('trunk_interior', 'Baúl interior'),
)


def _ensure_vehicle_zones_catalog():
    """Catálogo global vehicle_zones (mismos códigos que el SVG del mapa). Idempotente."""
    added = False
    for code, name in _WORKSHOP_BODY_MAP_ZONES:
        if not VehicleZone.query.filter_by(code=code).first():
            db.session.add(VehicleZone(code=code, name=name))
            added = True
    if not added:
        return
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()


def _ensure_tables():
    Tax.__table__.create(db.engine, checkfirst=True)
    Quotation.__table__.create(db.engine, checkfirst=True)
    Invoice.__table__.create(db.engine, checkfirst=True)
    VehicleZone.__table__.create(db.engine, checkfirst=True)
    WorkshopVehicle.__table__.create(db.engine, checkfirst=True)
    WorkshopOrder.__table__.create(db.engine, checkfirst=True)
    WorkshopLine.__table__.create(db.engine, checkfirst=True)
    WorkshopPhoto.__table__.create(db.engine, checkfirst=True)
    WorkshopChecklistItem.__table__.create(db.engine, checkfirst=True)
    WorkshopInspection.__table__.create(db.engine, checkfirst=True)
    VehicleInspectionPoint.__table__.create(db.engine, checkfirst=True)
    VehicleInspectionPhoto.__table__.create(db.engine, checkfirst=True)
    WorkshopProcessStageConfig.__table__.create(db.engine, checkfirst=True)
    WorkshopServiceProcessConfig.__table__.create(db.engine, checkfirst=True)
    WorkshopOrderProcessLog.__table__.create(db.engine, checkfirst=True)
    try:
        from nodeone.services.workshop_sla_schema import ensure_workshop_sla_schema

        ensure_workshop_sla_schema(db, db.engine, printfn=None)
    except Exception:
        pass
    _ensure_vehicle_zones_catalog()


def _order_query(org_id: int, oid: int):
    return WorkshopOrder.query.filter_by(id=oid, organization_id=org_id).first()


def _serialize_vehicle(v: WorkshopVehicle) -> dict:
    return {
        'id': v.id,
        'customer_id': v.customer_id,
        'plate': v.plate or '',
        'brand': v.brand or '',
        'model': v.model or '',
        'year': v.year,
        'color': v.color or '',
        'vin': v.vin or '',
        'mileage': float(v.mileage or 0),
        'nickname': v.nickname or '',
    }


def _serialize_line(ln: WorkshopLine) -> dict:
    return {
        'id': ln.id,
        'product_id': ln.product_id,
        'description': ln.description,
        'quantity': float(ln.quantity or 0),
        'price_unit': float(ln.price_unit or 0),
        'tax_id': ln.tax_id,
        'subtotal': float(ln.subtotal or 0),
        'tax_amount': float(ln.tax_amount or 0),
        'total': float(ln.total or 0),
    }


def _safe_dt_iso(dt) -> str | None:
    """Serializa fechas del taller sin tumbar la API (tipos raros / aware)."""
    if dt is None:
        return None
    try:
        if hasattr(dt, 'isoformat'):
            return dt.isoformat()
    except Exception:
        return None
    return None


def _serialize_order_lines(org_id: int, order_id: int) -> list:
    line_rows = WorkshopLine.query.filter_by(order_id=order_id).order_by(WorkshopLine.id).all()
    pids = list({ln.product_id for ln in line_rows if ln.product_id})
    svc_by_id: dict = {}
    if pids:
        for s in Service.query.filter(Service.id.in_(pids), Service.organization_id == org_id).all():
            svc_by_id[s.id] = s.name or ''
    out = []
    for ln in line_rows:
        d = _serialize_line(ln)
        d['product_name'] = svc_by_id.get(ln.product_id, '') if ln.product_id else ''
        out.append(d)
    return out


def _serialize_order(
    o: WorkshopOrder,
    vehicle: WorkshopVehicle | None = None,
    user_by_id: dict | None = None,
    *,
    include_photos: bool = False,
) -> dict:
    if vehicle is None:
        vehicle = WorkshopVehicle.query.filter_by(id=o.vehicle_id).first()
    photos_count = WorkshopPhoto.query.filter_by(order_id=o.id).count()
    pts = 0
    insp = WorkshopInspection.query.filter_by(order_id=o.id).first()
    if insp:
        pts = VehicleInspectionPoint.query.filter_by(inspection_id=insp.id).count()
    cust = None
    if o.customer_id:
        if user_by_id is not None:
            cust = user_by_id.get(o.customer_id)
        else:
            cust = User.query.filter_by(id=o.customer_id).first()
    customer_name = ''
    customer_email = ''
    if cust:
        customer_name = f'{(getattr(cust, "first_name", None) or "").strip()} {(getattr(cust, "last_name", None) or "").strip()}'.strip()
        customer_email = getattr(cust, 'email', None) or ''
    out = {
        'id': o.id,
        'code': o.code,
        'customer_id': o.customer_id,
        'customer_name': customer_name,
        'customer_email': customer_email,
        'vehicle_id': o.vehicle_id,
        'vehicle': _serialize_vehicle(vehicle) if vehicle else None,
        'status': o.status,
        'entry_date': _safe_dt_iso(o.entry_date),
        'promised_date': _safe_dt_iso(o.promised_date),
        'advisor_id': o.advisor_id,
        'notes': o.notes or '',
        'qc_notes': o.qc_notes or '',
        'total_estimated': float(o.total_estimated or 0),
        'total_final': float(o.total_final or 0),
        'quotation_id': o.quotation_id,
        'invoice_id': o.invoice_id,
        'photos_count': photos_count,
        'inspection_points_count': pts,
        'lines': _serialize_order_lines(o.organization_id, o.id),
        'sla_paused': bool(getattr(o, 'sla_paused', False)),
        'allowed_next_statuses': _allowed_next_safe(o),
    }
    out['sla'] = workshop_sla.compute_sla_payload(o)
    if include_photos:
        ph_rows = (
            WorkshopPhoto.query.filter_by(order_id=o.id).order_by(WorkshopPhoto.id.desc()).limit(80).all()
        )
        out['photos'] = [
            {
                'id': p.id,
                'url': p.url,
                'kind': p.kind or 'entrada',
                'created_at': _safe_dt_iso(p.created_at),
            }
            for p in ph_rows
        ]
    return out


def _allowed_next_safe(o: WorkshopOrder) -> list:
    try:
        return workshop_svc.allowed_next_statuses(o)
    except Exception:
        return []


def _serialize_order_loose(o: WorkshopOrder, **kwargs) -> dict:
    """Serializa orden; si falla (datos raros), devuelve payload mínimo para no tumbar GET /orders."""
    try:
        return _serialize_order(o, **kwargs)
    except Exception:
        current_app.logger.exception('workshop _serialize_order order_id=%s', getattr(o, 'id', None))
        try:
            sla = workshop_sla.compute_sla_payload(o)
        except Exception:
            sla = {
                'applicable': False,
                'state': 'gray',
                'label': 'SLA no disponible',
                'stage_key': getattr(o, 'status', None) or 'draft',
            }
        return {
            'id': o.id,
            'code': getattr(o, 'code', '') or '',
            'customer_id': getattr(o, 'customer_id', None),
            'customer_name': '',
            'customer_email': '',
            'vehicle_id': getattr(o, 'vehicle_id', None),
            'vehicle': None,
            'status': getattr(o, 'status', 'draft'),
            'entry_date': _safe_dt_iso(getattr(o, 'entry_date', None)),
            'promised_date': _safe_dt_iso(getattr(o, 'promised_date', None)),
            'advisor_id': getattr(o, 'advisor_id', None),
            'notes': '',
            'qc_notes': '',
            'total_estimated': float(getattr(o, 'total_estimated', 0) or 0),
            'total_final': float(getattr(o, 'total_final', 0) or 0),
            'quotation_id': getattr(o, 'quotation_id', None),
            'invoice_id': getattr(o, 'invoice_id', None),
            'photos_count': 0,
            'inspection_points_count': 0,
            'lines': [],
            'sla_paused': bool(getattr(o, 'sla_paused', False)),
            'sla': sla,
            'allowed_next_statuses': _allowed_next_safe(o),
        }


def _workshop_transition_user_message(err: str) -> str:
    if err == 'quotation_required':
        return 'Para pasar a Cotizado o Aprobado hace falta crear o vincular una cotización.'
    if err == 'deliver_requires_done':
        return 'Solo se puede pasar a Entregado desde el estado Terminado.'
    if err == 'invalid_status':
        return 'Estado no válido.'
    if err.startswith('transition_not_allowed:'):
        return (
            'Ese salto de estado no está permitido. Orden típico: '
            'Borrador → Inspeccionado → Cotizado → Aprobado → En proceso → Control calidad → Terminado → Entregado.'
        )
    return err


def _uploads_workshop_dir(org_id: int) -> str:
    root = os.path.join(current_app.root_path, '..', 'static', 'uploads', 'workshop', str(org_id))
    os.makedirs(root, exist_ok=True)
    return root


def _save_upload(org_id: int, storage) -> str:
    name = secure_filename(storage.filename or 'file') or 'file'
    ext = os.path.splitext(name)[1].lower() or '.bin'
    if ext not in ('.jpg', '.jpeg', '.png', '.webp', '.gif'):
        ext = '.jpg'
    new_name = f'{uuid.uuid4().hex}{ext}'
    path = os.path.join(_uploads_workshop_dir(org_id), new_name)
    storage.save(path)
    return f'/static/uploads/workshop/{org_id}/{new_name}'


def _add_inspection_point_from_payload(insp: WorkshopInspection, data: dict):
    """Añade punto + fotos URL a la sesión (sin commit). Devuelve (punto, None) o (None, código_error)."""
    zc = str(data.get('zone_code') or '').strip()
    if not zc or not VehicleZone.query.filter_by(code=zc).first():
        return None, 'invalid_zone'
    p = VehicleInspectionPoint(
        inspection_id=insp.id,
        zone_code=zc,
        damage_type=str(data.get('damage_type') or 'scratch').strip(),
        severity=str(data.get('severity') or 'low').strip(),
        notes=str(data.get('notes') or '').strip() or None,
        x_position=float(data['x_position']) if data.get('x_position') is not None else None,
        y_position=float(data['y_position']) if data.get('y_position') is not None else None,
    )
    db.session.add(p)
    db.session.flush()
    for url in data.get('photos') or []:
        if isinstance(url, str) and url.strip():
            db.session.add(VehicleInspectionPhoto(point_id=p.id, url=url.strip()))
    return p, None


def _inspection_point_bad_request(err: str):
    msg = (
        'Zona del mapa no válida o catálogo de zonas vacío. Recargue la página.'
        if err == 'invalid_zone'
        else err
    )
    return jsonify({'error': err, 'detail': msg}), 400


@workshop_api_bp.route('/zones', methods=['GET'])
@login_required
def api_zones_list():
    _ensure_tables()
    rows = VehicleZone.query.order_by(VehicleZone.code).all()
    return jsonify([{'code': z.code, 'name': z.name} for z in rows])


@workshop_api_bp.route('/customers/search', methods=['GET'])
@login_required
def api_workshop_customers_search():
    _ensure_tables()
    oid = _org_id()
    q = str(request.args.get('q') or '').strip()
    try:
        lim = int(request.args.get('limit') or 20)
    except (TypeError, ValueError):
        lim = 20
    lim = max(1, min(lim, 100))
    query = User.query.filter(user_in_org_clause(User, oid), User.is_active.is_(True))
    if q:
        like = f'%{q}%'
        conds = [
            User.email.ilike(like),
            User.first_name.ilike(like),
            User.last_name.ilike(like),
        ]
        if q.isdigit():
            try:
                conds.append(User.id == int(q))
            except (ValueError, OverflowError):
                pass
        query = query.filter(or_(*conds))
    rows = query.order_by(User.last_name.asc(), User.first_name.asc()).limit(lim).all()
    return jsonify(
        [
            {
                'id': u.id,
                'name': f'{(u.first_name or "").strip()} {(u.last_name or "").strip()}'.strip() or u.email,
                'email': u.email or '',
            }
            for u in rows
        ]
    )


@workshop_api_bp.route('/customers', methods=['POST'])
@login_required
def api_workshop_customers_create():
    _ensure_tables()
    oid = _org_id()
    data = request.get_json(silent=True) or {}
    email = (data.get('email') or '').strip().lower()
    quick = (data.get('quick_create_name') or '').strip()
    first_name = (data.get('first_name') or '').strip()
    last_name = (data.get('last_name') or '').strip()
    phone = (data.get('phone') or '').strip() or None
    if quick and not email:
        email = f'taller.{secrets.token_hex(8)}@sin-correo.invalid'
        if not first_name:
            first_name = quick[:50]
        if not last_name:
            last_name = '.'
    if not email or not _EMAIL_RE.match(email):
        return jsonify({'error': 'invalid_email', 'detail': 'Correo electrónico obligatorio y válido.'}), 400
    if not first_name:
        fn = email.split('@', 1)[0].replace('.', ' ').replace('_', ' ')
        first_name = (fn[:50] if fn else 'Cliente').strip() or 'Cliente'
    if not last_name:
        last_name = '.'
    existing = User.query.filter(db.func.lower(User.email) == email).first()
    if existing:
        if not user_has_active_membership(existing, oid):
            ensure_membership(existing.id, oid, role='user')
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
        u = User.query.filter(db.func.lower(User.email) == email).first() or existing
    else:
        pwd = secrets.token_urlsafe(24)
        u = User(
            email=email,
            first_name=first_name[:50],
            last_name=last_name[:50],
            phone=phone,
            password_hash=generate_password_hash(pwd),
            organization_id=oid,
            is_active=True,
            is_admin=False,
            is_advisor=False,
        )
        db.session.add(u)
        try:
            db.session.flush()
            ensure_membership(u.id, oid, role='user')
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            u = User.query.filter(db.func.lower(User.email) == email).first()
            if not u:
                return jsonify({'error': 'email_exists', 'detail': 'No se pudo crear ni reutilizar el correo.'}), 409
            if not user_has_active_membership(u, oid):
                ensure_membership(u.id, oid, role='user')
            db.session.commit()
    name = f'{(u.first_name or "").strip()} {(u.last_name or "").strip()}'.strip() or u.email
    return jsonify({'id': u.id, 'name': name, 'email': u.email or ''})


@workshop_api_bp.route('/products/search', methods=['GET'])
@login_required
def api_workshop_products_search():
    _ensure_tables()
    oid = _org_id()
    q = str(request.args.get('q') or '').strip()
    query = Service.query.filter_by(is_active=True, organization_id=oid)
    if q:
        like = f'%{q}%'
        conds = [Service.name.ilike(like), Service.description.ilike(like)]
        if q.isdigit():
            try:
                conds.append(Service.id == int(q))
            except (ValueError, OverflowError):
                pass
        query = query.filter(or_(*conds))
    try:
        lim = int(request.args.get('limit') or 20)
    except (TypeError, ValueError):
        lim = 20
    lim = max(1, min(lim, 500))
    rows = query.order_by(Service.name.asc()).limit(lim).all()
    return jsonify(
        [
            {
                'id': s.id,
                'name': s.name,
                'code': str(s.id),
                'description': s.description or '',
                'price_unit': float(getattr(s, 'base_price', 0.0) or 0.0),
                'default_tax_id': int(getattr(s, 'default_tax_id', None) or 0) or None,
            }
            for s in rows
        ]
    )


@workshop_api_bp.route('/orders', methods=['GET'])
@login_required
def api_orders_list():
    _ensure_tables()
    oid = _org_id()
    try:
        workshop_sla.ensure_default_process_stages(oid)
    except Exception:
        pass
    status = (request.args.get('status') or '').strip().lower()
    q = WorkshopOrder.query.filter_by(organization_id=oid)
    if status and status in workshop_svc.ORDER_STATUSES:
        q = q.filter(WorkshopOrder.status == status)
    qs = q.order_by(WorkshopOrder.id.desc()).limit(200).all()
    cids = list({q.customer_id for q in qs if q.customer_id})
    user_by_id: dict = {}
    if cids:
        for u in User.query.filter(User.id.in_(cids)).all():
            user_by_id[u.id] = u
    return jsonify([_serialize_order_loose(q, user_by_id=user_by_id) for q in qs])


@workshop_api_bp.route('/orders/<int:order_id>', methods=['GET'])
@login_required
def api_order_get(order_id: int):
    _ensure_tables()
    oid = _org_id()
    o = _order_query(oid, order_id)
    if not o:
        return jsonify({'error': 'not_found'}), 404
    return jsonify(_serialize_order_loose(o, include_photos=True))


@workshop_api_bp.route('/by-quotation/<int:quotation_id>', methods=['GET'])
@login_required
def api_workshop_bundle_by_quotation(quotation_id: int):
    """Orden de taller + inspección + checklist vinculados a una cotización (vista previa en Ventas)."""
    _ensure_tables()
    oid = _org_id()
    qrow = Quotation.query.filter_by(id=quotation_id, organization_id=oid).first()
    if not qrow:
        return jsonify({'error': 'not_found', 'user_message': 'Cotización no encontrada.'}), 404
    o = WorkshopOrder.query.filter_by(organization_id=oid, quotation_id=quotation_id).order_by(
        WorkshopOrder.id.desc()
    ).first()
    if not o:
        return jsonify({'error': 'no_workshop_order', 'user_message': 'No hay orden de taller vinculada.'}), 404

    order_payload = _serialize_order_loose(o, include_photos=True)

    insp = WorkshopInspection.query.filter_by(order_id=o.id).first()
    insp_payload: dict = {'inspection_id': None, 'notes': '', 'points': []}
    if insp:
        points = (
            VehicleInspectionPoint.query.filter_by(inspection_id=insp.id)
            .order_by(VehicleInspectionPoint.id)
            .all()
        )
        out_pts = []
        for p in points:
            photos = [
                {'id': ph.id, 'url': ph.url}
                for ph in VehicleInspectionPhoto.query.filter_by(point_id=p.id).all()
            ]
            out_pts.append(
                {
                    'id': p.id,
                    'zone_code': p.zone_code,
                    'damage_type': p.damage_type,
                    'severity': p.severity,
                    'notes': p.notes or '',
                    'photos': photos,
                }
            )
        insp_payload = {'inspection_id': insp.id, 'notes': insp.notes or '', 'points': out_pts}

    ch_rows = WorkshopChecklistItem.query.filter_by(order_id=o.id).order_by(WorkshopChecklistItem.id).all()
    checklist_items = [
        {'id': r.id, 'item': r.item, 'condition': r.condition, 'notes': r.notes or ''} for r in ch_rows
    ]

    zone_labels = {z.code: (z.name or z.code) for z in VehicleZone.query.all()}

    return jsonify(
        {
            'order': order_payload,
            'inspection': insp_payload,
            'checklist': {'items': checklist_items},
            'zone_labels': zone_labels,
        }
    )


@workshop_api_bp.route('/orders', methods=['POST'])
@login_required
def api_orders_post():
    _ensure_tables()
    org = _org_id()
    data = request.get_json() or {}
    customer_id = int(data.get('customer_id') or 0)
    if customer_id < 1:
        return jsonify({'error': 'customer_id_required'}), 400

    vdata = data.get('vehicle') or {}
    vid = int(data.get('vehicle_id') or 0)
    if vid > 0:
        veh = WorkshopVehicle.query.filter_by(id=vid, organization_id=org).first()
        if not veh:
            return jsonify({'error': 'vehicle_not_found'}), 404
        if int(veh.customer_id) != customer_id:
            return jsonify({'error': 'vehicle_customer_mismatch', 'detail': 'El vehículo pertenece a otro cliente.'}), 400
    else:
        veh = WorkshopVehicle(
            organization_id=org,
            customer_id=customer_id,
            plate=str(vdata.get('plate') or '').strip(),
            brand=str(vdata.get('brand') or '').strip(),
            model=str(vdata.get('model') or '').strip(),
            year=int(vdata['year']) if vdata.get('year') not in (None, '') else None,
            color=str(vdata.get('color') or '').strip(),
            vin=str(vdata.get('vin') or '').strip(),
            mileage=float(vdata.get('mileage') or 0),
            nickname=(str(vdata.get('nickname')).strip() or None) if vdata.get('nickname') else None,
        )
        db.session.add(veh)
        db.session.flush()

    order = WorkshopOrder(
        organization_id=org,
        code=workshop_svc.next_workshop_code(org),
        customer_id=customer_id,
        vehicle_id=veh.id,
        status='draft',
        entry_date=datetime.utcnow(),
        advisor_id=int(data['advisor_id']) if data.get('advisor_id') else None,
        notes=str(data.get('notes') or '').strip() or None,
    )
    db.session.add(order)
    db.session.flush()

    for row in data.get('lines') or []:
        ln = WorkshopLine(
            order_id=order.id,
            product_id=int(row['product_id']) if row.get('product_id') else None,
            description=str(row.get('description') or 'Servicio').strip(),
            quantity=float(row.get('quantity') or 1),
            price_unit=float(row.get('price_unit') or 0),
            tax_id=int(row['tax_id']) if row.get('tax_id') else None,
        )
        db.session.add(ln)
    workshop_svc.recompute_workshop_order_totals(order)
    try:
        workshop_sla.bootstrap_new_order(order)
    except Exception:
        pass
    for row in data.get('checklist') or []:
        if not isinstance(row, dict):
            continue
        db.session.add(
            WorkshopChecklistItem(
                order_id=order.id,
                item=str(row.get('item') or '').strip() or 'Ítem',
                condition=str(row.get('condition') or 'ok').strip(),
                notes=str(row.get('notes') or '').strip() or None,
            )
        )
    db.session.commit()
    return jsonify(_serialize_order_loose(order, include_photos=True)), 201


@workshop_api_bp.route('/orders/<int:order_id>', methods=['PATCH', 'PUT'])
@login_required
def api_order_patch(order_id: int):
    _ensure_tables()
    org = _org_id()
    o = _order_query(org, order_id)
    if not o:
        return jsonify({'error': 'not_found'}), 404
    data = request.get_json() or {}

    if 'notes' in data:
        o.notes = str(data.get('notes') or '').strip() or None
    if 'qc_notes' in data:
        o.qc_notes = str(data.get('qc_notes') or '').strip() or None
    if 'promised_date' in data:
        pd = data.get('promised_date')
        o.promised_date = (
            datetime.fromisoformat(str(pd).replace('Z', '+00:00')).replace(tzinfo=None) if pd else None
        )
    if 'advisor_id' in data:
        o.advisor_id = int(data['advisor_id']) if data.get('advisor_id') else None
    if 'invoice_id' in data:
        iid = int(data.get('invoice_id') or 0)
        if iid > 0:
            inv = Invoice.query.filter_by(id=iid, organization_id=org).first()
            if not inv:
                return jsonify({'error': 'invoice_not_found'}), 404
            o.invoice_id = iid
        else:
            o.invoice_id = None

    if 'sla_paused' in data:
        try:
            workshop_sla.apply_sla_pause(o, bool(data.get('sla_paused')))
        except Exception:
            pass

    if 'vehicle' in data and data['vehicle']:
        veh = WorkshopVehicle.query.filter_by(id=o.vehicle_id, organization_id=org).first()
        if veh:
            vd = data['vehicle']
            for fld in ('plate', 'brand', 'model', 'color', 'vin', 'nickname'):
                if fld in vd:
                    setattr(veh, fld, str(vd.get(fld) or '').strip())
            if 'year' in vd:
                veh.year = int(vd['year']) if vd.get('year') not in (None, '') else None
            if 'mileage' in vd:
                veh.mileage = float(vd.get('mileage') or 0)

    if 'lines' in data:
        WorkshopLine.query.filter_by(order_id=o.id).delete()
        for row in data.get('lines') or []:
            ln = WorkshopLine(
                order_id=o.id,
                product_id=int(row['product_id']) if row.get('product_id') else None,
                description=str(row.get('description') or 'Servicio').strip(),
                quantity=float(row.get('quantity') or 1),
                price_unit=float(row.get('price_unit') or 0),
                tax_id=int(row['tax_id']) if row.get('tax_id') else None,
            )
            db.session.add(ln)
        workshop_svc.recompute_workshop_order_totals(o)

    if 'status' in data and data.get('status'):
        err = workshop_svc.apply_transition(o, str(data['status']).strip())
        if err:
            um = _workshop_transition_user_message(err)
            return jsonify({'error': err, 'detail': um, 'user_message': um}), 400

    db.session.commit()
    return jsonify(_serialize_order_loose(o, include_photos=True))


@workshop_api_bp.route('/vehicles', methods=['POST'])
@login_required
def api_vehicle_create():
    _ensure_tables()
    org = _org_id()
    data = request.get_json() or {}
    cid = int(data.get('customer_id') or 0)
    if cid < 1:
        return jsonify({'error': 'customer_id_required'}), 400
    veh = WorkshopVehicle(
        organization_id=org,
        customer_id=cid,
        plate=str(data.get('plate') or '').strip(),
        brand=str(data.get('brand') or '').strip(),
        model=str(data.get('model') or '').strip(),
        year=int(data['year']) if data.get('year') not in (None, '') else None,
        color=str(data.get('color') or '').strip(),
        vin=str(data.get('vin') or '').strip(),
        mileage=float(data.get('mileage') or 0),
        nickname=(str(data.get('nickname')).strip() or None) if data.get('nickname') else None,
    )
    db.session.add(veh)
    db.session.commit()
    return jsonify({'id': veh.id, 'vehicle': _serialize_vehicle(veh)}), 201


@workshop_api_bp.route('/vehicles', methods=['GET'])
@login_required
def api_vehicles_search():
    _ensure_tables()
    org = _org_id()
    cid = int(request.args.get('customer_id') or 0)
    q = str(request.args.get('q') or '').strip()
    query = WorkshopVehicle.query.filter_by(organization_id=org)
    if cid > 0:
        query = query.filter_by(customer_id=cid)
    if q:
        like = f'%{q}%'
        from sqlalchemy import or_

        query = query.filter(
            or_(
                WorkshopVehicle.plate.ilike(like),
                WorkshopVehicle.brand.ilike(like),
                WorkshopVehicle.model.ilike(like),
                WorkshopVehicle.nickname.ilike(like),
            )
        )
    rows = query.order_by(WorkshopVehicle.id.desc()).limit(50).all()
    return jsonify([_serialize_vehicle(v) for v in rows])


@workshop_api_bp.route('/orders/<int:order_id>/inspection', methods=['GET'])
@login_required
def api_inspection_get(order_id: int):
    _ensure_tables()
    org = _org_id()
    o = _order_query(org, order_id)
    if not o:
        return jsonify({'error': 'not_found'}), 404
    insp = WorkshopInspection.query.filter_by(order_id=o.id).first()
    if not insp:
        return jsonify({'inspection_id': None, 'notes': '', 'points': []})
    points = VehicleInspectionPoint.query.filter_by(inspection_id=insp.id).order_by(VehicleInspectionPoint.id).all()
    out_pts = []
    for p in points:
        photos = [{'id': ph.id, 'url': ph.url} for ph in VehicleInspectionPhoto.query.filter_by(point_id=p.id).all()]
        out_pts.append(
            {
                'id': p.id,
                'zone_code': p.zone_code,
                'damage_type': p.damage_type,
                'severity': p.severity,
                'notes': p.notes or '',
                'x_position': p.x_position,
                'y_position': p.y_position,
                'photos': photos,
            }
        )
    return jsonify({'inspection_id': insp.id, 'notes': insp.notes or '', 'points': out_pts})


@workshop_api_bp.route('/orders/<int:order_id>/inspection/points', methods=['POST'])
@login_required
def api_order_inspection_point_post(order_id: int):
    """Crea la inspección si aún no existe (sin usar GET con side-effects)."""
    _ensure_tables()
    org = _org_id()
    o = _order_query(org, order_id)
    if not o:
        return jsonify({'error': 'not_found'}), 404
    if o.status in ('delivered', 'cancelled'):
        return jsonify(
            {
                'error': 'order_locked',
                'detail': 'La orden está entregada o cancelada; no se puede añadir inspección.',
            }
        ), 400
    insp = workshop_svc.get_or_create_inspection(o, getattr(current_user, 'id', None))
    data = request.get_json() or {}
    p, err = _add_inspection_point_from_payload(insp, data)
    if err:
        return _inspection_point_bad_request(err)
    db.session.commit()
    return jsonify({'id': p.id, 'inspection_id': insp.id}), 201


@workshop_api_bp.route('/orders/<int:order_id>/inspection', methods=['PATCH'])
@login_required
def api_inspection_patch(order_id: int):
    _ensure_tables()
    org = _org_id()
    o = _order_query(org, order_id)
    if not o:
        return jsonify({'error': 'not_found'}), 404
    if o.status in ('delivered', 'cancelled'):
        return jsonify({'error': 'order_locked'}), 400
    insp = workshop_svc.get_or_create_inspection(o, getattr(current_user, 'id', None))
    data = request.get_json() or {}
    if 'notes' in data:
        insp.notes = str(data.get('notes') or '').strip() or None
    db.session.commit()
    return jsonify({'ok': True})


@workshop_api_bp.route('/inspections/<int:inspection_id>/points', methods=['POST'])
@login_required
def api_inspection_point_post(inspection_id: int):
    _ensure_tables()
    org = _org_id()
    insp = WorkshopInspection.query.get(inspection_id)
    if not insp:
        return jsonify({'error': 'not_found'}), 404
    o = WorkshopOrder.query.filter_by(id=insp.order_id, organization_id=org).first()
    if not o:
        return jsonify({'error': 'forbidden'}), 403
    if o.status in ('delivered', 'cancelled'):
        return jsonify(
            {
                'error': 'order_locked',
                'detail': 'La orden está entregada o cancelada; no se puede añadir inspección.',
            }
        ), 400
    data = request.get_json() or {}
    p, err = _add_inspection_point_from_payload(insp, data)
    if err:
        return _inspection_point_bad_request(err)
    db.session.commit()
    return jsonify({'id': p.id}), 201


def _inspection_point_and_order(point_id: int):
    """Punto + orden del tenant; (None, None, resp_tuple) si error (resp_tuple = (jsonify(...), status))."""
    p = VehicleInspectionPoint.query.get(point_id)
    if not p:
        return None, None, (jsonify({'error': 'not_found'}), 404)
    insp = WorkshopInspection.query.get(p.inspection_id)
    org = _org_id()
    o = WorkshopOrder.query.filter_by(id=insp.order_id, organization_id=org).first() if insp else None
    if not o:
        return None, None, (jsonify({'error': 'forbidden'}), 403)
    return p, o, None


@workshop_api_bp.route('/inspection-points/<int:point_id>', methods=['DELETE', 'PATCH', 'PUT'])
@login_required
def api_inspection_point_item(point_id: int):
    _ensure_tables()
    p, o, err_resp = _inspection_point_and_order(point_id)
    if err_resp is not None:
        return err_resp

    if request.method == 'DELETE':
        VehicleInspectionPhoto.query.filter_by(point_id=p.id).delete()
        db.session.delete(p)
        db.session.commit()
        return jsonify({'ok': True})

    if o.status in ('delivered', 'cancelled'):
        return jsonify(
            {
                'error': 'order_locked',
                'detail': 'La orden está entregada o cancelada; no se puede editar la inspección.',
            }
        ), 400
    data = request.get_json() or {}
    if 'damage_type' in data:
        p.damage_type = str(data.get('damage_type') or 'scratch').strip() or 'scratch'
    if 'severity' in data:
        p.severity = str(data.get('severity') or 'low').strip() or 'low'
    if 'notes' in data:
        p.notes = str(data.get('notes') or '').strip() or None
    if 'zone_code' in data:
        zc = str(data.get('zone_code') or '').strip()
        if zc and VehicleZone.query.filter_by(code=zc).first():
            p.zone_code = zc
        elif zc:
            return _inspection_point_bad_request('invalid_zone')
    db.session.commit()
    return jsonify({'id': p.id, 'ok': True})


@workshop_api_bp.route('/orders/<int:order_id>/photos', methods=['POST'])
@login_required
def api_order_photos_post(order_id: int):
    _ensure_tables()
    org = _org_id()
    o = _order_query(org, order_id)
    if not o:
        return jsonify({'error': 'not_found'}), 404
    if 'file' not in request.files:
        return jsonify({'error': 'file_required'}), 400
    kind = str(request.form.get('kind') or 'entrada').strip()
    if kind not in ('entrada', 'proceso', 'salida'):
        kind = 'entrada'
    url = _save_upload(org, request.files['file'])
    ph = WorkshopPhoto(order_id=o.id, url=url, kind=kind)
    db.session.add(ph)
    db.session.commit()
    return jsonify({'url': url, 'id': ph.id}), 201


@workshop_api_bp.route('/inspection-points/<int:point_id>/photos', methods=['POST'])
@login_required
def api_point_photo_post(point_id: int):
    _ensure_tables()
    org = _org_id()
    p = VehicleInspectionPoint.query.get(point_id)
    if not p:
        return jsonify({'error': 'not_found'}), 404
    insp = WorkshopInspection.query.get(p.inspection_id)
    o = WorkshopOrder.query.filter_by(id=insp.order_id, organization_id=org).first() if insp else None
    if not o:
        return jsonify({'error': 'forbidden'}), 403
    if 'file' not in request.files:
        return jsonify({'error': 'file_required'}), 400
    url = _save_upload(org, request.files['file'])
    row = VehicleInspectionPhoto(point_id=p.id, url=url)
    db.session.add(row)
    db.session.commit()
    return jsonify({'url': url, 'id': row.id}), 201


@workshop_api_bp.route('/orders/<int:order_id>/create-quotation', methods=['POST'])
@login_required
def api_create_quotation(order_id: int):
    _ensure_tables()
    from app import has_saas_module_enabled

    org = _org_id()
    if not has_saas_module_enabled(org, 'sales'):
        return jsonify({'error': 'sales_module_required', 'detail': 'Habilita Ventas para generar cotización.'}), 403
    o = _order_query(org, order_id)
    if not o:
        return jsonify({'error': 'not_found'}), 404
    if o.status == 'cancelled':
        return jsonify({'error': 'order_cancelled'}), 400
    try:
        q = workshop_svc.create_quotation_from_workshop_order(o, getattr(current_user, 'id', None))
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    db.session.commit()
    return jsonify({'quotation_id': q.id, 'number': q.number, 'admin_url': f'/admin/sales/quotations/{q.id}'})


@workshop_api_bp.route('/orders/<int:order_id>/checklist', methods=['PUT'])
@login_required
def api_checklist_put(order_id: int):
    _ensure_tables()
    org = _org_id()
    o = _order_query(org, order_id)
    if not o:
        return jsonify({'error': 'not_found'}), 404
    data = request.get_json() or {}
    items = data.get('items')
    if not isinstance(items, list):
        return jsonify({'error': 'items_required'}), 400
    WorkshopChecklistItem.query.filter_by(order_id=o.id).delete()
    for row in items:
        db.session.add(
            WorkshopChecklistItem(
                order_id=o.id,
                item=str(row.get('item') or '').strip() or 'Ítem',
                condition=str(row.get('condition') or 'ok').strip(),
                notes=str(row.get('notes') or '').strip() or None,
            )
        )
    db.session.commit()
    return jsonify({'ok': True})


@workshop_api_bp.route('/orders/<int:order_id>/checklist', methods=['GET'])
@login_required
def api_checklist_get(order_id: int):
    _ensure_tables()
    org = _org_id()
    o = _order_query(org, order_id)
    if not o:
        return jsonify({'error': 'not_found'}), 404
    rows = WorkshopChecklistItem.query.filter_by(order_id=o.id).order_by(WorkshopChecklistItem.id).all()
    return jsonify(
        {
            'items': [
                {'id': r.id, 'item': r.item, 'condition': r.condition, 'notes': r.notes or ''} for r in rows
            ]
        }
    )


def _serialize_process_stage(r: WorkshopProcessStageConfig) -> dict:
    return {
        'id': r.id,
        'stage_key': r.stage_key,
        'stage_name': r.stage_name,
        'sequence': r.sequence,
        'expected_duration_minutes': int(r.expected_duration_minutes or 1),
        'color': r.color or '#0d6efd',
        'active': bool(r.active),
        'service_type_tag': (r.service_type_tag or '').strip(),
        'allow_skip': bool(r.allow_skip),
    }


def _serialize_service_process_row(r: WorkshopServiceProcessConfig) -> dict:
    return {
        'id': r.id,
        'service_id': r.service_id,
        'stage_key': r.stage_key,
        'expected_duration_minutes': int(r.expected_duration_minutes or 1),
    }


@workshop_api_bp.route('/sla/monitor', methods=['GET'])
@login_required
def api_sla_monitor():
    _ensure_tables()
    oid = _org_id()
    workshop_sla.ensure_default_process_stages(oid)
    orders = (
        WorkshopOrder.query.filter_by(organization_id=oid).order_by(WorkshopOrder.id.desc()).limit(400).all()
    )
    return jsonify(workshop_sla.sla_monitor_bundle(oid, orders))


@workshop_api_bp.route('/process-stages', methods=['GET'])
@login_required
def api_process_stages_list():
    _ensure_tables()
    oid = _org_id()
    workshop_sla.ensure_default_process_stages(oid)
    rows = (
        WorkshopProcessStageConfig.query.filter_by(organization_id=oid)
        .order_by(WorkshopProcessStageConfig.sequence, WorkshopProcessStageConfig.id)
        .all()
    )
    return jsonify([_serialize_process_stage(r) for r in rows])


@workshop_api_bp.route('/process-stages', methods=['PUT'])
@login_required
def api_process_stages_bulk_put():
    _ensure_tables()
    oid = _org_id()
    workshop_sla.ensure_default_process_stages(oid)
    data = request.get_json() or {}
    items = data.get('items')
    if not isinstance(items, list):
        return jsonify({'error': 'items_required'}), 400
    for it in items:
        if not isinstance(it, dict):
            continue
        sid = int(it.get('id') or 0)
        if sid < 1:
            continue
        row = WorkshopProcessStageConfig.query.filter_by(id=sid, organization_id=oid).first()
        if not row:
            continue
        if 'stage_name' in it:
            row.stage_name = str(it.get('stage_name') or '').strip() or row.stage_name
        if 'sequence' in it:
            try:
                row.sequence = int(it['sequence'])
            except (TypeError, ValueError):
                pass
        if 'expected_duration_minutes' in it:
            try:
                row.expected_duration_minutes = max(1, int(it.get('expected_duration_minutes') or 1))
            except (TypeError, ValueError):
                pass
        if 'color' in it:
            c = str(it.get('color') or '').strip()
            if c:
                row.color = c[:40]
        if 'active' in it:
            row.active = bool(it.get('active'))
        if 'allow_skip' in it:
            row.allow_skip = bool(it.get('allow_skip'))
        if 'service_type_tag' in it:
            v = str(it.get('service_type_tag') or '').strip()
            row.service_type_tag = v or None
    db.session.commit()
    rows = (
        WorkshopProcessStageConfig.query.filter_by(organization_id=oid)
        .order_by(WorkshopProcessStageConfig.sequence, WorkshopProcessStageConfig.id)
        .all()
    )
    return jsonify([_serialize_process_stage(r) for r in rows])


@workshop_api_bp.route('/process-stages/<int:stage_id>', methods=['PATCH'])
@login_required
def api_process_stage_patch(stage_id: int):
    _ensure_tables()
    oid = _org_id()
    workshop_sla.ensure_default_process_stages(oid)
    row = WorkshopProcessStageConfig.query.filter_by(id=stage_id, organization_id=oid).first()
    if not row:
        return jsonify({'error': 'not_found'}), 404
    data = request.get_json() or {}
    if 'stage_name' in data:
        row.stage_name = str(data.get('stage_name') or '').strip() or row.stage_name
    if 'sequence' in data:
        try:
            row.sequence = int(data['sequence'])
        except (TypeError, ValueError):
            pass
    if 'expected_duration_minutes' in data:
        try:
            row.expected_duration_minutes = max(1, int(data.get('expected_duration_minutes') or 1))
        except (TypeError, ValueError):
            pass
    if 'color' in data:
        c = str(data.get('color') or '').strip()
        if c:
            row.color = c[:40]
    if 'active' in data:
        row.active = bool(data.get('active'))
    if 'allow_skip' in data:
        row.allow_skip = bool(data.get('allow_skip'))
    if 'service_type_tag' in data:
        v = str(data.get('service_type_tag') or '').strip()
        row.service_type_tag = v or None
    db.session.commit()
    return jsonify(_serialize_process_stage(row))


@workshop_api_bp.route('/service-process-config', methods=['GET'])
@login_required
def api_service_process_config_get():
    _ensure_tables()
    oid = _org_id()
    try:
        sid = int(request.args.get('service_id') or 0)
    except (TypeError, ValueError):
        sid = 0
    if sid < 1:
        return jsonify({'error': 'service_id_required'}), 400
    svc = Service.query.filter_by(id=sid, organization_id=oid).first()
    if not svc:
        return jsonify({'error': 'service_not_found'}), 404
    rows = WorkshopServiceProcessConfig.query.filter_by(organization_id=oid, service_id=sid).all()
    return jsonify({'service_id': sid, 'items': [_serialize_service_process_row(r) for r in rows]})


@workshop_api_bp.route('/service-process-config', methods=['PUT'])
@login_required
def api_service_process_config_put():
    _ensure_tables()
    oid = _org_id()
    data = request.get_json() or {}
    try:
        sid = int(data.get('service_id') or 0)
    except (TypeError, ValueError):
        sid = 0
    if sid < 1:
        return jsonify({'error': 'service_id_required'}), 400
    svc = Service.query.filter_by(id=sid, organization_id=oid).first()
    if not svc:
        return jsonify({'error': 'service_not_found'}), 404
    items = data.get('items')
    if not isinstance(items, list):
        return jsonify({'error': 'items_required'}), 400
    from nodeone.modules.workshop import service as workshop_svc

    seen = set()
    for it in items:
        if not isinstance(it, dict):
            continue
        sk = str(it.get('stage_key') or '').strip()
        if not sk or sk not in workshop_svc.ORDER_STATUSES:
            continue
        key = (sid, sk)
        if key in seen:
            continue
        seen.add(key)
        raw_mins = it.get('expected_duration_minutes')
        if raw_mins is None:
            row = WorkshopServiceProcessConfig.query.filter_by(
                organization_id=oid, service_id=sid, stage_key=sk
            ).first()
            if row:
                db.session.delete(row)
            continue
        try:
            mins = max(1, int(raw_mins))
        except (TypeError, ValueError):
            continue
        row = WorkshopServiceProcessConfig.query.filter_by(
            organization_id=oid, service_id=sid, stage_key=sk
        ).first()
        if row:
            row.expected_duration_minutes = mins
        else:
            db.session.add(
                WorkshopServiceProcessConfig(
                    organization_id=oid,
                    service_id=sid,
                    stage_key=sk,
                    expected_duration_minutes=mins,
                )
            )
    db.session.commit()
    rows = WorkshopServiceProcessConfig.query.filter_by(organization_id=oid, service_id=sid).all()
    return jsonify({'service_id': sid, 'items': [_serialize_service_process_row(r) for r in rows]})


@workshop_api_bp.route('/service-process-config/<int:row_id>', methods=['DELETE'])
@login_required
def api_service_process_config_delete(row_id: int):
    _ensure_tables()
    oid = _org_id()
    row = WorkshopServiceProcessConfig.query.filter_by(id=row_id, organization_id=oid).first()
    if not row:
        return jsonify({'error': 'not_found'}), 404
    sid = row.service_id
    db.session.delete(row)
    db.session.commit()
    rows = WorkshopServiceProcessConfig.query.filter_by(organization_id=oid, service_id=sid).all()
    return jsonify({'service_id': sid, 'items': [_serialize_service_process_row(r) for r in rows]})


def register_admin_workshop_routes(app):
    if 'admin_workshop_orders' in getattr(app, 'view_functions', {}):
        return
    from flask import redirect, url_for
    from flask import flash

    from app import admin_data_scope_organization_id, admin_required, has_saas_module_enabled

    @app.route('/admin/workshop/orders')
    @admin_required
    def admin_workshop_orders():
        oid = admin_data_scope_organization_id()
        if not has_saas_module_enabled(oid, 'workshop'):
            flash('El módulo Taller no está habilitado para esta organización.', 'error')
            return redirect(url_for('dashboard'))
        return render_template('admin/workshop_orders_list.html')

    @app.route('/admin/workshop/process-config')
    @admin_required
    def admin_workshop_process_config():
        oid = admin_data_scope_organization_id()
        if not has_saas_module_enabled(oid, 'workshop'):
            flash('El módulo Taller no está habilitado para esta organización.', 'error')
            return redirect(url_for('dashboard'))
        return render_template('admin/workshop_process_config.html')

    @app.route('/admin/workshop/orders/new')
    @admin_required
    def admin_workshop_order_new():
        oid = admin_data_scope_organization_id()
        if not has_saas_module_enabled(oid, 'workshop'):
            flash('El módulo Taller no está habilitado para esta organización.', 'error')
            return redirect(url_for('dashboard'))
        from models.saas import SaasOrganization

        org_row = SaasOrganization.query.get(oid)
        workshop_org_name = (org_row.name or '').strip() if org_row else ''
        return render_template(
            'admin/workshop_order_detail.html',
            order_id=0,
            workshop_org_name=workshop_org_name,
        )

    @app.route('/admin/workshop/orders/<int:order_id>')
    @admin_required
    def admin_workshop_order_detail(order_id: int):
        oid = admin_data_scope_organization_id()
        if not has_saas_module_enabled(oid, 'workshop'):
            flash('El módulo Taller no está habilitado para esta organización.', 'error')
            return redirect(url_for('dashboard'))
        from models.saas import SaasOrganization

        org_row = SaasOrganization.query.get(oid)
        workshop_org_name = (org_row.name or '').strip() if org_row else ''
        return render_template(
            'admin/workshop_order_detail.html',
            order_id=order_id,
            workshop_org_name=workshop_org_name,
        )
