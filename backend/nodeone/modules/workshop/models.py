"""ORM: taller, vehículos, líneas, fotos, inspección y body map."""

from datetime import datetime

from nodeone.core.db import db


class VehicleZone(db.Model):
    """Catálogo de zonas del body map (vista superior)."""

    __tablename__ = 'vehicle_zones'

    code = db.Column(db.String(40), primary_key=True)
    name = db.Column(db.String(120), nullable=False)


class WorkshopVehicle(db.Model):
    __tablename__ = 'workshop_vehicles'

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(
        db.Integer,
        db.ForeignKey('saas_organization.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    customer_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='RESTRICT'), nullable=False, index=True)
    plate = db.Column(db.String(32), nullable=False, default='')
    brand = db.Column(db.String(80), nullable=False, default='')
    model = db.Column(db.String(80), nullable=False, default='')
    year = db.Column(db.Integer, nullable=True)
    color = db.Column(db.String(60), nullable=False, default='')
    vin = db.Column(db.String(64), nullable=False, default='')
    mileage = db.Column(db.Float, nullable=False, default=0.0)
    nickname = db.Column(db.String(120), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class WorkshopOrder(db.Model):
    __tablename__ = 'workshop_orders'

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(
        db.Integer,
        db.ForeignKey('saas_organization.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    code = db.Column(db.String(50), nullable=False, index=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='RESTRICT'), nullable=False, index=True)
    vehicle_id = db.Column(
        db.Integer,
        db.ForeignKey('workshop_vehicles.id', ondelete='RESTRICT'),
        nullable=False,
        index=True,
    )
    status = db.Column(
        db.String(24),
        nullable=False,
        default='draft',
        index=True,
    )
    entry_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    promised_date = db.Column(db.DateTime, nullable=True)
    advisor_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'), nullable=True, index=True)
    notes = db.Column(db.Text, nullable=True)
    total_estimated = db.Column(db.Float, nullable=False, default=0.0)
    total_final = db.Column(db.Float, nullable=False, default=0.0)
    quotation_id = db.Column(db.Integer, db.ForeignKey('quotations.id', ondelete='SET NULL'), nullable=True, index=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoices.id', ondelete='SET NULL'), nullable=True, index=True)
    qc_notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    # SLA por etapa (alineado a status del flujo)
    sla_stage_started_at = db.Column(db.DateTime, nullable=True)
    sla_expected_minutes = db.Column(db.Integer, nullable=True)
    sla_paused = db.Column(db.Boolean, nullable=False, default=False)
    sla_paused_at = db.Column(db.DateTime, nullable=True)

    __table_args__ = (db.UniqueConstraint('organization_id', 'code', name='uq_workshop_orders_org_code'),)


class WorkshopLine(db.Model):
    __tablename__ = 'workshop_lines'

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(
        db.Integer,
        db.ForeignKey('workshop_orders.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    product_id = db.Column(db.Integer, nullable=True, index=True)
    description = db.Column(db.String(500), nullable=False)
    quantity = db.Column(db.Float, nullable=False, default=1.0)
    price_unit = db.Column(db.Float, nullable=False, default=0.0)
    tax_id = db.Column(db.Integer, db.ForeignKey('taxes.id', ondelete='SET NULL'), nullable=True, index=True)
    subtotal = db.Column(db.Float, nullable=False, default=0.0)
    tax_amount = db.Column(db.Float, nullable=False, default=0.0)
    total = db.Column(db.Float, nullable=False, default=0.0)


class WorkshopPhoto(db.Model):
    __tablename__ = 'workshop_photos'

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(
        db.Integer,
        db.ForeignKey('workshop_orders.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    url = db.Column(db.String(500), nullable=False)
    kind = db.Column(db.String(24), nullable=False, default='entrada')
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class WorkshopChecklistItem(db.Model):
    """Checklist rápido por orden (además del body map)."""

    __tablename__ = 'workshop_checklist_items'

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(
        db.Integer,
        db.ForeignKey('workshop_orders.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    item = db.Column(db.String(200), nullable=False)
    condition = db.Column(db.String(24), nullable=False, default='ok')
    notes = db.Column(db.Text, nullable=True)


class WorkshopInspection(db.Model):
    __tablename__ = 'workshop_inspections'

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(
        db.Integer,
        db.ForeignKey('workshop_orders.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    created_by = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    notes = db.Column(db.Text, nullable=True)

    __table_args__ = (db.UniqueConstraint('order_id', name='uq_workshop_inspection_one_per_order'),)


class VehicleInspectionPoint(db.Model):
    __tablename__ = 'vehicle_inspection_points'

    id = db.Column(db.Integer, primary_key=True)
    inspection_id = db.Column(
        db.Integer,
        db.ForeignKey('workshop_inspections.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    zone_code = db.Column(db.String(40), db.ForeignKey('vehicle_zones.code', ondelete='RESTRICT'), nullable=False, index=True)
    damage_type = db.Column(db.String(40), nullable=False)
    severity = db.Column(db.String(16), nullable=False, default='low')
    notes = db.Column(db.Text, nullable=True)
    x_position = db.Column(db.Float, nullable=True)
    y_position = db.Column(db.Float, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class VehicleInspectionPhoto(db.Model):
    __tablename__ = 'vehicle_inspection_photos'

    id = db.Column(db.Integer, primary_key=True)
    point_id = db.Column(
        db.Integer,
        db.ForeignKey('vehicle_inspection_points.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    url = db.Column(db.String(500), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class WorkshopProcessStageConfig(db.Model):
    """Tiempos objetivo (SLA) por etapa del flujo taller — configurable por organización."""

    __tablename__ = 'workshop_process_stage_config'

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(
        db.Integer,
        db.ForeignKey('saas_organization.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    stage_key = db.Column(db.String(32), nullable=False)
    stage_name = db.Column(db.String(120), nullable=False)
    sequence = db.Column(db.Integer, nullable=False, default=0)
    expected_duration_minutes = db.Column(db.Integer, nullable=False, default=30)
    color = db.Column(db.String(40), nullable=False, default='#0d6efd')
    active = db.Column(db.Boolean, nullable=False, default=True)
    service_type_tag = db.Column(db.String(80), nullable=True)
    allow_skip = db.Column(db.Boolean, nullable=False, default=False)

    __table_args__ = (
        db.UniqueConstraint('organization_id', 'stage_key', name='uq_workshop_proc_stage_org_key'),
    )


class WorkshopServiceProcessConfig(db.Model):
    """Override de SLA por servicio del catálogo y etapa."""

    __tablename__ = 'workshop_service_process_config'

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(
        db.Integer,
        db.ForeignKey('saas_organization.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    service_id = db.Column(db.Integer, db.ForeignKey('service.id', ondelete='CASCADE'), nullable=False, index=True)
    stage_key = db.Column(db.String(32), nullable=False)
    expected_duration_minutes = db.Column(db.Integer, nullable=False, default=30)

    __table_args__ = (
        db.UniqueConstraint('organization_id', 'service_id', 'stage_key', name='uq_workshop_svc_proc_org_svc_stage'),
    )


class WorkshopOrderProcessLog(db.Model):
    """Historial de permanencia en cada etapa (duración real vs esperada)."""

    __tablename__ = 'workshop_order_process_log'

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(
        db.Integer,
        db.ForeignKey('workshop_orders.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    stage_key = db.Column(db.String(32), nullable=False)
    started_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    ended_at = db.Column(db.DateTime, nullable=True)
    duration_minutes = db.Column(db.Float, nullable=True)
    expected_minutes = db.Column(db.Float, nullable=True)
    is_delayed = db.Column(db.Boolean, nullable=False, default=False)
    delay_minutes = db.Column(db.Float, nullable=True)
