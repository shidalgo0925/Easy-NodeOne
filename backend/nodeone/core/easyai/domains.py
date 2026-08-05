"""Stable domain identifiers for EasyAI connectors (EN1)."""

from __future__ import annotations

from typing import Final, Literal

DomainId = Literal[
    'organizations',
    'users',
    'crm',
    'contacts',
    'membership',
    'payments',
    'subscriptions',
    'licenses',
    'analytics',
    'dashboard',
    'commerce',
    'products',
    'history',
    'audit',
    'event_bus',
    'context_resolver',
    'resolver',
    'entitlements',
]

DOMAIN_IDS: Final[tuple[str, ...]] = (
    'organizations',
    'users',
    'crm',
    'contacts',
    'membership',
    'payments',
    'subscriptions',
    'licenses',
    'analytics',
    'dashboard',
    'commerce',
    'products',
    'history',
    'audit',
    'event_bus',
    'context_resolver',
    'resolver',
    'entitlements',
)
