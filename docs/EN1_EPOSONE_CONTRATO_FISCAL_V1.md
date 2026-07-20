# Contrato Fiscal EPosOne V1

| Campo | Valor |
|-------|--------|
| Estado | **Borrador** — 19 jul 2026 · pendiente Analista + Arquitectura |
| Fase V6 | **2.1** — [`EN1_PLATFORM_EPOSONE_V6_ROADMAP.md`](EN1_PLATFORM_EPOSONE_V6_ROADMAP.md) |
| Depende de | [`EN1_EPOSONE_MODELO_COMERCIAL_V1.md`](EN1_EPOSONE_MODELO_COMERCIAL_V1.md) (Fase 1) |
| Siguiente | Fase 2.2 — [`EN1_EPOSONE_CONTRATO_PROPINAS_V1.md`](EN1_EPOSONE_CONTRATO_PROPINAS_V1.md) (borrador listo) · luego Pagos |
| Alcance | **Negocio** — sin tablas, APIs ni DDL |
| Dual Mode | Mismo contrato; origen local (Standalone) o EN1 (Integrado) |

---

## 0. Objetivo

Definir **cómo se aplican impuestos** a un pedido en EPosOne, de forma única para Standalone e Integrado.

El Contrato Fiscal es un **tipo de política comercial** (ver Modelo Comercial §4): versionado, con vigencia y asignable a empresa / sucursal / caja.

**No incluye:** propinas, promociones, layout de recibo, FE electrónica legal completa (solo prepara bases para ella).

---

## 1. Conceptos

| Concepto | Definición |
|----------|------------|
| **Contrato Fiscal** | Paquete nombrado de reglas impositivas vigentes para un ámbito |
| **Regla de impuesto** | Una tasa/tipo concreto (ej. ITBMS 7 %, ISC licor, Exento) |
| **Categoría fiscal** | Etiqueta de producto que apunta a una o más reglas |
| **Línea de impuesto** | Resultado tipificado: código, base, tasa, monto (en el resultado comercial) |
| **Precio** | Puede ser **neto** (impuesto aparte) o **incluido** (tax-inclusive) — ver §7 |

```text
Producto  →  Categoría fiscal  →  Regla(s) del Contrato Fiscal activo
                                      ↓
                              Líneas de impuesto del pedido
```

---

## 2. Datos del Contrato Fiscal

| Campo | Obligatorio | Notas |
|-------|-------------|--------|
| Nombre | Sí | Ej. “Panamá — Comercio general” |
| Código | Sí | Estable, único en la empresa |
| País | Sí | Ej. `PA` (catálogo extensible) |
| Activo | Sí | Solo contratos activos se asignan a nuevas ventas |
| Vigencia desde / hasta | Sí / opcional | Pedidos usan la versión vigente al momento del cálculo |
| Versión | Sí | Entero o semver; historial inmutable para pedidos cerrados |
| Moneda de referencia | No | Por defecto la de la empresa/caja |
| Notas / base legal | No | Texto operativo, no sustituye asesoría fiscal |

### Asignación (ámbito)

Orden de resolución (propuesto; se confirma en Fase 3 si hay override):

```text
Caja → Sucursal → Empresa → (default país)
```

Gana la asignación **más específica** activa en la fecha del pedido.

---

## 3. Reglas de impuesto

Cada regla dentro del contrato:

| Campo | Obligatorio | Descripción |
|-------|-------------|-------------|
| Código | Sí | Ej. `ITBMS_7`, `ITBMS_10`, `EXENTO`, `EXPORT`, `ISC_LICOR` |
| Nombre | Sí | Etiqueta para UI y recibo |
| Tipo | Sí | Ver §3.1 |
| Porcentaje | Condicional | 0 si exento / monto fijo especial |
| Monto fijo por unidad | Condicional | Si el tipo lo exige (raro en v1; reservado) |
| Prioridad | Sí | Orden de evaluación / impresión (menor = primero) |
| Acumula con otros | Sí | ¿Se suma a otras reglas de la misma línea? |
| Base imponible | Sí | Ver §5 |
| Descuento en base | Sí | ¿La base usa precio tras descuentos de línea/global? |
| Redondeo | Sí | Ver §6 |
| Incluido en precio | Sí | Si el precio de lista ya trae el impuesto |
| Activo | Sí | |
| Vigencia | Opcional | Puede acotar una regla sin versionar todo el contrato |

### 3.1 Tipos de impuesto (catálogo v1)

| Tipo | Uso típico (Panamá) | Ejemplo |
|------|---------------------|---------|
| `vat_like` | Impuesto al valor / consumo general | ITBMS 7 %, ITBMS 10 % |
| `excise` | Impuesto selectivo / especial | ISC licores |
| `exempt` | No genera monto; marca fiscal | Exento, consumo interno exento |
| `zero_rated` | Tasa 0 % con trazabilidad | Exportación (según régimen) |
| `other` | Extensible | Futuros impuestos |

**Regla:** no hardcodear tasas en la app. Toda tasa vive en una regla del contrato.

### 3.2 Ejemplos de reglas seed (Panamá — ilustrativos, no legales)

| Código | Tipo | % | Notas |
|--------|------|---|--------|
| `ITBMS_7` | `vat_like` | 7 | Gravado estándar frecuente |
| `ITBMS_10` | `vat_like` | 10 | Bienes/servicios a tasa especial (cuando aplique) |
| `EXENTO` | `exempt` | 0 | Producto/servicio exento |
| `EXPORT` | `zero_rated` | 0 | Exportación / régimen 0 |
| `INTERNO` | `exempt` | 0 | Consumo interno (si política del negocio lo usa) |
| `ISC_LICOR` | `excise` | según catálogo | Licores / especiales — % o fórmula en regla |

> Los % exactos y la aplicabilidad legal los valida el Analista / asesor; el contrato solo estructura el catálogo.

---

## 4. Categorías fiscales (producto)

Cada **producto** (o servicio) declara una **categoría fiscal**.

| Ejemplo producto | Categoría (ejemplo) | Reglas asociadas |
|------------------|---------------------|------------------|
| Hamburguesa | `GRAVADO_7` | `ITBMS_7` |
| Ron | `LICOR` | `ITBMS_7` + `ISC_LICOR` (si acumula) |
| Servicio médico X | `EXENTO` | `EXENTO` |
| Ítem exportación | `EXPORTACION` | `EXPORT` |

### Reglas de negocio

1. Sin categoría fiscal → el producto **no se vende** (o cae a categoría default de empresa, si la política lo permite; default debe ser explícito).
2. Una categoría puede mapear **N reglas** (multi-impuesto por línea).
3. El cambio de categoría en maestro no reescribe pedidos históricos; el snapshot del cálculo queda en el pedido.
4. Dual Mode: categorías y mapeos se editan en local (Standalone) o EN1 (Integrado).

---

## 5. Base imponible

Cada regla declara su base:

| Código base | Significado |
|-------------|-------------|
| `line_gross` | Cantidad × precio unitario (antes de descuentos) |
| `line_net` | Tras descuentos de **línea** |
| `line_after_order_discount` | Tras prorrateo de descuentos / promos **globales** del pedido |
| `previous_tax` | Sobre otro impuesto ya calculado (solo si `acumula` y política lo permite — excepcional) |

**Descuento antes/después (campo de la regla):**

- `discount_before_tax = true` → base = precio ya descontado (habitual).
- `discount_before_tax = false` → base = bruto; el descuento no reduce base (excepcional; documentar en política).

**Propinas:** no forman parte de la base fiscal en v1 salvo que una regla lo declare explícitamente (default: **propina fuera de base ITBMS**). Alineación final con orden de totales = Fase 4.

---

## 6. Redondeo

Por regla (o default del contrato):

| Modo | Descripción |
|------|-------------|
| `half_up` | Redondeo comercial al céntimo (0.005 → arriba) |
| `half_even` | Bancario |
| `floor` / `ceil` | Hacia abajo / arriba |
| Decimales | Default **2** (B/. ) |

Regla de consistencia: el **Motor de Totales** (Fase 4) aplica el mismo modo en Standalone e Integrado; EN1 valida en modo Integrado.

---

## 7. Precio incluido vs aparte

| Modo precio | Comportamiento |
|-------------|----------------|
| **Tax-exclusive** (default v1) | Precio de lista = neto; impuestos se suman al total |
| **Tax-inclusive** | Precio de lista incluye impuesto; el motor **desglosa** base + impuesto para recibo y reportes |

El modo puede ser:

- Por **regla**, o
- Default del **contrato**, o
- Override por **categoría** (si se aprueba en revisión)

**Abierto (Q3 del Modelo):** ¿algún vertical Panamá opera tax-inclusive por defecto? Decidir antes de congelar Fase 4.

---

## 8. Multi-impuesto y acumulación

1. Se evalúan todas las reglas activas de la categoría, ordenadas por **prioridad**.
2. Si `acumula = true`, el monto de la regla se suma a las líneas de impuesto del ítem.
3. Si `acumula = false` y hay conflicto (dos `vat_like` excluyentes), gana la de mayor prioridad o la categoría debe mapear solo una — **prohibido** dejar ambigüedad: el contrato debe ser determinista.
4. Exento + gravado en el mismo producto = error de configuración (no se vende hasta corregir).

---

## 9. Resultado en el pedido (negocio)

Tras el cálculo, el pedido expone (conceptualmente):

| Salida | Descripción |
|--------|-------------|
| Subtotal gravable / no gravable | Según bases |
| Líneas de impuesto | Lista tipificada (código, base, %, monto) |
| `tax_total` | Suma de montos de impuesto |
| Snapshot | Código + versión del Contrato Fiscal usado |

Compatibilidad temporal con Order Domain actual (`tax` escalar): el escalar = suma de líneas hasta migrar UI/API.

---

## 10. Reembolsos fiscales (visión)

- Reembolso total: invierte líneas de impuesto del pedido original (misma versión de contrato).
- Reembolso parcial: prorratea bases y montos según líneas/cantidades devueltas.
- Detalle operativo → Contrato de Pagos (2.3) + Motor de Totales (4).

---

## 11. Dual Mode

| | Standalone | Integrado |
|--|------------|-----------|
| Alta/edición contrato y categorías | En EPosOne | En EN1 BO |
| Cálculo en venta | Motor local (misma spec) | Preview local + **recálculo/validación EN1** al sync |
| Pedidos históricos | Conservan snapshot local | Conservan snapshot; EN1 es SoT del registro |

---

## 12. Fuera de alcance v1

- Emisión FE Panamá (DGI) — etapa FE; este contrato solo alimenta bases
- Retenciones / percepciones de terceros
- Impuestos por jurisdicción municipal distinta (extensible vía `other`)
- UI de administración (se describe en Fase desarrollo)

---

## 13. Criterio de aprobación

Aprobado cuando Analista + Arquitectura confirman:

1. Catálogo de tipos y campos de regla son suficientes para ITBMS multi-tasa + ISC + exento/export.
2. Categoría fiscal → N reglas es el modelo de producto.
3. Base imponible y redondeo quedan sin ambigüedad.
4. Dual Mode queda explícito.
5. Preguntas abiertas §14 resueltas o aplazadas con dueño (Fase 4).

---

## 14. Preguntas abiertas

| # | Pregunta | Dueño sugerido |
|---|----------|----------------|
| F1 | ¿Seed oficial de % ITBMS / ISC para demos Panamá? | Analista |
| F2 | ¿Tax-inclusive por defecto en algún vertical? | Analista |
| F3 | ¿ISC siempre acumula con ITBMS? | Analista |
| F4 | ¿Propina entra alguna vez en base ITBMS? | Analista + Fase 4 |
| F5 | ¿Default de categoría si el producto no tiene? (bloquear vs `EXENTO`) | Arquitectura |

---

## 15. Relación con otros docs

| Doc | Relación |
|-----|----------|
| Modelo Comercial V1 | Contratos = políticas tipificadas |
| Contrato Propinas 2.2 | Propina ≠ impuesto; no mezclar en recibo |
| Motor Totales Fase 4 | Aplica este contrato en el algoritmo |
| ADR-008 Fase 5 | Documenta ownership y sync del motor fiscal |

---

*Borrador V6 Fase 2.1. Sin implementación hasta aprobación de Fases 1–5 según roadmap.*
