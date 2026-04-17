"""Admin: catálogo de servicios y categorías (CRUD páginas + API)."""

import io
import re
from datetime import datetime

from flask import Blueprint, jsonify, render_template, request, send_file
from sqlalchemy import or_

import app as M
from nodeone.modules.accounting.models import Tax

from .catalog_io import (
    EXPORT_COLUMNS,
    apply_import_rows,
    rows_from_upload,
    service_to_row,
    validate_import_rows,
)

admin_services_catalog_bp = Blueprint('admin_services_catalog', __name__)


def _coerce_default_tax_id(data, oid):
    """None = sin impuesto por defecto. Lanza ValueError si el id no existe en la org."""
    if 'default_tax_id' not in data:
        return Ellipsis
    raw = data.get('default_tax_id')
    if raw in (None, ''):
        return None
    tid = int(raw)
    if tid < 1:
        return None
    if not Tax.query.filter_by(id=tid, organization_id=oid).first():
        raise ValueError('Impuesto no válido para esta organización')
    return tid


def _admin_catalog_org_id():
    """Organización activa en sesión (selector Empresa); mismo criterio que tipos de cita admin."""
    from utils.organization import get_admin_effective_organization_id

    return int(get_admin_effective_organization_id())


@admin_services_catalog_bp.route('/admin/services')
@M.require_permission('services.view')
def admin_services():
    """Panel de administración de servicios"""
    status = request.args.get('status', 'all')
    search = request.args.get('search', '').strip()
    q = M.Service.query.filter_by(organization_id=_admin_catalog_org_id())
    if status == 'active':
        q = q.filter_by(is_active=True)
    elif status == 'inactive':
        q = q.filter_by(is_active=False)
    if search:
        like = f'%{search}%'
        q = q.filter(
            or_(M.Service.name.ilike(like), M.Service.description.ilike(like))
        )
    services = q.order_by(M.Service.display_order, M.Service.name).all()
    return render_template('admin/services.html', services=services, current_status=status, search=search)


@admin_services_catalog_bp.route('/api/admin/services/create', methods=['POST'])
@M.admin_required
def admin_services_create():
    """Crear nuevo servicio"""
    try:
        data = request.get_json()

        appointment_type_id = data.get('appointment_type_id')
        if appointment_type_id == '' or appointment_type_id is None:
            appointment_type_id = None
        else:
            appointment_type_id = int(appointment_type_id) if appointment_type_id else None
            if appointment_type_id:
                appointment_type = M.AppointmentType.query.get(appointment_type_id)
                if not appointment_type:
                    return jsonify({'success': False, 'error': 'Tipo de cita no encontrado'}), 400

        service_type = (data.get('service_type') or 'AGENDABLE').strip().upper()
        if service_type not in ('CONSULTIVO', 'AGENDABLE', 'CV_REGISTRATION'):
            service_type = 'AGENDABLE'
        if service_type == 'CV_REGISTRATION':
            appointment_type_id = None
        oid = _admin_catalog_org_id()
        try:
            dtid = _coerce_default_tax_id(data, oid)
        except ValueError as e:
            return jsonify({'success': False, 'error': str(e)}), 400
        if dtid is Ellipsis:
            dtid = None

        raw_cat = data.get('category_id')
        if raw_cat in (None, ''):
            category_id = None
        else:
            try:
                category_id = int(raw_cat)
            except (TypeError, ValueError):
                category_id = None
        if category_id:
            cat = M.ServiceCategory.query.get(category_id)
            if not cat:
                return jsonify({'success': False, 'error': 'Categoría no encontrada'}), 400

        service = M.Service(
            name=data.get('name'),
            description=data.get('description', ''),
            icon=data.get('icon', 'fas fa-cog'),
            membership_type=data.get('membership_type', 'basic'),
            category_id=category_id,
            external_link=data.get('external_link', ''),
            base_price=float(data.get('base_price', 50.0)),
            is_active=data.get('is_active', True),
            display_order=int(data.get('display_order', 0)),
            appointment_type_id=appointment_type_id,
            service_type=service_type,
            organization_id=oid,
            default_tax_id=dtid,
        )

        M.db.session.add(service)
        M.db.session.commit()

        return jsonify({'success': True, 'message': 'Servicio creado exitosamente', 'service': service.to_dict()})
    except Exception as e:
        M.db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400


@admin_services_catalog_bp.route('/api/admin/services/update/<int:service_id>', methods=['PUT'])
@M.admin_required
def admin_services_update(service_id):
    """Actualizar servicio"""
    try:
        oid = _admin_catalog_org_id()
        service = M.Service.query.filter_by(id=service_id, organization_id=oid).first()
        if service is None:
            return jsonify({'success': False, 'error': 'Servicio no encontrado'}), 404
        data = request.get_json()

        membership_plans = data.get('membership_plans', [])
        if isinstance(membership_plans, str):
            membership_plans = [membership_plans]
        elif not isinstance(membership_plans, list):
            membership_plans = [data.get('membership_type', service.membership_type)]

        if not membership_plans:
            return jsonify({'success': False, 'error': 'Debe seleccionar al menos un plan de membresía'}), 400

        try:
            membership_hierarchy = M.MembershipPlan.get_hierarchy()
        except Exception:
            membership_hierarchy = {'basic': 0, 'pro': 1, 'premium': 2, 'deluxe': 3, 'corporativo': 4}
        base_plan = min(membership_plans, key=lambda p: membership_hierarchy.get(p, 999))

        category_id = data.get('category_id')
        if category_id:
            category = M.ServiceCategory.query.get(category_id)
            if not category:
                return jsonify({'success': False, 'error': 'Categoría no encontrada'}), 400

        service.name = data.get('name', service.name)
        service.description = data.get('description', service.description)
        service.icon = data.get('icon', service.icon)
        service.membership_type = base_plan
        service.category_id = category_id if category_id else None
        service.external_link = data.get('external_link', service.external_link)
        service.base_price = float(data.get('base_price', service.base_price))
        service.is_active = data.get('is_active', service.is_active)
        service.display_order = int(data.get('display_order', service.display_order))

        service_type = (data.get('service_type') or getattr(service, 'service_type', 'AGENDABLE') or 'AGENDABLE').strip().upper()
        if service_type in ('CONSULTIVO', 'AGENDABLE', 'CV_REGISTRATION'):
            service.service_type = service_type
        if service_type == 'CV_REGISTRATION':
            service.appointment_type_id = None
            service.diagnostic_appointment_type_id = None

        if (service.service_type or '').strip().upper() != 'CV_REGISTRATION':
            appointment_type_id = data.get('appointment_type_id')
            if appointment_type_id == '' or appointment_type_id is None:
                service.appointment_type_id = None
            else:
                appointment_type_id = int(appointment_type_id) if appointment_type_id else None
                if appointment_type_id:
                    appointment_type = M.AppointmentType.query.get(appointment_type_id)
                    if not appointment_type:
                        return jsonify({'success': False, 'error': 'Tipo de cita no encontrado'}), 400
                service.appointment_type_id = appointment_type_id

        service.updated_at = datetime.utcnow()

        try:
            dtid = _coerce_default_tax_id(data, oid)
        except ValueError as e:
            return jsonify({'success': False, 'error': str(e)}), 400
        if dtid is not Ellipsis:
            service.default_tax_id = dtid

        existing_rules = {rule.membership_type: rule for rule in service.pricing_rules}

        for plan in membership_plans:
            if plan != base_plan:
                if plan in existing_rules:
                    existing_rules[plan].is_included = True
                    existing_rules[plan].is_active = True
                else:
                    rule = M.ServicePricingRule(
                        service_id=service.id,
                        membership_type=plan,
                        is_included=True,
                        is_active=True
                    )
                    M.db.session.add(rule)

        for plan, rule in existing_rules.items():
            if plan not in membership_plans:
                rule.is_active = False

        M.db.session.commit()

        return jsonify({'success': True, 'message': 'Servicio actualizado exitosamente', 'service': service.to_dict()})
    except Exception as e:
        M.db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400


@admin_services_catalog_bp.route('/api/admin/services/<int:service_id>', methods=['GET'])
@M.admin_required
def admin_services_get(service_id):
    """Obtener un servicio por ID con sus reglas de precio"""
    try:
        oid = _admin_catalog_org_id()
        service = M.Service.query.filter_by(id=service_id, organization_id=oid).first()
        if service is None:
            return jsonify({'success': False, 'error': 'Servicio no encontrado'}), 404

        service_dict = {
            'id': service.id,
            'name': service.name,
            'description': service.description or '',
            'icon': service.icon or 'fas fa-cog',
            'membership_type': service.membership_type,
            'category_id': service.category_id,
            'external_link': service.external_link or '',
            'base_price': float(service.base_price) if service.base_price else 0.0,
            'is_active': service.is_active,
            'display_order': service.display_order or 0,
            'appointment_type_id': service.appointment_type_id,
            'requires_appointment': service.requires_appointment(),
            'service_type': getattr(service, 'service_type', 'AGENDABLE') or 'AGENDABLE',
            'default_tax_id': int(getattr(service, 'default_tax_id', None) or 0) or None,
        }

        pricing_rules = M.ServicePricingRule.query.filter_by(service_id=service_id).all()
        service_dict['pricing_rules'] = [{
            'id': rule.id,
            'membership_type': rule.membership_type,
            'price': float(rule.price) if rule.price else None,
            'discount_percentage': float(rule.discount_percentage) if rule.discount_percentage else 0.0,
            'is_included': rule.is_included,
            'is_active': rule.is_active
        } for rule in pricing_rules]

        return jsonify({'success': True, 'service': service_dict})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 404


@admin_services_catalog_bp.route('/api/admin/services/delete/<int:service_id>', methods=['DELETE'])
@M.admin_required
def admin_services_delete(service_id):
    """Eliminar servicio"""
    try:
        oid = _admin_catalog_org_id()
        service = M.Service.query.filter_by(id=service_id, organization_id=oid).first()
        if service is None:
            return jsonify({'success': False, 'error': 'Servicio no encontrado'}), 404
        M.db.session.delete(service)
        M.db.session.commit()

        return jsonify({'success': True, 'message': 'Servicio eliminado exitosamente'})
    except Exception as e:
        M.db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400


@admin_services_catalog_bp.route('/admin/service-categories')
@M.admin_required
def admin_service_categories():
    """Panel de administración de categorías de servicios"""
    categories = M.ServiceCategory.query.order_by(
        M.ServiceCategory.display_order, M.ServiceCategory.name
    ).all()
    return render_template('admin/service_categories.html', categories=categories)


@admin_services_catalog_bp.route('/api/admin/service-categories/create', methods=['POST'])
@M.admin_required
def admin_service_categories_create():
    """Crear nueva categoría"""
    try:
        data = request.get_json()

        slug = data.get('slug', '').strip()
        if not slug:
            name = data.get('name', '').strip()
            slug = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')

        existing = M.ServiceCategory.query.filter_by(slug=slug).first()
        if existing:
            counter = 1
            original_slug = slug
            while existing:
                slug = f"{original_slug}-{counter}"
                existing = M.ServiceCategory.query.filter_by(slug=slug).first()
                counter += 1

        category = M.ServiceCategory(
            name=data.get('name'),
            slug=slug,
            description=data.get('description', ''),
            icon=data.get('icon', 'fas fa-folder'),
            color=data.get('color', 'primary'),
            display_order=int(data.get('display_order', 0)),
            is_active=data.get('is_active', True)
        )

        M.db.session.add(category)
        M.db.session.commit()

        return jsonify({'success': True, 'message': 'Categoría creada exitosamente', 'category': category.to_dict()})
    except Exception as e:
        M.db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400


@admin_services_catalog_bp.route('/api/admin/service-categories/update/<int:category_id>', methods=['PUT'])
@M.admin_required
def admin_service_categories_update(category_id):
    """Actualizar categoría"""
    try:
        category = M.ServiceCategory.query.get_or_404(category_id)
        data = request.get_json()

        new_slug = data.get('slug', category.slug).strip()
        if new_slug != category.slug:
            existing = M.ServiceCategory.query.filter_by(slug=new_slug).first()
            if existing and existing.id != category_id:
                return jsonify({'success': False, 'error': 'El slug ya está en uso'}), 400

        category.name = data.get('name', category.name)
        category.slug = new_slug
        category.description = data.get('description', category.description)
        category.icon = data.get('icon', category.icon)
        category.color = data.get('color', category.color)
        category.display_order = int(data.get('display_order', category.display_order))
        category.is_active = data.get('is_active', category.is_active)
        category.updated_at = datetime.utcnow()

        M.db.session.commit()

        return jsonify({'success': True, 'message': 'Categoría actualizada exitosamente', 'category': category.to_dict()})
    except Exception as e:
        M.db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400


@admin_services_catalog_bp.route('/api/admin/service-categories/<int:category_id>', methods=['GET'])
@M.admin_required
def admin_service_categories_get(category_id):
    """Obtener una categoría por ID"""
    try:
        category = M.ServiceCategory.query.get_or_404(category_id)
        return jsonify({'success': True, 'category': category.to_dict()})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 404


@admin_services_catalog_bp.route('/api/admin/service-categories/delete/<int:category_id>', methods=['DELETE'])
@M.admin_required
def admin_service_categories_delete(category_id):
    """Eliminar categoría"""
    try:
        category = M.ServiceCategory.query.get_or_404(category_id)

        if category.services:
            return jsonify({
                'success': False,
                'error': f'No se puede eliminar la categoría porque tiene {len(category.services)} servicio(s) asociado(s)'
            }), 400

        M.db.session.delete(category)
        M.db.session.commit()

        return jsonify({'success': True, 'message': 'Categoría eliminada exitosamente'})
    except Exception as e:
        M.db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400


@admin_services_catalog_bp.route('/api/admin/service-categories', methods=['GET'])
@M.admin_required
def admin_service_categories_list():
    """Listar todas las categorías activas (para selects)"""
    try:
        categories = M.ServiceCategory.query.filter_by(is_active=True).order_by(
            M.ServiceCategory.display_order, M.ServiceCategory.name
        ).all()
        return jsonify({
            'success': True,
            'categories': [cat.to_dict() for cat in categories]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


def _services_export_rows():
    oid = _admin_catalog_org_id()
    services = M.Service.query.filter_by(organization_id=oid).order_by(
        M.Service.display_order, M.Service.name
    ).all()
    return [service_to_row(s) for s in services]


@admin_services_catalog_bp.route('/api/admin/services/export.csv')
@M.require_permission('services.view')
def admin_services_export_csv():
    """Exportar catálogo de la organización activa en CSV (UTF-8 con BOM)."""
    try:
        import pandas as pd
    except ImportError:
        return jsonify({'success': False, 'error': 'pandas no disponible'}), 500
    rows = _services_export_rows()
    df = pd.DataFrame(rows, columns=EXPORT_COLUMNS)
    buf = io.BytesIO()
    buf.write(df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig'))
    buf.seek(0)
    ts = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    return send_file(
        buf,
        as_attachment=True,
        download_name=f'servicios_catalogo_{ts}.csv',
        mimetype='text/csv; charset=utf-8',
    )


@admin_services_catalog_bp.route('/api/admin/services/export.xlsx')
@M.require_permission('services.view')
def admin_services_export_xlsx():
    """Exportar catálogo en Excel (.xlsx)."""
    try:
        import pandas as pd
    except ImportError:
        return jsonify({'success': False, 'error': 'pandas no disponible'}), 500
    rows = _services_export_rows()
    df = pd.DataFrame(rows, columns=EXPORT_COLUMNS)
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='servicios')
    buf.seek(0)
    ts = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    return send_file(
        buf,
        as_attachment=True,
        download_name=f'servicios_catalogo_{ts}.xlsx',
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )


@admin_services_catalog_bp.route('/api/admin/services/import-template.csv')
@M.require_permission('services.view')
def admin_services_import_template_csv():
    """Plantilla CSV solo con cabeceras (mismas columnas que export)."""
    try:
        import pandas as pd
    except ImportError:
        return jsonify({'success': False, 'error': 'pandas no disponible'}), 500
    df = pd.DataFrame(columns=EXPORT_COLUMNS)
    buf = io.BytesIO()
    buf.write(df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig'))
    buf.seek(0)
    return send_file(
        buf,
        as_attachment=True,
        download_name='plantilla_importar_servicios.csv',
        mimetype='text/csv; charset=utf-8',
    )


@admin_services_catalog_bp.route('/api/admin/services/import', methods=['POST'])
@M.admin_required
def admin_services_import():
    """Importar servicios desde CSV o XLSX (crear / actualizar por id de la org)."""
    f = request.files.get('file')
    if not f or not (f.filename or '').strip():
        return jsonify({'success': False, 'error': 'No se recibió ningún archivo'}), 400
    rows, err = rows_from_upload(f)
    if err:
        return jsonify({'success': False, 'error': err}), 400
    if not rows:
        return jsonify({'success': False, 'error': 'El archivo no tiene filas de datos'}), 400
    oid = _admin_catalog_org_id()
    val_errors = validate_import_rows(rows, oid)
    if val_errors:
        return jsonify({
            'success': False,
            'error': 'Errores de validación',
            'details': [{'row': r, 'message': m} for r, m in val_errors],
        }), 400
    try:
        created, updated = apply_import_rows(rows, oid)
        return jsonify({
            'success': True,
            'message': f'Importación lista: {created} creado(s), {updated} actualizado(s).',
            'created': created,
            'updated': updated,
        })
    except Exception as e:
        M.db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
