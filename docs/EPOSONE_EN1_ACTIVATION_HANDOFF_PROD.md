# HANDOFF PROD — Activación Standalone ADR-035 v1.3 (para LOCAL)

> **Nota (2026-08-07):** Contrato **v1.4** (email + código de activación) está en **appdev** — ver [`EPOSONE_EN1_ACTIVATION_HANDOFF_LOCAL_APPDEV.md`](EPOSONE_EN1_ACTIVATION_HANDOFF_LOCAL_APPDEV.md). Este documento describe **PROD actual (v1.3 App Link)** hasta GO de deploy.

| Campo | Valor |
|-------|--------|
| Entorno | **PROD** |
| EN1 commit | **`9c679c3`** |
| Host producto | `https://eposone.easytech.services` |
| APK | `https://eposone.easytech.services/static/apk/eposone/EPosOne.apk` |
| LOCAL esperado | **`9a84ba5`** |
| Fecha verificación | 2026-08-07 |
| Emisor | CODITO |
| Alcance | Solo Standalone · **NO ADR-034** · sin rediseño |

---

## 1. DDL PROD (verificado)

Tablas presentes en `easynodeone_prod`:

- `ets_activation_license` (incl. `modality`, `implementation_strategy`, `status`, vigencia, revoke…)
- `ets_activation_token` (incl. `token` = manual_code, `jti` = activation_ref, `expires_at`, `max_uses`, `uses_count`, consumed/revoked…)

Índices únicos: `uq_ets_activation_token_token`, `uq_ets_activation_token_jti`.

**Conclusión:** DDL ADR-035 requerido está aplicado en PROD. No hace falta migración adicional para v1.3 (v1.3 no añade columnas; reutiliza `jti`).

---

## 2. Transporte canónico EN1 (lo que emite PROD hoy)

| Transporte | Forma exacta |
|------------|----------------|
| App Link (principal) | `https://eposone.easytech.services/activate/<activation_ref>` |
| Deep link (principal) | `eposone://activate/<activation_ref>` |
| QR activación | PNG de la **misma** App Link → `GET /activate/<activation_ref>/qr.png` |
| Fallback manual | `manual_code` = `XXXX-XXXX-XXXX` (nunca en URL/QR canónico) |
| QR comercial | `https://eposone.easytech.services/start` (**no** activa) |

`activation_ref` = `jti` (32 hex).  
`manual_code` = columna `token`.

---

## 3. Compatibilidad exacta con LOCAL `9a84ba5`

LOCAL declara:

- `/activate?token=...`
- `eposone://activate?token=...`

### Matriz verificada en PROD (2026-08-07)

| Forma | Resultado EN1 | Redeem EP1 correcto |
|-------|---------------|---------------------|
| `GET /activate?token=<manual_code>` | **302** → `/activate/<activation_ref>` | Body `{ "token": "<manual_code>" }` o `{ "manual_code": "..." }` → OK |
| `GET /activate?token=<activation_ref>` | **200** página genérica (no resuelve jti vía query) | Si EP1 manda `{ "token": "<jti>" }` → **`activation_token_invalid`** |
| `GET /activate/<activation_ref>` | **200** puente Abrir + QR | Body `{ "activation_ref": "<jti>" }` → OK |
| `eposone://activate?token=<manual_code>` | (scheme EP1) | Redeem con `token`/`manual_code` → OK |
| `eposone://activate?token=<jti>` | (scheme EP1) | Redeem con `token=<jti>` → **FAIL**; requiere `activation_ref` |
| `eposone://activate/<jti>` (emisión actual ABRIR) | Canónico v1.3 | LOCAL debe parsear **path**, no solo `?token=` |

### Veredicto

- **Compatible con LOCAL 9a84ba5** si EP1 usa **`manual_code` en `?token=`** y redeem con campo `token` o `manual_code`.
- **No compatible a ciegas** si EP1 toma el deep link canónico `eposone://activate/<jti>` (sin query) o pone el **jti** en `?token=` y lo reenvía como `token` en redeem.
- El CTA web **ABRIR EPOSONE** emite deep link **path** (`eposone://activate/<ref>`). Para E2E físico con APK 9a84ba5 sin cambiar EN1: LOCAL debe aceptar path **o** usar fallback `manual_code` / legacy `?token=<manual_code>`.

**Puente HTTP legacy (sin deploy nuevo):**  
`https://eposone.easytech.services/activate?token=<manual_code>` → redirect al App Link path.

No se hizo deploy adicional: el puente query→path ya está en `9c679c3`.

---

## 4. Endpoints device (PROD)

Base: `https://eposone.easytech.services`

### Validate (no consume)

```http
POST /api/v1/activation/validate
Content-Type: application/json
```

```json
{ "activation_ref": "<jti>", "product_code": "eposone" }
```

o

```json
{ "manual_code": "XXXX-XXXX-XXXX", "product_code": "eposone" }
```

o legacy

```json
{ "token": "XXXX-XXXX-XXXX", "product_code": "eposone" }
```

### Redeem (single-use)

```http
POST /api/v1/activation/redeem
Content-Type: application/json
```

```json
{
  "activation_ref": "<jti>",
  "device_uuid": "<uuid-estable-dispositivo>",
  "product_code": "eposone"
}
```

(alternativas: `manual_code` o `token` = manual_code)

### Response 200 (verificado)

```json
{
  "ok": true,
  "redeemed": true,
  "modality": "standalone",
  "implementation_strategy": "self_serve",
  "product_code": "eposone",
  "organization_id": <int>,
  "license_id": <int>,
  "register_ref": null,
  "provisioning_hint": { "next": "standalone_assistant", "adr": "ADR-033" },
  "token_id": <int>,
  "token_expires_at": "...Z",
  "license_expires_at": null,
  "contract_id": null,
  "subscription_id": null
}
```

Con `modality=standalone` → EP1 arranca **ADR-033**. No Register/Bootstrap.

### Errores tipados (smoke: double redeem → 409)

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
| `ops_not_ready` | 409 (Connected only) |

### TTL / uso / reemisión / revocación

| Regla | PROD |
|-------|------|
| TTL | 14 días (rango 7–30) |
| max_uses | 1 → `consumed` |
| Reemisión | `POST /api/v1/activation/tokens` (auth) / helper issue — nueva `activation_ref` + `manual_code` |
| Revoke token | `POST /api/v1/activation/tokens/<id>/revoke` |
| Revoke license | `POST /api/v1/activation/licenses/<id>/revoke` (invalida tokens active) |

---

## 5. Flujo web PROD (comportamiento)

```text
QR comercial → https://eposone.easytech.services/start
→ registro → email verificación (gate)
→ Tu EPosOne está listo
→ DESCARGAR APK → INSTALAR → ABRIR (App Link / deep link)
→ opcional: Activar en otra tablet (QR App Link)
→ fallback: ¿Problemas para activar? → manual_code
```

Email continuidad (tras verify): asunto “Tu EPosOne está listo para instalar”; CTA = App Link; `manual_code` solo pie recuperación.

Teléfono/PC → QR otra tablet: mismo `/activate/<ref>/qr.png` → tablet escanea → redeem Standalone.

---

## 6. Fixture de prueba controlada (NO cliente real)

| Campo | Valor |
|-------|--------|
| Org | `26` · `E2E Standalone TEST e93ca933` · `e2e-sa-e93ca933` |
| User | `e2e.standalone+e93ca933@easytech.services` |
| Password | `E2eStand408f539` |
| email_verified | **true** (bypass gate para pruebas device) |
| modality | **standalone** / self_serve |
| activation_ref | `43489a4599918446d37ad17b57f30856` |
| manual_code | `AD81-9E9F-6A15` |
| App Link | `https://eposone.easytech.services/activate/43489a4599918446d37ad17b57f30856` |
| Deep v1.3 | `eposone://activate/43489a4599918446d37ad17b57f30856` |
| Legacy HTTPS (9a84ba5) | `https://eposone.easytech.services/activate?token=AD81-9E9F-6A15` |
| Legacy deep (9a84ba5) | `eposone://activate?token=AD81-9E9F-6A15` |
| expires_at | ~2026-08-21 (14d) |
| Estado al entregar | **active / consumable** (no redimido) |

Detalle local servidor: `/tmp/e2e_standalone_prod_e93ca933.json`

**Importante:** un redeem exitoso consume el token. Para reintentos físicos pedir reemisión CODITO.

---

## 7. Checklist LOCAL antes de APK física

1. Si build = **9a84ba5** estricto `?token=`: usar **manual_code** en query/deep link y redeem `{token|manual_code}`.
2. Si build entiende v1.3: path `/activate/<ref>` + redeem `{activation_ref}`.
3. Tras redeem `modality=standalone` → ADR-033 → READY_TO_SELL → primera venta.
4. No enviar a Connected/Register/Bootstrap.
5. APK instalar desde URL PROD arriba (o la que LOCAL firme).

---

## 8. Estado CODITO

| Ítem | Estado |
|------|--------|
| PROD `9c679c3` | OK |
| `/start` + APK | OK |
| DDL activation | OK |
| validate/redeem Standalone | OK (smoke) |
| Fixture E2E | Lista (sin consumir) |
| Gap LOCAL 9a84ba5 vs deep path v1.3 | **Documentado** — puente `?token=<manual_code>` operativo |
| ADR-034 | No tocado |
| Deploy extra | No |

**Detenerse.** Listo para que LOCAL genere APK y ejecuten E2E físico en PROD.
