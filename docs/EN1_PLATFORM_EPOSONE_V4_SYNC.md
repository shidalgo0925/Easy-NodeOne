# EPosOne V4 — Sincronización Modo Plataforma (Sprint 7)

| Campo | Valor |
|-------|--------|
| Sprint | **7 — Sincronización** |
| Estado | **Implementado** — 9 jul 2026 (Dev EN1 · sin reescribir motor) |
| Roadmap | [`EN1_PLATFORM_EPOSONE_V4_ROADMAP.md`](EN1_PLATFORM_EPOSONE_V4_ROADMAP.md) |
| ADR | [ADR-003](ADR-003-EPOSONE-SYNC.md) · § 6.9 |
| Motor | `backend/nodeone/core/sync/` (sin cambios de arquitectura) |
| Puente | `backend/nodeone/core/eposone_domain/platform_sync.py` |
| Handlers | `backend/nodeone/modules/eposone/sync_handlers.py` |

---

## 1. Objetivo

**Conectar** el sync ya existente al **Modo Plataforma** V4.  
**No** reescribir cola, conflictos, retry ni handlers.

```text
Cliente POS (Modo Plataforma)
        │
 PlatformSyncBridge  ← política ADR-003
        │
 SyncOperationService / IncrementalSyncService
        │
 apply_eposone_sync_operation
```

| Modo | Sync EN1 |
|------|----------|
| Local | **Bloqueado** (`403 sync_disabled_local_mode`) |
| Plataforma | **Activo** |
| Uninitialized | Bloqueado |
| Device `sync_enabled=false` | Bloqueado |

---

## 2. API (misma rutas)

| Ruta | Cambio Sprint 7 |
|------|-----------------|
| `GET /api/platform/sync/events` | Valida modo; opcional `device_id` + heartbeat |
| `POST /api/platform/sync/operations` | Idem; `client_id` ← `device_id` |
| `POST .../operations/process` | Sin cambio (servidor EN1) |
| Worker cycle | Sin cambio |

Parámetros / headers opcionales:

| Campo | Origen |
|-------|--------|
| `operating_mode` | query, JSON o `X-EPosOne-Mode` |
| `device_id` | query, JSON o `X-EPosOne-Device-Id` |

Si **omitido** `operating_mode` en sesión EN1 web → se asume **`platform`** (default).

---

## 3. Criterio de hecho

- [x] Política Local vs Plataforma documentada e implementada  
- [x] Bridge sin tocar lógica de `queue` / `conflicts` / handlers  
- [x] `device_id` como `client_id` + respeto `sync_enabled`  
- [x] Rutas sync usan el bridge  
- [x] Tests de política  
- [x] Roadmap V4 Sprint 7 ✅  

---

## 4. Fuera de alcance

- Reescritura del motor sync  
- Sync en Modo Local  
- APK / transporte Android  
- Nuevos operation types (ya cubiertos en handlers EPosOne)
