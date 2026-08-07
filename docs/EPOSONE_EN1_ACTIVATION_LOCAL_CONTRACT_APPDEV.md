# Contrato appdev — Activación Standalone ADR-035 v1.3 (HANDOFF LOCAL)

| Campo | Valor |
|-------|--------|
| Entorno | **appdev** — **NO PROD** |
| Superficie EPosOne | `https://eposone-dev.easynodeone.com` |
| APIs / APK | mismo silo Dev (`easynodeone-dev` :9101); también vía `https://appdev.easynodeone.com` para redeem/APK |
| Fecha | 2026-08-07 |
| ADRs | ADR-033 v1.2 · **ADR-035 v1.3** |
| Emisor | CODITO (EN1) |
| Consumidor | LOCAL (EP1 APK) |

---

## HANDOFF LOCAL

Todo lo que EP1 necesita sin inferir contratos.

### 1. Separación

| Qué | Forma | Activa |
|-----|-------|--------|
| QR comercial | `https://eposone-dev.easynodeone.com/start` | No |
| App Link (principal) | `https://eposone-dev.easynodeone.com/activate/<activation_ref>` | Sí |
| Deep link | `eposone://activate/<activation_ref>` | Sí |
| QR activación | encode(App Link) — misma `activation_ref` | Sí |
| Fallback manual | `manual_code` `XXXX-XXXX-XXXX` | Sí (recuperación) |

**Prod (documentado, no desplegado aquí):** `https://eposone.easytech.services/activate/<activation_ref>`

### 2. Credenciales tipadas (obligatorio)

`POST /api/v1/activation/validate` y `…/redeem` — **exactamente uno**:

```json
{ "activation_ref": "<jti hex 32>", "device_uuid": "<uuid>", "product_code": "eposone" }
```

o

```json
{ "manual_code": "XXXX-XXXX-XXXX", "device_uuid": "<uuid>", "product_code": "eposone" }
```

- **Prohibido** clasificar por longitud.
- Legacy: solo campo `token` → se interpreta como `manual_code`.
- Ambos campos → `activation_credential_ambiguous` (400).
- Ninguno → `activation_credential_missing` (400).

Validate: mismo body **sin** `device_uuid`.

### 3. Claims post-redeem 200

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
  "provisioning_hint": { "next": "standalone_assistant", "adr": "ADR-033" }
}
```

Si `modality=standalone` → arrancar **ADR-033**. **No** Register/Bootstrap Connected.

### 4. App Link / Intent (LOCAL)

1. Android App Links / intent filter: HTTPS host eposone + path `/activate/*`.
2. Scheme opcional: `eposone://activate/<activation_ref>`.
3. Extraer `activation_ref` del path (no query `token`).
4. `validate` → `redeem` con `{ activation_ref, device_uuid }`.
5. QR scan: leer URL App Link → misma ref.

### 5. TTL / single-use / reemisión / revocación

| Regla | Valor |
|-------|--------|
| TTL | 14 días (7–30) |
| max_uses | 1 → `consumed` |
| Re-emisión | admin / soporte emite nuevo token (nueva ref) |
| Revoke token | invalida App Link + manual_code |
| Revoke license | invalida todos pendientes |

### 6. Errores

| error | HTTP |
|-------|------|
| `activation_credential_missing` | 400 |
| `activation_credential_ambiguous` | 400 |
| `activation_token_invalid` | 401 |
| `activation_token_expired` | 400 |
| `activation_token_used` | 409 |
| `activation_token_revoked` | 403 |
| `license_revoked` / `license_expired` | 403 |
| `product_mismatch` | 400 |
| `modality_mismatch` | 409 |
| `ops_not_ready` | 409 (solo Connected) |

### 7. Flujo web EN1 (contexto)

```text
/start → registro → verify email (gate) → listo
  → DESCARGAR → INSTALAR → ABRIR (App Link)
  → opcional QR otra tablet
  → fallback manual oculto
```

### 8. APK

`https://appdev.easynodeone.com/static/apk/eposone/EPosOne.apk`  
(o mismo path en host eposone-dev)

### 9. No hacer

- No enviar Standalone a Connect/Register/Bootstrap.
- No usar `/start` como activación.
- No poner `manual_code` en URL/QR.
- No heurística `length >= 20`.

---

*Fuente: ADR-035 v1.3. Contrato operativo appdev para LOCAL.*
