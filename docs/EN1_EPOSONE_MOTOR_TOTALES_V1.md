# Motor de Totales EPosOne V1

| Campo | Valor |
|-------|--------|
| Estado | **Borrador** — 19 jul 2026 · pendiente Analista + Arquitectura |
| Fase V6 | **4** — [`EN1_PLATFORM_EPOSONE_V6_ROADMAP.md`](EN1_PLATFORM_EPOSONE_V6_ROADMAP.md) |
| Depende de | [Modelo](EN1_EPOSONE_MODELO_COMERCIAL_V1.md) · Contratos 2.x · [Motor Comercial](EN1_EPOSONE_MOTOR_COMERCIAL_V1.md) |
| Siguiente | Fase 5 — [`ADR-008-EPOSONE-COMMERCIAL-ENGINE.md`](ADR-008-EPOSONE-COMMERCIAL-ENGINE.md) (borrador docs listo) · luego aprobación Analista (T1) |
| Alcance | **Negocio + algoritmo** — sin tablas, APIs ni código |
| Dual Mode | Misma spec; preview local; en Integrado EN1 recalcula y valida |

---

## 0. Objetivo

Congelar **cómo se obtiene el total a cobrar** a partir de un pedido ya resuelto por el Motor Comercial (precios + descuentos/promos).

Entrada: pedido con líneas y ajustes comerciales tipificados.  
Salida: resultado comercial versionado (subtotales, propina, impuestos, redondeos, total, detalle).

```text
Order Calculation Engine (nombre de negocio)
```

---

## 1. Orden de cálculo (propuesto — Analista)

Hasta confirmación formal, el orden de trabajo es:

```text
Pedido
  ↓
Descuentos / promociones     ← Motor Comercial (ya aplicados a la entrada)
  ↓
Propinas                     ← Contrato Propinas
  ↓
Impuestos                    ← Contrato Fiscal
  ↓
Redondeos
  ↓
Total
  ↓
Pagos / Recibo / Caja        ← fuera de este motor (consumidores)
```

### Decisión abierta Q1

| Opción | Orden propina ↔ impuesto | Uso típico |
|--------|--------------------------|------------|
| **A (este doc)** | Propina **antes** de impuesto | Alineado al Analista V6; propina sobre base neta descontada |
| **B** | Impuesto **antes** de propina | Propina sobre total con ITBMS |

**Default de este borrador: Opción A.**  
Si Analista elige B, se invierten los pasos 3–4 y se rehace §6 con los mismos casos.

**Constante en ambas:** propina e impuestos son líneas **separadas** en el resultado y en el recibo.

---

## 2. Entradas

| Entrada | Origen |
|---------|--------|
| Líneas (qty, precio unitario efectivo, categoría fiscal, flags tip_eligible) | Pedido + Motor Comercial |
| Ajustes tipificados (descuentos/promos) | Motor Comercial |
| Contrato Fiscal + versión | Política activa |
| Contrato Propinas + versión | Política activa |
| Modo redondeo | Fiscal / contrato caja |
| Moneda | Empresa / caja |

---

## 3. Pasos del algoritmo (Opción A)

### Paso 0 — Normalizar líneas

Para cada línea:

- `line_gross = qty × unit_price`
- Aplicar descuentos de línea ya resueltos → `line_net`
- Acumular `merchandise_subtotal` = Σ `line_net` (solo mercancía; sin propina)

### Paso 1 — Descuentos / promos de pedido

Si quedan ajustes a nivel pedido no prorrateados:

- Prorratear a líneas elegibles (base proporcional a `line_net`) **o** mantener como ajuste de pedido según Motor Comercial
- Resultado: `order_discount_total`, `base_after_commercial`

`base_after_commercial` = mercancía neta tras todos los beneficios comerciales.

### Paso 2 — Propina

Según Contrato Propinas:

1. Determinar base (`subtotal_discounted` / `pre_tax` / …) filtrando exclusiones.
2. Calcular monto propuesto (%, fijo, escalonado).
3. Aplicar modo aplicación (mandatory / suggested / optional) y ediciones permitidas **ya capturadas** en el pedido.
4. Salida: `tip_amount` + metadatos (no mezcla con tax).

Si contrato = `none` → `tip_amount = 0`.

### Paso 3 — Impuestos

Según Contrato Fiscal + categorías por línea:

1. Para cada línea (y su `line_net` post-prorrateo): obtener reglas de la categoría.
2. Calcular cada regla (base, %, redondeo de regla) → líneas de impuesto.
3. Multi-impuesto: respetar `acumula` y prioridad.
4. Propina: **no** entra en base ITBMS salvo regla explícita (default no).
5. Salida: lista `tax_lines[]`, `tax_total`.

Tax-inclusive: desglosar base + impuesto desde precio incluido (Contrato Fiscal §7).

### Paso 4 — Redondeo de total

1. `raw_total = base_after_commercial + tax_total + tip_amount` (+ recargos tipificados si existieran).
2. Aplicar redondeo de contrato (default `half_up`, 2 decimales) → `total`.
3. `rounding_adjustment = total − raw_total` (puede ser 0).

### Paso 5 — Resultado comercial (inmutable al cerrar)

| Campo | Descripción |
|-------|-------------|
| `merchandise_subtotal` | Bruto mercancía |
| `discount_total` | Suma descuentos/promos |
| `base_after_commercial` | Neto mercancía |
| `tip_amount` | Propina |
| `tax_lines` / `tax_total` | Impuestos tipificados |
| `rounding_adjustment` | |
| `total` | A cobrar |
| `engine_version` | Versión de este algoritmo |
| Snapshots | Códigos/versiones Fiscal + Propinas + políticas comerciales usadas |

Compatibilidad temporal Order Domain: `subtotal`, `discount`, `tax`, `tip`, `total` escalares = agregados de lo anterior.

---

## 4. Validación Dual Mode

| Modo | Comportamiento |
|------|----------------|
| Standalone | Motor corre en POS; resultado se persiste local |
| Integrado + online | EN1 ejecuta la misma spec; es SoT |
| Integrado + offline | POS preview con políticas cacheadas; al sync EN1 **recalcula**; si diferencia &gt; tolerancia (ej. 0.01) → rechazo o corrección según política de sync |

---

## 5. Tolerancias

| Caso | Regla propuesta |
|------|-----------------|
| Diferencia ≤ 0.01 | Aceptar (centavos) |
| Diferencia por redondeo documentado | Aceptar si mismo `engine_version` + mismos snapshots |
| Tip/pago overflow legacy | Redes de seguridad actuales **no** sustituyen este motor |

---

## 6. Ejemplos Panamá (ilustrativos)

> % y reglas son **didácticos**. El Analista valida cifras legales reales.

### Ejemplo 1 — Restaurante (ITBMS 7 % + propina sugerida 10 %)

| Ítem | Qty | Precio | Categoría |
|------|-----|--------|-----------|
| Hamburguesa | 2 | 8.00 | GRAVADO_7 |
| Refresco | 2 | 2.00 | GRAVADO_7 |

- Subtotal mercancía = 20.00  
- Descuentos = 0  
- Base propina = 20.00 → tip 10 % = **2.00**  
- Base ITBMS = 20.00 → 7 % = **1.40**  
- Total = 20.00 + 2.00 + 1.40 = **23.40**

Pago: Yappy 23.40 (referencia real).

### Ejemplo 2 — Retail con descuento línea + exento

| Ítem | Qty | Precio | Desc. línea | Categoría |
|------|-----|--------|-------------|-----------|
| Camisa | 1 | 30.00 | −10 % (3.00) | GRAVADO_7 |
| Pan farmacéutico* | 1 | 5.00 | 0 | EXENTO |

\* Ilustrativo.

- Camisa neta = 27.00 → ITBMS 7 % = 1.89  
- Exento = 5.00 → tax 0  
- Propina = none  
- Total = 27.00 + 5.00 + 1.89 = **33.89**

### Ejemplo 3 — Bar con ISC + ITBMS (acumulan)

| Ítem | Qty | Precio | Categoría |
|------|-----|--------|-----------|
| Ron copa | 1 | 10.00 | LICOR → ITBMS_7 + ISC_LICOR |

Supuesto didáctico: ISC 5 % sobre neto, acumula; ITBMS 7 % sobre neto (no sobre ISC).

- Neto = 10.00  
- ISC = 0.50  
- ITBMS = 0.70  
- Tip none  
- Total = 10.00 + 0.50 + 0.70 = **11.20**

### Ejemplo 4 — Estación / retail sin propina + pago mixto

| Ítem | Qty | Precio | Categoría |
|------|-----|--------|-----------|
| Snack | 1 | 3.50 | GRAVADO_7 |

- Tax 7 % = 0.25 → Total **3.75**  
- Pago: efectivo 5.00 → cambio 1.25; o mixto efectivo 2.00 + Clave 1.75  

### Ejemplo 5 — Happy hour (Motor Comercial) + propina

| Ítem | Precio lista | Promo HH −20 % | Neto |
|------|--------------|----------------|------|
| Cerveza | 5.00 | −1.00 | 4.00 |

- Tip 10 % sobre 4.00 = 0.40  
- ITBMS 7 % sobre 4.00 = 0.28  
- Total = 4.00 + 0.40 + 0.28 = **4.68**  
- Recibo muestra: línea promo “Happy Hour −1.00”, tip e ITBMS separados.

### Ejemplo 6 — Opción B (referencia): mismo caso 1 con impuesto antes de propina

Si se eligiera B:

- Base = 20.00 → ITBMS 1.40 → subtotal+tax = 21.40  
- Tip 10 % sobre 21.40 = 2.14  
- Total = **23.54** (≠ 23.40)

Por eso Q1 debe cerrarse **antes** de congelar este documento.

---

## 7. Criterio de aprobación

1. Orden A o B elegido explícitamente por Analista.
2. Pasos 0–5 deterministas y Dual Mode claro.
3. Ejemplos 1–5 aceptados o corregidos con cifras oficiales.
4. Compatibilidad con escalares actuales documentada.
5. Autoriza pasar a **ADR-008** (Fase 5) sin reabrir el algoritmo salvo excepción.

---

## 8. Preguntas abiertas

| # | Pregunta | Impacto |
|---|----------|---------|
| T1 | ¿Opción A o B (propina vs impuesto)? | Ejemplos y APK/EN1 |
| T2 | ¿Prorrateo de descuento pedido a líneas siempre? | Bases fiscales |
| T3 | ¿Tolerancia sync 0.01 suficiente? | Integrado |
| T4 | ¿Recargo `surcharge` suma antes o después de tip? | Si se usa Motor Comercial |

---

*Borrador V6 Fase 4. Sin implementación hasta aprobación de Fases 1–5.*
