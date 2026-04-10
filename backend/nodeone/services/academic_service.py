"""Dominio académico: facturas de matrícula, activación al pagar, sync Moodle."""

from __future__ import annotations

import os
from datetime import datetime
from typing import Optional, Tuple

from nodeone.core.db import db
from nodeone.modules.accounting.models import Invoice, InvoiceLine, Tax
from nodeone.services.academic_module import is_academic_module_enabled_for_org
from nodeone.services.moodle_client import MoodleClientError, enrol_manual, ensure_moodle_user, unenrol_manual
from nodeone.services.tax_calculation import compute_line_amounts


def _student_role_id() -> int:
    try:
        return int(os.environ.get('NODEONE_MOODLE_STUDENT_ROLE_ID', '5'))
    except (TypeError, ValueError):
        return 5


def generate_invoice_for_enrollment(enrollment_id: int, organization_id: int) -> Tuple[Optional[Invoice], Optional[str]]:
    """Crea factura borrador y enlaza enrollment ↔ invoice."""
    from models import AcademicCourse, Enrollment, Student, User

    if not is_academic_module_enabled_for_org(organization_id):
        return None, 'academic_module_disabled'
    en = Enrollment.query.filter_by(id=enrollment_id, organization_id=organization_id).first()
    if not en:
        return None, 'enrollment_not_found'
    if en.invoice_id:
        inv = Invoice.query.filter_by(id=en.invoice_id, organization_id=organization_id).first()
        return inv, None if inv else 'invoice_missing'
    st = Student.query.filter_by(id=en.student_id, organization_id=organization_id).first()
    if not st:
        return None, 'student_not_found'
    course = AcademicCourse.query.filter_by(id=en.academic_course_id, organization_id=organization_id).first()
    if not course:
        return None, 'course_not_found'
    user = User.query.get(st.user_id)
    if not user:
        return None, 'user_not_found'

    from flask_login import current_user

    inv = Invoice(
        organization_id=organization_id,
        number=_next_inv_number(organization_id),
        customer_id=user.id,
        status='draft',
        origin_quotation_id=None,
        enrollment_id=en.id,
        due_date=None,
        total=0.0,
        tax_total=0.0,
        grand_total=0.0,
        created_by=getattr(current_user, 'id', None),
    )
    db.session.add(inv)
    db.session.flush()

    tax = Tax.query.filter_by(organization_id=organization_id, active=True).order_by(Tax.id.asc()).first()
    qty = 1.0
    pu = float(course.price or 0)
    ln_sub, ln_total, _ = compute_line_amounts(qty, pu, tax)
    ln = InvoiceLine(
        invoice_id=inv.id,
        product_id=None,
        description=f'Matrícula: {course.name}'[:500],
        quantity=qty,
        price_unit=pu,
        tax_id=tax.id if tax else None,
        subtotal=float(ln_sub),
        total=float(ln_total),
    )
    db.session.add(ln)
    inv.total = round(ln_sub, 2)
    inv.tax_total = round(ln_total - ln_sub, 2)
    inv.grand_total = round(ln_total, 2)

    en.invoice_id = inv.id
    if en.status in ('draft', 'pending_payment'):
        en.status = 'pending_payment'
    db.session.commit()
    return inv, None


def _next_inv_number(organization_id: int) -> str:
    cnt = Invoice.query.filter_by(organization_id=organization_id).count() + 1
    return f'INV-ACAD-{cnt:05d}'


def on_invoice_paid_hook(invoice_id: int, organization_id: int) -> None:
    """Tras marcar factura pagada: activar matrícula y sync Moodle."""
    inv = Invoice.query.filter_by(id=invoice_id, organization_id=organization_id).first()
    if not inv or not inv.enrollment_id:
        return
    if not is_academic_module_enabled_for_org(organization_id):
        return
    from models import Enrollment

    en = Enrollment.query.filter_by(id=inv.enrollment_id, organization_id=organization_id).first()
    if not en:
        return
    en.status = 'active'
    en.activated_at = datetime.utcnow()
    db.session.commit()
    sync_enrollment_to_moodle(en.id, organization_id)


def on_invoice_cancelled_hook(invoice_id: int, organization_id: int) -> None:
    """Factura cancelada (solo estados no pagados): matrícula pendiente → cancelled."""
    inv = Invoice.query.filter_by(id=invoice_id, organization_id=organization_id).first()
    if not inv or not inv.enrollment_id:
        return
    if not is_academic_module_enabled_for_org(organization_id):
        return
    from models import Enrollment

    en = Enrollment.query.filter_by(id=inv.enrollment_id, organization_id=organization_id).first()
    if not en:
        return
    if en.status == 'pending_payment':
        en.status = 'cancelled'
        en.updated_at = datetime.utcnow()
        db.session.commit()


def sync_enrollment_to_moodle(enrollment_id: int, organization_id: int) -> None:
    from models import AcademicCourse, Enrollment, MoodleConfig, Student, User

    en = Enrollment.query.filter_by(id=enrollment_id, organization_id=organization_id).first()
    if not en or en.status != 'active':
        return
    if en.moodle_sync_status == 'success':
        return

    cfg = MoodleConfig.query.filter_by(organization_id=organization_id).first()
    if not cfg or not cfg.enabled or not (cfg.base_url or '').strip() or not (cfg.token or '').strip():
        en.moodle_sync_status = 'error'
        en.moodle_error_message = 'Moodle no configurado o deshabilitado para esta organización.'
        db.session.commit()
        return

    course = AcademicCourse.query.filter_by(id=en.academic_course_id, organization_id=organization_id).first()
    st = Student.query.filter_by(id=en.student_id, organization_id=organization_id).first()
    if not course or not st or not course.moodle_course_id:
        en.moodle_sync_status = 'error'
        en.moodle_error_message = 'Falta moodle_course_id en el curso o datos de estudiante.'
        db.session.commit()
        return

    user = User.query.get(st.user_id)
    if not user or not user.email:
        en.moodle_sync_status = 'error'
        en.moodle_error_message = 'Usuario sin email.'
        db.session.commit()
        return

    base = cfg.base_url.strip()
    token = cfg.token.strip()
    try:
        muid = ensure_moodle_user(
            base,
            token,
            email=user.email,
            firstname=user.first_name or 'Estudiante',
            lastname=user.last_name or '',
        )
        enrol_manual(
            base,
            token,
            roleid=_student_role_id(),
            userid=muid,
            courseid=int(course.moodle_course_id),
        )
        en.moodle_enrol_synced_at = datetime.utcnow()
        en.moodle_sync_status = 'success'
        en.moodle_error_message = None
    except MoodleClientError as e:
        en.moodle_sync_status = 'error'
        en.moodle_error_message = str(e)[:2000]
    except Exception as e:
        en.moodle_sync_status = 'error'
        en.moodle_error_message = str(e)[:2000]
    db.session.commit()


def sync_unenroll_from_moodle(enrollment_id: int, organization_id: int) -> None:
    from models import AcademicCourse, Enrollment, MoodleConfig, Student, User

    en = Enrollment.query.filter_by(id=enrollment_id, organization_id=organization_id).first()
    if not en:
        return
    cfg = MoodleConfig.query.filter_by(organization_id=organization_id).first()
    if not cfg or not cfg.enabled:
        return
    course = AcademicCourse.query.filter_by(id=en.academic_course_id, organization_id=organization_id).first()
    st = Student.query.filter_by(id=en.student_id, organization_id=organization_id).first()
    if not course or not course.moodle_course_id or not st:
        return
    user = User.query.get(st.user_id)
    if not user:
        return
    base = cfg.base_url.strip()
    token = cfg.token.strip()
    try:
        from nodeone.services.moodle_client import get_user_by_email

        mu = get_user_by_email(base, token, user.email)
        if mu and mu.get('id'):
            unenrol_manual(base, token, userid=int(mu['id']), courseid=int(course.moodle_course_id))
    except MoodleClientError:
        pass
    en.moodle_enrol_synced_at = None
    en.moodle_sync_status = 'pending'
    db.session.commit()


def create_moodle_course_for_academic_course(course_id: int, organization_id: int, category_id: int = 1) -> Tuple[Optional[int], Optional[str]]:
    from models import AcademicCourse, MoodleConfig

    course = AcademicCourse.query.filter_by(id=course_id, organization_id=organization_id).first()
    if not course:
        return None, 'course_not_found'
    if course.moodle_course_id:
        return course.moodle_course_id, None
    cfg = MoodleConfig.query.filter_by(organization_id=organization_id).first()
    if not cfg or not cfg.enabled:
        return None, 'moodle_disabled'
    from nodeone.services.moodle_client import create_course

    try:
        cid = create_course(
            cfg.base_url.strip(),
            cfg.token.strip(),
            fullname=course.name,
            shortname=f'n1_{organization_id}_{course.id}',
            categoryid=category_id,
        )
        course.moodle_course_id = cid
        db.session.commit()
        return cid, None
    except MoodleClientError as e:
        return None, str(e)
