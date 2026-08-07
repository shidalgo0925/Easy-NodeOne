# SUBSCRIPTION_STATE_MACHINE

SoT: [ADR-030](../ADR-030-SUBSCRIPTION-LIFECYCLE-V2.md) · [ADR-014](../ADR-014-SUBSCRIPTION-REGISTRY.md) · [ADR-023](../ADR-023-EPOSONE-TRIAL-SUBSCRIPTION-GRACE.md).

## Estados (producto → Registry)

```text
Draft ──────────────► PENDING (+ meta draft)
Pendiente aprobación ► PENDING
Pendiente pago ──────► PENDING | PAST_DUE
Activa ──────────────► ACTIVE
Trial ───────────────► TRIAL
Suspendida ──────────► SUSPENDED
Cancelada ───────────► CANCELLED
```

## Transiciones típicas

```text
/start self-serve     → TRIAL
Venta asistida        → PENDING → (Activar) → TRIAL | ACTIVE
Pago confirmado       → ACTIVE
Impago                → PAST_DUE → GRACE/SUSPENDED (ADR-023)
```

## Aprovisionamiento

Solo con estados entitled operativos: **TRIAL · ACTIVE · PAST_DUE** (ADR-016).  
**PENDING** no provisiona device por defecto.
