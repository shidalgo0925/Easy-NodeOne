"""Capacidades oficiales del Core (sin lógica de negocio vertical)."""

from __future__ import annotations

from enum import Enum


class CoreCapability(str, Enum):
    SECURITY = 'security'
    TENANT = 'tenant'
    IDENTITY = 'identity'
    LICENSING = 'licensing'
    FILES = 'files'
    NOTIFICATIONS = 'notifications'
    API = 'api'
    AUDIT = 'audit'
    CONFIG = 'config'
    PAYMENTS_INFRA = 'payments_infra'
    CONTACTS_MASTER = 'contacts_master'
    AI_SERVICE = 'ai_service'
