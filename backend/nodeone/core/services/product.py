"""ProductService — catálogo maestro (Etapa 11 stub → Etapa 10d)."""

from __future__ import annotations


class ProductServiceNotReadyError(NotImplementedError):
    pass


class ProductService:
    """Contrato reservado. Hoy los catálogos viven por app (services, plans, events)."""

    @staticmethod
    def search(*_args, **_kwargs):
        raise ProductServiceNotReadyError(
            'ProductService pendiente de core_product (Etapa 10d). Usar catálogo de la app hasta entonces.'
        )
