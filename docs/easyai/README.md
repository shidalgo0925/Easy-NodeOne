# EasyAI Core — CODITO Connector Pack (EN1)

| Campo | Valor |
|-------|--------|
| Rol CODITO | Arquitecto de Contexto Empresarial |
| Proyecto | EasyAI Core |
| Estado | **Diseño V1** — interfaces + catálogos (sin wiring runtime, sin LLM) |
| Código SDK | `backend/nodeone/core/easyai/` |
| Fecha | 5 ago 2026 |
| Inventario previo | Conversación inventario CODITO ↔ ARP |

---

## Qué es / qué no es

**Es:** contrato para que EasyAI consuma EN1 vía **connectors de dominio** (contextos, herramientas, eventos) sobre **servicios** existentes.

**No es:** gateway LLM, prompts, RAG, embeddings, ni conexión a GPT. Eso es EasyAI / ARP.

---

## Entregables

| Entregable | Archivo |
|------------|---------|
| Connector SDK (interfaces) | `backend/nodeone/core/easyai/` |
| Connector Specification | [`CONNECTOR_SPECIFICATION.md`](CONNECTOR_SPECIFICATION.md) |
| API Contracts | [`API_CONTRACTS.md`](API_CONTRACTS.md) |
| Context Catalog | [`CONTEXT_CATALOG.md`](CONTEXT_CATALOG.md) |
| Tool Catalog | [`TOOL_CATALOG.md`](TOOL_CATALOG.md) |
| Event Catalog | [`EVENT_CATALOG.md`](EVENT_CATALOG.md) |

---

## Principios (congelados V1)

1. **Solo servicios** — prohibido exponer tablas, SQL, sesiones ORM.
2. **Tres superficies por dominio:** Contextos · Herramientas · Eventos.
3. **Interfaces primero** — `DomainConnector` Protocol; adapters EN1 = fase wiring (GO aparte).
4. **Request compuesto** — EasyAI no inventa `organization_id`; lo recibe en `ConnectorRequest`.
5. **DTO JSON** — `payload` / tool results serializables.
6. **Complemento ARP** — CODITO = negocio; ARP = IA.

---

## Dominios V1 (`domain_id`)

`organizations` · `users` · `crm` · `contacts` · `membership` · `payments` · `subscriptions` · `licenses` · `analytics` · `dashboard` · `commerce` · `products` · `history` · `audit` · `event_bus` · `context_resolver` · `resolver` · `entitlements`

Ver `domains.py` y catálogos.

---

## Fases posteriores (fuera de este entregable)

| Fase | Contenido |
|------|-----------|
| Wiring | Adapters que llaman servicios EN1 existentes |
| HTTP façade (opcional) | `/api/easyai/v1/...` para consumo remoto |
| Enforcement | AuthZ + entitlement en cada tool |
| Multi-org platform tools | Solo tras contrato explícito |

---

## Cómo validar el diseño

```bash
cd /opt/easynodeone/dev/app/backend
# Import del SDK (sin Flask app)
python -c "from nodeone.core.easyai import DomainConnector, ConnectorRegistry, DOMAIN_IDS; print(len(DOMAIN_IDS))"
```
