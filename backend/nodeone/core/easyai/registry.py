"""In-process registry of DomainConnector implementations."""

from __future__ import annotations

from typing import Iterable

from nodeone.core.easyai.contracts import DomainConnector, ToolDescriptor
from nodeone.core.easyai.domains import DOMAIN_IDS


class ConnectorRegistry:
    """Registers connectors by domain_id. No auto-discovery in V1."""

    def __init__(self) -> None:
        self._by_id: dict[str, DomainConnector] = {}

    def register(self, connector: DomainConnector) -> None:
        did = str(connector.domain_id)
        if did not in DOMAIN_IDS:
            raise ValueError(f'unknown_domain_id:{did}')
        if did in self._by_id:
            raise ValueError(f'duplicate_domain_id:{did}')
        self._by_id[did] = connector

    def get(self, domain_id: str) -> DomainConnector | None:
        return self._by_id.get(str(domain_id))

    def all(self) -> list[DomainConnector]:
        return [self._by_id[k] for k in DOMAIN_IDS if k in self._by_id]

    def list_all_tools(self) -> list[ToolDescriptor]:
        tools: list[ToolDescriptor] = []
        for c in self.all():
            tools.extend(list(c.list_tools()))
        return tools

    def registered_domain_ids(self) -> list[str]:
        return [k for k in DOMAIN_IDS if k in self._by_id]

    def missing_domain_ids(self) -> list[str]:
        return [k for k in DOMAIN_IDS if k not in self._by_id]
