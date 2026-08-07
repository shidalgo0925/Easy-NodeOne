# ADR-032 — Modelo de Implementación de Productos

| Campo | Valor |
|-------|--------|
| ID | **ADR-032** |
| Título | Implementación Autogestionada (Standalone) e Implementación Asistida (Connected) |
| Estado | **Aprobado (arquitectura)** — 7 ago 2026 · GO usuario (v1.1 Licencia/Token/QR) |
| Versión | 1.1 |
| Fecha | Agosto 2026 |
| Autor | Arquitectura EN1 / EPosOne |
| Impacto | EN1 · Portal ETS · EPosOne APK |
| Implementación de código | **NO autorizada** por este ADR — requiere GO de implementación por fases |
| Pregunta rectora | **¿Quién implementa el producto?** |
| Complementa | [ADR-031](ADR-031-EN1-COMMERCIAL-DOMAIN-ARCHITECTURE.md) (dominio comercial) |
| Detalle Standalone (asistente) | [ADR-033](ADR-033-STANDALONE-ONBOARDING-ASSISTANT.md) (**PROPOSED**) |
| Detalle Connected (provisioning) | [ADR-034](ADR-034-CONNECTED-PROVISIONING-FLOW.md) (**PROPOSED**) |
| Activación | [ADR-035](ADR-035-ACTIVATION-LICENSE-TOKEN-QR.md) (**PROPOSED**) |
| Relacionados | [ADR-027](ADR-027-EPOSONE-ONBOARDING-UNIFICADO-V1.md) · [ADR-024](ADR-024-EPOSONE-START-ASSISTANT.md) · [ADR-021](ADR-021-EPOSONE-INSTALLATION-LIFECYCLE.md) · [ADR-001](ADR-001-EPOSONE-STANDALONE.md) · [EN1_MODELO_COMERCIAL_V1.md](EN1_MODELO_COMERCIAL_V1.md) |

---

## 1. Objetivo

Definir las **dos estrategias oficiales de implementación** de productos ETS y **quién** las ejecuta.

Este ADR complementa el [ADR-031](ADR-031-EN1-COMMERCIAL-DOMAIN-ARCHITECTURE.md). **No** especifica pantallas del asistente Standalone ni el flujo detallado de provisioning Connected: eso vive en ADR dedicados (033 / 034).

---

## 2. Problema

EN1 asumía que registrar un cliente implicaba iniciar de inmediato la implementación técnica (`Registro → Org → Provisioning → Bootstrap → Operación`), forzando el mismo camino a Standalone y Connected.

---

## 3. Principio: Comercial ≠ Implementación

El **registro comercial** finaliza cuando el cliente obtiene:

```text
Cliente → Organización → Contrato → Suscripción → Licencia
```

La **implementación** comienza solo cuando el producto debe ponerse en operación.

---

## 4. Estrategias

| Estrategia | Modalidad típica (EPosOne) | ¿Quién implementa? |
|------------|----------------------------|--------------------|
| **Autogestionada** | Standalone | **Cliente** |
| **Asistida** | Connected | **Easy Technology Services** |

Todo producto ETS debe declarar su estrategia.

---

## 5. Implementación Autogestionada (Standalone)

**Responsable:** el cliente.  
**ETS aporta:** licencia, token de activación, documentación, soporte (opcional).

### Flujo (alto nivel)

```text
Registro comercial (ADR-031)
  → Licencia
  → Token de activación
  → Entrega del token (QR / correo / enlace / copia manual)
  → APK activa con el token
  → Asistente local (detalle: ADR-033)
  → Operación
```

### EN1 NO crea automáticamente

Sucursales, POS, cajas, cajeros, inventario cloud, bootstrap cloud.  
La Organización queda como **entidad comercial** (ADR-031).

El detalle del asistente local, ayuda y servicios profesionales embebidos en la APK: **[ADR-033](ADR-033-STANDALONE-ONBOARDING-ASSISTANT.md)**.

---

## 6. Implementación Asistida (Connected)

**Responsable:** Easy Technology Services.

### Flujo (alto nivel)

```text
Registro comercial (ADR-031)
  → Licencia
  → Asignación a implementación
  → Configuración operacional en EN1 (Sucursal → POS → Caja → Cajeros)
  → Token de activación
  → Entrega del token
  → APK → Provisioning → Bootstrap → Operación
```

El detalle del aprovisionamiento Connected: **[ADR-034](ADR-034-CONNECTED-PROVISIONING-FLOW.md)**.

---

## 7. Activación: Licencia → Token → QR

Cadena canónica (desacoplada del QR):

```text
Contrato
  → Suscripción
  → Licencia                 ← derecho / orden de activación
  → Token de Activación      ← referencia usable
  → QR / correo / enlace / copia  ← medios de transporte
  → APK
```

| Concepto | Rol |
|----------|-----|
| **Licencia** | Portadora del derecho de uso y de la **orden de activación** (producto, modalidad, estrategia, vigencia, firma) |
| **Token de activación** | Referencia operable derivada de la licencia; puede enviarse por correo, enlace o copia manual |
| **QR** | **Solo** representación gráfica del token (o de una URL que lo contiene). **No** es la orden |

Ventajas del desacople: el mismo token sirve sin QR; el modelo no depende de un canal visual.

El contrato HTTP/payload del token y la firma: **[ADR-035](ADR-035-ACTIVATION-LICENSE-TOKEN-QR.md)**.

---

## 8. Comportamiento de la APK

La APK **no** pregunta la modalidad al usuario.  
La modalidad y la estrategia salen de la **activación** (licencia vía token). La APK ejecuta el flujo Autogestionado o Asistido según esa información.

---

## 9. Responsabilidades

| Actor | Hace |
|-------|------|
| **Cliente** | Instala APK; completa asistente Standalone (ADR-033); mantiene datos; pide soporte |
| **ETS** | Clientes, contratos, licencias, tokens, documentación, soporte; ejecuta implementaciones asistidas |

---

## 10. Servicios profesionales

La implementación asistida / acompañamiento es un **servicio independiente** del producto: puede ir incluido en el plan o contratarse después, sin cambiar el producto.

---

## 11. Principios

1. Este ADR responde solo: **¿quién implementa?**  
2. Estrategias: Autogestionada o Asistida.  
3. Registro comercial termina antes de la implementación.  
4. Licencia = orden; Token = referencia; QR = transporte.  
5. La APK elige el flujo desde la activación, no desde una pregunta al usuario.  
6. Standalone no requiere infraestructura ops en EN1 para empezar.  
7. Connected requiere implementación ETS antes del aprovisionamiento.  
8. Detalle de pantallas / provisioning → ADR-033 / ADR-034, no aquí.

---

## 12. Impacto esperado (sin implementar)

| Equipo | Analizar contra |
|--------|-----------------|
| **LOCAL** | [ADR-033](ADR-033-STANDALONE-ONBOARDING-ASSISTANT.md) · [ADR-035](ADR-035-ACTIVATION-LICENSE-TOKEN-QR.md) |
| **CODITO** | [ADR-034](ADR-034-CONNECTED-PROVISIONING-FLOW.md) · [ADR-035](ADR-035-ACTIVATION-LICENSE-TOKEN-QR.md) · [ADR-031](ADR-031-EN1-COMMERCIAL-DOMAIN-ARCHITECTURE.md) |

---

## 13. Fuera de alcance

No autoriza cambios en `/start`, bootstrap, provisioning, eliminación de código, ni enmiendas de otros ADR.  
No especifica el asistente Standalone ni el provisioning Connected en detalle.

---

## 14. Estado

**Aprobado (arquitectura)** — 7 ago 2026 (v1.1).

Define solo las estrategias Autogestionada / Asistida y la cadena Licencia → Token → transporte.  
**No** autoriza código. Detalle: ADR-033 / 034 / 035 bajo sus propios GO.
