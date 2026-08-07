# ADR-034 — Connected Provisioning Flow

| Campo | Valor |
|-------|--------|
| ID | **ADR-034** |
| Título | Flujo de aprovisionamiento Connected — Implementación Asistida |
| Estado | **PROPOSED** — pendiente revisión / aprobación Arquitectura · handoff CODITO |
| Versión | 1.0 |
| Fecha | Agosto 2026 |
| Autor | Arquitectura EN1 / EPosOne |
| Impacto | EN1 · Portal ETS · Device API · EPosOne APK (consumo) |
| Implementación de código | **NO autorizada** — documento de arquitectura únicamente |
| Pregunta rectora | **¿Cómo materializa ETS un EPosOne Connected antes de que el dispositivo opere?** |
| Responsable de análisis EN1 | **CODITO** |
| Complementa | [ADR-032](ADR-032-PRODUCT-IMPLEMENTATION-MODEL.md) (§ Asistida) · [ADR-031](ADR-031-EN1-COMMERCIAL-DOMAIN-ARCHITECTURE.md) |
| Activación | [ADR-035](ADR-035-ACTIVATION-LICENSE-TOKEN-QR.md) (Licencia → Token → transporte) |
| Relacionados | [ADR-021](ADR-021-EPOSONE-INSTALLATION-LIFECYCLE.md) · [ADR-027](ADR-027-EPOSONE-ONBOARDING-UNIFICADO-V1.md) · [ADR-003](ADR-003-EPOSONE-SYNC.md) · [ADR-024](ADR-024-EPOSONE-START-ASSISTANT.md) |

---

## 1. Objetivo

Definir el **flujo de implementación asistida** de EPosOne **Connected**: cómo Easy Technology Services (ETS) crea la infraestructura operacional en EN1 **antes** del provisioning del dispositivo.

**Única responsabilidad:** el camino Connected post-registro comercial hasta operación sincronizada.

No define quién implementa en abstracto (ADR-032), ni el asistente Standalone (ADR-033), ni el modelo formal Licencia/Token/QR (ADR-035).

---

## 2. Precondiciones

1. Registro comercial completo (ADR-031): Cliente → Organización → Contrato → Suscripción → Licencia.  
2. Modalidad del contrato/suscripción: **Connected** / estrategia **Asistida** (ADR-032).  
3. Correo verificado según política comercial vigente (ADR-031 §9) antes de emitir/activar licencia operativa.  
4. Caso asignado a cola / ejecutivo de **implementación** ETS.

---

## 3. Flujo canónico

```text
Licencia (Connected / Asistida)
  → Asignación a implementación
  → Configuración operacional en EN1
       → Sucursal
       → POS
       → Caja
       → Cajeros (mínimo administrador operativo)
  → Emisión de Token de activación (ADR-035)
  → Entrega del token (correo / enlace / QR / copia)
  → Cliente descarga APK
  → Activación con token
  → Provisioning (device ↔ caja)
  → Bootstrap
  → Operación (sync)
```

Principio ADR-032: **Connected requiere implementación ETS antes del aprovisionamiento del dispositivo.**

---

## 4. Fases

| Fase | Actor | Resultado |
|------|-------|-----------|
| **A. Asignación** | ETS | Ticket/caso de implementación ligado a Contrato/Licencia |
| **B. Árbol ops** | CODITO / ops EN1 | Sucursal → POS → Caja (+ cajeros) en la Organización |
| **C. Token** | EN1 | Token de activación anclado a Licencia + caja/dispositivo previsto (ADR-035) |
| **D. Entrega** | ETS / Portal | Token al cliente por canal acordado |
| **E. Device** | Cliente + APK | Activación; modalidad Connected fijada por token (sin pregunta UX) |
| **F. Cloud** | EN1 Device API | Provisioning + bootstrap + sync operativa |

---

## 5. Qué crea EN1 (Connected)

A diferencia de Standalone, en Connected **sí** se materializa en EN1 (fase B), como mínimo:

- Sucursal  
- POS  
- Caja  
- Cajero(s) operativo(s)  

Catálogo, políticas comerciales, impuestos, etc. según el alcance del servicio de implementación contratado (pueden cargarse en B o en sesiones posteriores).

---

## 6. Qué NO hace este flujo

- Asistente local de negocio estilo ADR-033 (no es el camino principal Connected).  
- Preguntar al usuario “¿Standalone o Connected?” en la APK.  
- Tratar el QR como la orden de activación (la orden es la **Licencia**; ADR-035).  
- Sustituir el registro comercial (`/start` / Portal).

---

## 7. Relación con provisioning / bootstrap existentes

| Capa | Rol en Connected |
|------|------------------|
| Árbol OrgUnit | Creado en fase B (asistida) |
| Token / código | Fase C–D (ADR-035); puede mapear a código por caja |
| Provisioning | Fase F — vincula terminal a caja ya existente |
| Bootstrap | Fase F — catálogo y config cloud → dispositivo |
| Sync | Operación continua (ADR-003) |

Contratos HTTP detallados de device API: fuera de este ADR (evolucionar ADR-021 / contratos device con GO).

---

## 8. Responsabilidades

| Actor | Hace |
|-------|------|
| **ETS / CODITO** | Asignación, árbol ops, emisión token, soporte de implementación |
| **Cliente** | Instala APK, activa con token, opera |
| **LOCAL** | APK consume token Connected y ejecuta provisioning/bootstrap (sin elegir modalidad) |

---

## 9. Impacto (analizar, no implementar)

### CODITO

- Cola de implementación y estados del caso  
- UI/ops para crear Sucursal→POS→Caja→Cajero bajo Contrato Connected  
- Emisión de token post-árbol (ADR-035)  
- No crear árbol ops en altas Standalone  

### LOCAL

- Flujo APK Connected post-token (sin asistente Standalone completo)  
- Errores si el token exige Connected pero el árbol no está listo  

---

## 10. Fuera de alcance

Código; cambios a `/start`; ADR-033; payload criptográfico del token (ADR-035); billing de servicios de implementación.

---

## 11. Estado

**PROPOSED**

Handoff conceptual para CODITO. Requiere aprobación Arquitectura + **GO de implementación** por fases.
