# Arquitectura EN1-POS V7

| Campo | Valor |
|-------|--------|
| Estado | **Borrador Release 0** — 19 jul 2026 |
| Rector | [`EN1_POS_CONSTITUCION_V1.md`](EN1_POS_CONSTITUCION_V1.md) |
| Dominio | [`EN1_POS_DOMAIN_MODEL_V1.md`](EN1_POS_DOMAIN_MODEL_V1.md) |
| Ownership | [`EN1_POS_OWNERSHIP_MATRIX_V1.md`](EN1_POS_OWNERSHIP_MATRIX_V1.md) |

---

## 1. Vista lógica

```text
┌─────────────────────────────────────────────────────────┐
│                     EN1-POS (Back Office)                 │
│  Maestros · Políticas · Licencias · FE · Reportes · Audit │
│  PostgreSQL (silo) · APIs · Web BO                        │
└───────────────────────────▲─────────────────────────────┘
                            │ Bootstrap / Pull (versiones)
                            │ Push eventos (idempotent)
                            │ Heartbeat / licencia
┌───────────────────────────┴─────────────────────────────┐
│              EPosOne (Operación · offline-first)          │
│  Pedido · Turno · Pago · Recibo · Cola sync · Réplica     │
│  Motor de totales (paridad) · Snapshot políticas          │
└─────────────────────────────────────────────────────────┘
```

Misma **lógica de negocio**; distinto **origen de maestros** (Standalone vs Integrado).

---

## 2. Capas (EN1)

| Capa | Responsabilidad | Nota V7 |
|------|-----------------|---------|
| **Domain** | Entidades y reglas (pedido, venta, pago, turno, política, FE) | Separar **Venta** de Pedido |
| **Application services** | Casos de uso, idempotencia, permisos | Un servicio de totales compartido |
| **API / Sync** | HTTP devices/orders + cola sync | Demostrabilidad (quién/cuándo/resultado) |
| **BO UI** | Administración y consulta | No es el motor |
| **Integrations** | PAC FE, pasarelas futuras | FE no contamina totales comerciales |

Código existente relevante (no es inventario exhaustivo):

- `backend/nodeone/modules/eposone/` — app EPosOne BO + routes devices/orders
- `backend/nodeone/core/commerce/` — order/payment/cash/fiscal/reports
- `backend/nodeone/core/eposone_domain/` — dominio Dual Mode / link
- `backend/models/eposone_*.py` — persistencia específica

---

## 3. Motor de totales (paridad)

```text
Input: líneas + políticas (versión) + propina/cargos
        ↓
   Motor de totales (especificación única)
        ↓
   Desglose auditable
        ↓
   ┌────────┬────────┬────────┬────────┐
   │ APK    │ EN1    │ Recibo │ FE/Rep. │
   └────────┴────────┴────────┴────────┘
```

Infra de políticas ya existe (store + sync); **algoritmo** aún stub. Contratos V6 alimentan la especificación; ADR-008 documenta decisiones tras aprobación.

---

## 4. Venta vs documento fiscal

```text
Pedido (operativo)
  → Venta (financiera cerrada)
      → Pagos 1:N
      → Recibo (operativo)
      → Documento fiscal (legal) ──► PAC / contingencia
```

Una caída del PAC **no** debe impedir cerrar la venta si hay modo contingencia autorizado; estados FE quedan auditables.

---

## 5. Sync (requisitos arquitectónicos R1)

| Requisito | Descripción |
|-----------|-------------|
| Idempotency key | Por evento de dispositivo |
| Sequence / versiones | Por dominio sync |
| Observabilidad | Recibido_at, device, resultado, error, reintento |
| Conflictos | Según Ownership Matrix |
| DLQ / replay | Soporte sin SSH (mínimo R1) |

---

## 6. Seguridad

- Device token + org isolation (multi-tenant).
- Cajero: PIN hash; nunca pin en logs/bootstrap.
- Acciones sensibles: auditoría.
- Licencia: snapshot local + grace offline (ADR-007).

---

## 7. Lo que esta arquitectura prohíbe

- Cálculos distintos en UI Flutter vs EN1.
- Escribir stock/maestros EN1 desde el POS en Integrado (solo eventos).
- Tratar FE como “campo del recibo” sin entidad propia.
- Nuevos módulos fuera del backlog del release activo.

---

## 8. Relación con docs previos

| Doc | Rol bajo V7 |
|-----|-------------|
| ADR-001…007 | Siguen vigentes; Ownership/Constitución los precisan |
| V4/V5 roadmaps | Históricos / base técnica |
| V6 comercial | Inputs de contratos/motores → se consumen en R1 (B-R1-08+) |
| Constitución V1 | Gana en conflictos de producto |
