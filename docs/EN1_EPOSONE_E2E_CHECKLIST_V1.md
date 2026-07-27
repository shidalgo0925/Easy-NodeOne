# Lista oficial de pruebas E2E — Hito 2.5 + Cadena operativa

| Campo | Valor |
|-------|--------|
| Estado | **Oficial borrador** — 19 jul 2026 (Analista + Prog1) |
| Cierra | **Hito 2.5 Cajeros** + validación de cadena base Sync |
| Antes de | Motor Comercial V6 (algoritmos) · Hito 2.6 Observabilidad puede ir en paralelo corto |
| DoD | Cada caso: APK + EN1 + evidencia (screenshot/log/id) |
| Roadmap | [`EN1_POS_V7_ROADMAP.md`](EN1_POS_V7_ROADMAP.md) |

**Regla:** Hito 2.5 no se declara **cerrado** hasta pasar bloques **A + B + C + D**. El bloque **E** es regresión obligatoria el mismo día.

Leyenda: ☐ pendiente · ✅ OK · ❌ falló · N/A

---

## A. Provisioning + Bootstrap

| # | Caso | Resp. | ☐ |
|---|------|-------|---|
| A1 | APK limpia (sin datos / wipe) | Prog2 | ✅ |
| A2 | Provisionar dispositivo a caja EN1 | Ambos | ✅ |
| A3 | Bootstrap inicial completo | Ambos | ✅ |
| A4 | Descargar catálogo | Ambos | ✅ |
| A5 | Descargar cajeros | Ambos | ✅ |
| A6 | Descargar configuración de caja | Ambos | ✅ |
| A7 | Descargar versión de políticas (aunque vacía) | Ambos | ✅ |
| A8 | Verificar `cashiers_version` (y coherencia con EN1) | Ambos | ✅ |
| A9 | Reiniciar APK y confirmar persistencia (sin re-provisionar) | Prog2 | ✅ |

**Resultado esperado:** dispositivo listo para operar sin repetir provisioning.

**Acta 20 jul 2026:** Bloque A **OK** (Prog2 / tablet).

---

## B. Operación de Cajeros (cierre Hito 2.5)

| # | Caso | Resp. | ☐ |
|---|------|-------|---|
| B1 | Login PIN online | Prog2 | ☐ |
| B2 | Login PIN offline | Prog2 | ☐ |
| B3 | PIN incorrecto (mensaje / no entra) | Prog2 | ☐ |
| B4 | PIN bloqueado (si aplica política) | Ambos | ☐ |
| B5 | Abrir turno | Ambos | ☐ |
| B6 | Cambio de cajero | Prog2 | ☐ |
| B7 | Cambio de cajero con pedido abierto | Ambos | ☐ |
| B8 | Cambio de cajero con pedido pagado | Ambos | ☐ |
| B9 | Desactivar cajero desde EN1 | Prog1 | ☐ |
| B10 | Sincronizar tras desactivar | Ambos | ☐ |
| B11 | Confirmar bloqueo del cajero desactivado en APK | Prog2 | ☐ |
| B12 | Operaciones anteriores conservan cajero original (atribución) | Ambos | ☐ |

**Resultado esperado:** cajero atribuible, revocable y sincronizado. Sin esto → 2.5 sigue 🟡.

---

## C. Cadena operativa completa (prueba más importante)

| # | Caso | Resp. | ☐ |
|---|------|-------|---|
| C1 | Abrir turno | Ambos | ☐ |
| C2 | Crear pedido | Ambos | ☐ |
| C3 | Modificar pedido | Ambos | ☐ |
| C4 | Agregar productos | Ambos | ☐ |
| C5 | Eliminar productos | Ambos | ☐ |
| C6 | Cobrar en efectivo | Ambos | ☐ |
| C7 | Cobro mixto (persistencia correcta) | Ambos | ☐ |
| C8 | Imprimir recibo (o preview equivalente v1) | Prog2 | ☐ |
| C9 | Cerrar pedido / venta pagada | Ambos | ☐ |
| C10 | Sincronizar Push | Ambos | ☐ |
| C11 | EN1: ver pedido | Prog1 | ☐ |
| C12 | EN1: ver eventos | Prog1 | ☐ |
| C13 | EN1: ver pagos | Prog1 | ☐ |
| C14 | EN1: ver cajero atribuido | Prog1 | ☐ |
| C15 | EN1: ver caja | Prog1 | ☐ |
| C16 | EN1: ver turno | Prog1 | ☐ |

**Resultado esperado:** misma operación reconstruible en EN1 (pedido, pagos, cajero, caja, turno).

### C-extra — Multi-dispositivo y propina (R-PAY-MULTI / R-TIP-COBRO)

| # | Caso | Resp. | ☐ |
|---|------|-------|---|
| C17 | Device A (mesero): crear pedido abierto | Prog2 | ☐ |
| C18 | Device B (caja): abrir **el mismo** pedido (no duplicar) | Ambos | ☐ |
| C19 | Device B: cobrar (efectivo o mixto) | Ambos | ☐ |
| C20 | Device A online: sync → pedido **sale de abiertos** / estado pagado | Prog2 | ☐ |
| C21 | Device A: intentar cobrar de nuevo → **rechazado** (already_paid) | Ambos | ☐ |
| C22 | Device A offline al pagar B; al reconectar: cierra local, **sin** segundo cobro | Prog2 | ☐ |
| C23 | Cobro en caja **con propina libre** (si política lo permite) | Ambos | ☐ |
| C24 | Mesero dejó tip; caja **modifica tip** al cobrar → un solo tip en EN1/recibo | Ambos | ☐ |
| C25 | BO EN1: cobro + tip sobre pedido abierto de tablet | Prog1 | ☐ |

**Resultado esperado:** un pedido, un cobro, tip única; todos los devices alineados tras sync.

Docs: Domain Model §2.1 · Order Domain Spec §6 · [Contrato Propinas](EN1_EPOSONE_CONTRATO_PROPINAS_V1.md).

---

## D. Offline

| # | Caso | Resp. | ☐ |
|---|------|-------|---|
| D1 | Provisionar (online) | Ambos | ☐ |
| D2 | Desconectar Internet | Prog2 | ☐ |
| D3 | Login offline | Prog2 | ☐ |
| D4 | Abrir turno offline | Prog2 | ☐ |
| D5 | Crear pedido offline | Prog2 | ☐ |
| D6 | Cobrar offline | Prog2 | ☐ |
| D7 | Imprimir offline | Prog2 | ☐ |
| D8 | Cerrar turno offline | Prog2 | ☐ |
| D9 | Reconectar + Push | Ambos | ☐ |
| D10 | Sin duplicados (pedido/pago/turno) | Ambos | ☐ |
| D11 | Idempotencia (reintento no crea doble) | Ambos | ☐ |

---

## E. Regresión

Confirmar que **no se rompió**:

| # | Área | ☐ |
|---|------|---|
| E1 | Productos / catálogo | ☐ |
| E2 | Clientes | ☐ |
| E3 | Inventario (consulta/ajuste básico) | ☐ |
| E4 | Tickets / pedidos listado | ☐ |
| E5 | Pagos | ☐ |
| E6 | Recibos / impresión | ☐ |
| E7 | Bootstrap | ☐ |
| E8 | Historial | ☐ |

---

## Cierre formal

| Artefacto | Condición |
|-----------|-----------|
| Hito 2.5 | A+B+C+D en ✅ (E sin regresiones ❌) |
| Acta | Fecha, build APK, commit EN1, IDs de pedido/turno/pago de prueba C |
| Handoff | Actualizar [`EN1_EPOSONE_HANDOFF_STATUS.md`](EN1_EPOSONE_HANDOFF_STATUS.md) → 2.5 **Cerrado** |

Plantilla acta (copiar):

```text
Fecha:
APK build / versión:
EN1 commit:
Ambiente: appdev / easynodeone_dev
Casos A–E: (adjuntar checklist marcado)
IDs evidencia C: pedido=… turno=… pagos=…
Firmas: Prog2 · Prog1 · Analista (opcional)
```
