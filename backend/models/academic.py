"""ERP educativo: estudiantes, cursos académicos, matrículas, config Moodle (por tenant)."""

from datetime import datetime

from nodeone.core.db import db


class Student(db.Model):
    __tablename__ = 'students'

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(
        db.Integer,
        db.ForeignKey('saas_organization.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False, index=True)
    student_code = db.Column(db.String(64), nullable=False)
    academic_status = db.Column(db.String(20), nullable=False, default='active')
    # Datos académicos extendidos (universidad / programa)
    program_name = db.Column(db.String(200))
    faculty = db.Column(db.String(200))
    campus = db.Column(db.String(120))
    cohort_year = db.Column(db.Integer)
    institutional_email = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('student_profiles', lazy='dynamic'))
    organization = db.relationship('SaasOrganization', backref='students')

    __table_args__ = (
        db.UniqueConstraint('organization_id', 'user_id', name='uq_students_org_user'),
        db.UniqueConstraint('organization_id', 'student_code', name='uq_students_org_code'),
    )


class AcademicCourse(db.Model):
    __tablename__ = 'academic_courses'

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(
        db.Integer,
        db.ForeignKey('saas_organization.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Float, nullable=False, default=0.0)
    currency = db.Column(db.String(3), nullable=False, default='USD')
    modality = db.Column(db.String(20), nullable=False, default='online')
    status = db.Column(db.String(20), nullable=False, default='draft')
    moodle_course_id = db.Column(db.Integer, nullable=True, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    organization = db.relationship('SaasOrganization', backref='academic_courses')


class Enrollment(db.Model):
    __tablename__ = 'enrollments'

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(
        db.Integer,
        db.ForeignKey('saas_organization.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    student_id = db.Column(db.Integer, db.ForeignKey('students.id', ondelete='CASCADE'), nullable=False, index=True)
    academic_course_id = db.Column(
        db.Integer,
        db.ForeignKey('academic_courses.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    status = db.Column(db.String(24), nullable=False, default='pending_payment')
    # Sin FK ORM a invoices (orden de importación / CREATE); coherencia en academic_service.
    invoice_id = db.Column(db.Integer, nullable=True, index=True)
    activated_at = db.Column(db.DateTime, nullable=True)
    moodle_enrol_synced_at = db.Column(db.DateTime, nullable=True)
    moodle_sync_status = db.Column(db.String(20), nullable=True)
    moodle_error_message = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    student = db.relationship('Student', backref=db.backref('enrollments', lazy='dynamic'))
    academic_course = db.relationship('AcademicCourse', backref=db.backref('enrollments', lazy='dynamic'))


class MoodleConfig(db.Model):
    __tablename__ = 'moodle_config'

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(
        db.Integer,
        db.ForeignKey('saas_organization.id', ondelete='CASCADE'),
        nullable=False,
        unique=True,
        index=True,
    )
    base_url = db.Column(db.String(500), nullable=False, default='')
    token = db.Column(db.String(500), nullable=False, default='')
    enabled = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    organization = db.relationship('SaasOrganization', backref=db.backref('moodle_config', uselist=False))
