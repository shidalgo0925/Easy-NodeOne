# HANDOFF LOCAL (appdev) — Activación Standalone ADR-035 v1.4

| Campo | Valor |
|-------|--------|
| Entorno | **Dev EN1 / appdev** |
| Host API | `https://appdev.easynodeone.com` (puerto app `9101`) |
| Host UX `/start` | Producto EPosOne (Host `eposone.*`); en local: `Host: eposone.easytech.services` → `:9101/start` |
| Contrato | **ADR-035 v1.4** — email + código de activación |
| Alcance | Solo Standalone · **NO ADR-034** · Connected sin cambio |
| Emisor | CODITO |
| Fecha | 2026-08-07 |

**PROD:** no desplegar hasta GO explícito. El handoff PROD v1.3 (`EPOSONE_EN1_ACTIVATION_HANDOFF_PROD.md`) queda histórico hasta el próximo deploy.

---

## 1. UX canónica (lo que ve el usuario)

1. QR / web comercial → `/start`
2. Registro + verificar correo
3. EN1 emite **código de activación** (6 dígitos) bound al email + licencia Standalone
4. Email “Tu EPosOne está listo”: **código destacado** + CTA **Descargar EPosOne** (APK)
5. Web `/start`: descarga / instalar; muestra el código tras verify
6. EP1: **Correo + Código + ACTIVAR**
7. `POST /api/v1/activation/redeem` → claims `modality=standalone` → ADR-033

Léxico: solo **“código de activación”**. Nunca “aprovisionamiento / caja / register / bootstrap” en Standalone.

Reinstalación / otra tablet: **reemitir** sobre la misma licencia/org (`POST /api/v1/activation/reissue`).

---

## 2. Credencial

| Campo | Valor |
|-------|--------|
| `activation_code` | 6 dígitos (`100000`–`999999`), columna `ets_activation_token.token` |
| `bound_email` | Email del titular (case-insensitive) |
| `jti` / `activation_ref` | Opaco interno / secundario (no UX principal) |
| TTL | Default 14 días |
| Uso | `max_uses=1` → `consumed` |

DDL: columna `bound_email` en `ets_activation_token` (schema idempotente).

---

## 3. HTTP — Validate / Redeem

Base appdev: `https://appdev.easynodeone.com`

### Validate (no consume)

```http
POST /api/v1/activation/validate
Content-Type: application/json

{
  "email": "user@example.com",
  "activation_code": "482731",
  "product_code": "eposone"
}
```

### Redeem (consume)

```http
POST /api/v1/activation/redeem
Content-Type: application/json

{
  "email": "user@example.com",
  "activation_code": "482731",
  "device_uuid": "<uuid-dispositivo>",
  "product_code": "eposone"
}
```

### Response OK (espíritu)

```json
{
  "ok": true,
  "redeemed": true,
  "modality": "standalone",
  "implementation_strategy": "self_serve",
  "organization_id": 123,
  "license_id": 45,
  "product_code": "eposone",
  "provisioning_hint": { "next": "standalone_assistant" }
}
```

(`validate` omite `redeemed`; incluye `consumable`.)

### Errores tipados

| error | HTTP |
|-------|------|
| `activation_credential_missing` | 400 |
| `activation_credential_ambiguous` | 400 |
| `activation_code_invalid` | 401 |
| `activation_code_expired` | 400 |
| `activation_code_used` | 409 |
| `activation_code_revoked` | 403 |
| `email_mismatch` | 403 |
| `license_revoked` / `license_expired` | 403 |
| `product_mismatch` | 400 |

Sin heurística por longitud: el campo tipado es `activation_code`.

---

## 4. Reissue

```http
POST /api/v1/activation/reissue
Authorization: session (login requerido)
Content-Type: application/json

{
  "organization_id": 123,
  "email": "user@example.com",
  "send_email": true
}
```

- Revoca códigos `active` de la licencia Standalone de esa org
- Emite nuevo 6 dígitos + opcionalmente reenvía email
- **No** crea org/contrato nuevo
- Respuesta: mismo shape que emisión (`activation_code`, `bound_email`, `apk_url`, …) + `ok: true` · HTTP 201

---

## 5. Compat secundaria (no UX Standalone)

Siguen funcionando como puente interno (documentado, no mostrados en UX):

| Campo | Uso |
|-------|-----|
| `activation_ref` | = `jti` |
| `manual_code` / `token` | = mismo string que el código (6 dígitos en Standalone) |

No mezclar con `activation_code` en el mismo body → `activation_credential_ambiguous`.

Connected (ADR-034): sin cambio; códigos legado `XXXX-XXXX-XXXX` cuando modality=connected.

---

## 6. Qué implementar en EP1 (LOCAL)

Pantalla **Activar EPosOne**:

- Campo correo
- Campo código de activación
- Botón **ACTIVAR**
- `POST …/redeem` con el JSON de §3
- Si `modality=standalone` → flujo ADR-033 (`standalone_assistant`)

App Link / deep link / QR técnico: **secundarios**; no son el camino canónico Standalone.

---

## 7. Referencias

- [ADR-035](ADR-035-ACTIVATION-LICENSE-TOKEN-QR.md) v1.4
- [EN1_COMMERCIAL_IMPLEMENTATION_GATE](EN1_COMMERCIAL_IMPLEMENTATION_GATE.md)
- Código: `backend/nodeone/core/platform/activation_service.py` · `activation_v1_routes.py` · `/start`
