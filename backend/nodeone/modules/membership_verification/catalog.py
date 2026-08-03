"""Catálogo interno de APIs publicadas (Sprint B: APIs Disponibles)."""

from __future__ import annotations

API_CATALOG: tuple[dict, ...] = (
    {
        'id': 'membership_verification',
        'name': 'Membership Verification',
        'version': 'v1',
        'status': 'active',
        'method': 'POST',
        'path': '/api/v1/membership/verification',
        'auth': 'X-API-Key',
        'supported_types': ('email',),
        'reserved_types': ('member_number', 'document', 'qr', 'barcode', 'nfc'),
    },
)

SUPPORTED_VERIFICATION_TYPES = frozenset({'email'})
RESERVED_VERIFICATION_TYPES = frozenset(
    {'member_number', 'document', 'qr', 'barcode', 'nfc'}
)
PERMISSION_API_MANAGER = 'integrations.manage'
