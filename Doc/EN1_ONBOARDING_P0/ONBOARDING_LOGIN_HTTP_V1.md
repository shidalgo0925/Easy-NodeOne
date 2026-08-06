# Onboarding Login HTTP V1 (Gate 1)

| Campo | Valor |
|-------|--------|
| Contrato | [`LOGIN_CONTRACT_V1.md`](LOGIN_CONTRACT_V1.md) |
| Estado | **Implementado EN1** — 6 ago 2026 |
| Prefijo | `/api/v1/onboarding` |

## Endpoints

| Método | Ruta | Auth | Rol |
|--------|------|------|-----|
| `POST` | `/api/v1/onboarding/login` | email+password | Emite Bearer + session |
| `GET` | `/api/v1/onboarding/session` | Bearer onboarding | Refresca payload |
| `POST` | `/api/v1/onboarding/issue-code` | Bearer onboarding | Genera código EN1-02 |

### Login body

```json
{ "email": "a@b.com", "password": "…", "organization_id": 5 }
```

`organization_id` opcional; si el user tiene una sola org, se selecciona sola.

### Respuesta login

```json
{
  "access_token": "…",
  "token_type": "Bearer",
  "expires_in": 43200,
  "session": { "schema_version": 1, "user_id": 1, "organizations": […], "next_action": "…" }
}
```

Token **≠** Device Bearer. Tras Register, el POS usa Device Bearer + PIN cajero.

## Errores

`invalid_credentials` · `auth_required` · `token_expired` · `org_forbidden` · `no_organization` · `subscription` vía `next_action=subscription_inactive`
