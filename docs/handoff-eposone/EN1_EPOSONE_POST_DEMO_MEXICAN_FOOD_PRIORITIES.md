# EPosOne — Post-demo Mexican Food · Prioridades (estabilización)

| Campo | Valor |
|-------|--------|
| Fecha | **28 jul 2026** (presentación comercial + validación cliente) |
| Design Partner #1 | **Mexican Food** (org prod) · plan actual **Starter** |
| Instalación en sitio | **Jueves 30 jul 2026** |
| Fase | **Estabilización para producción** (no expansión de features) |
| Relacionados | [`EN1_EPOSONE_HANDOFF_STATUS.md`](EN1_EPOSONE_HANDOFF_STATUS.md) · [`EN1_POS_V7_ROADMAP.md`](EN1_POS_V7_ROADMAP.md) · [`ADR-020`](ADR-020-ORDER-EVENT-OWNERSHIP.md) · Cash Shift [`EN1_EPOSONE_CASH_SHIFT_SPEC_V1.md`](EN1_EPOSONE_CASH_SHIFT_SPEC_V1.md) · Order Domain [`EN1_EPOSONE_ORDER_DOMAIN_SPEC_V1.md`](EN1_EPOSONE_ORDER_DOMAIN_SPEC_V1.md) |

---

## Hito

La presentación del **28 jul 2026** no fue solo demo técnica: fue **validación comercial** frente a un cliente real listo para instalar.

**Conclusión de producto:** el cliente **no pidió nuevas funcionalidades**. El valor funcional ya alcanza para vender. El foco pasa a **confiabilidad operativa y comercial**.

Pregunta filtro hasta el jueves:

> ¿Esto ayuda a que la instalación en sitio sea impecable?  
> Si no → siguiente ciclo del roadmap.

**Congelado:** desarrollo de features nuevas hasta estabilizar P0 (+ avanzar P1 comercial sin bloquear el jueves).

---

## Feedback de la presentación

### Lo que más impresionó

| Señal | Notas |
|-------|--------|
| Facilidad de uso | Muy valorada |
| Offline | Generó confianza |
| Integración con EN1 | Bien recibida |

### Preguntas del cliente (oro comercial)

| Tema | Implicación |
|------|-------------|
| Informes | Landing / folleto / pitch deben mostrar reportes claros |
| Cierres de cajero | Debe cuadrar y verse igual en EN1 y EPosOne |
| Apertura de caja / sync | No puede haber dudas ni duplicados |

→ Contenido a reforzar en landing, folleto y discurso de ventas.

### Objeciones / gaps detectados

| Gap | Severidad |
|-----|-----------|
| Cierres de cajero no están bien | P0 |
| Apertura de cajeros no sincroniza correctamente | P0 |
| Nombres de cajeros en EN1 inconsistentes | P0 |
| Internet caído durante operación — sync debe ser forzada / confiable | P0 |
| Estados de recibos / pedidos a definir y manejar | P0 |

### Funcionalidades pedidas

**Ninguna nueva.** Solo afinar **cierres** y **estados de recibos**.

### Siguiente paso acordado

```text
Firma de contrato
      ↓
Instalación en sitio (jueves)
      ↓
Operación real
```

Antes de escalar: licenciamiento funcional + pago en EN1 + correo de creación de cuenta (P1).

---

## Orden de prioridades (oficial post-demo)

### P0 — Obligatorio antes del jueves (instalación)

#### 1. Caja y Turnos (CRÍTICO)

- Apertura de caja  
- Sync EN1 ↔ EPosOne  
- Estado consistente · sin aperturas duplicadas  
- Recuperación si la tablet se desconecta  
- Auditoría completa  
- Cierre de caja que cuadre:

  | Concepto |
  |----------|
  | Efectivo · tarjeta · transferencia · Yappy · otros |
  | Total ventas · devoluciones · anulaciones |
  | Diferencia de caja · arqueo |

**Criterio:** EN1 y EPosOne muestran **exactamente los mismos números**.

#### 2. Sincronización (CRÍTICO)

Probar al menos:

- Internet cae antes de cobrar / durante el cobro / vuelve  
- Dos sync seguidas · sync manual · sync automática  
- Pedidos / pagos / apertura / cierre pendientes  

**Objetivo:** nunca perder una venta. Sync forzosa cuando hay conectividad.

#### 3. Estados de pedidos / recibos

Contrato alineado a [ADR-020](ADR-020-ORDER-EVENT-OWNERSHIP.md) + Order Domain:

| Ejemplo de estados | Regla |
|--------------------|--------|
| Draft · Pendiente · Confirmado · Pagado · Parcial · Cerrado · Cancelado · Reembolsado | Draft puede eliminarse; **confirmados nunca** se borran físicamente; mutación vía **eventos** |

#### 4. Informes

- Venta diaria · por cajero · por forma de pago  
- Cierre X / Cierre Z  
- Historial de cierres · turnos · movimientos de caja  

Deben inspirar confianza en el cliente.

---

### P1 — Comercial (post-instalación / paralelo sin bloquear jueves)

5. **Licenciamiento completo**

```text
Cliente → Portal EN1 → Compra plan → Pago → Licencia activa
      → EPosOne recibe licencia → Puede operar
```

6. Integración EN1 compra / pago / activación  
7. Correo de creación de cuenta + onboarding  

---

### P2 — Escalamiento

8. Portal comercial (plan · registro · pago · suscripción)  
9. Automatización de provisión (org · admin · licencia · dispositivos · credenciales)  
10. Nuevas funcionalidades (solo después de pilares P0+P1)

---

### P3 — Automatización comercial (detalle)

Tras contrato: correo cta → crear org → admin → licencia → provisionar → instalar tablet. Idealmente casi automático.

---

## DoD instalación jueves (Mexican Food)

Demostrar en sitio:

| # | Capacidad |
|---|-----------|
| 1 | Abre caja correctamente |
| 2 | Vende |
| 3 | Imprime |
| 4 | Sincroniza |
| 5 | Trabaja offline |
| 6 | Recupera sync al volver internet |
| 7 | Cierra caja correctamente |
| 8 | Informes consistentes EN1 ↔ EPosOne |
| 9 | Listo para operar al día siguiente |

---

## Capacidades ya maduras (contexto de la demo)

Provisioning · sync con EN1 · turnos de caja (base) · impresión · multi-pago · licenciamiento (base) · arquitectura SaaS definida.

La conversación ya es **solución lista para operar**, no “una idea” — el riesgo ahora es **confiabilidad**, no feature gap.

---

## Relación con roadmaps previos

| Doc | Rol |
|-----|-----|
| Este archivo | **SoT de prioridades inmediatas** post-demo → jueves |
| V7 / Backlog V7 | Siguen vigentes; ítems que no ayuden al jueves **bajan** de cola |
| ADR-020 | Gobierna mutación de pedidos/recibos (eventos, no delete) |
| Cash Shift Spec/HTTP | Base técnica de apertura/cierre a endurecer en P0.1 |

---

*Actualizar este doc solo con GO tras la instalación del jueves (resultado piloto + gaps reales).*
