"""Módulo central Contactos: kill switch global + toggle SaaS `contacts` por tenant."""

from __future__ import annotations

import os


def is_contacts_globally_allowed() -> bool:
    """NODEONE_CONTACTS_MODULE_ENABLED=0|false|… apaga rutas y registro del módulo en todo el despliegue."""
    raw = (os.environ.get('NODEONE_CONTACTS_MODULE_ENABLED') or '1').strip().lower()
    return raw not in ('0', 'false', 'no', 'off', 'disabled')


def is_contacts_enabled_for_org(organization_id) -> bool:
    if not is_contacts_globally_allowed():
        return False
    from nodeone.services.org_scope import has_saas_module_enabled

    return has_saas_module_enabled(organization_id, 'contacts')
