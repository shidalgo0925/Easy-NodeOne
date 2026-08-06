# EIS-000 — Easy Integration Specification (raíz)

| Campo | Valor |
|-------|--------|
| ID | **EIS-000** |
| Título | Easy Integration Specification |
| Versión | **1.0.0** |
| Estado | **Frozen / Approved** |
| ADR | ADR-026 |
| Ámbito | Ecosistema ETS × EasyAI Core |

---

## 1. Objetivos

1. Ser la **única norma** de integración producto ↔ EasyAI Core.
2. Definir el **Connector SDK** (conjunto de contratos) sin ser una segunda especificación.
3. Permitir Contexts · Tools · Events · Sessions sin exponer SQL/tablas.
4. Separar: **producto = negocio** · **EasyAI Core = inteligencia**.
5. Habilitar Discovery, Security, Versionado y conformidad multi-producto.

---

## 2. Alcance

### Incluye (normativo)

Connector SDK · Contexts · Tools · Events · Sessions · Discovery · Capabilities · Security · Authentication · Manifest · Errors · Versionado · Compatibilidad · Health (contrato) · Checklist.

### Excluye

- Implementación de LLMs, prompts, embeddings, RAG, Memory runtime.
- Código de Connectors en productos (eso es LOCAL / owners).
- DDL/SQL/ORM hacia EasyAI.
- Redefinición de contratos por ARP o LOCAL.

---

## 3. Principios (congelados)

| # | Principio |
|---|-----------|
| P1 | Solo contratos — no SQL/tablas/ORM |
| P2 | Superficies: Contexts + Tools + Events (Sessions en el Core) |
| P3 | Producto dueño del dato |
| P4 | Tenant primero |
| P5 | Least privilege (capabilities / scopes) |
| P6 | Idempotencia preferente en writes |
| P7 | Evolución aditiva (MAJOR = ruptura) |
| P8 | Un solo canal hacia EasyAI Core |
| P9 | Observabilidad (errors + audit metadata) |
| P10 | Independencia de lenguaje de implementación |
| P11 | **Solo EasyAI Core** habla con modelos de IA |
| P12 | Productos **nunca** llaman OpenAI/Gemini/Ollama/etc. directamente |

---

## 4. Terminología

| Término | Definición |
|---------|------------|
| **EIS** | Esta especificación (norma única) |
| **Connector SDK** | Nombre del *conjunto de contratos* definidos por el EIS — no norma aparte |
| **EasyAI Core** | Runtime de IA (ARP) |
| **Connector** | Adaptador de producto conforme a EIS-001 |
| **Context / Tool / Event / Session** | Ver EIS-002 / 003 / 004 / 009 |
| **Capability** | Permiso abstracto (catálogo) |
| **Manifest** | Declaración estática (EIS-006) |

---

## 5. Arquitectura lógica

Ver diagramas en `diagrams/`. Flujo:

```text
Producto ETS ──Connector (EIS)──► EasyAI Core (ARP)
                                      │
                                      ├── Context Builder
                                      ├── Tool Dispatcher
                                      ├── Conversation / Memory
                                      └── AI Gateway → Modelos
```

---

## 6. Versionado del EIS

SemVer **MAJOR.MINOR.PATCH**. Actual: **1.0.0** Frozen.  
Detalle: EIS-010.

---

## 7. Conformidad

Un Connector es conforme si cumple [`CONFORMITY-CHECKLIST.md`](CONFORMITY-CHECKLIST.md).

---

## 8. Documentos hijos

EIS-001 … EIS-011 + catálogos — índice en [`README.md`](README.md).

---

## 9. Changelog

| Versión | Fecha | Notas |
|---------|-------|-------|
| 1.0.0 | 2026-08-05 | Frozen — norma única; Connector SDK definido por EIS |
