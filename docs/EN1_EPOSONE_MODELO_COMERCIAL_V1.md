# Modelo Comercial EPosOne V1

| Campo | Valor |
|-------|--------|
| Estado | **Borrador** — 19 jul 2026 · pendiente aprobación Analista + Arquitectura |
| Roadmap | [`EN1_PLATFORM_EPOSONE_V6_ROADMAP.md`](EN1_PLATFORM_EPOSONE_V6_ROADMAP.md) **Fase 1** |
| Principio | Un solo modelo de negocio para **Standalone** e **Integrado**; solo cambia el origen de los datos |
| Alcance | **Negocio** — sin tablas, APIs ni DDL |
| Antecedente | Dominio Etapa 6 ([`EN1_PLATFORM_ETAPA6_DOMINIO_COMERCIAL.md`](EN1_PLATFORM_ETAPA6_DOMINIO_COMERCIAL.md)) · Pedido = centro · ADR-001/003 modos |
| Siguiente tras aprobación | Fase 2.1 — [`EN1_EPOSONE_CONTRATO_FISCAL_V1.md`](EN1_EPOSONE_CONTRATO_FISCAL_V1.md) (borrador listo) · luego Propinas / Pagos / Recibo |
| ADR-008 | **Después** de Fases 1–4 — solo documenta decisiones ya tomadas |

---

## 0. Objetivo

Responder: **¿Cómo funciona un negocio dentro de EPosOne?**

Este documento congela el vocabulario y las relaciones del negocio. No define implementación.

**Regla del sprint:** no se desarrolla lógica comercial nueva hasta que este modelo y los contratos posteriores estén aprobados.

**Paralelo permitido:** Hito 4, Cajeros, Sync E2E (ya aprobados) — no dependen de estos contratos.

---

## 1. Principio Dual Mode

| Modo | Origen de configuración y maestros | Quién edita reglas |
|------|--------------------------------------|--------------------|
| **Standalone (Local)** | Base local del POS | El comercio en EPosOne |
| **Integrado (Plataforma)** | EN1 (source of truth) | EN1 BO; POS solo consume |
| **Vincular** | Cutover Local → Integrado sin reinstalar | Asistente de vinculación |

```text
Misma lógica de negocio
        │
   ┌────┴────┐
Standalone  Integrado
   │            │
Datos locales  Datos EN1 (+ sync)
```

- No hay dos productos ni dos motores “lite” vs “EN1”.
- Toda regla de negocio se define **una vez** en este modelo y en los contratos.
- La diferencia operativa es **ownership de datos**, no de comportamiento.

---

## 2. Estructura del negocio

```text
Empresa
  └── Sucursal
        └── POS (punto de venta lógico)
              └── Caja (register / turno de dinero)
                    └── Terminal / dispositivo (ejecuta la app)
```

| Concepto | Qué es | Qué no es |
|----------|--------|-----------|
| **Empresa** | Negocio / razón operativa (identidad comercial) | Un dispositivo |
| **Sucursal** | Local o punto con dirección, stock y políticas propias si aplica | El tablet |
| **POS** | Punto lógico donde nacen pedidos (precios, impresora, políticas) | El hardware; unidad de licencia comercial (ADR-005) |
| **Caja** | Cuenta lógica de efectivo / medios; abre y cierra turnos | Solo el cajón físico (aunque suele mapearse 1:1) |
| **Terminal** | Dispositivo que corre EPosOne | El POS lógico |
| **Cajero** | Persona operativa que autentica (PIN) y responde por el turno | Usuario de back-office EN1 (puede coincidir, roles distintos) |
| **Cliente** | Contado (anónimo) o registrado (datos fiscales / crédito) | Obligatorio en todo ticket |

### Reglas

1. Todo pedido pertenece a una **Empresa** y una **Sucursal**.
2. Todo cobro ocurre en contexto de **Caja** + **Cajero** (turno abierto en operación normal).
3. Un **POS** puede tener N terminales; el licenciamiento cuenta POS, no dispositivos.
4. Políticas comerciales (fiscal, propinas, pagos, recibo, promos) se **asignan** a empresa, sucursal y/o caja (detalle en contratos y Motor Comercial).

---

## 3. Cadena operativa (vocabulario)

```text
Cliente (opcional)
    ↓
Pedido          ← documento vivo; centro del sistema
    ↓
Cobro           ← aplicación de medios de pago al pedido
    ↓
Venta           ← pedido cobrado / cerrado comercialmente
    ↓
Recibo / Factura ← documento de impresión o fiscal derivado
    ↓
Caja / Turno    ← movimiento de dinero y arqueo
    ↓
Reportes
```

| Concepto | Definición de negocio |
|----------|----------------------|
| **Pedido** | Intención de venta: líneas, cantidades, precios, estados operativos. Puede abrirse, modificarse, suspenderse, transferirse de cobro. **No es** aún la factura. |
| **Cobro** | Registro de uno o más pagos (mixto) contra el saldo del pedido. Puede ser parcial hasta completar. |
| **Venta** | Resultado comercial cuando el pedido queda pagado (o política de crédito lo cierra como CxC). Alimenta caja, inventario (futuro) y reportes. |
| **Recibo** | Comprobante impreso/digital según **Contrato de Recibo**. |
| **Factura** | Documento fiscal derivado cuando la política fiscal lo exige (FE / régimen). Fuera del detalle de este V1; se enlaza en Contrato Fiscal / FE. |

**Principio heredado (Etapa 6 / V5):** el centro es el **Pedido**, no la Factura.

---

## 4. Contratos comerciales (qué son)

Un **contrato comercial** es un paquete versionado de reglas de negocio, con vigencia y alcance (empresa / sucursal / caja).

No es una pantalla aislada: es una **política tipificada**.

| Tipo de contrato | Pregunta que responde | Documento V6 |
|------------------|----------------------|--------------|
| **Fiscal** | ¿Qué impuestos aplican y cómo? | Fase 2.1 |
| **Propinas** | ¿Hay propina, cómo se calcula y a quién va? | Fase 2.2 |
| **Pagos** | ¿Qué medios, parciales, reembolsos, crédito? | Fase 2.3 |
| **Recibo** | ¿Qué se imprime y cómo se ve? | Fase 2.4 |

Más adelante: [`EN1_EPOSONE_MOTOR_COMERCIAL_V1.md`](EN1_EPOSONE_MOTOR_COMERCIAL_V1.md) (Fase 3) — promociones / descuentos / pricing como tipos del mismo motor de políticas.

### Propiedades comunes (negocio)

- Nombre y código
- Activo / inactivo
- Vigencia (desde / hasta)
- Versión (historial; pedidos antiguos conservan la versión usada)
- Ámbito de asignación (empresa → sucursal → caja; la más específica gana salvo regla explícita)

---

## 5. Políticas

**Política** = instancia activa de un contrato (o conjunto) aplicada en un contexto operativo.

Ejemplos:

- La Caja A de Sucursal Centro usa Contrato Fiscal “Panamá ITBMS estándar” + Propinas “Restaurante 10% sugerida”.
- La Caja B (retail) usa el mismo Fiscal pero Propinas “Sin propina”.

En **Standalone**, las políticas se crean y editan en el POS.  
En **Integrado**, se crean en EN1 y se sincronizan; el POS no es dueño de la edición.

---

## 6. Pedido → totales (visión; algoritmo en Fase 4)

El pedido acumula líneas. Antes del cobro, el negocio necesita un **resultado comercial** (subtotal, descuentos, impuestos, propinas, redondeos, total).

Ese algoritmo se congela en **Fase 4 — Motor de Totales**, con ejemplos Panamá.

**Orden de trabajo del analista (propuesto para Fase 4; no congelado aquí):**

```text
Pedido → Descuentos → Promociones → Propinas → Impuestos → Redondeos → Total
```

> **Abierto:** confirmar en Fase 4 si propinas van antes o después de impuestos (hay práctica mixta; debe ser una sola regla documentada + ejemplos).

Hasta Fase 4, este documento **no** fija el algoritmo.

---

## 7. Cobro y caja (visión)

- Un pedido admite **pagos mixtos** y **parciales** hasta cubrir el total (o dejar saldo en crédito / CxC según Contrato de Pagos).
- El cobro impacta el **turno de caja** del cajero.
- Reembolsos y cancelaciones son reglas del Contrato de Pagos, no improvisación de UI.
- El recibo refleja el resultado comercial + estructura del Contrato de Recibo.

Detalle: Fases 2.3 y 2.4.

---

## 8. Roles de responsabilidad (negocio)

| Actor | Standalone | Integrado |
|-------|------------|-----------|
| Dueño / admin local | Configura empresa, productos, contratos, cajeros | Consulta; edición maestra en EN1 |
| Cajero | Vende, cobra, cierra turno | Igual en piso; reglas vienen de sync |
| EN1 BO | No aplica (o no es SoT) | Fuente oficial de maestros y políticas |
| EPosOne app | Ejecuta venta + motores con datos locales | Preview offline + sync; EN1 valida al integrar |

---

## 9. Qué queda fuera de este documento

- Tablas, endpoints, payloads
- Implementación Flutter o Python
- Catálogo fiscal detallado, % de propina, layout de ticket (van a contratos)
- Inventario avanzado, FE legal completa, hardware fino (impresora/gaveta como asignación de caja → Contrato Recibo / config caja en fases posteriores)
- ADR-008 (Fase 5 del V6)

---

## 10. Criterio de aprobación (Fase 1)

Este modelo pasa a **Aprobado (congelado)** cuando Analista + Arquitectura confirman:

1. Vocabulario Empresa → … → Venta / Recibo es suficiente y sin ambigüedad.
2. Dual Mode (mismo negocio, distinto origen de datos) queda explícito.
3. “Contrato” vs “Política” queda claro.
4. Pedido es el centro; cobro/venta/recibo son derivados.
5. Se autoriza pasar a **Fase 2 — Contratos** sin reabrir esta estructura salvo excepción explícita.

---

## 11. Preguntas abiertas (resolver antes o durante Fase 2–4)

| # | Pregunta | Dónde se cierra |
|---|----------|-----------------|
| Q1 | ¿Propinas antes o después de impuestos? | Fase 4 (+ ejemplos) |
| Q2 | ¿Recargos de servicio = propina tipificada o ítem/fiscal aparte? | Fase 2.2 / 2.1 |
| Q3 | ¿Precio de lista incluye impuesto (tax-inclusive) en algún vertical? | Fase 2.1 / 4 |
| Q4 | ¿Asignación de políticas: override estricto caja > sucursal > empresa? | Fase 3 |
| Q5 | Al Vincular: ¿quién gana si hay conflicto local vs EN1? | ADR-008 / ADR-004 |

---

*Documento de negocio V6 Fase 1. Tras aprobación, no se implementa código comercial nuevo hasta completar Fases 2–5 según roadmap.*
