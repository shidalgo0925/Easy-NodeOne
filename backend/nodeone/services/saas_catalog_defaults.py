"""
Catálogo SaaS por defecto (tabla saas_module) y vínculos org → sales.

Idempotente: seguro en bootstrap (ExecStartPre) y en migraciones.
"""

from __future__ import annotations

import os

from sqlalchemy import inspect, text

# Códigos usados en guards/plantillas.
# is_core=True → sin fila en saas_org_module se considera ON; además no se puede desactivar desde /admin Módulos SaaS.
# is_core=False → hace falta fila en saas_org_module; se puede activar/desactivar por tenant (con default ON vía ensure_toggleable_tenant_module_links).
SAAS_CATALOG_MODULES: tuple[tuple[str, str, str, bool], ...] = (
    ('appointments', 'Citas', 'Agenda y citas', False),
    ('events', 'Eventos', 'Eventos e inscripciones', False),
    ('chatbot', 'IA / Chatbots', 'Asistentes y configuración IA', False),
    ('crm_contacts', 'Contactos CRM', 'Contactos del tenant', False),
    ('crm', 'CRM', 'CRM (menú y funciones comerciales)', False),
    ('marketing_email', 'Marketing email', 'Campañas y cola de correo', False),
    ('certificates', 'Certificados', 'Certificados y plantillas', False),
    ('payments', 'Pagos', 'Checkout y pagos', True),
    ('policies', 'Normativas', 'Políticas y normativas públicas', False),
    ('communications', 'Comunicaciones', 'Integraciones y mensajería', False),
    (
        'office365',
        'Office 365 (correo)',
        'Solicitudes de correo institucional y flujo Office 365.',
        False,
    ),
    (
        'sales',
        'Ventas',
        'Cotizaciones, facturación e impuestos (flujo comercial).',
        False,
    ),
    (
        'analytics',
        'Analítica',
        'KPIs, tableros por área y APIs de resumen (permiso analytics.view).',
        False,
    ),
    (
        'accounting',
        'Contabilidad',
        'Reservado para contabilidad avanzada (sin guard SaaS en facturas).',
        False,
    ),
    (
        'workshop',
        'Taller + SLA',
        'Recepción de vehículos, inspección (body map), monitor operativo y configuración de procesos SLA.',
        False,
    ),
    (
        'academic',
        'Educación / LMS',
        'Estudiantes, cursos académicos, matrículas e integración Moodle.',
        False,
    ),
    (
        'contador',
        'Contador',
        'Conteos físicos de inventario por variante, catálogo e importación masiva.',
        False,
    ),
    (
        'qr_generator',
        'Generador QR',
        'Generación de códigos QR estáticos (PNG, SVG, PDF) e historial por organización.',
        False,
    ),
)


def _log(printfn, msg: str) -> None:
    if printfn:
        printfn(msg)


def _org_ids_with_sales_usage() -> set[int]:
    from app import db

    ids: set[int] = set()
    insp = inspect(db.engine)
    names = set(insp.get_table_names())
    if 'quotations' in names:
        for row in db.session.execute(text('SELECT DISTINCT organization_id FROM quotations')).fetchall():
            if row[0] is not None:
                try:
                    ids.add(int(row[0]))
                except (TypeError, ValueError):
                    pass
    if 'invoices' in names:
        for row in db.session.execute(text('SELECT DISTINCT organization_id FROM invoices')).fetchall():
            if row[0] is not None:
                try:
                    ids.add(int(row[0]))
                except (TypeError, ValueError):
                    pass
    return ids


def _org_ids_accounting_saas_enabled() -> set[int]:
    from app import SaasModule, SaasOrgModule

    acc = SaasModule.query.filter_by(code='accounting').first()
    if acc is None:
        return set()
    return {
        int(l.organization_id)
        for l in SaasOrgModule.query.filter_by(module_id=acc.id, enabled=True).all()
        if l.organization_id is not None
    }


def ensure_saas_module_catalog(printfn=None) -> None:
    """Inserta o alinea filas en saas_module con SAAS_CATALOG_MODULES (is_core, nombre, descripción). No toca saas_org_module."""
    from app import SaasModule, db

    for code, name, description, is_core in SAAS_CATALOG_MODULES:
        mod = SaasModule.query.filter_by(code=code).first()
        if mod is None:
            db.session.add(SaasModule(code=code, name=name, description=description, is_core=is_core))
            _log(printfn, f'+ saas_module: {code}')
            continue
        if (
            (mod.name or '') != name
            or (mod.description or '') != description
            or bool(mod.is_core) != bool(is_core)
        ):
            mod.name = name
            mod.description = description
            mod.is_core = is_core
            _log(printfn, f'* saas_module actualizado: {code}')
    db.session.commit()


def ensure_sales_org_module_links(printfn=None) -> None:
    """Crea saas_org_module para sales donde falte (heurística de uso / accounting)."""
    from app import SaasModule, SaasOrgModule, SaasOrganization, db

    sales_mod = SaasModule.query.filter_by(code='sales').first()
    if sales_mod is None:
        return
    usage = _org_ids_with_sales_usage()
    acc_on = _org_ids_accounting_saas_enabled()
    should_on = usage | acc_on
    created = 0
    for org in SaasOrganization.query.order_by(SaasOrganization.id.asc()).all():
        oid = int(org.id)
        link = SaasOrgModule.query.filter_by(organization_id=oid, module_id=sales_mod.id).first()
        if link is not None:
            continue
        en = oid in should_on
        db.session.add(SaasOrgModule(organization_id=oid, module_id=sales_mod.id, enabled=en))
        created += 1
        _log(printfn, f'+ saas_org_module: org={oid} sales enabled={en}')
    if created:
        db.session.commit()


# Módulos que el admin puede encender/apagar por empresa (deben tener is_core=False en SAAS_CATALOG_MODULES).
TOGGLEABLE_BY_TENANT_CODES: tuple[str, ...] = (
    'analytics',
    'appointments',
    'crm',
    'crm_contacts',
    'certificates',
    'communications',
    'office365',
    'events',
    'chatbot',
    'marketing_email',
    'policies',
    'academic',
    'workshop',
    'contador',
    'qr_generator',
)


def ensure_toggleable_tenant_module_links(printfn=None, organization_id: int | None = None) -> None:
    """
    Para módulos por-tenant: si no existe saas_org_module, crea enabled=True.
    Así al pasar de core→opcional no se apagan todos los tenants de golpe; empresas nuevas quedan con todo lo toggleable encendido.
    """
    from app import SaasModule, SaasOrgModule, SaasOrganization, db

    mods: list = []
    for code in TOGGLEABLE_BY_TENANT_CODES:
        m = SaasModule.query.filter_by(code=code).first()
        if m is not None:
            mods.append(m)
    if not mods:
        return

    if organization_id is not None:
        orgs = [SaasOrganization.query.get(int(organization_id))]
    else:
        orgs = SaasOrganization.query.order_by(SaasOrganization.id.asc()).all()

    created = 0
    for org in orgs:
        if org is None:
            continue
        oid = int(org.id)
        for mod in mods:
            link = SaasOrgModule.query.filter_by(organization_id=oid, module_id=mod.id).first()
            if link is not None:
                continue
            db.session.add(SaasOrgModule(organization_id=oid, module_id=mod.id, enabled=True))
            created += 1
            _log(printfn, f'+ saas_org_module: org={oid} {mod.code}=on (default toggleable)')
    if created:
        db.session.commit()


def ensure_office365_module_dependency(printfn=None) -> None:
    """office365 depende de communications (Admin → Módulos)."""
    from app import SaasModule, SaasModuleDependency, db

    child = SaasModule.query.filter_by(code='office365').first()
    parent = SaasModule.query.filter_by(code='communications').first()
    if child is None or parent is None:
        return
    existing = SaasModuleDependency.query.filter_by(
        module_id=child.id, depends_on_module_id=parent.id
    ).first()
    if existing is not None:
        return
    db.session.add(SaasModuleDependency(module_id=child.id, depends_on_module_id=parent.id))
    _log(printfn, '+ saas_module_dependency: office365 → communications')
    db.session.commit()


def ensure_academic_module_dependency(printfn=None) -> None:
    """academic depende de sales (facturación / cotizaciones)."""
    from app import SaasModule, SaasModuleDependency, db

    child = SaasModule.query.filter_by(code='academic').first()
    parent = SaasModule.query.filter_by(code='sales').first()
    if child is None or parent is None:
        return
    existing = SaasModuleDependency.query.filter_by(
        module_id=child.id, depends_on_module_id=parent.id
    ).first()
    if existing is not None:
        return
    db.session.add(SaasModuleDependency(module_id=child.id, depends_on_module_id=parent.id))
    _log(printfn, '+ saas_module_dependency: academic → sales')
    db.session.commit()


def ensure_workshop_org_modules_on(printfn=None) -> None:
    """
    Enciende saas_org_module para `workshop` donde estaba en off (p. ej. migración que copió ventas apagado).
    Omitir con NODEONE_WORKSHOP_KEEP_DEFAULT_OFF=1.
    """
    if os.environ.get('NODEONE_WORKSHOP_KEEP_DEFAULT_OFF', '').strip().lower() in ('1', 'true', 'yes'):
        return
    from app import SaasModule, SaasOrgModule, db

    m = SaasModule.query.filter_by(code='workshop').first()
    if m is None:
        return
    n = 0
    for link in SaasOrgModule.query.filter_by(module_id=m.id, enabled=False).all():
        link.enabled = True
        n += 1
    if n:
        db.session.commit()
        _log(printfn, f'* saas_org_module: workshop → on ({n} vínculo(s))')


def ensure_academic_org_modules_on(printfn=None) -> None:
    """
    Enciende saas_org_module para `academic` donde estaba en off (instalación inicial lo dejó apagado).
    Omitir con NODEONE_ACADEMIC_KEEP_DEFAULT_OFF=1.
    """
    if os.environ.get('NODEONE_ACADEMIC_KEEP_DEFAULT_OFF', '').strip().lower() in ('1', 'true', 'yes'):
        return
    from app import SaasModule, SaasOrgModule, db

    m = SaasModule.query.filter_by(code='academic').first()
    if m is None:
        return
    n = 0
    for link in SaasOrgModule.query.filter_by(module_id=m.id, enabled=False).all():
        link.enabled = True
        n += 1
    if n:
        db.session.commit()
        _log(printfn, f'* saas_org_module: academic → on ({n} vínculo(s))')


def ensure_saas_catalog_full(printfn=None) -> None:
    ensure_saas_module_catalog(printfn=printfn)
    ensure_office365_module_dependency(printfn=printfn)
    ensure_academic_module_dependency(printfn=printfn)
    ensure_sales_org_module_links(printfn=printfn)
    ensure_toggleable_tenant_module_links(printfn=printfn)
    # No llamar ensure_workshop_org_modules_on / ensure_academic_org_modules_on aquí:
    # forzaban enabled=True en cada arranque y anulaban lo apagado en Admin → Módulos por org.
    # Los toggles viven en saas_org_module; si hace falta re-migrar, ejecutar esas funciones a mano o vía script.


def apply_platform_org_allowlist(printfn=None) -> None:
    """
    Si EASYNODEONE_PLATFORM_VISIBLE_ORG_IDS está definido: desactiva tenants fuera de la lista
    y reasigna sus usuarios a la organización por defecto (id canónico).
    La org por defecto nunca se desactiva aunque no esté en el env (se fuerza en allow).
    """
    from utils.organization import default_organization_id, platform_visible_organization_ids

    raw_allow = platform_visible_organization_ids()
    if raw_allow is None:
        return
    def_oid = int(default_organization_id())
    allow = set(raw_allow) | {def_oid}

    from app import SaasOrganization, User, db

    changed = False
    for o in SaasOrganization.query.order_by(SaasOrganization.id.asc()).all():
        oid = int(o.id)
        if oid in allow:
            continue
        if bool(getattr(o, 'is_active', True)):
            o.is_active = False
            changed = True
            _log(printfn, f'* org {oid} desactivada (fuera de EASYNODEONE_PLATFORM_VISIBLE_ORG_IDS)')
        n = User.query.filter_by(organization_id=oid).update({'organization_id': def_oid}, synchronize_session=False)
        if n:
            _log(printfn, f'* {n} usuario(s) reasignados de org {oid} → {def_oid}')
            changed = True
    if changed:
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise
