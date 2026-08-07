# ADR-029 — Organization Context Resolver V2

| Campo | Valor |
|-------|--------|
| ID | **ADR-029** |
| Título | Organization Context Resolver V2 — onboarding sin org equivocada |
| Estado | **Aceptado (diseño + P0.1 implementación)** — 6 ago 2026 |
| Fecha | 2026-08-06 |
| Producto | EN1 (todas las superficies) · EPosOne `/start` |
| Relacionados | [ADR-028](ADR-028-EPOSONE-PLAN-DEFAULTS-COMMERCIAL-OVERRIDES.md) · [ADR-024](ADR-024-EPOSONE-START-ASSISTANT.md) · [ADR-027](ADR-027-EPOSONE-ONBOARDING-UNIFICADO-V1.md) · [`ORGANIZATION_RESOLVER_V2.md`](eposone-onboarding/ORGANIZATION_RESOLVER_V2.md) |
| Este GO | Docs + implementación crítica P0.1 (`pending_initial_context` + orden de resolución) |

---

## 1. Problema

Tras `/start`, el primer login abría **otra** organización (p. ej. Mexican Food) por:

1. usuarios de `/start` marcados `is_admin=True` → veían **todas** las orgs;
2. heurística admin en host producto: `last_selected` o «org con más catálogo».

## 2. Decisión

### 2.1 Separación de dominios

| Dominio | Responsabilidad |
|---------|-----------------|
| **Login** | Autenticar usuario. Nada más. |
| **Organization Resolver** | Decidir `organization_id` de sesión. No autentica. |

### 2.2 Orden de resolución (obligatorio)

```text
1. organization_id explícito (form / query / picker)
2. pending_initial_context (creación /start — una sola vez)
3. Organización seleccionada explícitamente (require_org_selection → pick)
4. Host/subdominio tenant (si el usuario tiene acceso)
5. Única organización elegible
6. last_selected_organization (solo si NO hay pending)
7. Selector de organizaciones (ambigüedad)
```

**Nunca** aplicar `last_selected` ni «más catálogo» si existe `pending_initial_context` vigente.

### 2.3 `pending_initial_context`

Tras `complete_start` (sin login):

- persistir en el usuario: `pending_initial_organization_id` + `pending_initial_organization_at`;
- TTL por defecto **7 días**;
- al primer login exitoso que consuma el pending → fijar sesión a esa org y **limpiar** el pending.

### 2.4 Usuarios creados por `/start`

- `is_admin=False` (dueño vía `user_organization` role=owner).
- No deben ver el catálogo global de orgs de plataforma.

## 3. Consecuencias

- Primer login post-`/start` → siempre la org recién creada (Gate P0).
- Multi-org legítimo → selector si hay ambigüedad y no hay pending.
- Heurística «más productos» queda **detrás** del pending y del picker explícito.

## 4. Código

- `nodeone.services.organization_context_resolver`
- Integración en `finalize_post_login_organization`
- Columnas `user.pending_initial_organization_*` + DDL idempotente
