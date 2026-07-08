"""
EasyNodeOne Platform — Core (Etapa 2).

Contratos y registro del núcleo de plataforma. Las apps de negocio viven fuera
de este paquete y se registran vía ``register_platform_apps``.
"""

from nodeone.core.platform.app_integration import (
    app_dependencies_satisfied,
    filter_launcher_apps_for_org,
    get_app_runtime,
    organization_has_integrated_apps,
)
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
from nodeone.core.platform.events import (
    dispatch_pending_events,
    publish_domain_event,
    subscribe,
)
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
    'app_dependencies_satisfied',
    'ApplicationDescriptor',
    'app_dependencies_satisfied',
    'build_app_shell_nav_payload',
    'CoreCapability',
    'dispatch_pending_events',
    'filter_launcher_apps_for_org',
    'get_active_app_id',
    'get_app_runtime',
    'get_application',
    'has_permission',
    'has_saas_module',
    'is_app_shell_enabled',
    'launcher_mode_for_organization',
    'list_applications',
    'merge_app_shell_nav_context',
    'organization_has_integrated_apps',
    'post_login_redirect_target',
    'publish_domain_event',
    'register_platform_apps',
    'register_platform_core',
    'resolve_organization_id',
    'set_active_app_id',
    'subscribe',
    'visible_launcher_apps',
]
