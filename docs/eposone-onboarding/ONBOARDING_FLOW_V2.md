# ONBOARDING_FLOW_V2 — Flujo oficial EN1 / EPosOne

| Campo | Valor |
|-------|--------|
| Estado | **Norma P0** — 6 ago 2026 |
| ADRs | [ADR-024](../ADR-024-EPOSONE-START-ASSISTANT.md) · [ADR-027](../ADR-027-EPOSONE-ONBOARDING-UNIFICADO-V1.md) · [ADR-028](../ADR-028-EPOSONE-PLAN-DEFAULTS-COMMERCIAL-OVERRIDES.md) · [ADR-029](../ADR-029-ORGANIZATION-CONTEXT-RESOLVER-V2.md) · [ADR-030](../ADR-030-SUBSCRIPTION-LIFECYCLE-V2.md) |

---

## Flujo oficial

```text
/start
  → Crear cuenta
  → Crear organización
  → Seleccionar plan (sin precio)
  → Crear suscripción + entitlement (defaults del plan)
  → Recursos mínimos instalables + cajero seed
  → Provision code
  → Mostrar resumen (código + PIN)
  → FIN   ← sin login, sin cookie de sesión de app
  → Login (solo autentica)
  → Organization Resolver (pending → org nueva)
  → Panel de instalación
  → Instalar dispositivo → register → bootstrap → PIN → caja → operar
```

## Pantalla final `/start`

Solo debe indicar:

- Organización creada correctamente.
- Ahora puede: Descargar EPosOne · Iniciar sesión · Instalar su primer dispositivo.
- Mostrar código de instalación y PIN de cajero (si se generaron).

## Separación

| Paso | Dominio |
|------|---------|
| `/start` complete | Comercial + alta |
| Login | Identidad |
| Resolver org | Contexto tenant |
| Install panel | Licencia técnica / cupos |
| Device register | Provisioning |

Ver también: [`ORGANIZATION_RESOLVER_V2.md`](ORGANIZATION_RESOLVER_V2.md) · [`INSTALLATION_PORTAL_V2.md`](INSTALLATION_PORTAL_V2.md).
