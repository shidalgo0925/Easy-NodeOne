"""API JSON taller + registro admin HTML."""

from __future__ import annotations

import os
import uuid
from datetime import datetime

from flask import Blueprint, current_app, jsonify, render_template, request
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

from nodeone.core.db import db
from models.users import User
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
    WorkshopPhoto,
    WorkshopVehicle,
)
from nodeone.modules.workshop import service as workshop_svc

workshop_api_bp = Blueprint('workshop_api', __name__, url_prefix='/api/workshop')


def _org_id():
    from app import admin_data_scope_organization_id, default_organization_id, get_current_organization_id

    oid = get_current_organization_id()
    if oid is None:
        try:
            oid = admin_data_scope_organization_id()
        except Exception:
            oid = default_organization_id()
    return int(oid)


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
        'entry_date': o.entry_date.isoformat() if o.entry_date else None,
        'promised_date': o.promised_date.isoformat() if o.promised_date else None,
        'advisor_id': o.advisor_id,
        'notes': o.notes or '',
        'qc_notes': o.qc_notes or '',
        'total_estimated': float(o.total_estimated or 0),
        'total_final': float(o.total_final or 0),
        'quotation_id': o.quotation_id,
        'invoice_id': o.invoice_id,
        'photos_count': photos_count,
        'inspection_points_count': pts,
        'lines': [_serialize_line(ln) for ln in WorkshopLine.query.filter_by(order_id=o.id).order_by(WorkshopLine.id).all()],
    }
    if include_photos:
        ph_rows = (
            WorkshopPhoto.query.filter_by(order_id=o.id).order_by(WorkshopPhoto.id.desc()).limit(80).all()
        )
        out['photos'] = [
            {
                'id': p.id,
                'url': p.url,
                'kind': p.kind or 'entrada',
                'created_at': p.created_at.isoformat() if p.created_at else None,
            }
            for p in ph_rows
        ]
    return out


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


@workshop_api_bp.route('/zones', methods=['GET'])
@login_required
def api_zones_list():
    _ensure_tables()
    rows = VehicleZone.query.order_by(VehicleZone.code).all()
    return jsonify([{'code': z.code, 'name': z.name} for z in rows])


@workshop_api_bp.route('/orders', methods=['GET'])
@login_required
def api_orders_list():
    _ensure_tables()
    oid = _org_id()
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
    return jsonify([_serialize_order(q, user_by_id=user_by_id) for q in qs])


@workshop_api_bp.route('/orders/<int:order_id>', methods=['GET'])
@login_required
def api_order_get(order_id: int):
    _ensure_tables()
    oid = _org_id()
    o = _order_query(oid, order_id)
    if not o:
        return jsonify({'error': 'not_found'}), 404
    return jsonify(_serialize_order(o, include_photos=True))


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
    return jsonify(_serialize_order(order, include_photos=True)), 201


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
            return jsonify({'error': err, 'detail': err}), 400

    db.session.commit()
    return jsonify(_serialize_order(o, include_photos=True))


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
        return jsonify({'error': 'order_locked'}), 400
    insp = workshop_svc.get_or_create_inspection(o, getattr(current_user, 'id', None))
    data = request.get_json() or {}
    p, err = _add_inspection_point_from_payload(insp, data)
    if err:
        return jsonify({'error': err}), 400
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
        return jsonify({'error': 'order_locked'}), 400
    data = request.get_json() or {}
    p, err = _add_inspection_point_from_payload(insp, data)
    if err:
        return jsonify({'error': err}), 400
    db.session.commit()
    return jsonify({'id': p.id}), 201


@workshop_api_bp.route('/inspection-points/<int:point_id>', methods=['DELETE'])
@login_required
def api_inspection_point_delete(point_id: int):
    _ensure_tables()
    org = _org_id()
    p = VehicleInspectionPoint.query.get(point_id)
    if not p:
        return jsonify({'error': 'not_found'}), 404
    insp = WorkshopInspection.query.get(p.inspection_id)
    o = WorkshopOrder.query.filter_by(id=insp.order_id, organization_id=org).first() if insp else None
    if not o:
        return jsonify({'error': 'forbidden'}), 403
    VehicleInspectionPhoto.query.filter_by(point_id=p.id).delete()
    db.session.delete(p)
    db.session.commit()
    return jsonify({'ok': True})


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

    @app.route('/admin/workshop/orders/new')
    @admin_required
    def admin_workshop_order_new():
        oid = admin_data_scope_organization_id()
        if not has_saas_module_enabled(oid, 'workshop'):
            flash('El módulo Taller no está habilitado para esta organización.', 'error')
            return redirect(url_for('dashboard'))
        return render_template('admin/workshop_order_detail.html', order_id=0)

    @app.route('/admin/workshop/orders/<int:order_id>')
    @admin_required
    def admin_workshop_order_detail(order_id: int):
        oid = admin_data_scope_organization_id()
        if not has_saas_module_enabled(oid, 'workshop'):
            flash('El módulo Taller no está habilitado para esta organización.', 'error')
            return redirect(url_for('dashboard'))
        return render_template('admin/workshop_order_detail.html', order_id=order_id)
