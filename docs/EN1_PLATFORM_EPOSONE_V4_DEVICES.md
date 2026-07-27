# EPosOne V4 — Dispositivos POS (Sprint 6)

| Campo | Valor |
|-------|--------|
| Sprint | **6 — Dispositivos POS** |
| Estado | **Implementado** — 9 jul 2026 (Dev EN1) |
| Roadmap | [`EN1_PLATFORM_EPOSONE_V4_ROADMAP.md`](EN1_PLATFORM_EPOSONE_V4_ROADMAP.md) |
| Contrato | Device en [`EN1_PLATFORM_EPOSONE_V4_DOMAIN_CONTRACTS.md`](EN1_PLATFORM_EPOSONE_V4_DOMAIN_CONTRACTS.md) |
| Código dominio | `backend/nodeone/core/eposone_domain/devices.py` |
| EN1 | `core_pos_terminal` + `PosTerminalService` + UI `/admin/eposone/section/terminals` |

---

## 1. Objetivo

Registro lógico de terminales con:

| Campo | Notas |
|-------|--------|
| **UUID** (`device.id` / `terminal_ref`) | Estable; no rowid |
| **Perfil** | `fixed` \| `handheld` |
| **App** | `platform`, `app_version`, `device_model` |
| **Empresa / sucursal / caja** | `business_id`, `branch_id` / `branch_ref`, `register_id` |
| **Sync** | `sync_enabled` (flag; motor = Sprint 7) |

---

## 2. Capas

```text
DeviceRegistry (devices.py)
        │
 DeviceRepository (ports)
   ┌────┼────┐
Memory SQLite ApiDeviceRepository → PosTerminalService
```

---

## 3. API EN1

| Método | Ruta | Uso |
|--------|------|-----|
| GET/POST | `/api/eposone/terminals` | Listar / registrar (`device_id` o `terminal_ref`) |
| POST | `/api/eposone/terminals/<ref>/heartbeat` | `last_seen_at` + `app_version` |

Body POST ejemplo:

```json
{
  "device_id": "550e8400-e29b-41d4-a716-446655440000",
  "profile": "handheld",
  "name": "Tablet mesero 1",
  "platform": "android",
  "app_version": "1.2.0",
  "branch_id": "7",
  "register_id": "CAJA-01",
  "sync_enabled": true
}
```

DDL: columnas V4 en `ensure_commercial_core_schema` (`_ensure_pos_terminal_v4_columns`).

---

## 4. UI

Sección nav **Dispositivos POS** — muestra UUID, perfil, plataforma/app, caja, sync, último visto.

---

## 5. Criterio de hecho

- [x] `DeviceRepository` + Memory / SQLite / API  
- [x] `DeviceRegistry` (register, assign, heartbeat, deactivate, sync flag)  
- [x] Columnas V4 en `core_pos_terminal`  
- [x] API + UI actualizadas  
- [x] `ApiConfigRepository.get_registers` vía org_units  
- [x] Tests  
- [x] **Sin** cablear motor hasta Sprint 7 — ver [`EN1_PLATFORM_EPOSONE_V4_SYNC.md`](EN1_PLATFORM_EPOSONE_V4_SYNC.md)

---

## 6. Fuera de alcance

- Reescritura del motor sync  
- Sync en Modo Local  
- Emparejamiento BLE / QR de fábrica  
- APK Android
