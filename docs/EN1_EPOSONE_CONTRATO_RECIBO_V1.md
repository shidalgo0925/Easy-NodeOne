# Contrato de Recibo EPosOne V1

| Campo | Valor |
|-------|--------|
| Estado | **Borrador** — 19 jul 2026 · pendiente Analista + Arquitectura |
| Fase V6 | **2.4** — [`EN1_PLATFORM_EPOSONE_V6_ROADMAP.md`](EN1_PLATFORM_EPOSONE_V6_ROADMAP.md) |
| Depende de | [Modelo](EN1_EPOSONE_MODELO_COMERCIAL_V1.md) · [Fiscal](EN1_EPOSONE_CONTRATO_FISCAL_V1.md) · [Propinas](EN1_EPOSONE_CONTRATO_PROPINAS_V1.md) · [Pagos](EN1_EPOSONE_CONTRATO_PAGOS_V1.md) |
| Siguiente | Fase 3 — [`EN1_EPOSONE_MOTOR_COMERCIAL_V1.md`](EN1_EPOSONE_MOTOR_COMERCIAL_V1.md) (borrador listo) · luego Motor de Totales |
| Alcance | **Negocio** — sin tablas, APIs ni drivers de impresora |
| Dual Mode | Mismo contrato; plantilla local (Standalone) o sync desde EN1 (Integrado) |

---

## 0. Objetivo

Definir **qué se imprime (o muestra como comprobante)** al cobrar un pedido, de forma configurable por empresa / sucursal / caja, sin layouts hardcodeados por vertical.

El Contrato de Recibo es una **política comercial tipificada**: plantilla por **secciones** (on/off + contenido), no un PDF fijo.

**Principio:** la impresión **consume** el resultado comercial (totales, impuestos tipificados, propina, pagos). No recalcula reglas fiscales ni de propina.

---

## 1. Conceptos

| Concepto | Definición |
|----------|------------|
| **Contrato de Recibo** | Paquete nombrado de plantilla + opciones de impresión |
| **Sección** | Bloque on/off del ticket (encabezado, detalle, QR, …) |
| **Tipo de documento** | Recibo de venta, precuenta, reembolso, apertura/cierre caja (v1 enfoca venta) |
| **Destino** | Impresora térmica, PDF/email, pantalla (reimpresión) |

```text
Resultado comercial del pedido
        +
Contrato de Recibo (secciones + branding)
        ↓
Documento de impresión / comprobante digital
```

---

## 2. Datos del contrato

| Campo | Obligatorio | Notas |
|-------|-------------|--------|
| Nombre / código | Sí | Ej. “Ticket 80 mm — restaurante” |
| Activo / vigencia / versión | Sí | Snapshot opcional en reimpresión histórica |
| Tipo papel | Sí | `58mm` / `80mm` / `A4` / `digital` |
| Idioma | Sí | Default empresa (`es-PA`, …) |
| Copias | No | Default 1; cocina vs cliente = destinos distintos |
| Impresora por defecto | No | Asignación también puede vivir en **config de caja** |

### Asignación

```text
Caja → Sucursal → Empresa
```

---

## 3. Secciones del recibo de venta

Cada sección: `enabled`, orden, y campos propios.

| # | Sección | Contenido típico | Default |
|---|---------|------------------|---------|
| 1 | **Encabezado** | Logo, nombre comercial, razón social, sucursal, dirección, teléfono, RUC/DV | On |
| 2 | **Meta operación** | Caja, cajero, turno, POS, fecha/hora local, nº recibo / nº pedido / local_number | On |
| 3 | **Cliente** | Contado o registrado (nombre, RUC/cédula, teléfono) | On si hay cliente |
| 4 | **Detalle** | Líneas: qty, unidad, descripción, precio, desc. línea, importe; opc. impuesto por línea | On |
| 5 | **Resumen comercial** | Subtotal, descuentos, **impuestos tipificados** (código/%/monto), recargos, **propina**, redondeo, **total** | On |
| 6 | **Pagos** | Cada medio + monto + referencia enmascarada; cambio si hubo | On |
| 7 | **QR** | FE / verificación EN1 / consulta recibo / URL custom | Configurable |
| 8 | **Pie** | Mensajes, redes, promo, política de devolución, leyendas legales | On |
| 9 | **Datos fiscales extra** | Régimen, resolución, CAI/FE placeholders | Según Fiscal/FE |

### Reglas de presentación

1. **Impuestos y propina nunca se fusionan** en una sola línea ambigua.
2. Si el Contrato Fiscal devolvió N líneas de impuesto, el recibo las lista (no solo un `tax` opaco), salvo sección detalle compacta opt-in.
3. Precios tax-inclusive: mostrar desglose si el contrato fiscal/recibo lo exige.
4. Reimpresión usa el **mismo snapshot** comercial del pedido (no recalcular con reglas nuevas).

---

## 4. Branding y mensajes

| Elemento | Descripción |
|----------|-------------|
| Logo | Imagen / omitir |
| Encabezado libre | 1–N líneas de texto |
| Pie libre | 1–N líneas |
| Redes | Handles / URLs opcionales |
| Política de devolución | Texto corto o “ver Términos” |
| Mensaje post-venta | Gracias / promo del día |

---

## 5. Numeración

| Campo | Notas |
|-------|--------|
| Número de recibo / ticket | Secuencia por caja o empresa (política) |
| Número de pedido | `local_number` / ref EN1 |
| Número de factura | Solo si hay documento fiscal emitido; distinto del ticket |

Dual Mode: en Standalone la secuencia es local; en Integrado EN1 puede ser autoridad de numeración fiscal (FE) mientras el ticket operativo sigue reglas del contrato.

---

## 6. QR

| Tipo QR | Uso |
|---------|-----|
| `none` | Sin QR |
| `receipt_lookup` | Consulta del comprobante |
| `en1_verify` | Verificación plataforma |
| `fe` | Factura electrónica (cuando exista) |
| `custom_url` | URL configurada |

Un contrato puede habilitar 0..N QR (v1: máximo 1 recomendado por ticket).

---

## 7. Tipos de documento (v1)

| Tipo | Estado v1 |
|------|-----------|
| `sale_receipt` | **En alcance** |
| `pre_account` | Preparado (mismas secciones; sin pagos o pagos parciales) |
| `refund_receipt` | Preparado (totales negativos / leyenda reembolso) |
| `shift_open` / `shift_close` | Fuera o mínimo — Hito caja |

---

## 8. Destinos e impresoras

| Destino | Notas |
|---------|--------|
| Impresora térmica de caja | Asignada en config de caja |
| Impresora cocina / barra | Destino por estación (no es el recibo fiscal; ticket producción) |
| Digital (PDF / share) | Misma plantilla, otro renderer |
| No imprimir | Cobro sin ticket (política) |

**Hardware fino** (ESC/POS, gaveta al imprimir): implementación; este contrato solo declara destino lógico y si `open_drawer_on_cash` (enlace Pagos).

---

## 9. Idioma y localización

- Idioma del contrato o override por caja.
- Formato fecha/hora: zona de la empresa (`America/Panama`) vía política TZ ya existente.
- Moneda: símbolo y decimales del pedido.

---

## 10. Dual Mode

| | Standalone | Integrado |
|--|------------|-----------|
| Edición plantilla | EPosOne | EN1 BO → sync |
| Impresión offline | Local con plantilla cacheada | Igual |
| FE / QR cloud | Limitado / local | EN1 puede completar URL FE al sync |

---

## 11. Criterio de aprobación

1. Modelo por secciones cubre encabezado → pie sin formato fijo único.
2. Separación impuestos / propina / pagos explícita.
3. Papel, idioma, QR, numeración tipificados.
4. Dual Mode y snapshot de reimpresión claros.
5. Preguntas §12 resueltas o aplazadas.

---

## 12. Preguntas abiertas

| # | Pregunta | Dueño |
|---|----------|-------|
| R1 | ¿Secuencia de ticket por caja o por empresa? | Analista |
| R2 | ¿Precuenta usa el mismo contrato con flag o contrato aparte? | Analista |
| R3 | ¿Logo obligatorio en Integrado? | Analista |
| R4 | ¿Máximo de líneas de pie / caracteres 58 mm? | Prog2 (constraint) + Analista |
| R5 | ¿Reimpresión cuenta como nuevo número o mismo? | Analista (propuesta: mismo número + marca REIMP) |

---

## 13. Relación con otros docs

| Doc | Relación |
|-----|----------|
| Fiscal / Propinas / Pagos | Datos del resumen y pagos |
| Motor Totales Fase 4 | Fuente del desglose |
| Config caja | Impresora, gaveta, contrato asignado |
| FE Panamá | Extiende sección fiscal / QR `fe` |

---

## 14. Cierre Fase 2

Con este documento, la **Fase 2 — Contratos** queda en borrador completo:

| # | Contrato | Doc |
|---|----------|-----|
| 2.1 | Fiscal | `EN1_EPOSONE_CONTRATO_FISCAL_V1.md` |
| 2.2 | Propinas | `EN1_EPOSONE_CONTRATO_PROPINAS_V1.md` |
| 2.3 | Pagos | `EN1_EPOSONE_CONTRATO_PAGOS_V1.md` |
| 2.4 | Recibo | `EN1_EPOSONE_CONTRATO_RECIBO_V1.md` |

**Siguiente sprint docs:** Fase 3 — Motor Comercial (promos, descuentos, políticas por scope).

---

*Borrador V6 Fase 2.4. Sin implementación hasta aprobación de Fases 1–5.*
