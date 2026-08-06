# EPosOne — Manual de operaciones para cajero y usuario final

| Campo | Valor |
|-------|--------|
| Audiencia | Cajero / operador de tablet EPosOne |
| No es para | Administrador EN1 (catálogo, licencias, reportes de negocio, OCC) |
| Producto | EPosOne (operación) + EN1 (administración) |
| Versión | 1.0 |
| Fecha | 6 ago 2026 |
| Alcance | Día a día en la tablet: login, turno, venta, cobro, cierre |

**Principio:** EPosOne ejecuta la venta; EN1 administra el negocio. El cajero opera el POS; no configura la plataforma.

Documentos técnicos de respaldo (admin / desarrollo):  
[`ADR-006`](ADR-006-EPOSONE-OPERATION-VS-ADMIN.md) · [`Hito 2.5 Cajero`](EPOSONE_EN1_HITO2_5_CASHIER_CONTRACT.md) · [`Turnos`](EN1_EPOSONE_CASH_SHIFT_SPEC_V1.md) · [`Pedido Hito 3`](EN1_EPOSONE_HITO3_SPEC_FUNCIONAL_V1.md)

---

## 1. Antes de empezar

Necesitás:

1. Tablet ya **vinculada** a tu caja (el administrador pegó el código de provisioning en la app).
2. Tu usuario de **cajero** creado en EN1 y un **PIN** (4 a 8 dígitos).
3. Que el turno anterior de esa caja esté **cerrado** (si quedó abierto, avisá al administrador).

En pantalla, durante la operación, debe verse siempre: **Caja · Cajero · Turno**.

| Concepto | Qué es |
|----------|--------|
| **Caja** | Punto de cobro fijo de la tablet (no la elegís vos al entrar) |
| **Cajero** | Vos: persona con PIN |
| **Turno** | Tu jornada de caja (abrir → vender → arqueo → cerrar) |
| **Código de provisioning** | Solo para vincular tablet; **no** es tu PIN |
| **Licencia** | De la **caja**, no del cajero; la gestiona el admin |

---

## 2. Arranque del día

| Paso | Qué hacés |
|------|-----------|
| 1 | Abrí la app **EPosOne** en la tablet |
| 2 | Elegí tu nombre e ingresá el **PIN** |
| 3 | **Abrí turno** e indicá el efectivo inicial del cajón |
| 4 | Confirmá que el turno quedó abierto |

Sin turno abierto no cobrás.

### Sin internet

- El PIN puede validarse **en la tablet** (no hace falta EN1 en ese momento).
- La apertura de turno se **sincroniza** cuando vuelva la red.
- Si la app muestra un conflicto al sincronizar, **no inventés datos**: avisá al administrador.

---

## 3. Vender (día a día)

Flujo normal:

```text
Nuevo pedido → Agregar productos → (Enviar a cocina si aplica) → Cobrar → Entregar / imprimir
```

| Acción | Uso |
|--------|-----|
| **Nuevo pedido** | Arranca la venta |
| **Agregar / quitar / cantidad** | Armá el pedido |
| **Guardar** | Dejá el pedido abierto sin cobrar |
| **Enviar** | Cocina / preparación (si el local lo usa) |
| **Cobrar** | Cierre de pago (efectivo, tarjeta, mixto, etc.) |
| **Entregar** | Marca entrega (parcial o total según el local) |
| **Reimprimir** | Ticket de nuevo |
| **Anular** | Después de preparar; pedí / registrá motivo |
| **Devolver** | Después de entregar |

### Reglas útiles

- Un pedido abierto por mesa: las órdenes nuevas se **agregan** al mismo pedido.
- Podés cobrar con **varios medios** (pago mixto), si está habilitado.
- Abonos o pagos parciales: solo clientes **registrados** (cuenta por cobrar), si el negocio lo usa.
- Offline: seguí operando si la app lo permite; al volver la red se sincroniza.
- Un pedido **ya cobrado** en otra caja no se cobra otra vez.

---

## 4. Durante el turno

- Cada venta queda a **tu nombre** (cajero del PIN con el que entraste).
- **No** cambies de caja desde la app: la tablet ya está fija a una caja.
- Cambio de cajero a mitad de turno: lo hace el **administrador en EN1** (no el flujo normal del POS).
- No es trabajo diario del cajero: crear bodegas, órdenes de compra, Kardex, costos ni licencias.

---

## 5. Cierre del turno

```text
Dejá de cobrar → Contá el efectivo del cajón → Arqueo + Cerrar turno
```

| Paso | Qué hacés |
|------|-----------|
| 1 | Asegurate de no dejar pedidos a medias que deban cobrarse en tu turno |
| 2 | Contá el **efectivo** real del cajón |
| 3 | Ingresá el monto contado y **cerrá el turno** |
| 4 | Guardá o imprimí el comprobante de cierre si la app lo ofrece |

El esperado del cajón es **solo efectivo** (ventas en cash y movimientos de caja autorizados).

Si **no cuadra**: no “arreglés” a mano. Avisá al administrador para revisar el arqueo / Centro de Control en EN1.

---

## 6. Problemas frecuentes

| Situación | Qué hacer |
|-----------|-----------|
| PIN incorrecto | Reintentá; tras varios fallos puede haber bloqueo temporal |
| Olvidé el PIN | Solo el administrador puede reasignarlo en EN1 |
| “Sin licencia” / la app no opera | Avisá al admin: es licencia de la **caja** |
| Tablet nueva o reemplazo | El admin genera un código de provisioning nuevo; la licencia de la caja se mantiene |
| Sin red | Vendé si la app lo permite; sincronizá al volver |
| Pedido ya cobrado | No insistir; revisar con admin si hace falta |
| La app pide código de instalación | Es provisioning (admin), **no** tu PIN de cajero |
| Conflicto al sincronizar | No borres ni dupliques: avisá al admin |

---

## 7. Qué no hace el cajero

- Crear o renovar códigos de provisioning  
- Activar, extender o suspender licencias  
- Administrar el catálogo “de fondo” en locales con Back Office EN1  
- Editar stock oficial / Kardex  
- Abrir o cerrar turnos de **otras** cajas desde la tablet  

---

## 8. Resumen rápido (checklist)

**Al abrir**

- [ ] App abierta y tablet vinculada  
- [ ] Login con PIN  
- [ ] Turno abierto con efectivo inicial  

**Al operar**

- [ ] Pedidos claros (mesa / cliente si aplica)  
- [ ] Cobro correcto (medio y monto)  
- [ ] Ticket / entrega según el local  

**Al cerrar**

- [ ] Conteaste el efectivo  
- [ ] Cerraste el turno  
- [ ] Avisaste diferencias al admin  

---

*Documento orientado a operación diaria. Los nombres exactos de botones pueden variar levemente según versión de la APK y configuración del local.*
