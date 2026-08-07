# ORGANIZATION_RESOLVER_V2

Norma operativa de [ADR-029](../ADR-029-ORGANIZATION-CONTEXT-RESOLVER-V2.md).

## Orden

1. `organization_id` explícito  
2. `pending_initial_context` (post-`/start`)  
3. Selección explícita (picker)  
4. Host tenant (si acceso)  
5. Única org elegible  
6. `last_selected` (solo sin pending)  
7. Selector si hay ambigüedad  

## Pending

| Campo | Uso |
|-------|-----|
| `user.pending_initial_organization_id` | Org creada en `/start` |
| `user.pending_initial_organization_at` | Timestamp; TTL 7 días |

Consumo: primer login que aplica el pending → NULL.

## Reglas

- Usuarios `/start`: **no** `is_admin` plataforma.
- Nunca auto-entrar a otra org si hay pending vigente.
- Ambigüedad multi-org sin pending → pantalla de selección.
