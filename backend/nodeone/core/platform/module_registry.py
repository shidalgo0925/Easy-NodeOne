"""ADR-038 F1 — Module Registry service (aditivo + dual-write a saas_org_module).

Hasta F2, los guards/nav siguen leyendo saas_org_module vía has_saas_module_enabled.
Este registry es la API formal; enable/disable escribe ambas capas.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

# F1: module_key == saas_code (identidad). App Registry ids ≠ module_key
# (ver APP_ID_TO_SAAS_CODES; formalización de apps = F8).
SAAS_CODE_TO_MODULE_KEY: dict[str, str] = {}
MODULE_KEY_TO_SAAS_CODE: dict[str, str] = {}

# Referencia App Registry → códigos SaaS (no son filas ModuleDefinition en F1).
APP_ID_TO_SAAS_CODES: dict[str, tuple[str, ...]] = {
    'contacts': ('contacts', 'crm_contacts'),
    'emembership': ('memberships',),
    'ecrm': ('crm', 'crm_contacts'),
    'eevents': ('events',),
    'ecertificates': ('certificates',),
    'eappointments': ('appointments',),
    'academic': ('academic',),
    'eposone': ('eposone',),
    'epayroll': ('epayroll',),
    'esales': ('sales',),
    'efactura': ('efactura',),
    'emarketing': ('marketing_email',),
    'ecommunications': ('communications',),
    'eanalytics': ('analytics',),
}


def _log(printfn, msg: str) -> None:
    if printfn:
        printfn(msg)


def saas_code_to_module_key(saas_code: str) -> str:
    code = (saas_code or '').strip().lower()
    return SAAS_CODE_TO_MODULE_KEY.get(code, code)


def module_key_to_saas_code(module_key: str) -> str:
    key = (module_key or '').strip().lower()
    return MODULE_KEY_TO_SAAS_CODE.get(key, key)


def _deps_list(defn) -> list[str]:
    raw = getattr(defn, 'dependencies_json', None) or ''
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except (TypeError, ValueError, json.JSONDecodeError):
        return []
    if not isinstance(data, list):
        return []
    return [str(x).strip().lower() for x in data if str(x).strip()]


def _set_deps(defn, deps: list[str]) -> None:
    clean = [str(x).strip().lower() for x in deps if str(x).strip()]
    defn.dependencies_json = json.dumps(clean, ensure_ascii=False)


def _now() -> datetime:
    return datetime.utcnow()


def ensure_module_registry(printfn=None, *, sync_orgs: bool = True) -> None:
    """DDL + seed desde SAAS_CATALOG + sync organization_module desde saas_org_module."""
    from nodeone.core.db import db
    from nodeone.services.module_registry_schema import ensure_module_registry_schema

    ensure_module_registry_schema(db, db.engine, printfn=printfn)
    seed_module_definitions_from_saas_catalog(printfn=printfn)
    if sync_orgs:
        sync_all_organization_modules_from_saas(printfn=printfn)


def seed_module_definitions_from_saas_catalog(printfn=None) -> None:
    """Idempotente: ModuleDefinition alineado a SAAS_CATALOG_MODULES + deps SaaS."""
    from models.module_registry import ModuleDefinition
    from models.saas import SaasModule, SaasModuleDependency
    from nodeone.core.db import db
    from nodeone.services.saas_catalog_defaults import SAAS_CATALOG_MODULES

    global SAAS_CODE_TO_MODULE_KEY, MODULE_KEY_TO_SAAS_CODE

    # Identidad F1
    SAAS_CODE_TO_MODULE_KEY = {code: code for code, *_ in SAAS_CATALOG_MODULES}
    MODULE_KEY_TO_SAAS_CODE = {code: code for code, *_ in SAAS_CATALOG_MODULES}

    # deps desde tabla saas (si existe)
    saas_deps: dict[str, list[str]] = {}
    for dep in SaasModuleDependency.query.all():
        child = SaasModule.query.get(dep.module_id)
        parent = SaasModule.query.get(dep.depends_on_module_id)
        if not child or not parent:
            continue
        saas_deps.setdefault(child.code, []).append(parent.code)

    created = 0
    updated = 0
    for code, name, description, is_core in SAAS_CATALOG_MODULES:
        module_key = saas_code_to_module_key(code)
        deps = [saas_code_to_module_key(d) for d in saas_deps.get(code, [])]
        row = ModuleDefinition.query.filter_by(module_key=module_key).first()
        if row is None:
            row = ModuleDefinition(
                module_key=module_key,
                name=name,
                description=description,
                version='1',
                status='active',
                configurable_per_org=not bool(is_core),
                is_core=bool(is_core),
                saas_code=code,
            )
            _set_deps(row, deps)
            db.session.add(row)
            created += 1
            _log(printfn, f'+ module_definition: {module_key}')
            continue
        changed = False
        if (row.name or '') != name:
            row.name = name
            changed = True
        if (row.description or '') != (description or ''):
            row.description = description
            changed = True
        if bool(row.is_core) != bool(is_core):
            row.is_core = bool(is_core)
            row.configurable_per_org = not bool(is_core)
            changed = True
        if (row.saas_code or '') != code:
            row.saas_code = code
            changed = True
        if _deps_list(row) != deps and deps:
            _set_deps(row, deps)
            changed = True
        if changed:
            row.updated_at = _now()
            updated += 1
            _log(printfn, f'* module_definition: {module_key}')
    if created or updated:
        db.session.commit()
    else:
        db.session.commit()  # flush mapping side-effects none; keep session clean


def sync_organization_modules_from_saas(organization_id: int, printfn=None) -> int:
    """Copia estado desde saas_org_module → organization_module (no borra filas)."""
    from models.module_registry import ModuleDefinition, OrganizationModule
    from models.saas import SaasModule, SaasOrgModule
    from nodeone.core.db import db

    oid = int(organization_id)
    upserts = 0
    defs = {d.module_key: d for d in ModuleDefinition.query.all()}

    for mod in SaasModule.query.all():
        module_key = saas_code_to_module_key(mod.code)
        if module_key not in defs:
            continue
        link = SaasOrgModule.query.filter_by(organization_id=oid, module_id=mod.id).first()
        if link is not None:
            enabled = bool(link.enabled)
        else:
            enabled = bool(mod.is_core)
        row = OrganizationModule.query.filter_by(organization_id=oid, module_key=module_key).first()
        now = _now()
        if row is None:
            row = OrganizationModule(
                organization_id=oid,
                module_key=module_key,
                enabled=enabled,
                enabled_at=now if enabled else None,
                disabled_at=None if enabled else now,
            )
            db.session.add(row)
            upserts += 1
        elif bool(row.enabled) != enabled:
            row.enabled = enabled
            if enabled:
                row.enabled_at = now
                row.disabled_at = None
            else:
                row.disabled_at = now
            row.updated_at = now
            upserts += 1

    if upserts:
        db.session.commit()
        _log(printfn, f'* organization_module sync org={oid} upserts={upserts}')
    return upserts


def sync_all_organization_modules_from_saas(printfn=None) -> int:
    from models.saas import SaasOrganization

    total = 0
    for org in SaasOrganization.query.order_by(SaasOrganization.id.asc()).all():
        total += sync_organization_modules_from_saas(int(org.id), printfn=None)
    if total:
        _log(printfn, f'* organization_module sync total upserts={total}')
    return total


def get_module_definition(module_key: str):
    from models.module_registry import ModuleDefinition

    key = (module_key or '').strip().lower()
    return ModuleDefinition.query.filter_by(module_key=key).first()


def is_module_enabled(organization_id: int, module_key: str) -> bool:
    """Lee organization_module; si no hay fila, fallback a definición is_core / saas."""
    from models.module_registry import OrganizationModule

    key = (module_key or '').strip().lower()
    oid = int(organization_id)
    row = OrganizationModule.query.filter_by(organization_id=oid, module_key=key).first()
    if row is not None:
        return bool(row.enabled)
    defn = get_module_definition(key)
    if defn is not None and defn.is_core:
        return True
    # fallback legado
    try:
        from app import has_saas_module_enabled

        return bool(has_saas_module_enabled(oid, module_key_to_saas_code(key)))
    except Exception:
        return False


def _get_or_create_org_module(organization_id: int, module_key: str):
    from models.module_registry import OrganizationModule
    from nodeone.core.db import db

    oid = int(organization_id)
    key = module_key.strip().lower()
    row = OrganizationModule.query.filter_by(organization_id=oid, module_key=key).first()
    if row is None:
        row = OrganizationModule(organization_id=oid, module_key=key, enabled=False)
        db.session.add(row)
        db.session.flush()
    return row


def _dual_write_saas(organization_id: int, module_key: str, enabled: bool) -> str | None:
    """Escribe saas_org_module sin re-validar deps (ya validadas en registry)."""
    from models.saas import SaasModule, SaasOrgModule
    from nodeone.core.db import db

    saas_code = module_key_to_saas_code(module_key)
    mod = SaasModule.query.filter_by(code=saas_code).first()
    if mod is None:
        return f'saas_module ausente para {saas_code}'
    row = SaasOrgModule.query.filter_by(organization_id=organization_id, module_id=mod.id).first()
    if row is None:
        row = SaasOrgModule(organization_id=organization_id, module_id=mod.id, enabled=bool(enabled))
        db.session.add(row)
    else:
        row.enabled = bool(enabled)
    return None


def enable_module(organization_id: int, module_key: str) -> tuple[bool, str | None]:
    from models.saas import SaasOrganization
    from nodeone.core.db import db

    oid = int(organization_id)
    key = (module_key or '').strip().lower()
    if SaasOrganization.query.get(oid) is None:
        return False, 'Organización no encontrada'
    defn = get_module_definition(key)
    if defn is None:
        return False, 'Código de módulo desconocido'
    if (defn.status or '') not in ('active', 'draft'):
        return False, f'Módulo no disponible (status={defn.status})'

    for dep_key in _deps_list(defn):
        dep_def = get_module_definition(dep_key)
        if dep_def and dep_def.is_core:
            continue
        if not is_module_enabled(oid, dep_key):
            return False, f'Active primero el módulo requerido: {dep_key}'

    now = _now()
    row = _get_or_create_org_module(oid, key)
    row.enabled = True
    row.enabled_at = now
    row.disabled_at = None
    row.updated_at = now
    err = _dual_write_saas(oid, key, True)
    if err:
        db.session.rollback()
        return False, err
    db.session.commit()
    try:
        from saas_admin_api import clear_saas_request_cache

        clear_saas_request_cache()
    except Exception:
        pass
    return True, None


def disable_module(organization_id: int, module_key: str) -> tuple[bool, str | None]:
    from models.module_registry import ModuleDefinition, OrganizationModule
    from models.saas import SaasOrganization
    from nodeone.core.db import db

    oid = int(organization_id)
    key = (module_key or '').strip().lower()
    if SaasOrganization.query.get(oid) is None:
        return False, 'Organización no encontrada'
    defn = get_module_definition(key)
    if defn is None:
        return False, 'Código de módulo desconocido'
    if defn.is_core:
        return False, 'Los módulos core no se pueden desactivar'

    # Dependientes declarados en ModuleDefinition
    for other in ModuleDefinition.query.all():
        if key in _deps_list(other) and is_module_enabled(oid, other.module_key):
            return False, f'Desactive primero el módulo dependiente: {other.module_key}'

    now = _now()
    row = _get_or_create_org_module(oid, key)
    # disable ≠ DELETE
    row.enabled = False
    row.disabled_at = now
    row.updated_at = now
    err = _dual_write_saas(oid, key, False)
    if err:
        db.session.rollback()
        return False, err
    db.session.commit()
    # Verificar que la fila sigue existiendo
    still = OrganizationModule.query.filter_by(organization_id=oid, module_key=key).first()
    if still is None:
        return False, 'Error interno: disable eliminó la fila'
    try:
        from saas_admin_api import clear_saas_request_cache

        clear_saas_request_cache()
    except Exception:
        pass
    return True, None


def list_org_modules(organization_id: int) -> list[dict[str, Any]]:
    from models.module_registry import ModuleDefinition

    oid = int(organization_id)
    out: list[dict[str, Any]] = []
    for d in ModuleDefinition.query.order_by(ModuleDefinition.id).all():
        out.append(
            {
                'module_key': d.module_key,
                'saas_code': d.saas_code or d.module_key,
                'name': d.name,
                'description': d.description or '',
                'is_core': bool(d.is_core),
                'configurable_per_org': bool(d.configurable_per_org),
                'enabled': is_module_enabled(oid, d.module_key),
                'depends_on': _deps_list(d),
                'status': d.status,
                'version': d.version,
            }
        )
    return out
