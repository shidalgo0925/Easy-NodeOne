# COMMERCIAL_OVERRIDE_MODEL

SoT: [ADR-028](../ADR-028-EPOSONE-PLAN-DEFAULTS-COMMERCIAL-OVERRIDES.md) · [ADR-016](../ADR-016-COMMERCIAL-LICENSING-V2-ENTITLEMENT.md).

## Separación

| Capa | Editable por cliente | Editable por Gerencia |
|------|----------------------|------------------------|
| Plan (catálogo) | Solo elegir en `/start` | Cambiar plan (evento auditado) |
| Recursos del plan | No | No (solo lectura) |
| Overrides | No | Sí (motivo + #contrato) |

```text
effective_limits = plan_defaults ⊕ overrides
```

## Admin UI (norma)

- Bloque **Recursos del plan**
- Bloque **Ajustes comerciales**
- Historial auditado

Implementación de pantalla Admin: GO aparte (ADR-028 §10).
