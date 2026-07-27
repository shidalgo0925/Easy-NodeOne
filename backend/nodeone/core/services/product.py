"""ProductService — catálogo maestro (Etapa 10d)."""

from __future__ import annotations

from typing import Any

from nodeone.core.master.dtos import ProductDTO
from nodeone.core.master.product import CoreProductService

ProductServiceNotReadyError = NotImplementedError


class ProductService:
    """API Core para catálogo unificado (`core_product`)."""

    @staticmethod
    def search(
        organization_id: int,
        *,
        query: str | None = None,
        product_type: str | None = None,
        status: str | None = None,
        limit: int = 50,
    ) -> list[ProductDTO]:
        return CoreProductService.search(
            int(organization_id),
            query=query,
            product_type=product_type,
            status=status,
            limit=limit,
        )

    @staticmethod
    def get_by_ref(organization_id: int, product_ref: str) -> ProductDTO | None:
        return CoreProductService.get_by_ref(int(organization_id), product_ref)

    @staticmethod
    def create(organization_id: int, data: dict[str, Any]) -> ProductDTO:
        return CoreProductService.create(int(organization_id), data)

    @staticmethod
    def update(organization_id: int, product_ref: str, data: dict[str, Any]) -> ProductDTO:
        return CoreProductService.update(int(organization_id), product_ref, data)

    @staticmethod
    def deactivate(organization_id: int, product_ref: str) -> ProductDTO:
        return CoreProductService.deactivate(int(organization_id), product_ref)

    @staticmethod
    def delete(organization_id: int, product_ref: str) -> None:
        CoreProductService.delete(int(organization_id), product_ref)

    @staticmethod
    def has_operational_usage(organization_id: int, product_ref: str) -> bool:
        return CoreProductService.has_operational_usage(int(organization_id), product_ref)

