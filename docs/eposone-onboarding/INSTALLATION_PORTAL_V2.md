# INSTALLATION_PORTAL_V2

| Campo | Valor |
|-------|--------|
| Ruta | `/admin/eposone/install` |
| ADRs | ADR-021 · ADR-027 · ADR-028 · ADR-029 |

## Debe mostrar

| Métrica | Significado |
|---------|------------|
| POS incluidos | Cupo efectivo (`effective_limits.pos`) |
| POS instalados | Devices/cajas ya vinculadas |
| POS disponibles | incluidos − instalados |

Cada instalación (código → register) **consume** un cupo disponible.

## Separación de licencias

| Comercial | Técnica |
|-----------|---------|
| Suscripción / plan / overrides / facturación | Tablet / POS / provision / bootstrap |

## Gate

Sin suscripción entitled (`TRIAL`/`ACTIVE`/…) o sin cupo → no emitir código / no register (según ADR-030).
