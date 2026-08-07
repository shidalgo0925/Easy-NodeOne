# EN1 — Gate de implementación comercial / producto

| Campo | Valor |
|-------|--------|
| ID | **EN1-COMMERCIAL-IMPLEMENTATION-GATE** |
| Fecha | Agosto 2026 |
| Estado | **LIBERADO** — 7 ago 2026 · ADR-033 + ADR-034 + ADR-035 **ACCEPTED** |
| Audiencia | CODITO (EN1) · LOCAL (EPosOne APK) · Arquitectura |

---

## 1. Resultado

```text
ADR-033 + ADR-035 + ADR-034 ACCEPTED  →  COMMERCIAL IMPLEMENTATION GATE OPEN
```

| ADR | Tema | Estado |
|-----|------|--------|
| **031** | Dominio Comercial | **ACCEPTED** (+ Fase 1 código `/start` sin árbol ops) |
| **032** | Modelo de Implementación | **ACCEPTED** |
| **033** | Asistente Standalone | **ACCEPTED** v1.2 |
| **034** | Connected Provisioning | **ACCEPTED** v1.2 |
| **035** | Licencia → Token → QR | **ACCEPTED** v1.2 |

---

## 2. Qué significa “LIBERADO”

- Queda **autorizado arquitectónicamente** implementar según 033/034/035.  
- **No** sustituye un **GO de implementación** explícito por fase/equipo.  
- Dominio comercial 031 (Cliente/Contrato/…) sigue **congelado** salvo bugs, hasta GO de cambios comerciales.

Orden de implementación recomendado: **033 → 035 → 034**.

---

## 3. Separación vigente

```text
Registro Comercial → Implementación → Provisioning → Operación
```

| Modalidad | Dueño del árbol ops | Post-activación |
|-----------|---------------------|-----------------|
| Standalone | EP1 local (ADR-033); EN1 **no** crea Sucursal/POS/Caja | READY_TO_SELL local; sin Bootstrap Connected |
| Connected | EN1 antes de Register (ADR-034) | Register → Bootstrap → sync |

QR comercial = `/start`. QR técnico = transporte token (ADR-035).

---

## 4. Instrucciones habilitadas

### LOCAL (tras GO implementación Standalone)

1. Diseñar/implementar asistente ADR-033 hasta **READY_TO_SELL**.  
2. Consumir activación ADR-035 (`modality` / claims); no preguntar modalidad.  
3. No crear árbol Connected en el wizard Standalone.  
4. Mantener puente legacy de códigos hasta que CODITO publique token en prod (GO 035).

### CODITO (tras GO por fase)

1. **035:** emisión/validación/redeem de token; QR técnico; errores tipados.  
2. **034:** casos de implementación, árbol ops, gate `ops_ready`, token Connected.  
3. No recrear árbol ops en `/start` Standalone.  
4. No desplegar sin GO de deploy explícito.

---

## 5. Sigue prohibido sin GO específico

- Deploy a prod de estas features sin pedido explícito.  
- Borrado masivo de endpoints legacy.  
- Mezclar registro comercial con creación de Sucursal/POS/Caja en Standalone.

---

## 6. Referencias

- [ADR-031](ADR-031-EN1-COMMERCIAL-DOMAIN-ARCHITECTURE.md) · [ADR-032](ADR-032-PRODUCT-IMPLEMENTATION-MODEL.md)  
- [ADR-033](ADR-033-STANDALONE-ONBOARDING-ASSISTANT.md) · [ADR-034](ADR-034-CONNECTED-PROVISIONING-FLOW.md) · [ADR-035](ADR-035-ACTIVATION-LICENSE-TOKEN-QR.md)  
