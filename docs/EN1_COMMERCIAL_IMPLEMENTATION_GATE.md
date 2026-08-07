# EN1 — Gate de implementación comercial / producto

| Campo | Valor |
|-------|--------|
| ID | **EN1-COMMERCIAL-IMPLEMENTATION-GATE** |
| Fecha | Agosto 2026 |
| Estado | **Activo** — congelamiento post Fase 1 |
| Audiencia | CODITO (EN1) · LOCAL (EPosOne APK) · Arquitectura |

---

## 1. Contexto

Queda **cerrado** el bloque de arquitectura del Dominio Comercial e Implementación estratégica:

| ADR | Tema | Estado |
|-----|------|--------|
| **031** | Dominio Comercial | **Aprobado** |
| **032** | Modelo de Implementación (¿quién?) | **Aprobado** |
| **033** | Asistente Standalone | **PROPOSED (completo revisión)** |
| **034** | Connected Provisioning | **PROPOSED (completo revisión)** |
| **035** | Licencia → Token → QR | **PROPOSED (completo revisión)** |

**Código ya hecho (único):** Fase 1 comercial — `/start` crea Cliente/Contrato/Suscripción **sin** árbol operacional automático.

---

## 2. Separación obligatoria de conceptos

```text
Registro Comercial  →  Implementación  →  Provisioning  →  Operación
   ADR-031               032/033/034         device API         sync
```

No volver a mezclar alta comercial con creación de Sucursal/POS/Caja ni con bootstrap.

---

## 3. Congelamiento — dominio comercial (CODITO)

**No modificar** salvo corrección de errores:

- Cliente  
- Organización (identidad)  
- Contrato  
- Suscripción  
- Licencia (modelo conceptual; entidad física futura bajo GO)

Dominio comercial estabilizado. No deuda técnica nueva en esta capa.

---

## 4. Trabajo autorizado ahora

### CODITO

- Revisar / refinar docs **ADR-034** y **ADR-035** (ya especificados v1.1).  
- Comentarios de arquitectura en esos ADR.  
- **Sin código.**

### LOCAL

- Diseñar UX según **ADR-033** (wireframes fuera o anexos).  
- Analizar pasos, offline, ayuda, copy de soporte.  
- **Mantener flujo APK vigente.**  
- **Sin código** del asistente nuevo / token / QR definitivo.

---

## 5. No iniciar todavía

| Prohibido hasta Gate |
|----------------------|
| Portal ETS nuevo |
| Email verification productizado |
| Connected provisioning (código) |
| QR / Token canónicos (código) |
| Asistente Standalone nuevo (código) |
| Refactors / eliminación de endpoints / dead code cleanup masivo |
| Cambios a Register / Bootstrap / Gate 2 / Welcome / licenciamiento APK |

---

## 6. Criterio de cierre de esta etapa (apertura de implementación)

**No** se inicia implementación Standalone ni Connected hasta que estén **aprobados**:

1. ADR-033  
2. ADR-034  
3. ADR-035  

Después: **chat/ciclo nuevo**, implementación por fases, coherente con ADR-031 y ADR-032.

---

## 7. Referencias

- [ADR-031](ADR-031-EN1-COMMERCIAL-DOMAIN-ARCHITECTURE.md)  
- [ADR-032](ADR-032-PRODUCT-IMPLEMENTATION-MODEL.md)  
- [ADR-033](ADR-033-STANDALONE-ONBOARDING-ASSISTANT.md)  
- [ADR-034](ADR-034-CONNECTED-PROVISIONING-FLOW.md)  
- [ADR-035](ADR-035-ACTIVATION-LICENSE-TOKEN-QR.md)  
