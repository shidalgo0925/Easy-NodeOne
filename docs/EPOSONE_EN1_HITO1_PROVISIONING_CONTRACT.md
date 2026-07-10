# EPosOne ↔ EN1 — Hito 1 Provisioning (contrato EN1)

| Campo | Valor |
|-------|--------|
| Hito | **EN1-01** — Servidor de Provisioning |
| Estado | **Implementado en EN1** (`847a09f`, 10 jul 2026) · **E2E tablet pendiente** |
| Commit | `847a09f` |
| Handoff | [`EN1_EPOSONE_HANDOFF_STATUS.md`](EN1_EPOSONE_HANDOFF_STATUS.md) |
| Nota | El archivo `EPOSONE_EN1_HITO1_PROVISIONING_CONTRACT.md` del repo Flutter **no** estaba en Easy-NodeOne; este documento es la **referencia oficial en EN1**. Si Flutter difiere, proponer ajuste **antes** de cambiar paths. |

---

## Base URL

Dev: `https://appdev.easynodeone.com`

Prefijo: `/api/v1/devices`

---

## Auth

### Registro (provisioning)

Header obligatorio:

```http
X-EN1-Provisioning-Code: <código de la organización>
```

El código se genera/almacena por org en `eposone_settings.provisioning_code` (visible en BackOffice EPosOne → Dispositivos).

Fallback Dev (opcional): variable de entorno `EPOSONE_PROVISIONING_CODE` si la org aún no tiene código propio **y** el body trae `organization_id` válido con módulo `eposone` activo.

**No** usar cookie de sesión admin ni credenciales de usuario ERP.

### Config y llamadas posteriores

```http
Authorization: Bearer <access_token>
```

El token identifica **un dispositivo**; solo puede leer su propia config.

---

## `POST /api/v1/devices/register`

### Body (JSON)

| Campo | Tipo | Obligatorio | Notas |
|-------|------|-------------|-------|
| `device_uuid` | string | sí | UUID estable del dispositivo |
| `organization_id` | int | sí* | ID tenant EN1 |
| `organization_ref` | string | sí* | Alternativa a id (subdomain / slug) |
| `branch_ref` | string | sí | Sucursal (`core_org_unit.unit_ref` type branch) |
| `pos_ref` | string | sí | Punto de Venta |
| `register_ref` | string | sí | Caja |
| `device_name` | string | no | Etiqueta |
| `platform` | string | no | default `android` |
| `device_model` | string | no | |
| `android_version` | string | no | |
| `app_version` | string | no | |

\*Uno de `organization_id` o `organization_ref`.

### Comportamiento

- Valida provisioning code + org con EPosOne habilitado.
- Valida que branch / POS / caja existan (refs) en la org (POS acepta tipo `pos` o legado `pos_terminal`).
- Si UUID no existe → crea `core_pos_terminal`.
- Si UUID existe → **reprovisiona** (actualiza vínculos, rota token, bump `config_version`).
- No duplica filas por UUID.

### Respuesta `201`

```json
{
  "access_token": "<token opaco>",
  "token_type": "Bearer",
  "device": {
    "uuid": "...",
    "name": "...",
    "status": "active",
    "registered_at": "ISO-8601",
    "last_seen_at": "ISO-8601",
    "organization_id": 1,
    "branch_ref": "...",
    "pos_ref": "...",
    "register_ref": "..."
  },
  "config": { }
}
```

`config` = mismo objeto que `GET .../config`.

### Errores

| HTTP | `error` |
|------|---------|
| 400 | validación / refs inválidas |
| 401 | provisioning code inválido o ausente |
| 403 | módulo eposone no activo / org inactiva |
| 404 | organización no encontrada |

---

## `GET /api/v1/devices/config`

Header: `Authorization: Bearer <access_token>`

### Respuesta `200`

```json
{
  "config_version": 1,
  "business_name": "Nombre org",
  "currency": "USD",
  "timezone": "America/Panama",
  "organization": { "id": 1, "name": "..." },
  "branch": { "ref": "...", "name": "..." },
  "pos": { "ref": "...", "name": "..." },
  "register": { "ref": "...", "name": "..." },
  "device": {
    "uuid": "...",
    "name": "...",
    "status": "active",
    "app_version": "...",
    "last_seen_at": "ISO-8601"
  }
}
```

**No** incluye productos, clientes, inventario ni ventas.

### Errores

| HTTP | `error` |
|------|---------|
| 401 | token ausente/inválido |
| 403 | dispositivo inactivo |

---

## Persistencia (`core_pos_terminal`)

| Campo | Uso |
|-------|-----|
| `terminal_ref` | UUID dispositivo |
| `organization_id` | Empresa (tenant) |
| `branch_ref` | Sucursal |
| `pos_ref` | POS |
| `register_ref` | Caja |
| `device_label` | Nombre |
| `status` | active / inactive |
| `created_at` | Registro |
| `last_seen_at` | Última conexión |
| `app_version` | Versión APK |
| `access_token_hash` | SHA-256 del Bearer |
| `config_version` | Entero de config |

---

## Auditoría (eventos)

| Evento | Cuándo |
|--------|--------|
| `eposone.device.registered` | Alta |
| `eposone.device.reprovisioned` | Re-registro |
| `eposone.device.auth_failed` | Token/código inválido |
| `eposone.device.provision_failed` | Error de validación de negocio |

---

## Fuera de alcance (Hito 1)

Sync de productos/clientes/ventas/inventario · licencias · FE · CRM · IA.
