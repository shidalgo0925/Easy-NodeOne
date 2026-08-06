# Gate 1 HTTP — Freeze oficial para LOCAL (Gate 2)

| Campo | Valor |
|-------|--------|
| Emisor | **CODITO / EN1** |
| Destino | Repo **LOCAL** → copiar a `Doc/` |
| Estado | **FROZEN** — 6 ago 2026 · implementado en appdev |
| Tag Git | **`eposone-onboarding-p0-v1.3`** |
| Remoto | `git@github.com:shidalgo0925/Easy-NodeOne.git` |
| Commit tip (referencia) | tip de `develop` al publicar este tag |
| Carpeta EN1 | `Doc/EN1_ONBOARDING_P0/` |

**Propósito:** desbloquear Gate 2 APK **sin inventar HTTP**.  
Todo cliente Login / Session / Issue / Restore / QR / modality está aquí o se compone de APIs ya listadas.

---

## Sync al repo LOCAL

```bash
git remote add en1-codito git@github.com:shidalgo0925/Easy-NodeOne.git 2>/dev/null || true
git fetch en1-codito tag eposone-onboarding-p0-v1.3
git checkout eposone-onboarding-p0-v1.3 -- Doc/EN1_ONBOARDING_P0
git add Doc/EN1_ONBOARDING_P0
git commit -m "docs(onboarding): import CODITO Gate1 HTTP freeze (eposone-onboarding-p0-v1.3)"
```

### Verificación Gate 2 (LOCAL)

```bash
test -f Doc/EN1_ONBOARDING_P0/GATE1_HTTP_FROZEN_FOR_LOCAL.md
test -f Doc/EN1_ONBOARDING_P0/ONBOARDING_LOGIN_HTTP_V1.md
test -f Doc/EN1_ONBOARDING_P0/DEVICE_CONFIG_COMMERCIAL_V1.md
test -f Doc/EN1_ONBOARDING_P0/QR_CONTRACT_V1.md
test -f Doc/EN1_ONBOARDING_P0/RESTORE_CONTRACT_V1.md
grep -q 'User Bearer' Doc/EN1_ONBOARDING_P0/GATE1_HTTP_FROZEN_FOR_LOCAL.md
grep -q 'Device Bearer' Doc/EN1_ONBOARDING_P0/GATE1_HTTP_FROZEN_FOR_LOCAL.md
```

---

## 1. Separación de tokens (obligatorio)

| Token | Nombre | Dónde se obtiene | Dónde se usa | No usar para |
|-------|--------|------------------|--------------|--------------|
| **User Bearer** | Onboarding access token | `POST /api/v1/onboarding/login` | `/api/v1/onboarding/session`, `/api/v1/onboarding/issue-code` | Orders, cash shifts, bootstrap operativo |
| **Device Bearer** | Device access token | `POST /api/v1/devices/register` | `/api/v1/devices/config`, `/bootstrap`, `/cash/*`, `/orders*` | Login de usuario admin |

```text
User Bearer  →  solo asistente de instalación (caminos B/D + issue code)
Device Bearer →  operación POS tras Register
PIN cajero    →  local (Hito 2.5); no es HTTP login
```

Header común:

```http
Authorization: Bearer <token>
```

---

## 2. Checklist LOCAL ↔ este freeze

| Necesario Gate 2 | Documento / sección |
|------------------|----------------------|
| Login Onboarding (método, path, body, errores) | §3 |
| GET sesión onboarding (shape org/POS/devices) | §4 |
| Issue Provision Code | §5 |
| Restore dispositivo | §6 (composición; **sin** endpoint `/restore`) |
| Payload QR | §7 |
| Modalidad Standalone/Connected | §8 + `config.commercial` |
| Ejemplos request/response + tag | este archivo + tag `eposone-onboarding-p0-v1.3` |

---

## 3. Login Onboarding

### Request

```http
POST /api/v1/onboarding/login
Content-Type: application/json

{
  "email": "owner@negocio.com",
  "password": "secreto123",
  "organization_id": 5
}
```

| Campo | Obligatorio | Notas |
|-------|-------------|--------|
| `email` | Sí | Case-insensitive |
| `password` | Sí | |
| `organization_id` | No | Si hay una sola org, se selecciona sola; si hay varias y se omite → session con lista sin detalle de cajas |

### Response `200`

```json
{
  "access_token": "eyJ...",
  "token_type": "Bearer",
  "expires_in": 43200,
  "session": {
    "schema_version": 1,
    "user_id": 12,
    "email": "owner@negocio.com",
    "full_name": "Ana Owner",
    "organization_count": 1,
    "selected_organization_id": 5,
    "next_action": "issue_code",
    "generated_at": "2026-08-06T20:00:00Z",
    "organizations": [
      {
        "organization_id": 5,
        "name": "Café Demo",
        "can_issue_provisioning_code": true,
        "modality": "standalone",
        "plan_code": "standalone",
        "subscription": {
          "product_code": "eposone",
          "status": "active",
          "entitled": true,
          "trial_ends_at": null,
          "starts_at": "2026-08-06T15:00:00",
          "ends_at": null
        },
        "commercial": {
          "schema_version": 1,
          "product_code": "eposone",
          "plan_code": "standalone",
          "plan_name": "Standalone",
          "modality": "standalone",
          "operating_modality": "standalone",
          "sync_cloud": false
        },
        "branches": [{ "branch_ref": "centro", "name": "Centro", "status": "active" }],
        "pos": [{ "pos_ref": "posfran", "name": "PosFran", "status": "active" }],
        "registers": [
          {
            "register_ref": "Caja - Fran",
            "name": "Francisco Caja",
            "status": "active",
            "pos_ref": "posfran",
            "pos_name": "PosFran",
            "branch_ref": "centro",
            "branch_name": "Centro",
            "has_active_code": true,
            "active_code_expires_at": "2026-08-06T16:25:00",
            "active_provisioning_code": "L2cG-RZg-MK4Kkyd"
          }
        ],
        "devices": [
          {
            "device_uuid": "1ec06bf2-2351-4a1b-9e5c-55f7cc99fffc",
            "device_label": "EPosOne-1ec06bf2",
            "status": "active",
            "register_ref": "Caja - Fran",
            "branch_ref": "centro",
            "pos_ref": "posfran",
            "app_version": "1.0.0+1",
            "last_seen_at": "2026-08-06T16:03:07",
            "installation_ready_at": null
          }
        ],
        "licenses": [
          {
            "register_ref": "Caja - Fran",
            "license_type": "trial",
            "status": "active",
            "plan_code": "trial",
            "can_operate": true,
            "commercial_ui": "Trial",
            "expires_at": "2026-08-21T16:03:06",
            "days_remaining": 15
          }
        ]
      }
    ]
  }
}
```

### Errores login

| HTTP | `error` | Cuándo |
|------|---------|--------|
| 401 | `invalid_credentials` | Email/password mal / vacío |
| 403 | `no_organization` | User sin org |
| 403 | `org_forbidden` | `organization_id` no autorizada |
| 400 | `invalid_organization_id` | No numérico |

---

## 4. GET sesión onboarding

```http
GET /api/v1/onboarding/session?organization_id=5
Authorization: Bearer <User Bearer>
```

### Response `200`

Mismo shape que `session` del login (raíz = payload de sesión, **sin** envolver en `session`).

Campos clave por org (cuando hay detalle):

| Campo | Tipo |
|-------|------|
| `modality` / `commercial.modality` | `standalone` \| `connected` |
| `plan_code` | comercial |
| `subscription` | status + `entitled` |
| `registers[]` | cajas + código activo opcional |
| `pos[]` / `branches[]` | jerarquía |
| `devices[]` | tablets |
| `licenses[]` | por `register_ref` |
| `can_issue_provisioning_code` | bool |
| `next_action` | ver §4.1 |

### 4.1 `next_action` (máquina APK)

| Valor | Significado |
|-------|-------------|
| `select_organization` | Multi-org; pedir elección |
| `subscription_inactive` | Bloquear (no inventar trial) |
| `issue_code` | Llamar issue-code o usar código del portal |
| `provision_with_code` | Hay código activo → Register |
| `restore_or_cashier` | Hay device active → Restore o PIN |

### Errores session

| HTTP | `error` |
|------|---------|
| 401 | `auth_required` / `invalid_token` / `token_expired` |
| 403 | `org_forbidden` |
| 400 | `invalid_organization_id` |

---

## 5. Issue Provision Code

```http
POST /api/v1/onboarding/issue-code
Authorization: Bearer <User Bearer>
Content-Type: application/json

{
  "organization_id": 5,
  "register_ref": "Caja - Fran"
}
```

### Response `201`

```json
{
  "organization_id": 5,
  "register_ref": "Caja - Fran",
  "code": "L2cG-RZg-MK4Kkyd",
  "expires_at": "2026-08-06T16:25:42",
  "status": "active"
}
```

TTL ~30 min · un solo uso · re-issue revoca el anterior.

Luego APK:

```http
POST /api/v1/devices/register
X-EN1-Provisioning-Code: L2cG-RZg-MK4Kkyd
Content-Type: application/json

{
  "device_uuid": "1ec06bf2-2351-4a1b-9e5c-55f7cc99fffc",
  "platform": "android",
  "app_version": "1.0.0+1"
}
```

→ **Device Bearer** + config (incluye `commercial` + `license`).

---

## 6. Restore dispositivo (sin endpoint `/restore`)

**No existe** `POST /api/v1/onboarding/restore` en V1.

Composición oficial (Restore Contract V1):

```text
1. POST /api/v1/onboarding/login
2. GET  /api/v1/onboarding/session?organization_id=
3. Usuario elige register_ref (de session.organizations[].registers)
4. Si necesita vínculo nuevo:
      POST /api/v1/onboarding/issue-code
      POST /api/v1/devices/register   (mismo device_uuid = re-provision)
5. GET /api/v1/devices/bootstrap     (Device Bearer)
6. GET /api/v1/devices/config        (modality + license)
7. PIN cajero local
```

Si Device Bearer aún válido tras reinstall → saltar a bootstrap (sin issue-code).

---

## 7. Payload QR técnico

| Regla | Valor |
|-------|--------|
| Contenido QR | **Solo** el string del provisioning code |
| Ejemplo | `L2cG-RZg-MK4Kkyd` |
| Opcional deep link | `eposone://provision?code=<CODE>` (solo extrae `code`) |
| Prohibido en QR | modality, plan, org_id, tokens, precios |

Flujo: QR → code → `POST /devices/register` → bootstrap.

Portal web QR: `GET /admin/eposone/install/provisioning-qr.png?register_ref=` (sesión BO; no APK).

---

## 8. Modalidad Standalone / Connected

### En User Session (onboarding)

```json
"modality": "standalone",
"plan_code": "standalone",
"commercial": {
  "modality": "standalone",
  "operating_modality": "standalone",
  "sync_cloud": false
}
```

Valores oficiales: **`standalone`** | **`connected`** (nunca `local` hacia la APK).

### En Device config / bootstrap (post-register)

```http
GET /api/v1/devices/config
Authorization: Bearer <Device Bearer>
```

```json
{
  "commercial": {
    "schema_version": 1,
    "product_code": "eposone",
    "plan_code": "starter",
    "plan_name": "Starter",
    "modality": "connected",
    "operating_modality": "connected",
    "sync_cloud": true
  },
  "license": { "...": "License Engine caja; plan_code puede ser trial" }
}
```

`license.plan_code` (**caja**) ≠ `commercial.plan_code` (**suscripción**).

---

## 9. Mapa caminos A–D → HTTP

| Camino | HTTP |
|--------|------|
| **A** Crear negocio | Web `/start` → portal → código/QR → register → bootstrap |
| **B** Tengo cuenta | login → session → issue-code → register → bootstrap |
| **C** Código / QR | register (código) → bootstrap |
| **D** Restaurar | login → session → (issue-code) → register → bootstrap |

Convergencia: **Register → Bootstrap → PIN → Operar**.

---

## 10. Archivos del pack `Doc/EN1_ONBOARDING_P0/`

| Archivo | Rol |
|---------|-----|
| **GATE1_HTTP_FROZEN_FOR_LOCAL.md** | **Este freeze (leer primero)** |
| ONBOARDING_LOGIN_HTTP_V1.md | Resumen endpoints |
| LOGIN_CONTRACT_V1.md | Contrato lógico login |
| RESTORE_CONTRACT_V1.md | Restore composición |
| QR_CONTRACT_V1.md | QR = code only |
| DEVICE_CONFIG_COMMERCIAL_V1.md | `config.commercial` |
| ONBOARDING_CONTRACT_V2.md | Caminos A–D |
| DEVICE_LIFECYCLE_V1.md | Estados device |
| ADR-027 / ADR-014 | Marco producto |
| HANDOFF-LOCAL.md | Sync genérico |

---

## Confirmación LOCAL

*Gate 1 HTTP freeze recibido — tag `eposone-onboarding-p0-v1.3` en `Doc/EN1_ONBOARDING_P0/GATE1_HTTP_FROZEN_FOR_LOCAL.md`. Arranco Gate 2.*
