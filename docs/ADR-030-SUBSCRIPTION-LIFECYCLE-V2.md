# ADR-030 — Subscription Lifecycle V2 (estados comerciales)

| Campo | Valor |
|-------|--------|
| ID | **ADR-030** |
| Título | Ciclo de vida de suscripción — estados y aprovisionamiento |
| Estado | **Aceptado (diseño)** — 6 ago 2026 · implementación por fases |
| Relacionados | [ADR-014](ADR-014-SUBSCRIPTION-REGISTRY.md) · [ADR-016](ADR-016-COMMERCIAL-LICENSING-V2-ENTITLEMENT.md) · [ADR-023](ADR-023-EPOSONE-TRIAL-SUBSCRIPTION-GRACE.md) · [ADR-028](ADR-028-EPOSONE-PLAN-DEFAULTS-COMMERCIAL-OVERRIDES.md) · [`SUBSCRIPTION_STATE_MACHINE.md`](eposone-onboarding/SUBSCRIPTION_STATE_MACHINE.md) |

---

## Decisión

Estados de producto (mapa a Registry):

| Producto | `subscription.status` (Registry) | Provision device |
|----------|----------------------------------|------------------|
| Draft | `PENDING` + meta `draft` | No |
| Pendiente aprobación | `PENDING` | No (salvo flag soporte) |
| Pendiente pago | `PENDING` / `PAST_DUE` según política | No |
| Activa / Trial | `ACTIVE` / `TRIAL` | Sí |
| Suspendida | `SUSPENDED` | No |
| Cancelada | `CANCELLED` | No |

Self-serve `/start` (Camino A, ADR-028): alta en **`TRIAL`** (comportamiento actual).  
Venta asistida (Camino B): **`PENDING`** hasta Activar.

Detalle: [`SUBSCRIPTION_STATE_MACHINE.md`](eposone-onboarding/SUBSCRIPTION_STATE_MACHINE.md).

**No** duplica ADR-016 entitlements; los estados gobiernan **cuándo** se puede provisionar.
