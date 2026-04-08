#!/usr/bin/env python3
"""Crea tablas del módulo Taller, semilla de zonas body-map y SaaS workshop."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db  # noqa: E402
from nodeone.modules.accounting.models import Invoice, Tax  # noqa: E402
from nodeone.modules.sales.models import Quotation  # noqa: E402
from nodeone.modules.workshop.models import (  # noqa: E402
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
from nodeone.services.saas_catalog_defaults import (  # noqa: E402
    ensure_saas_module_catalog,
    ensure_sales_org_module_links,
)


ZONES = (
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
)


def main():
    with app.app_context():
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

        for code, name in ZONES:
            if not VehicleZone.query.filter_by(code=code).first():
                db.session.add(VehicleZone(code=code, name=name))
        db.session.commit()
        print('✅ Tablas taller + zonas body map')

        ensure_saas_module_catalog(printfn=print)
        ensure_sales_org_module_links(printfn=print)
        from app import SaasModule, SaasOrgModule, SaasOrganization

        wmod = SaasModule.query.filter_by(code='workshop').first()
        if not wmod:
            print('⚠️ saas_module workshop no encontrado (añade en saas_catalog_defaults)')
            return
        sales_mod = SaasModule.query.filter_by(code='sales').first()
        linked = 0
        for org in SaasOrganization.query.order_by(SaasOrganization.id.asc()).all():
            oid = int(org.id)
            link = SaasOrgModule.query.filter_by(organization_id=oid, module_id=wmod.id).first()
            if link is not None:
                continue
            en = False
            if sales_mod:
                sl = SaasOrgModule.query.filter_by(organization_id=oid, module_id=sales_mod.id).first()
                en = bool(sl and sl.enabled)
            db.session.add(SaasOrgModule(organization_id=oid, module_id=wmod.id, enabled=en))
            linked += 1
        if linked:
            db.session.commit()
        print(f'✅ saas_org_module workshop: +{linked} enlaces (enabled si ventas activo)')


if __name__ == '__main__':
    main()
