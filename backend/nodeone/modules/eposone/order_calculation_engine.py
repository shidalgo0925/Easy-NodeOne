"""Order Calculation Engine — interfaz preparada (V6).

No implementa algoritmos comerciales. Tras aprobación de contratos V6 + T1
se reemplazará el cuerpo de ``calculate``.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class OrderCalculationResult:
    status: str
    message: str
    engine_version: str = '0.0.0-stub'
    subtotal: float | None = None
    discount_total: float | None = None
    tip_amount: float | None = None
    tax_total: float | None = None
    tax_lines: list[dict[str, Any]] = field(default_factory=list)
    rounding_adjustment: float | None = None
    total: float | None = None
    detail: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class OrderCalculationEngine:
    """Interfaz oficial EN1 para cálculo de operación comercial."""

    ENGINE_VERSION = '0.0.0-stub'

    @staticmethod
    def calculate(
        organization_id: int,
        order_payload: dict[str, Any],
        *,
        branch_ref: str | None = None,
        pos_ref: str | None = None,
        register_ref: str | None = None,
        policy_bundles: dict[str, Any] | None = None,
    ) -> OrderCalculationResult:
        """Calcula totales usando políticas vigentes.

        Infra V6: stub. No aplica fiscal/propinas/promos todavía.
        """
        _ = (
            organization_id,
            order_payload,
            branch_ref,
            pos_ref,
            register_ref,
            policy_bundles,
        )
        return OrderCalculationResult(
            status='not_implemented',
            message=(
                'OrderCalculationEngine pendiente de aprobación contratos V6 '
                '(Motor de Totales + T1). Infra de políticas lista.'
            ),
            engine_version=OrderCalculationEngine.ENGINE_VERSION,
            detail={'ready_for_policies': True},
        )
