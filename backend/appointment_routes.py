"""
Compatibilidad: implementación en nodeone.modules.appointments.routes.
Import estable para app.py y despliegues existentes.
"""
from nodeone.modules.appointments.routes import (
    admin_appointments_bp,
    appointments_api_bp,
    appointments_bp,
    appointments_http_legacy_bp,
    ensure_models,
    init_models,
)

__all__ = [
    'admin_appointments_bp',
    'appointments_api_bp',
    'appointments_bp',
    'appointments_http_legacy_bp',
    'ensure_models',
    'init_models',
]
