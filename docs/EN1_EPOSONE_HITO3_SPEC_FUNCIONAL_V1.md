# HITO 3 — Dominio Operativo del Pedido

## Especificación Funcional V1.0

| Campo | Valor |
|-------|--------|
| Estado | **Decisiones A–E cerradas** · Order Domain Spec **CONGELADA** v1.0 |
| Fuente de verdad dominio | [`EN1_EPOSONE_ORDER_DOMAIN_SPEC_V1.md`](EN1_EPOSONE_ORDER_DOMAIN_SPEC_V1.md) |
| Roadmap | [`EN1_PLATFORM_EPOSONE_V5_ROADMAP.md`](EN1_PLATFORM_EPOSONE_V5_ROADMAP.md) |
| ADR | [`ADR-006-EPOSONE-OPERATION-VS-ADMIN.md`](ADR-006-EPOSONE-OPERATION-VS-ADMIN.md) |
| Brief | [`EN1_EPOSONE_HITO3_ORDER_LIFECYCLE.md`](EN1_EPOSONE_HITO3_ORDER_LIFECYCLE.md) |
| Desarrollo | Spec congelada · código solo con **GO P1** |
| Audiencia código | P1 tras GO |

Documento histórico de la Spec Funcional. Las respuestas §13 y el contrato de implementación viven en la **Order Domain Spec v1.0**.

---

## 1–12. Resumen

Ver Order Domain Spec + secciones originales abajo por continuidad.

### Principios

- Un solo Pedido · dueño POS en operación / EN1 tras sync · acciones ≠ estados · eventos no tablas · inventario oficial EN1 · caja en POS con eventos  

### Acciones

Nuevo Pedido · Guardar · Agregar/Quitar Producto · Modificar Cantidad · Enviar · Cobrar · Entregar · Anular · Devolver · Reimprimir  

### Cancelaciones

| Momento | Tratamiento |
|---------|-------------|
| Antes de preparar | Modificar |
| Después de preparar | Anulación (+ motivo) |
| Después de entregar | Devolución |

---

## 13. Preguntas A–E — respuestas (cerradas 14 jul)

### A. Pedido

| Pregunta | Respuesta |
|----------|-----------|
| ¿Más de un pedido abierto por mesa? | **No** — uno abierto; nuevas órdenes se **agregan** |
| ¿Cambiar de caja? | Cobro desde **cualquier caja autorizada** (etapa cobro) |
| ¿Cambiar de cajero? | **Sí** |
| ¿Dividir? | **Sí** |
| ¿Fusionar? | **No** |

### B. Pago

| Pregunta | Respuesta |
|----------|-----------|
| ¿Varios pagos / mixto? | **Sí** |
| ¿Abonos / parciales? | **Sí** — solo clientes registrados → **CxC** |
| ¿Un cierre financiero? | **Sí** |

### C. Cocina

| Pregunta | Respuesta |
|----------|-----------|
| ¿Línea lista antes que otra? | **Sí** |
| ¿Entrega parcial? | **Sí** |
| ¿Cancelar una línea? | **Sí** |

### D. Inventario

| Pregunta | Respuesta |
|----------|-----------|
| ¿Quién descuenta? | **EN1** tras eventos; POS no escribe Kardex |
| ¿Combos? | No descontar combo; descontar **productos/componentes** |
| ¿Recetas? | Soporte futuro; **no** implementar aún |
| ¿Cobrar vs entregar? | Decisión de **Hito 5**; dominio emite ambos eventos |

### E. Sincronización

| Pregunta | Respuesta |
|----------|-----------|
| ¿Conflictos POS vs BO? | **Ownership**: no owner → no edita; no hay race de merge |
| ¿Quién gana? | No aplica: solo el owner escribe en abierto; cobro multi-punto autorizado |

---

## Detalle narrativo (V1.0 original)

### Objetivo

Un modelo para Food Truck, cafeterías, kioscos, restaurantes, bares, hoteles, VIP, franquicias — sin cambiar el motor del POS.

### Comunicación

```text
POS → Eventos → EN1 → Eventos → BackOffice / Otros POS
```

### Offline

```text
Cola → Eventos → EN1 → Confirmación
```

### Flujos ejemplo

- Food Truck: Pedido → Cobrar → Entregar  
- Restaurante: Pedido → Enviar → Listo → Cobrar → Entregar  
- VIP: Pedido → Preparación → Listo → Entregado → Cobrado → Factura  

Todos = mismo Pedido.
