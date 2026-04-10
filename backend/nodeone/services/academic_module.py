"""Módulo ERP educativo + Moodle: kill switch global + toggle SaaS `academic` por tenant."""

import os


def is_academic_globally_allowed() -> bool:
    """NODEONE_ACADEMIC_MODULE_ENABLED=0|false|… apaga rutas y registro del módulo en todo el despliegue."""
    raw = (os.environ.get('NODEONE_ACADEMIC_MODULE_ENABLED') or '1').strip().lower()
    return raw not in ('0', 'false', 'no', 'off', 'disabled')


def is_academic_module_enabled_for_org(organization_id) -> bool:
    if not is_academic_globally_allowed():
        return False
    from nodeone.services.org_scope import has_saas_module_enabled

    return has_saas_module_enabled(organization_id, 'academic')
