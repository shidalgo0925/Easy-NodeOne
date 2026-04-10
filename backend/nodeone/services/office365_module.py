"""Office 365: kill switch por entorno + módulo SaaS por tenant (`office365`)."""

import os


def is_office365_globally_allowed() -> bool:
    """Por defecto permitido; NODEONE_OFFICE365_MODULE_ENABLED=0|false|no|off|disabled apaga todo el despliegue."""
    raw = (os.environ.get('NODEONE_OFFICE365_MODULE_ENABLED') or '1').strip().lower()
    return raw not in ('0', 'false', 'no', 'off', 'disabled')


def is_office365_module_enabled_for_org(organization_id) -> bool:
    """True si el entorno lo permite y el tenant tiene el módulo SaaS `office365` activo."""
    if not is_office365_globally_allowed():
        return False
    from nodeone.services.org_scope import has_saas_module_enabled

    return has_saas_module_enabled(organization_id, 'office365')
