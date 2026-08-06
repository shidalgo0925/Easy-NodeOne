# ADR-026 — Easy Integration Specification (EIS) v1.0 Frozen

| Campo | Valor |
|-------|--------|
| ID | **ADR-026** |
| Título | Easy Integration Specification (EIS) v1.0 — norma única del Connector SDK |
| Estado | **Aprobado / Frozen** — 5 ago 2026 |
| Decisores | CODITO (contratos) · alineado a reparto ARP (runtime) · LOCAL (Connectors) |
| Paquete normativo | [`docs/easyai/eis/`](easyai/eis/README.md) |

---

## Contexto

EasyAI Core (ARP) concentra gateway, conversación, seguridad de runtime, prompts y auditoría.  
EPOSOne Operations Connector lo implementará LOCAL.  
CODITO no implementa IA ni productos: define **cómo** cualquier producto habla con EasyAI Core.

Existía riesgo de **dos normas** (EIS vs “Connector SDK” vs “AI SDK”) describiendo lo mismo.

---

## Decisión

1. **Una sola norma:** **Easy Integration Specification (EIS) v1.0**.
2. El nombre comercial **Connector SDK** designa el *conjunto de contratos* que el EIS define — **no** es una especificación separada ni una librería obligatoria de CODITO.
3. Prohibido crear normas paralelas (“AI SDK”, “Connector SDK SPEC” fuera del EIS).
4. CODITO entrega solo **documentación normativa** (ADR, SPEC, diagramas, checklist, conformidad).
5. ARP implementa runtime **consumiendo** EIS; no redefine contratos.
6. LOCAL implementa el primer Connector real (**EPOSOne Operations Connector**) **conforme** a EIS; no modifica la especificación.

### Principios congelados

- Solo EasyAI Core conversa con modelos (OpenAI, Gemini, Ollama, …).
- Productos no acceden a LLMs directamente.
- Productos conservan toda la lógica de negocio.
- Productos exponen únicamente **Contexts · Tools · Events** (+ Sessions / Discovery / Security según EIS).
- La IA razona sobre contratos, nunca sobre SQL/tablas.

---

## Consecuencias

**Positivo:** una fuente de verdad; continuidad del pack EIS S1; gate claro ARP/LOCAL.  
**Riesgo mitigado:** dualidad EIS/SDK.  
**Fuera de alcance CODITO:** código, endpoints, EN1, EPosOne, runtime IA.

---

## Paquete Frozen

Ver [`docs/easyai/eis/FROZEN.md`](easyai/eis/FROZEN.md) y [`docs/easyai/eis/README.md`](easyai/eis/README.md).

---

## Changelog

| Fecha | Nota |
|-------|------|
| 2026-08-05 | Aprobado — EIS v1.0 Frozen como norma única |
