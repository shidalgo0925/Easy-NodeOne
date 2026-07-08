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
from nodeone.core.platform.app_shell import (
    build_app_shell_nav_payload,
    is_app_shell_enabled,
    merge_app_shell_nav_context,
)
from nodeone.core.platform.capabilities import CoreCapability
from nodeone.core.platform.launcher import (
    get_active_app_id,
    launcher_mode_for_organization,
    post_login_redirect_target,
    set_active_app_id,
    visible_launcher_apps,
)
from nodeone.core.platform.register import register_platform_apps, register_platform_core
from nodeone.core.platform.runtime import (
    has_permission,
    has_saas_module,
    resolve_organization_id,
)

__all__ = [
    'APPLICATIONS',
    'ApplicationDescriptor',
    'build_app_shell_nav_payload',
    'CoreCapability',
    'get_active_app_id',
    'get_application',
    'has_permission',
    'has_saas_module',
    'is_app_shell_enabled',
    'launcher_mode_for_organization',
    'list_applications',
    'merge_app_shell_nav_context',
    'post_login_redirect_target',
    'register_platform_apps',
    'register_platform_core',
    'resolve_organization_id',
    'set_active_app_id',
    'visible_launcher_apps',
]
