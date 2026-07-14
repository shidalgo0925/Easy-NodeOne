# HITO 3 — Dominio Operativo del Pedido

## Especificación Funcional V1.0

| Campo | Valor |
|-------|--------|
| Estado | **En diseño** — 14 jul 2026 |
| Objetivo | Definir el corazón operativo de EPosOne y EN1 **antes** de escribir código |
| ADR | [`ADR-006-EPOSONE-OPERATION-VS-ADMIN.md`](ADR-006-EPOSONE-OPERATION-VS-ADMIN.md) |
| Brief / instructions | [`EN1_EPOSONE_HITO3_ORDER_LIFECYCLE.md`](EN1_EPOSONE_HITO3_ORDER_LIFECYCLE.md) |
| Desarrollo | **CONGELADO** hasta congelar esta especificación (preguntas §13 respondidas) |
| Audiencia ahora | **Solo arquitectura** — no pasar a P1/P2 para implementar |

---

## 1. Objetivo

Construir un único modelo operativo que funcione para:

- Food Truck  
- Cafeterías  
- Kioscos  
- Restaurantes  
- Bares  
- Hoteles  
- Restaurantes VIP  
- Franquicias  

Sin cambiar el motor del POS.

---

## 2. Principios

### Regla 1 — Un solo Pedido

No existen “Pedido Food Truck”, “Pedido Restaurante”, “Pedido Express”.  
Existe únicamente: **Pedido**.

### Regla 2 — El Pedido vive en dos lugares

| Momento | Dueño |
|---------|--------|
| Durante la operación | **EPosOne** (puede trabajar offline) |
| Después del Sync | **EN1** (fuente oficial) |

### Regla 3 — El usuario nunca administra estados

El usuario ejecuta **acciones**. El sistema cambia los **estados**.

Ejemplo: Agregar producto → Enviar → Cobrar → Entregar.

---

## 3. Modelo principal

### Pedido (mínimo)

- Número local  
- Número EN1 (cuando sincronice)  
- Empresa  
- Sucursal  
- POS  
- Caja  
- Usuario  
- Cliente (opcional)  
- Fecha  
- Hora  
- Estado  
- Total  
- Impuestos  
- Descuentos  
- Propinas  
- Observaciones  
- Líneas  

### Cada línea

- Producto  
- Cantidad  
- Precio  
- Impuesto  
- Descuento  
- Observaciones  
- Estado  

---

## 4. Acciones

Únicas acciones visibles para el usuario:

| Acción |
|--------|
| Nuevo Pedido |
| Guardar |
| Agregar Producto |
| Quitar Producto |
| Modificar Cantidad |
| Enviar |
| Cobrar |
| Entregar |
| Anular |
| Devolver |
| Reimprimir |

Nada más.

---

## 5. Eventos

EN1 recibe **eventos**, no sincronización de tablas.

Ejemplos:

- `pedido.creado`  
- `pedido.actualizado`  
- `producto.agregado`  
- `producto.eliminado`  
- `cantidad.modificada`  
- `pedido.enviado`  
- `pedido.entregado`  
- `pedido.cobrado`  
- `pedido.anulado`  
- `pedido.devuelto`  

Todo auditable.

---

## 6. Cancelaciones — decisión oficial

| Caso | Momento | Tratamiento |
|------|---------|-------------|
| **1** | Antes de preparar | **No** hay cancelación: se **modifica** el pedido. No afecta inventario. |
| **2** | Después de preparar | **Anulación**. Registra motivo, usuario, fecha, hora. Puede requerir autorización. |
| **3** | Después de entregar | **Devolución**. Nunca “Cancelación”. |

---

## 7. Comunicación

```text
POS → Eventos → EN1 → Eventos → Otros POS / BackOffice
```

Nunca sincronización directa de tablas.

---

## 8. Operación (mismos Pedido, distintos flujos)

### Food Truck

Pedido → Cobrar → Entregar

### Restaurante

Pedido → Enviar → Listo → Cobrar → Entregar

### Restaurante VIP

Pedido → Preparación → Listo → Entregado → Cobrado → Factura

Todos usan el mismo **Pedido**.

---

## 9. Inventario — decisión arquitectónica

- Inventario oficial = **EN1**  
- EPosOne solo genera **eventos**  

Ejemplo: `pedido.cobrado` → EN1 → Kardex → Stock → Reportes

---

## 10. Caja

La caja pertenece al **POS**.  
Sus eventos también viajan a EN1:

- Caja abierta  
- Caja cerrada  
- Ingreso  
- Retiro  
- Arqueo  

---

## 11. Sincronización

Nunca sincronizar tablas.  
Siempre sincronizar **eventos**.

---

## 12. Offline

Todo debe funcionar sin Internet.

Al volver la conexión:

```text
Cola → Eventos → EN1 → Confirmación
```

---

## 13. Preguntas abiertas (antes de programar)

Sesión de arquitectura pendiente. **Nadie inventa reglas** hasta responder.

### A. Pedido

1. ¿Puede existir más de un pedido abierto por mesa?  
2. ¿Puede un pedido cambiar de caja?  
3. ¿Puede cambiar de cajero?  
4. ¿Puede dividirse en dos pedidos?  
5. ¿Puede fusionarse con otro?  

### B. Pago

1. ¿Un pedido puede tener varios pagos?  
2. ¿Pago mixto?  
3. ¿Abonos?  
4. ¿Pago parcial?  

### C. Cocina

1. ¿Una línea puede estar lista antes que otra?  
2. ¿Se entrega parcialmente?  
3. ¿Se cancela una sola línea?  

### D. Inventario

1. ¿Se descuenta al cobrar o al entregar?  
2. ¿Qué pasa con productos compuestos (combos)?  
3. ¿Qué pasa con recetas?  

### E. Sincronización

1. ¿Qué ocurre si el POS A modifica un pedido y el BackOffice también?  
2. ¿Quién gana?  
3. ¿Cómo se resuelven conflictos?  

---

## Próximo paso (solo Arquitectura)

1. Sesión exclusiva para responder §13 (A–E).  
2. Congelar esta especificación (V1.0 → **congelada**).  
3. Entonces: P1 dominio/APIs · P2 operación POS · E2E Hito 3.  

**No** pasar aún a programadores para implementar.  
Este documento, una vez congelado, será el más importante del proyecto después del Roadmap.
