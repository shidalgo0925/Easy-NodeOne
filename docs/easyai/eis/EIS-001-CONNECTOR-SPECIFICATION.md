# EIS-001 — Connector SDK Specification

| Campo | Valor |
|-------|--------|
| ID | **EIS-001** |
| Título | Connector SDK Specification |
| Versión | **1.0.0** |
| Estado | **Frozen / Approved** |
| Padre | EIS-000 |
| Nota de naming | “Connector SDK” = contratos de este documento + EIS-002…011 — **no** es una norma separada del EIS |

---

## 1. Qué es el Connector SDK

El Connector SDK es el **conjunto normativo** que un producto debe cumplir para integrarse con EasyAI Core:

| Pieza | Documento |
|-------|-----------|
| Ciclo de vida / registro | Este documento |
| Contexts | EIS-002 |
| Tools | EIS-003 |
| Events | EIS-004 |
| Auth | EIS-005 |
| Manifest | EIS-006 |
| Discovery | EIS-007 |
| Errors | EIS-008 |
| Sessions | EIS-009 |
| Versionado | EIS-010 |
| Security | EIS-011 |
| Checklist | CONFORMITY-CHECKLIST |

CODITO **no** entrega librería obligatoria. ARP/LOCAL pueden publicar SDKs de *implementación* alineados a este contrato.

---

## 2. Connector

Unidad de integración de un producto (o dominio) hacia EasyAI Core.

### Obligaciones

1. `connector_id` estable (kebab-case, único ETS).
2. Manifest válido (EIS-006).
3. Superficies Contexts / Tools / Events según declaración.
4. Auth (EIS-005) + Security (EIS-011) + Errors (EIS-008).
5. Health endpoint lógico (ver §8).
6. Sin filtrar secretos; sin SQL hacia EasyAI; sin llamadas a LLMs.

### Tipos

| Tipo | Uso |
|------|-----|
| Product Connector | Producto completo (`eposone`, `en1-platform`, `em-accion`) |
| Domain Connector | Opcional, modularidad interna |

V1 recomienda Product Connector + capabilities.

---

## 3. Ciclo de vida

```text
declared → registered → discoverable → ready → deprecated → retired
```

| Estado | Significado |
|--------|-------------|
| `declared` | En catálogo / diseño |
| `registered` | Conocido por EasyAI |
| `discoverable` | Discovery entrega Manifest |
| `ready` | Invocable en el ambiente |
| `deprecated` | Aún responde; fecha de retiro |
| `retired` | Solo histórico |

---

## 4. Registro

1. Entrada en Connector Catalog.
2. `manifest_url` por ambiente.
3. Importación por Discovery (EIS-007) o registro operativo controlado.
4. Sin auto-registro silencioso en producción sin revisión.

---

## 5. Descubrimiento

EIS-007. Obligatorio para estado `discoverable` / `ready`.

---

## 6. Capacidades

`capabilities[]` del Manifest ⊆ Capability Catalog.  
Autorización EasyAI por capability + scope (EIS-005), no por tablas.

---

## 7. Operaciones lógicas del Connector

| Operación | Descripción |
|-----------|-------------|
| `GET manifest` | Manifest |
| `GET health` | Liveness/readiness |
| `GET contexts` / resolve | EIS-002 |
| `GET tools` | Descriptors |
| `POST tools/{id}/invoke` | EIS-003 |
| `GET events/types` | EIS-004 |
| Events pull/push | Según declaración |

Transporte HTTP concreto lo implementa el producto/ARP en sprints posteriores; la forma es normativa.

---

## 8. Health

Contrato mínimo de respuesta:

```json
{
  "status": "ok",
  "connector_id": "eposone",
  "connector_version": "1.0.0",
  "eis_version": "1.0.0",
  "checks": { "ready": true }
}
```

`status`: `ok` | `degraded` | `unavailable`.  
EasyAI marca Connector unavailable tras fallos repetidos de health (política runtime ARP).

---

## 9. Interoperabilidad con EasyAI Core

| EasyAI Core (ARP) | Usa del Connector |
|-------------------|-------------------|
| Context Builder | Contexts + Session (EIS-009) |
| Tool Dispatcher | Tools invoke |
| Conversation / Memory | Eventos + resultados (no redefine schemas) |
| AI Gateway | **No** llama al Connector para modelos |

El Connector **nunca** es un proxy hacia LLM.
