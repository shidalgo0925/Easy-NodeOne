# Validación cruzada ARP · CODITO · LOCAL — EIS v1.0

| Campo | Valor |
|-------|--------|
| Norma | EIS 1.0.0 Frozen |
| ADR | ADR-026 |
| Fecha | 5 ago 2026 |
| Objetivo | Confirmar que el contrato único es implementable sin solapar roles |

---

## 1. Reparto (fuente de verdad)

| Actor | Entrega | Consume |
|-------|---------|---------|
| **CODITO** | EIS Frozen (esta carpeta) | — |
| **ARP** | EasyAI Core runtime (Gateway, Context Builder, Tool Dispatcher, Memory, Conversation, Security Foundation, auditoría runtime) | EIS tal cual |
| **LOCAL** | EPOSOne Operations Connector | EIS tal cual |
| **Productos (EN1, EM1, …)** | Futuros Connectors | EIS tal cual |

Nadie más redefine Contexts/Tools/Events/Sessions.

---

## 2. Matriz de no-solapamiento

| Responsabilidad | CODITO | ARP | LOCAL |
|-----------------|--------|-----|-------|
| Redactar/cambiar EIS | ✅ | ❌ | ❌ |
| AI Gateway / modelos | ❌ | ✅ | ❌ |
| Conversation / Memory / Prompt | ❌ | ✅ | ❌ |
| Context Builder (ensambla Contexts EIS) | ❌ | ✅ | ❌ |
| Tool Dispatcher (invoke EIS) | ❌ | ✅ | ❌ |
| EPOSOne Operations Connector | ❌ | ❌ | ✅ |
| Lógica de negocio POS | ❌ | ❌ | ✅ (producto) |
| Aprovisionamiento EN1 (código/device) | Fuera EIS* | ❌ | Consume APIs producto |

\*El inventario de provisioning EN1 informa **qué Tools/Contexts** puede exponer el Connector; no es trabajo de este freeze.

---

## 3. Contraste ARP (EasyAI Core)

| Pieza ARP (existente / prevista) | Relación con EIS |
|----------------------------------|------------------|
| AI Gateway | Downstream de Conversation — **no** pasa por Connector |
| Conversation | Usa Session EIS-009 + resultados Tool |
| Security Foundation | Complementa EIS-011 (runtime vs canal Connector) |
| Prompt Manager | Fuera EIS — no redefine Tool schemas |
| Auditoría runtime | Puede correlacionar `request_id` / `session_id` EIS |
| Context Builder | **Debe** pedir Contexts según EIS-002 + Manifest |
| Tool Dispatcher | **Debe** invocar según EIS-003 + Errors EIS-008 |

**Conclusión ARP:** puede implementar runtime sin modificar EIS; cualquier extensión de contrato = MINOR/MAJOR EIS vía CODITO.

---

## 4. Contraste CODITO

| Entrega | Estado |
|---------|--------|
| Norma única EIS | ✅ Frozen |
| Connector SDK = contratos EIS | ✅ (EIS-001) |
| Sessions / Security / Versionado | ✅ EIS-009/010/011 |
| Checklist | ✅ |
| Código / endpoints / EN1 changes | ❌ Fuera de alcance (cumplido) |

**Conclusión CODITO:** misión de contratos cerrada en v1.0; mantenimiento = cambios versionados solamente.

---

## 5. Contraste LOCAL (EPOSOne Operations Connector)

| Requisito EIS | Factibilidad con EN1/EPosOne actual |
|---------------|-------------------------------------|
| Contexts commerce/dashboard/license | ✅ Servicios OCC/dashboard/license existen (fachada Connector) |
| Tools read operaciones | ✅ |
| Events commerce | ✅ Outbox / order events (mapear aliases) |
| Manifest + Discovery | 🟡 A implementar por LOCAL/producto — contrato listo |
| Sessions | ✅ LOCAL no implementa Session EasyAI; solo Call Context |
| No LLM en producto | ✅ Cumple principio |
| Provisioning gaps (revoke device, etc.) | ⚠ Son gaps de **producto EN1**, no del EIS; el Connector puede empezar read-only |

**Conclusión LOCAL:** puede desarrollar el primer Connector **read-only** conforme a EIS sin esperar cerrar todos los gaps de provisioning; writes/admin Tools requieren GO aparte.

---

## 6. Riesgos residuales

1. Que ARP “extienda” schemas en código sin bump EIS → **prohibido**.  
2. Que LOCAL publique Tools fuera de Manifest → **no conforme**.  
3. Que EN1/CODITO reabra features de Core IA → **fuera de rol**.  
4. Dual naming en chats (“SDK” vs “EIS”) → usar: *EIS define el Connector SDK*.

---

## 7. Veredicto

| Pregunta | Respuesta |
|----------|-----------|
| ¿Hay una sola norma? | **Sí — EIS v1.0** |
| ¿ARP puede construir runtime? | **Sí** |
| ¿LOCAL puede construir EPOSOne Operations Connector? | **Sí** |
| ¿CODITO debe seguir desarrollando EN1/EasyAI Core? | **No** (salvo mantenimiento EIS) |

**Gate de salida S1/Freeze: CUMPLIDO a nivel documental.**
