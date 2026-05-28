# Módulo FE EN1 — Instrucciones por fase (programador)

Plan maestro: [`../PLAN_MODULO_EFACTURA_EN1.md`](../PLAN_MODULO_EFACTURA_EN1.md)

Ejecutar **en orden**. No iniciar fase siguiente sin checklist de la anterior en staging/dev.

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
