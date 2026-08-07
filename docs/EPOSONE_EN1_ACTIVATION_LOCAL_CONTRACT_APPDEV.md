# Contrato appdev — Activación Standalone (ADR-035) para LOCAL

| Campo | Valor |
|-------|--------|
| Entorno | **appdev** (Dev EN1) — **NO PROD** |
| Base URL | `https://appdev.easynodeone.com` |
| Fecha | 2026-08-07 |
| ADRs | ADR-033 v1.2 · ADR-035 v1.2 |
| Emisor | CODITO (EN1) |
| Consumidor | LOCAL (EP1 APK) |

---

## 1. Separación comercial vs técnica

| Qué | URL / forma | Activa dispositivo |
|-----|-------------|--------------------|
| **QR comercial (appdev)** | `https://eposone-dev.easynodeone.com/start` (silo Dev EN1 `:9101`) | **No** — solo embudo registro |
| **APIs / APK (appdev)** | `https://appdev.easynodeone.com/…` | redeem/validate/APK |
| **Transporte técnico** | token · `eposone://activate?token=…` · `https://appdev…/activate?token=…` · QR PNG del token | **Sí** — credencial ADR-035 |

Notas:
- `appdev.easynodeone.com` es superficie **EN1** (portal); `/start` allí responde 404 a propósito.
- Superficie producto EPosOne en Dev: host `eposone-dev.easynodeone.com` (mismo backend `easynodeone-dev`).
- EP1 **no** debe tratar `/start` como activación.

---

## 2. Camino web (appdev) que entrega el token

```text
https://eposone-dev.easynodeone.com/start
  → registro → POST /api/public/eposone-start/complete
  → activation { token, modality=standalone, deep_link, activate_url }
  → Descargar APK (appdev static) → Instalar → Abrir EPosOne (deep_link)
```

Respuesta relevante de `complete` (201):

```json
{
  "ok": true,
  "activation": {
    "token": "EN1A…",
    "modality": "standalone",
    "implementation_strategy": "self_serve",
    "expires_at": "…Z",
    "max_uses": 1,
    "activate_url": "https://appdev.easynodeone.com/activate?token=EN1A…",
    "deep_link": "eposone://activate?token=EN1A…",
    "transport": {
      "commercial_qr": "/start",
      "technical_qr": "token_only",
      "activate_url": "…",
      "deep_link": "…"
    },
    "redeem": {
      "method": "POST",
      "path": "/api/v1/activation/redeem",
      "validate_path": "/api/v1/activation/validate"
    }
  },
  "installation": {
    "code": "<mismo token>",
    "kind": "activation_token"
  }
}
```

P0 appdev: `/start` **siempre** emite activación **Standalone** (sin árbol ops), aunque el plan comercial sea connected. Connected ops = ADR-034 (fuera de alcance).

---

## 3. Cómo EP1 recibe la activación

### 3.1 Preferido — deep link

```text
eposone://activate?token=<TOKEN>
```

- Intent filter Android: scheme `eposone`, host `activate`, query `token`.
- Al abrir, EP1 toma `token` y llama `validate` → `redeem` (no reinventar claims).

### 3.2 HTTPS puente (misma credencial)

```text
GET https://appdev.easynodeone.com/activate?token=<TOKEN>
```

Página puente intenta redirigir al deep link y muestra el token para copia manual.

### 3.3 Copia manual

Usuario pega el token en la pantalla de activación del asistente Standalone (ADR-033).

---

## 4. Endpoints device (appdev)

Base: `https://appdev.easynodeone.com`

### Validate (no consume)

```http
POST /api/v1/activation/validate
Content-Type: application/json

{ "token": "<TOKEN>", "product_code": "eposone" }
```

### Redeem (consume, default 1 uso)

```http
POST /api/v1/activation/redeem
Content-Type: application/json

{
  "token": "<TOKEN>",
  "device_uuid": "<uuid-estable-del-dispositivo>",
  "product_code": "eposone"
}
```

### Response 200 (redeem OK) — claims mínimos

```json
{
  "ok": true,
  "redeemed": true,
  "license_id": 1,
  "organization_id": 123,
  "product_code": "eposone",
  "modality": "standalone",
  "implementation_strategy": "self_serve",
  "register_ref": null,
  "license_expires_at": null,
  "contract_id": 45,
  "subscription_id": 67,
  "token_id": 9,
  "token_expires_at": "…Z",
  "provisioning_hint": {
    "next": "standalone_assistant",
    "adr": "ADR-033"
  }
}
```

Con `modality=standalone` EP1 **entra ADR-033** (asistente local). **No** pregunta Standalone vs Connected. **No** exige `register_ref`.

---

## 5. Errores tipados (EP1)

| `error` | HTTP | Acción EP1 |
|---------|------|------------|
| `activation_token_invalid` | 401 | Reingresar token |
| `activation_token_expired` | 400 | Pedir nuevo token (re-emisión web/soporte) |
| `activation_token_used` | 409 | No reintentar a ciegas; pedir re-emisión |
| `activation_token_revoked` | 403 | Soporte |
| `license_revoked` / `license_expired` | 403 | Soporte / renovar |
| `ops_not_ready` | 409 | Solo Connected (no aplica Standalone) |
| `product_mismatch` | 400 | App incorrecta |
| `modality_mismatch` | 409 | Flujo APK incorrecto |

Cuerpo error:

```json
{ "ok": false, "error": "activation_token_used", "message": "…" }
```

---

## 6. Vigencia y reutilización

| Regla | Valor appdev |
|-------|----------------|
| TTL token | 14 días (rango 7–30) |
| `max_uses` | 1 (default) → tras redeem OK queda `consumed` |
| Reutilización | Solo con re-emisión o política `max_uses>1` |
| Skew reloj | ±5 min |
| QR técnico | regenerable mientras token `active` (`/api/v1/activation/tokens/<id>/qr.png`, auth admin) |

---

## 7. APK

```text
https://appdev.easynodeone.com/static/apk/eposone/EPosOne.apk
```

---

## 8. Checklist LOCAL

1. Registrar deep link `eposone://activate?token=`.
2. Parsear token desde intent / entrada manual.
3. `POST …/validate` luego `POST …/redeem` contra **appdev**.
4. Si `modality=standalone` → asistente ADR-033 (sin árbol EN1).
5. No usar `/start` ni provisioning code legacy como camino canónico (bridge legacy opcional).

---

*Fuente de verdad arquitectura: ADR-035 v1.2. Este doc es el contrato operativo de **appdev** para handoff LOCAL.*
