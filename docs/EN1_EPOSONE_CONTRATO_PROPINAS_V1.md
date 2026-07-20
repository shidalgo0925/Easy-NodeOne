# Contrato de Propinas EPosOne V1

| Campo | Valor |
|-------|--------|
| Estado | **Borrador** — 19 jul 2026 · pendiente Analista + Arquitectura |
| Fase V6 | **2.2** — [`EN1_PLATFORM_EPOSONE_V6_ROADMAP.md`](EN1_PLATFORM_EPOSONE_V6_ROADMAP.md) |
| Depende de | [`EN1_EPOSONE_MODELO_COMERCIAL_V1.md`](EN1_EPOSONE_MODELO_COMERCIAL_V1.md) · [`EN1_EPOSONE_CONTRATO_FISCAL_V1.md`](EN1_EPOSONE_CONTRATO_FISCAL_V1.md) |
| Siguiente | Fase 2.3 — [`EN1_EPOSONE_CONTRATO_PAGOS_V1.md`](EN1_EPOSONE_CONTRATO_PAGOS_V1.md) (borrador listo) · luego Recibo |
| Alcance | **Negocio** — sin tablas, APIs ni DDL |
| Dual Mode | Mismo contrato; origen local (Standalone) o EN1 (Integrado) |

---

## 0. Objetivo

Definir **cómo se calculan, aplican, modifican y distribuyen las propinas** en un pedido EPosOne, igual en Standalone e Integrado.

El Contrato de Propinas es un **tipo de política comercial** (Modelo Comercial §4): versionado, con vigencia y asignable a empresa / sucursal / caja.

**Principio:** la propina **no es un impuesto**. En recibo, reportes y desglose va en sección propia, nunca mezclada con ITBMS/ISC.

**No incluye:** layout de ticket (Contrato Recibo), medios de pago (Contrato Pagos), motor de totales completo (Fase 4).

---

## 1. Conceptos

| Concepto | Definición |
|----------|------------|
| **Contrato de Propinas** | Paquete nombrado de reglas de propina para un ámbito |
| **Modo de aplicación** | Obligatoria / sugerida / opcional / sin propina |
| **Modo de cálculo** | Sin propina, %, monto fijo, escalonada, según consumo |
| **Base de cálculo** | Sobre qué monto se aplica el % o el escalado |
| **Distribución** | A quién se asigna contablemente / operativamente la propina |
| **Línea de propina** | Resultado tipificado en el pedido (monto, modo, si fue editada) |

```text
Contrato de Propinas activo (caja/sucursal/empresa)
        ↓
Cálculo propuesto (o cero)
        ↓
Cajero / cliente confirma, modifica o elimina (según permisos)
        ↓
Monto de propina en el resultado comercial
        ↓
Cobro (puede ir en el mismo tender o separado — Contrato Pagos)
```

---

## 2. Datos del contrato

| Campo | Obligatorio | Notas |
|-------|-------------|--------|
| Nombre | Sí | Ej. “Restaurante — 10 % sugerida” |
| Código | Sí | Único en la empresa |
| Activo | Sí | |
| Vigencia desde / hasta | Sí / opcional | |
| Versión | Sí | Snapshot en pedidos cerrados |
| País / vertical (opcional) | No | Ayuda operativa (PA / restaurante) |

### Asignación

Misma resolución que Fiscal (propuesta):

```text
Caja → Sucursal → Empresa → (default: Sin propina)
```

---

## 3. Información general — perfiles seed (ilustrativos)

| Código | Nombre | Uso típico |
|--------|--------|------------|
| `NONE` | Sin propina | Retail, gasolinera, kiosco |
| `SUG_10_15_20` | Sugerida 10/15/20 % | Restaurante / café |
| `AUTO_10` | Obligatoria 10 % | Grupos / política casa |
| `FIXED_SERVICE` | Monto fijo servicio | Eventos / catering |

---

## 4. Cálculo

### 4.1 Modos de cálculo

| Modo | Descripción |
|------|-------------|
| `none` | No calcula propina (contrato “Sin propina”) |
| `percent` | Un porcentaje sobre la base (§5) |
| `fixed` | Monto fijo por pedido (o por cubierto si se declara) |
| `tiered` | Escalonada: tramos de consumo → % o monto |
| `by_spend` | Según consumo: reglas tipo “si subtotal ≥ X → Y %” (puede solaparse con `tiered`; v1 trata `tiered` como la forma canónica) |

### 4.2 Escalonada (`tiered`) — estructura

Lista ordenada de tramos:

| Desde (base) | Hasta (base) | % o monto fijo |
|--------------|--------------|----------------|
| 0 | 49.99 | 0 % |
| 50 | 99.99 | 10 % |
| 100 | ∞ | 15 % |

Gana el tramo que contiene la base. Sin solapes; gaps = 0 o error de configuración.

### 4.3 Sugerencias múltiples (UI)

Aunque el modo sea `percent`, el contrato puede declarar **opciones sugeridas** (ej. 10 / 15 / 20 %) para el teclado de cobro. Una de ellas puede ser `default_suggestion`.

Esto no cambia el modo de cálculo: son atajos de captura cuando la aplicación es `suggested` u `optional`.

---

## 5. Base de cálculo

| Código | Significado |
|--------|-------------|
| `subtotal` | Suma de líneas antes de descuentos globales |
| `subtotal_discounted` | Tras descuentos de línea y globales / promos |
| `pre_tax` | Base antes de impuestos (= suele alinearse con `subtotal_discounted`) |
| `post_tax` | Tras impuestos |
| `minimum_spend` | Solo si la base ≥ umbral; si no, propina = 0 (salvo obligatoria con otra regla) |

**Default propuesto v1:** `subtotal_discounted` + **antes del impuesto** (`pre_tax`).

> Alineación final con el orden Pedido → … del Motor de Totales = **Fase 4** (pregunta abierta Q1 / F4).

### Exclusiones de productos

- Lista de categorías de producto o flags (`tip_eligible = false`) excluidos de la base.
- Ej.: propina no se calcula sobre tabaco, gift cards, o ítems marcados “sin propina”.

---

## 6. Aplicación (comportamiento en caja)

| Modo aplicación | Comportamiento |
|-----------------|----------------|
| `none` | No se muestra captura de propina (o solo lectura 0) |
| `mandatory` | Se aplica el cálculo; el cajero **no puede eliminar**; modificar solo si `allow_modify` |
| `suggested` | Se propone el monto/default; cajero o cliente puede aceptar otra sugerencia o editar si está permitido |
| `optional` | Por defecto 0; se puede agregar |

### Flags de control

| Flag | Default propuesto | Descripción |
|------|-------------------|-------------|
| `allow_modify` | `true` en sugerida/opcional; `false` o supervisor en obligatoria | Permite cambiar el monto |
| `allow_remove` | `true` solo si no es `mandatory` | Permite dejar propina en 0 |
| `require_supervisor_to_modify` | `false` | Si `true`, PIN supervisor para editar/quitar |
| `max_percent_of_base` | ej. 50 % | Tope de seguridad (evita errores / fraude) |
| `min_amount` / `max_amount` | opcional | Cotas absolutas |

**Compatibilidad con hoy:** el fallback EN1 que infiere propina desde overflow de pago es **red de seguridad**, no el flujo normal. El flujo normal = propina tipificada según este contrato **antes o junto** al cobro.

---

## 7. Distribución

Define el **destino operativo/contable** de la propina (no el cálculo).

| Destino | Descripción |
|---------|-------------|
| `waiters` | Meseros |
| `cashiers` | Cajeros |
| `kitchen` | Cocina |
| `bar` | Barra |
| `delivery` | Delivery / repartidores |
| `common_pool` | Fondo común |
| `custom` | Distribución personalizada (porcentajes que suman 100 %) |

### Distribución personalizada

Lista de destinatarios con `%` (suma = 100). Opcional: “por turno / por persona” queda fuera de v1 (solo pool por rol).

**Reportes:** el Motor de Totales y caja deben poder totalizar propinas por destino; el detalle de liquidación a personas es fase posterior.

---

## 8. Relación con impuestos y pagos

| Tema | Regla v1 |
|------|----------|
| Impuestos | Propina **fuera** del desglose fiscal salvo regla fiscal explícita (Fiscal F4 → default no) |
| Recibo | Sección “Propina” distinta de “Impuestos” |
| Pagos | El monto a cobrar = total comercial **incluye** propina; puede pagarse en el mismo tender o tender tipificado (Contrato Pagos) |
| Reembolso | Propina se revierte según política de reembolso (total/parcial) en Contrato Pagos |

---

## 9. Resultado en el pedido (negocio)

| Salida | Descripción |
|--------|-------------|
| `tip_amount` | Monto final |
| `tip_mode` | none / percent / fixed / tiered / … |
| `tip_application` | mandatory / suggested / optional |
| `tip_base` | Base usada |
| `tip_percent` | Si aplica |
| `tip_edited` | Si el usuario modificó el propuesto |
| `tip_distribution` | Código de destino / snapshot |
| Snapshot contrato | Código + versión del Contrato de Propinas |

Compatibilidad temporal: campo escalar `tip` del Order Domain = `tip_amount`.

---

## 10. Dual Mode

| | Standalone | Integrado |
|--|------------|-----------|
| Alta/edición contrato | EPosOne local | EN1 BO |
| Cálculo en venta | Motor local (misma spec) | Preview local; EN1 valida al sync |
| UI 10/15/20 hardcode | **Prohibido** a futuro; debe leer opciones del contrato | Igual |

---

## 11. Fuera de alcance v1

- Liquidación nómina / propina por empleado nominado
- Propina en moneda distinta a la del pedido
- Propina “invisible” (service charge disfrazado) — si es recargo fiscal, va a Fiscal o a un tipo `surcharge` del Motor Comercial (Fase 3), no aquí

---

## 12. Criterio de aprobación

1. Modos de cálculo y aplicación cubren restaurante, retail (none) y obligatoriedad.
2. Base, exclusiones y topes quedan claros.
3. Distribución es tipificada (incl. custom).
4. Separación estricta propina ≠ impuesto.
5. Dual Mode explícito.
6. Preguntas §13 resueltas o aplazadas a Fase 4 con dueño.

---

## 13. Preguntas abiertas

| # | Pregunta | Dueño |
|---|----------|-------|
| P1 | ¿Default Panamá restaurante = sugerida 10/15/20 sobre `subtotal_discounted` pre-tax? | Analista |
| P2 | ¿Service charge obligatorio = este contrato (`mandatory`) o recargo del Motor Comercial? | Analista |
| P3 | ¿Propina compartida en pago mixto (ej. tip solo en tarjeta)? | Analista + 2.3 |
| P4 | Orden exacto propina vs impuesto | Fase 4 |
| P5 | ¿Obligatoria se calcula al agregar ítems o solo en pantalla de cobro? | Arquitectura / UX |

---

## 14. Relación con otros docs

| Doc | Relación |
|-----|----------|
| Modelo Comercial V1 | Política tipificada |
| Contrato Fiscal 2.1 | No mezclar; base fiscal default sin propina |
| Contrato Pagos 2.3 | Cobro del total con tip; reembolsos |
| Contrato Recibo 2.4 | Sección propina |
| Motor Totales Fase 4 | Aplica este contrato en el algoritmo |

---

*Borrador V6 Fase 2.2. Sin implementación hasta aprobación de Fases 1–5 según roadmap.*
