"""Admin + API ERP educativo. Modular: requiere módulo SaaS `academic` + env."""

from __future__ import annotations

from datetime import datetime

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from werkzeug.security import generate_password_hash

from nodeone.core.db import db
from nodeone.services.academic_module import is_academic_module_enabled_for_org
from nodeone.services.academic_schema import ensure_academic_schema
from nodeone.services.academic_service import (
    create_moodle_course_for_academic_course,
    generate_invoice_for_enrollment,
    sync_enrollment_to_moodle,
)

academic_admin_bp = Blueprint('academic_admin', __name__, url_prefix='/admin/academic')
academic_api_bp = Blueprint('academic_api', __name__, url_prefix='/api/admin/academic')


def _oid():
    from app import admin_data_scope_organization_id, default_organization_id, get_current_organization_id

    oid = get_current_organization_id()
    if oid is None:
        try:
            oid = admin_data_scope_organization_id()
        except Exception:
            oid = default_organization_id()
    return int(oid)


def _guard_html():
    oid = _oid()
    if not is_academic_module_enabled_for_org(oid):
        flash('El módulo Educación / LMS no está habilitado para esta organización.', 'error')
        return redirect(url_for('dashboard'))
    return None


def _guard_json():
    if not getattr(current_user, 'is_authenticated', False):
        return jsonify({'success': False, 'error': 'unauthorized'}), 401
    oid = _oid()
    if not is_academic_module_enabled_for_org(oid):
        return jsonify({'success': False, 'error': 'academic_module_disabled'}), 404
    if getattr(current_user, 'is_admin', False):
        return None
    from app import _user_has_any_admin_permission

    if not _user_has_any_admin_permission(current_user):
        return jsonify({'success': False, 'error': 'forbidden'}), 403
    if hasattr(current_user, 'has_permission') and not (
        current_user.has_permission('users.view')
        or current_user.has_permission('academic.students.manage')
    ):
        return jsonify({'success': False, 'error': 'forbidden'}), 403
    return None


@academic_admin_bp.before_request
def _academic_admin_before():
    if not getattr(current_user, 'is_authenticated', False):
        return redirect(url_for('auth.login', next=request.path))
    from app import _user_has_any_admin_permission

    if not current_user.is_admin and not _user_has_any_admin_permission(current_user):
        flash('No tienes permisos.', 'error')
        return redirect(url_for('dashboard'))
    err = _guard_html()
    if err:
        return err
    try:
        ensure_academic_schema(db, db.engine)
    except Exception:
        pass


@academic_api_bp.before_request
def _academic_api_before():
    g = _guard_json()
    if g is not None:
        return g
    try:
        ensure_academic_schema(db, db.engine)
    except Exception:
        pass


# --- HTML ---


@academic_admin_bp.route('/students')
def admin_academic_students():
    return render_template('admin/academic_students.html')


@academic_admin_bp.route('/courses')
def admin_academic_courses():
    return render_template('admin/academic_courses.html')


@academic_admin_bp.route('/enrollments')
def admin_academic_enrollments():
    return render_template('admin/academic_enrollments.html')


@academic_admin_bp.route('/moodle')
def admin_academic_moodle():
    return render_template('admin/academic_moodle.html')


# --- API: students ---


@academic_api_bp.route('/students', methods=['GET'])
@login_required
def api_students_list():
    from models import Student, User

    oid = _oid()
    rows = (
        db.session.query(Student, User)
        .join(User, User.id == Student.user_id)
        .filter(Student.organization_id == oid)
        .order_by(Student.id.desc())
        .limit(500)
        .all()
    )
    out = []
    for st, u in rows:
        out.append(
            {
                'id': st.id,
                'user_id': st.user_id,
                'student_code': st.student_code,
                'academic_status': st.academic_status,
                'program_name': st.program_name or '',
                'faculty': st.faculty or '',
                'campus': st.campus or '',
                'cohort_year': st.cohort_year,
                'institutional_email': st.institutional_email or '',
                'email': u.email,
                'first_name': u.first_name,
                'last_name': u.last_name,
            }
        )
    return jsonify({'success': True, 'students': out})


@academic_api_bp.route('/students', methods=['POST'])
@login_required
def api_students_create():
    from models import Student, User

    oid = _oid()
    data = request.get_json(silent=True) or {}
    user_id = int(data.get('user_id') or 0)
    code = (data.get('student_code') or '').strip()
    if not code:
        return jsonify({'success': False, 'error': 'student_code_required'}), 400

    if user_id > 0:
        u = User.query.filter_by(id=user_id, organization_id=oid).first()
        if not u:
            return jsonify({'success': False, 'error': 'user_not_found'}), 404
    else:
        email = (data.get('email') or '').strip().lower()
        fn = (data.get('first_name') or '').strip()
        ln = (data.get('last_name') or '').strip()
        pwd = data.get('password') or ''
        if not email or not fn:
            return jsonify({'success': False, 'error': 'email_and_name_required'}), 400
        if User.query.filter_by(email=email).first():
            return jsonify({'success': False, 'error': 'email_exists'}), 409
        if not pwd or len(pwd) < 8:
            return jsonify({'success': False, 'error': 'password_min_8'}), 400
        u = User(
            email=email,
            password_hash=generate_password_hash(pwd),
            first_name=fn,
            last_name=ln or '.',
            organization_id=oid,
        )
        db.session.add(u)
        db.session.flush()

    if Student.query.filter_by(organization_id=oid, user_id=u.id).first():
        return jsonify({'success': False, 'error': 'student_already_exists'}), 409
    if Student.query.filter_by(organization_id=oid, student_code=code).first():
        return jsonify({'success': False, 'error': 'student_code_taken'}), 409

    cy = data.get('cohort_year')
    try:
        cohort_year = int(cy) if cy is not None and str(cy).strip() != '' else None
    except (TypeError, ValueError):
        cohort_year = None
    st = Student(
        organization_id=oid,
        user_id=u.id,
        student_code=code,
        academic_status=(data.get('academic_status') or 'active').strip()[:20],
        program_name=(data.get('program_name') or '').strip()[:200] or None,
        faculty=(data.get('faculty') or '').strip()[:200] or None,
        campus=(data.get('campus') or '').strip()[:120] or None,
        cohort_year=cohort_year,
        institutional_email=(data.get('institutional_email') or '').strip()[:255] or None,
    )
    db.session.add(st)
    db.session.commit()
    return jsonify({'success': True, 'id': st.id, 'user_id': u.id}), 201


@academic_api_bp.route('/students/<int:sid>', methods=['PUT'])
@login_required
def api_students_put(sid):
    from models import Student

    oid = _oid()
    st = Student.query.filter_by(id=sid, organization_id=oid).first()
    if not st:
        return jsonify({'success': False, 'error': 'not_found'}), 404
    data = request.get_json(silent=True) or {}
    if 'student_code' in data:
        c = (data.get('student_code') or '').strip()
        if c and c != st.student_code:
            if Student.query.filter_by(organization_id=oid, student_code=c).first():
                return jsonify({'success': False, 'error': 'student_code_taken'}), 409
            st.student_code = c
    if 'academic_status' in data:
        st.academic_status = str(data.get('academic_status') or '')[:20] or st.academic_status
    if 'program_name' in data:
        v = (data.get('program_name') or '').strip()[:200]
        st.program_name = v or None
    if 'faculty' in data:
        v = (data.get('faculty') or '').strip()[:200]
        st.faculty = v or None
    if 'campus' in data:
        v = (data.get('campus') or '').strip()[:120]
        st.campus = v or None
    if 'cohort_year' in data:
        cy = data.get('cohort_year')
        try:
            st.cohort_year = int(cy) if cy is not None and str(cy).strip() != '' else None
        except (TypeError, ValueError):
            pass
    if 'institutional_email' in data:
        v = (data.get('institutional_email') or '').strip()[:255]
        st.institutional_email = v or None
    st.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'success': True})


# --- API: courses ---


@academic_api_bp.route('/courses', methods=['GET'])
@login_required
def api_courses_list():
    from models import AcademicCourse

    oid = _oid()
    rows = (
        AcademicCourse.query.filter_by(organization_id=oid).order_by(AcademicCourse.id.desc()).limit(500).all()
    )
    return jsonify(
        {
            'success': True,
            'courses': [
                {
                    'id': c.id,
                    'name': c.name,
                    'description': c.description,
                    'price': c.price,
                    'currency': c.currency,
                    'modality': c.modality,
                    'status': c.status,
                    'moodle_course_id': c.moodle_course_id,
                }
                for c in rows
            ],
        }
    )


@academic_api_bp.route('/courses', methods=['POST'])
@login_required
def api_courses_create():
    from models import AcademicCourse

    oid = _oid()
    data = request.get_json(silent=True) or {}
    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({'success': False, 'error': 'name_required'}), 400
    c = AcademicCourse(
        organization_id=oid,
        name=name[:200],
        description=(data.get('description') or '').strip() or None,
        price=float(data.get('price') or 0),
        currency=(data.get('currency') or 'USD').strip()[:3] or 'USD',
        modality=(data.get('modality') or 'online').strip()[:20],
        status=(data.get('status') or 'draft').strip()[:20],
        moodle_course_id=int(data['moodle_course_id']) if data.get('moodle_course_id') else None,
    )
    db.session.add(c)
    db.session.commit()
    return jsonify({'success': True, 'id': c.id}), 201


@academic_api_bp.route('/courses/<int:cid>', methods=['PUT'])
@login_required
def api_courses_put(cid):
    from models import AcademicCourse

    oid = _oid()
    c = AcademicCourse.query.filter_by(id=cid, organization_id=oid).first()
    if not c:
        return jsonify({'success': False, 'error': 'not_found'}), 404
    data = request.get_json(silent=True) or {}
    for field in ('name', 'description', 'modality', 'status', 'currency'):
        if field in data and data[field] is not None:
            setattr(c, field, str(data[field])[:500 if field == 'description' else 200])
    if 'price' in data:
        c.price = float(data.get('price') or 0)
    if 'moodle_course_id' in data:
        v = data.get('moodle_course_id')
        c.moodle_course_id = int(v) if v else None
    c.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'success': True})


@academic_api_bp.route('/courses/<int:cid>/create-in-moodle', methods=['POST'])
@login_required
def api_courses_create_moodle(cid):
    oid = _oid()
    data = request.get_json(silent=True) or {}
    cat = int(data.get('category_id') or 1)
    mid, err = create_moodle_course_for_academic_course(cid, oid, category_id=cat)
    if err:
        return jsonify({'success': False, 'error': err}), 400
    return jsonify({'success': True, 'moodle_course_id': mid})


# --- API: enrollments ---


@academic_api_bp.route('/enrollments', methods=['GET'])
@login_required
def api_enrollments_list():
    from models import AcademicCourse, Enrollment, Student, User

    oid = _oid()
    q = (
        db.session.query(Enrollment, Student, AcademicCourse, User)
        .join(Student, Student.id == Enrollment.student_id)
        .join(AcademicCourse, AcademicCourse.id == Enrollment.academic_course_id)
        .join(User, User.id == Student.user_id)
        .filter(Enrollment.organization_id == oid)
        .order_by(Enrollment.id.desc())
        .limit(500)
    )
    out = []
    for en, st, co, u in q:
        out.append(
            {
                'id': en.id,
                'student_id': st.id,
                'student_code': st.student_code,
                'user_email': u.email,
                'course_id': co.id,
                'course_name': co.name,
                'status': en.status,
                'invoice_id': en.invoice_id,
                'moodle_sync_status': en.moodle_sync_status,
                'moodle_error_message': en.moodle_error_message,
                'activated_at': en.activated_at.isoformat() if en.activated_at else None,
            }
        )
    return jsonify({'success': True, 'enrollments': out})


@academic_api_bp.route('/enrollments', methods=['POST'])
@login_required
def api_enrollments_create():
    from models import AcademicCourse, Enrollment, Student

    oid = _oid()
    data = request.get_json(silent=True) or {}
    sid = int(data.get('student_id') or 0)
    cid = int(data.get('academic_course_id') or 0)
    if sid < 1 or cid < 1:
        return jsonify({'success': False, 'error': 'student_and_course_required'}), 400
    if not Student.query.filter_by(id=sid, organization_id=oid).first():
        return jsonify({'success': False, 'error': 'student_not_found'}), 404
    if not AcademicCourse.query.filter_by(id=cid, organization_id=oid).first():
        return jsonify({'success': False, 'error': 'course_not_found'}), 404
    if Enrollment.query.filter_by(
        organization_id=oid, student_id=sid, academic_course_id=cid
    ).first():
        return jsonify({'success': False, 'error': 'enrollment_exists'}), 409
    st = (data.get('status') or 'pending_payment').strip()[:24]
    en = Enrollment(
        organization_id=oid,
        student_id=sid,
        academic_course_id=cid,
        status=st if st in ('draft', 'pending_payment', 'active', 'suspended', 'cancelled') else 'pending_payment',
    )
    db.session.add(en)
    db.session.commit()
    return jsonify({'success': True, 'id': en.id}), 201


@academic_api_bp.route('/enrollments/<int:eid>/generate-invoice', methods=['POST'])
@login_required
def api_enrollments_invoice(eid):
    oid = _oid()
    inv, err = generate_invoice_for_enrollment(eid, oid)
    if err:
        return jsonify({'success': False, 'error': err}), 400
    return jsonify({'success': True, 'invoice_id': inv.id, 'number': inv.number})


@academic_api_bp.route('/enrollments/<int:eid>/sync-moodle', methods=['POST'])
@login_required
def api_enrollments_sync_moodle(eid):
    oid = _oid()
    from models import Enrollment

    en = Enrollment.query.filter_by(id=eid, organization_id=oid).first()
    if not en:
        return jsonify({'success': False, 'error': 'not_found'}), 404
    if en.status != 'active':
        return jsonify({'success': False, 'error': 'enrollment_not_active'}), 400
    en.moodle_sync_status = None
    en.moodle_error_message = None
    db.session.commit()
    sync_enrollment_to_moodle(eid, oid)
    en = Enrollment.query.filter_by(id=eid, organization_id=oid).first()
    return jsonify(
        {
            'success': en.moodle_sync_status == 'success',
            'moodle_sync_status': en.moodle_sync_status,
            'moodle_error_message': en.moodle_error_message,
        }
    )


# --- Moodle config ---


@academic_api_bp.route('/moodle-config', methods=['GET'])
@login_required
def api_moodle_config_get():
    from models import MoodleConfig

    oid = _oid()
    row = MoodleConfig.query.filter_by(organization_id=oid).first()
    if not row:
        return jsonify(
            {
                'success': True,
                'config': {'base_url': '', 'enabled': False, 'has_token': False},
            }
        )
    return jsonify(
        {
            'success': True,
            'config': {
                'base_url': row.base_url,
                'enabled': row.enabled,
                'has_token': bool((row.token or '').strip()),
            },
        }
    )


@academic_api_bp.route('/moodle-config', methods=['PUT'])
@login_required
def api_moodle_config_put():
    from models import MoodleConfig

    oid = _oid()
    data = request.get_json(silent=True) or {}
    row = MoodleConfig.query.filter_by(organization_id=oid).first()
    if row is None:
        row = MoodleConfig(organization_id=oid, base_url='', token='', enabled=False)
        db.session.add(row)
    if 'base_url' in data:
        row.base_url = str(data.get('base_url') or '')[:500]
    if 'token' in data and str(data.get('token') or '').strip():
        row.token = str(data.get('token') or '')[:500]
    if 'enabled' in data:
        row.enabled = bool(data.get('enabled'))
    row.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'success': True})
