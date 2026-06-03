# Módulo FE EN1 — Instrucciones por fase (programador)

**Plan de negocio (Contactos + Factura comercial + FE):** [`../PLAN_MAESTRO_CONTACTOS_FACTURACION_FE_EN1.md`](../PLAN_MAESTRO_CONTACTOS_FACTURACION_FE_EN1.md)  
**Detalle técnico FE/PAC:** [`../PLAN_MODULO_EFACTURA_EN1.md`](../PLAN_MODULO_EFACTURA_EN1.md)

> **Importante:** la emisión fiscal debe enlazarse a `invoice_id` (Fase 8+).  
> `FASE_C_PAGOS.md` (emitir desde pago directo) queda **obsoleta**; ver Fase 9 del plan maestro (pago → factura → FE).

Ejecutar **en orden**. No iniciar fase siguiente sin checklist de la anterior en staging/dev.

| Estado | Fase doc | Nota |
|--------|----------|------|
| ✅ Hecho | A (código `917d139`) | Motor FE, config, prueba manual |
| ⏳ Reorientar | C | Sustituir por plan maestro Fase 9 |
| Pendiente | B, D–F | Según plan maestro fases 1–12 |

| Fase | Archivo | Objetivo |
|------|---------|----------|
| A | [FASE_A_BASE.md](FASE_A_BASE.md) | Módulo ON/OFF, modelos, admin, adapter efacturapty, emisión manual |
| B | [FASE_B_NORMALIZACION.md](FASE_B_NORMALIZACION.md) | Payload estándar EN1, mapper, validaciones |
| C | [FASE_C_PAGOS.md](FASE_C_PAGOS.md) | Hook post-pago, idempotencia |
| D | [FASE_D_NCR_ND.md](FASE_D_NCR_ND.md) | Nota crédito y débito |
| E | [FASE_E_OPERACION.md](FASE_E_OPERACION.md) | Reintentos, PDF/XML, consulta |
| F | [FASE_F_PRODUCCION.md](FASE_F_PRODUCCION.md) | Seguridad, cifrado, go-live |

**Ruta de código:** `backend/nodeone/modules/efactura/`  
**Entorno autorizado para commits:** `/opt/easynodeone/dev/app` → rama `develop`.
