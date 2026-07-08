"""
EasyNodeOne Platform — Core (Etapa 2).

Contratos y registro del núcleo de plataforma. Las apps de negocio viven fuera
de este paquete y se registran vía ``register_platform_apps``.
"""

from nodeone.core.platform.app_registry import (
    APPLICATIONS,
    ApplicationDescriptor,
    get_application,
    list_applications,
)
from nodeone.core.platform.capabilities import CoreCapability
from nodeone.core.platform.register import register_platform_apps, register_platform_core
from nodeone.core.platform.runtime import (
    has_permission,
    has_saas_module,
    resolve_organization_id,
)

__all__ = [
    'APPLICATIONS',
    'ApplicationDescriptor',
    'CoreCapability',
    'get_application',
    'has_permission',
    'has_saas_module',
    'list_applications',
    'register_platform_apps',
    'register_platform_core',
    'resolve_organization_id',
]
