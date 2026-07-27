# Motor Comercial EPosOne V1

| Campo | Valor |
|-------|--------|
| Estado | **Borrador** — 19 jul 2026 · pendiente Analista + Arquitectura |
| Fase V6 | **3** — [`EN1_PLATFORM_EPOSONE_V6_ROADMAP.md`](EN1_PLATFORM_EPOSONE_V6_ROADMAP.md) |
| Depende de | [Modelo](EN1_EPOSONE_MODELO_COMERCIAL_V1.md) + Contratos [Fiscal](EN1_EPOSONE_CONTRATO_FISCAL_V1.md) · [Propinas](EN1_EPOSONE_CONTRATO_PROPINAS_V1.md) · [Pagos](EN1_EPOSONE_CONTRATO_PAGOS_V1.md) · [Recibo](EN1_EPOSONE_CONTRATO_RECIBO_V1.md) |
| Siguiente | Fase 4 — Motor de Totales (algoritmo + ejemplos Panamá) |
| Alcance | **Negocio** — sin tablas, APIs ni DDL |
| Dual Mode | Misma lógica; políticas locales o sync EN1 |
| Relación ADR-008 | Este doc **descubre/define** reglas; ADR-008 (Fase 5) solo las documenta |

---

## 0. Objetivo

Definir el **Motor Comercial**: el sistema de **políticas versionadas** que alteran precios, descuentos y elegibilidad de ítems **antes** del cálculo fiscal/propina final.

Responde:

- ¿Qué promociones y descuentos existen?
- ¿En qué orden se aplican?
- ¿Quién puede usarlos (empresa / sucursal / caja / horario / membresía)?
- ¿Cómo se relacionan con Fiscal, Propinas y Pagos sin duplicar lógica?

```text
Políticas comerciales (este motor)
        ↓
Precio efectivo + descuentos + promos aplicados al Pedido
        ↓
Motor de Totales (Fase 4) → propinas / impuestos / redondeo / total
        ↓
Pagos + Recibo
```

---

## 1. Motor de políticas (unificado)

No son “configs sueltas”. Todo es una **política** tipificada:

| Tipo de política | Doc / fase |
|------------------|------------|
| `fiscal` | Contrato Fiscal 2.1 |
| `tips` | Contrato Propinas 2.2 |
| `payments` | Contrato Pagos 2.3 |
| `receipt` | Contrato Recibo 2.4 |
| `pricing` | Este motor — listas / horario / sucursal |
| `discount` | Este motor — descuentos manuales o reglas |
| `promotion` | Este motor — 2x1, happy hour, combos, cupones |

### Propiedades comunes (todas las políticas)

| Campo | Descripción |
|-------|-------------|
| Código / nombre | Identidad estable |
| Tipo | Uno de la tabla arriba |
| Activo | |
| Vigencia desde–hasta | Fecha/hora |
| Versión | Inmutable en pedidos cerrados |
| Ámbito | Empresa → Sucursal → POS → Caja |
| Prioridad | Desempate entre políticas del mismo tipo |
| Stackable | ¿Puede coexistir con otras del mismo tipo? |

### Resolución de ámbito

```text
Caja → POS → Sucursal → Empresa → (ninguna / default)
```

Gana la más específica **activa** en el momento del cálculo, salvo que una política de nivel superior declare `force_cascade` (excepción documentada).

---

## 2. Precio base (`pricing`)

Antes de descuentos/promos, el motor resuelve el **precio unitario** de cada línea:

| Fuente | Descripción |
|--------|-------------|
| Precio de lista del producto | Default |
| Lista por sucursal | Override de catálogo |
| Precio por horario | Happy-hour price list (distinto de promo %) |
| Precio por membresía | Nivel de cliente |
| Precio manual cajero | Solo si política `allow_manual_price` + permiso |

**Regla:** un solo precio unitario efectivo por línea al entrar al Motor de Totales; las promos posteriores generan **descuentos tipificados**, no reescriben historia sin traza.

---

## 3. Descuentos (`discount`)

### 3.1 Tipos

| Tipo | Nivel | Descripción |
|------|-------|-------------|
| `line_percent` | Línea | % sobre qty × precio |
| `line_amount` | Línea | Monto fijo en la línea |
| `order_percent` | Pedido | % sobre base (ver §5) |
| `order_amount` | Pedido | Monto fijo al pedido |
| `manual` | Línea o pedido | Captura cajero; requiere motivo / supervisor según flags |

### 3.2 Controles

| Flag | Uso |
|------|-----|
| `requires_supervisor` | PIN supervisor |
| `max_percent` / `max_amount` | Topes |
| `reason_required` | Motivo obligatorio |
| `exclude_tip_base` | Si el descuento saca ítems de base de propina (enlace Propinas) |
| `exclude_tax_base` | Raro; default false — Fiscal define si descuento reduce base |

---

## 4. Promociones (`promotion`)

### 4.1 Familias v1

| Familia | Ejemplo | Comportamiento |
|---------|---------|----------------|
| `happy_hour` | 2 h de descuento en categoría Bebidas | Ventana horaria + % o lista de precios |
| `bogo` / `NxM` | 2x1, 3x2 | Elegibles + cantidad gatillo |
| `combo` | Combo almuerzo | Bundle precio fijo o % sobre suma |
| `coupon` | Cupón código | Código único / multi-uso; 1 por pedido salvo stack |
| `membership` | 10 % socio | Cliente con membresía vigente |
| `spend_threshold` | −5 $ si subtotal ≥ 50 | Umbral de consumo |
| `quantity_break` | 2ª unidad −50 % | Por producto |

### 4.2 Datos mínimos de una promo

| Campo | Descripción |
|-------|-------------|
| Código / nombre | |
| Familia | Tabla §4.1 |
| Vigencia + horarios + días semana | |
| Ámbito (sucursal/caja) | |
| Productos / categorías incluidos y excluidos | |
| Beneficio | % / monto / precio combo / ítem gratis |
| Límites | Usos por día, por cliente, por pedido |
| Acumulable | Con otras promos / con descuento manual |
| Prioridad | Orden de evaluación |
| Requiere código | Cupón |
| Requiere cliente | Membresía / cupón nominativo |

### 4.3 Happy Hour vs precio por horario

| Enfoque | Cuándo usar |
|---------|-------------|
| Lista `pricing` por horario | Cambia el precio de catálogo en ese slot |
| Promo `happy_hour` | Descuento tipificado sobre precio de lista (mejor trazabilidad en recibo) |

**Preferencia v1:** promo tipificada cuando el recibo debe mostrar “Happy Hour −20 %”. Lista de precios cuando el vertical no quiere ver descuento, solo precio.

---

## 5. Orden de aplicación comercial (antes del Motor de Totales)

Propuesto (se congela con ejemplos en Fase 4):

```text
1. Resolver precio unitario (pricing)
2. Descuentos de línea (manual + reglas línea)
3. Promociones de línea / NxM / quantity break
4. Combos (reexpresión de líneas o descuento de bundle)
5. Descuentos / promos a nivel pedido (cupón, membresía, umbral)
6. → Entregar “pedido con bases comerciales” al Motor de Totales
```

**Conflictos:**

- Si dos promos no son `stackable`, gana mayor **prioridad**; empate → mayor beneficio al cliente **o** rechazo de la segunda (flag `prefer_customer_best` default **true**).
- Descuento manual + promo: permitido solo si ambas `stackable` o supervisor.

---

## 6. Salidas tipificadas (para Totales / Recibo)

Cada beneficio aplicado genera una **línea de ajuste**:

| Campo | Descripción |
|-------|-------------|
| Tipo | discount / promotion |
| Código política | |
| Nivel | line / order |
| Monto | |
| Líneas afectadas | refs |
| Stack id | Para auditoría |

El recibo muestra estas líneas en “Descuentos / Promociones”, separadas de impuestos y propina.

---

## 7. Relación con otros contratos

| Contrato | Relación |
|----------|----------|
| Fiscal | Base imponible suele ser post-descuento (`discount_before_tax`) |
| Propinas | Base tip suele ser post-descuento; exclusiones de producto |
| Pagos | Cupón no es tender; crédito/GC son pagos |
| Recibo | Secciones de descuentos y mensajes promo en pie |

**Recargo / service charge:** si es obligatorio tipo “servicio 10 %”, Analista elige: Propinas `mandatory` **o** ajuste `surcharge` de este motor (pregunta P2 Propinas). No inventar un tercer silo.

---

## 8. Dual Mode

| | Standalone | Integrado |
|--|------------|-----------|
| Alta de promos/descuentos/listas | EPosOne | EN1 BO |
| Evaluación en venta | Motor local | Preview local + validación EN1 al sync |
| Pedido cerrado | Snapshot de políticas usadas | Igual; EN1 SoT del registro |

---

## 9. Fuera de alcance v1

- Motor de lealtad avanzado (puntos, cashback)
- Market Basket Analysis / IA de promos
- Precio dinámico por demanda
- Acuerdos B2B complejos (contratos mayoristas multi-escala) — extensible vía `quantity_break` + listas

---

## 10. Criterio de aprobación

1. Políticas unificadas por tipo + ámbito quedan claras.
2. Familias de promo v1 cubren happy hour, 2x1, combo, cupón, membresía, umbral.
3. Orden de aplicación comercial (§5) aceptado o ajustado antes de Fase 4.
4. Salidas tipificadas suficientes para recibo y totales.
5. Dual Mode explícito.
6. Preguntas §11 resueltas o aplazadas a Fase 4.

---

## 11. Preguntas abiertas

| # | Pregunta | Dueño |
|---|----------|-------|
| C1 | ¿`prefer_customer_best` siempre true? | Analista |
| C2 | ¿Combos rompen líneas del pedido o solo descuentan? | Arquitectura (propuesta: descuento bundle + refs) |
| C3 | ¿Cupón exclusive con membresía? | Analista |
| C4 | Service charge → tips vs surcharge | Analista (P2) |
| C5 | ¿Límite de promos por pedido (N máx)? | Analista |

---

## 12. Siguiente fase

**Fase 4 — Motor de Totales:** [`EN1_EPOSONE_MOTOR_TOTALES_V1.md`](EN1_EPOSONE_MOTOR_TOTALES_V1.md) (borrador listo) — algoritmo + ejemplos Panamá · cerrar T1 (propina↔impuesto).

---

*Borrador V6 Fase 3. Sin implementación hasta aprobación de Fases 1–5.*
