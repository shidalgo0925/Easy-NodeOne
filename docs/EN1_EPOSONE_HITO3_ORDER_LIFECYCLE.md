# EPosOne ↔ EN1 — Hito 3/4: instrucciones P1/P2

| Campo | Valor |
|-------|--------|
| Roadmap | [`EN1_PLATFORM_EPOSONE_V5_ROADMAP.md`](EN1_PLATFORM_EPOSONE_V5_ROADMAP.md) |
| Spec dominio | [`EN1_EPOSONE_ORDER_DOMAIN_SPEC_V1.md`](EN1_EPOSONE_ORDER_DOMAIN_SPEC_V1.md) |
| Spec funcional | [`EN1_EPOSONE_HITO3_SPEC_FUNCIONAL_V1.md`](EN1_EPOSONE_HITO3_SPEC_FUNCIONAL_V1.md) |
| Estado código | Spec **CONGELADA** · implementación ⏸ hasta **GO P1** |

---

## Pieza 1 — Programador 1 (EN1) · Hito 3

Va **primero**. Define el contrato.

### Debe crear únicamente

Entidades: `Order` · `OrderItem` · `OrderPayment` · `OrderEvent` · `OrderCancellation` · `OrderReturn`  

APIs (ejemplo; paths finales en Spec):

- `POST/GET /api/v1/orders`  
- `GET/PATCH /api/v1/orders/{id}`  
- `POST /api/v1/orders/{id}/events`  
- `POST /api/v1/orders/{id}/payments`  

### No escribir

Inventario · Kardex · stock · FE · reabrir H1/H2 · inventar reglas fuera de la Spec  

Auth POS: Device Bearer (mismo espíritu Hito 1/2).

---

## Pieza 2 — Programador 2 (EPosOne) · Hito 4

Solo **después** de contrato congelado.

Adaptar APK: consumir APIs · no inventar reglas.

Mínimo: Nuevo Pedido · Agregar/Eliminar · Cantidad · Cobrar · Entregar · Sincronizar  

---

## Criterio E2E (cierra Hito 4; Hito 3 entrega base EN1)

1. Pedido nace en un POS  
2. Se modifica  
3. Se sincroniza  
4. Visible en EN1 / BackOffice  
5. Cobro desde otro POS o BO  
6. Trazabilidad completa  
7. Sin conflictos (Ownership)  

---

## Congelado siempre

Provisioning · Bootstrap · Catálogo · Productos · Inventario maestro · POS Core  
