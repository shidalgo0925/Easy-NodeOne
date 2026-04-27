"""Listado mínimo de programas académicos (admin)."""
from flask import Blueprint, render_template, abort
from flask_login import current_user, login_required

from app import admin_required, default_organization_id

academic_enrollment_admin_bp = Blueprint(
    'academic_enrollment_admin', __name__, url_prefix='/admin/academic-enrollment'
)


@academic_enrollment_admin_bp.route('/programs')
@login_required
@admin_required
def list_programs():
    from app import AcademicProgram, admin_data_scope_organization_id

    try:
        oid = int(admin_data_scope_organization_id())
    except Exception:
        oid = int(default_organization_id())
    programs = (
        AcademicProgram.query.filter_by(organization_id=oid)
        .order_by(AcademicProgram.name)
        .all()
    )
    return render_template('admin/academic_programs_list.html', programs=programs, organization_id=oid)
