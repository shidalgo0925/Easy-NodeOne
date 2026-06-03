"""Rutas HTML admin — Contactos."""

from __future__ import annotations

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from models.saas import SaasOrganization
from nodeone.core.db import db
from nodeone.modules.contacts import service as contact_svc
from nodeone.modules.contacts.photo_upload import save_contact_photo
from nodeone.services.contacts_module import is_contacts_enabled_for_org, is_contacts_globally_allowed
contacts_admin_bp = Blueprint('contacts_admin', __name__, url_prefix='/admin/contacts')


def _org_id() -> int:
    from app import admin_data_scope_organization_id, default_organization_id

    try:
        oid = int(admin_data_scope_organization_id())
    except Exception:
        oid = int(default_organization_id())
    if SaasOrganization.query.get(int(oid)) is None:
        return int(default_organization_id())
    return int(oid)


def _platform_admin() -> bool:
    return bool(current_user.is_authenticated and getattr(current_user, 'is_admin', False))


def _can_admin() -> bool:
    if not current_user.is_authenticated:
        return False
    if _platform_admin():
        return True
    from app import _user_has_any_admin_permission

    return bool(_user_has_any_admin_permission(current_user))


def _guard_module():
    if not is_contacts_globally_allowed():
        from flask import abort

        abort(404)
    if not _can_admin():
        flash('No tenés permisos de administración.', 'error')
        return redirect(url_for('dashboard'))
    if not is_contacts_enabled_for_org(_org_id()):
        flash('El módulo Contactos no está habilitado para esta organización.', 'error')
        return redirect(url_for('dashboard'))
    return None


@contacts_admin_bp.before_request
def _contacts_admin_before():
    if not current_user.is_authenticated:
        return redirect(url_for('auth.login', next=request.path))
    err = _guard_module()
    if err:
        return err


def _form_bool(name: str) -> bool:
    return request.form.get(name) in ('1', 'on', 'true', 'yes')


def _form_to_dict() -> dict:
    return {
        'contact_type': request.form.get('contact_type'),
        'display_name': request.form.get('display_name'),
        'first_name': request.form.get('first_name'),
        'last_name': request.form.get('last_name'),
        'company_name': request.form.get('company_name'),
        'commercial_name': request.form.get('commercial_name'),
        'email': request.form.get('email'),
        'phone': request.form.get('phone'),
        'mobile': request.form.get('mobile'),
        'country': request.form.get('country'),
        'province': request.form.get('province'),
        'district': request.form.get('district'),
        'township': request.form.get('township'),
        'fiscal_address': request.form.get('fiscal_address'),
        'identification_type': request.form.get('identification_type'),
        'tax_id': request.form.get('tax_id'),
        'dv': request.form.get('dv'),
        'is_customer': _form_bool('is_customer'),
        'is_supplier': _form_bool('is_supplier'),
        'is_member': _form_bool('is_member'),
        'is_student': _form_bool('is_student'),
        'is_participant': _form_bool('is_participant'),
        'is_instructor': _form_bool('is_instructor'),
        'is_donor': _form_bool('is_donor'),
        'is_employee': _form_bool('is_employee'),
        'is_tax_exempt': _form_bool('is_tax_exempt'),
        'active': _form_bool('active') if 'active' in request.form else True,
    }


def _apply_contact_photo(organization_id: int, contact) -> None:
    if _form_bool('remove_photo'):
        contact.image_url = None
        return
    file_storage = request.files.get('photo')
    if not file_storage or not (file_storage.filename or '').strip():
        return
    contact.image_url = save_contact_photo(organization_id, file_storage)


@contacts_admin_bp.route('/')
@login_required
def contacts_index():
    oid = _org_id()
    q = (request.args.get('q') or '').strip()
    role = (request.args.get('role') or '').strip()
    ctype = (request.args.get('contact_type') or '').strip()
    active = request.args.get('active', '1')
    active_only = True if active == '1' else False if active == '0' else None
    page = max(1, int(request.args.get('page', 1)))
    per_page = 50
    rows, total = contact_svc.search_contacts(
        oid,
        q=q,
        role=role,
        active_only=active_only,
        contact_type=ctype,
        limit=per_page,
        offset=(page - 1) * per_page,
    )
    return render_template(
        'contacts/list.html',
        contacts=rows,
        total=total,
        page=page,
        per_page=per_page,
        q=q,
        role=role,
        contact_type=ctype,
        active=active,
    )


@contacts_admin_bp.route('/nuevo', methods=['GET', 'POST'])
@login_required
def contacts_new():
    oid = _org_id()
    if request.method == 'POST':
        try:
            row = contact_svc.create_contact(oid, _form_to_dict())
            try:
                _apply_contact_photo(oid, row)
            except ValueError as exc:
                flash(str(exc), 'warning')
            db.session.commit()
            flash('Contacto creado.', 'success')
            return redirect(url_for('contacts_admin.contacts_edit', contact_id=row.id))
        except contact_svc.ContactValidationError as exc:
            db.session.rollback()
            flash(str(exc), 'error')
        except Exception as exc:
            db.session.rollback()
            flash(str(exc), 'error')
    return render_template('contacts/form.html', contact=None, title='Nuevo contacto')


@contacts_admin_bp.route('/<int:contact_id>')
@login_required
def contacts_detail(contact_id: int):
    oid = _org_id()
    row = contact_svc.get_contact(oid, contact_id)
    if not row:
        flash('Contacto no encontrado.', 'error')
        return redirect(url_for('contacts_admin.contacts_index'))
    return render_template('contacts/detail.html', contact=row)


@contacts_admin_bp.route('/<int:contact_id>/editar', methods=['GET', 'POST'])
@login_required
def contacts_edit(contact_id: int):
    oid = _org_id()
    row = contact_svc.get_contact(oid, contact_id)
    if not row:
        flash('Contacto no encontrado.', 'error')
        return redirect(url_for('contacts_admin.contacts_index'))
    if request.method == 'POST':
        try:
            contact_svc.update_contact(oid, contact_id, _form_to_dict())
            try:
                _apply_contact_photo(oid, row)
            except ValueError as exc:
                flash(str(exc), 'warning')
            db.session.commit()
            flash('Contacto actualizado.', 'success')
            return redirect(url_for('contacts_admin.contacts_edit', contact_id=row.id))
        except contact_svc.ContactValidationError as exc:
            db.session.rollback()
            flash(str(exc), 'error')
        except Exception as exc:
            db.session.rollback()
            flash(str(exc), 'error')
    return render_template('contacts/form.html', contact=row, title=f'Editar contacto #{row.id}')


@contacts_admin_bp.route('/<int:contact_id>/desactivar', methods=['POST'])
@login_required
def contacts_deactivate(contact_id: int):
    oid = _org_id()
    row = contact_svc.get_contact(oid, contact_id)
    if not row:
        flash('Contacto no encontrado.', 'error')
    else:
        row.active = False
        db.session.commit()
        flash('Contacto desactivado.', 'success')
    return redirect(url_for('contacts_admin.contacts_detail', contact_id=contact_id))
