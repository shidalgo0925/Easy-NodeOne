"""Licenciamiento EN1 Core — preparación ADR-005 (sin cupos activos).

NULL o -1 en campos max_* = ilimitado.
LicensePolicy siempre permite en esta fase.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal

LicenseResource = Literal[
    'company',
    'branch',
    'pos',
    'register',
    'cash_register',
    'device',
    'user',
]

UNLIMITED = -1


@dataclass(frozen=True)
class LicenseLimits:
    """Cupos del tenant. None / -1 = ilimitado."""

    max_companies: int | None = UNLIMITED
    max_branches: int | None = UNLIMITED
    max_pos: int | None = UNLIMITED
    max_cash_registers: int | None = UNLIMITED
    max_devices: int | None = UNLIMITED
    max_users: int | None = UNLIMITED
    features: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @staticmethod
    def is_unlimited(value: int | None) -> bool:
        return value is None or int(value) < 0

    @classmethod
    def unlimited(cls) -> LicenseLimits:
        return cls()


class LicensePolicy:
    """Contrato de políticas de licencia.

    Fase actual: **siempre permite**. Fase futura: consulta EN1 / cupos reales.
    EPosOne no conoce planes; solo consume este contrato.
    """

    def __init__(self, limits: LicenseLimits | None = None) -> None:
        self.limits = limits or LicenseLimits.unlimited()

    def can_create_company(self) -> bool:
        return True

    def can_create_branch(self) -> bool:
        return True

    def can_create_pos(self) -> bool:
        return True

    def can_create_cash_register(self) -> bool:
        return True

    def can_create_register(self) -> bool:
        return self.can_create_cash_register()

    def can_create_device(self) -> bool:
        """Dispositivos no consumen licencia POS; siempre permitido en v1."""
        return True

    def can_create_user(self) -> bool:
        return True

    def can_create(self, resource: str) -> bool:
        key = (resource or '').strip().lower()
        mapping = {
            'company': self.can_create_company,
            'branch': self.can_create_branch,
            'pos': self.can_create_pos,
            'pos_point': self.can_create_pos,
            'register': self.can_create_register,
            'cash_register': self.can_create_cash_register,
            'device': self.can_create_device,
            'user': self.can_create_user,
        }
        fn = mapping.get(key)
        if fn is None:
            return True
        return bool(fn())

    def has_feature(self, feature: str) -> bool:
        _ = feature
        # Sin catálogo de features activo — todo permitido
        return True

    def assert_can_create(self, resource: str) -> None:
        if not self.can_create(resource):
            raise PermissionError(f'license_denied:{resource}')


def default_policy() -> LicensePolicy:
    """Política por defecto del Core (ilimitada)."""
    return LicensePolicy(LicenseLimits.unlimited())


def policy_for_organization(organization_id: int) -> LicensePolicy:
    """Resuelve política del tenant. Hoy: siempre ilimitada (sin persistencia)."""
    _ = organization_id
    return default_policy()
