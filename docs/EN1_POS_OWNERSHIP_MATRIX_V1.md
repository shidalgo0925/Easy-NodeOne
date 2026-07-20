# Ownership Matrix EN1-POS V1

| Campo | Valor |
|-------|--------|
| Estado | **Borrador Release 0** — 19 jul 2026 |
| Rector | [`EN1_POS_CONSTITUCION_V1.md`](EN1_POS_CONSTITUCION_V1.md) |
| Dominio | [`EN1_POS_DOMAIN_MODEL_V1.md`](EN1_POS_DOMAIN_MODEL_V1.md) |

---

## Leyenda

| Código | Significado |
|--------|-------------|
| **EN1** | Editable / creado solo en Back Office (SoT Integrado) |
| **LOCAL** | Editable en EPosOne (admin básica o Standalone SoT) |
| **GEN-POS** | Generado por operación del dispositivo |
| **GEN-EN1** | Generado por EN1 (reportes, FE enviada, etc.) |
| **SYNC** | Debe sincronizarse (dirección en columna) |
| **BOTH** | Editable en ambos con reglas de conflicto |

Conflictos (política por entidad):

| Código | Resolución |
|--------|------------|
| **S>D** | Servidor (EN1) gana |
| **D>S** | Dispositivo gana (raro; solo operación local en curso) |
| **MERGE** | Fusión controlada |
| **MANUAL** | Revisión humana |
| **REJECT** | Rechazo + dead-letter |

---

## Matriz — cadena operativa R1

| Entidad | Standalone SoT | Integrado SoT | Editable local | Sync | Conflicto | Notas |
|---------|----------------|---------------|----------------|------|-----------|-------|
| Empresa | LOCAL | EN1 | Solo datos básicos en Solo-POS | Up al vincular | S>D | Legal/FE en EN1 |
| Sucursal | LOCAL | EN1 | No (Integrado) | Down | S>D | |
| POS | LOCAL | EN1 | No (Integrado) | Down | S>D | |
| Caja | LOCAL | EN1 | No (Integrado) | Down | S>D | |
| Dispositivo | LOCAL+EN1 | EN1 | Provisioning/revocación EN1 | Heartbeat up | S>D | Token EN1 |
| Licencia | LOCAL snapshot | EN1 | No | Down + heartbeat | S>D | Offline grace ADR-007 |
| Cajero / PIN | LOCAL | EN1 | Cambio PIN local con sync | Down + eventos | S>D | Hash nunca en claro |
| Turno | GEN-POS | GEN-POS → EN1 | Apertura/cierre POS | Up | D>S si abierto; S>D meta | |
| Pedido | GEN-POS | GEN-POS → EN1 | POS | Up | MERGE líneas; S>D estado consolidado | |
| Venta | GEN-POS | GEN-POS → EN1 | No editar post-cierre | Up | S>D | Debe existir como entidad explícita |
| Pago | GEN-POS | GEN-POS → EN1 | POS | Up | REJECT dup idempotency | |
| Recibo | GEN-POS | GEN-POS / GEN-EN1 | Reimpresión | Up metadatos | S>D numeración | |
| Documento fiscal | GEN-POS o GEN-EN1 | Preferente GEN-EN1 | Contingencia local | Up/down estado | MANUAL si divergencia PAC | Relacionado a venta |
| Política comercial | LOCAL | EN1 | No (Integrado) | Down versionada | S>D | |
| Método de pago catálogo | LOCAL | EN1 | No (Integrado) | Down | S>D | |
| Reporte | — | GEN-EN1 | Solo consulta | — | — | |

---

## Matriz — catálogo e inventario

| Entidad | Standalone SoT | Integrado SoT | Editable local | Sync | Conflicto | Release |
|---------|----------------|---------------|----------------|------|-----------|---------|
| Producto | LOCAL | EN1 | Admin básica Solo-POS | Up/down | S>D Integrado | R1 |
| Categoría comercial | LOCAL | EN1 | Solo-POS básico | Down | S>D | R1 |
| Categoría fiscal | LOCAL/EN1 | EN1 | Vía producto | Down | S>D | R1 |
| Precio por sucursal | LOCAL | EN1 | No Integrado | Down | S>D | R1 parcial / R2 |
| Modificadores / variantes | LOCAL | EN1 | No Integrado | Down | S>D | R2 (mínimo R1 si bloquea venta) |
| Stock / movimiento | GEN-POS+LOCAL | EN1 SoT stock | Ajuste rápido Solo-POS = evento | Up | S>D stock oficial | R1 básico / R2 pleno |
| Compra / proveedor | — | EN1 | No | — | — | R2 |
| Cliente | LOCAL | EN1 | Alta rápida POS | Up/down | MERGE | R1 básico / R2 crédito |
| Promoción / descuento motor | LOCAL | EN1 política | No Integrado | Down | S>D | R1 |

---

## Matriz — seguridad y sync

| Entidad | Owner Integrado | Sync | Conflicto |
|---------|-----------------|------|-----------|
| Usuario admin EN1 | EN1 | — | — |
| Rol / permiso | EN1 | Down resumen a POS si aplica | S>D |
| Evento sync / cola | GEN-POS | Up | Idempotency key |
| Tombstone / delete lógico | EN1 | Down | S>D |
| Diagnóstico dispositivo | BOTH | Up telemetría | MERGE |

---

## Reglas operativas

1. En **Integrado**, el POS **no** escribe maestros EN1 directamente; emite eventos.
2. En **Standalone**, lo local es SoT hasta Vincular.
3. **Vincular** aplica estrategias importar / conservar EN1 / fusionar por entidad (ADR-004); resultado documentado en informe de migración.
4. Toda entidad **SYNC** exige versión o sequence + idempotency en el contrato de sync.

---

## Pendiente de congelar (Release 0 → aprobación)

- Precisión de conflicto en **pedido concurrente multi-dispositivo** (mesa).
- Contingencia FE: cuándo D>S vs MANUAL.
- Alcance exacto de “admin básica” Solo-POS (lista cerrada).
