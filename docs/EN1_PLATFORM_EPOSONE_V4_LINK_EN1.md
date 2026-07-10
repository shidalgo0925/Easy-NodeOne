# EPosOne V4 — Vincular con EasyNodeOne (Sprint 5)

| Campo | Valor |
|-------|--------|
| Sprint | **5 — Vincular con EN1** |
| Estado | **Implementado** — 9 jul 2026 (Dev EN1 · dominio; sin APK / sin sync cableado) |
| Roadmap | [`EN1_PLATFORM_EPOSONE_V4_ROADMAP.md`](EN1_PLATFORM_EPOSONE_V4_ROADMAP.md) |
| ADR | [ADR-004](ADR-004-EPOSONE-MIGRATION.md) |
| Primer inicio | [`EN1_PLATFORM_EPOSONE_V4_FIRST_START.md`](EN1_PLATFORM_EPOSONE_V4_FIRST_START.md) |
| Código | `backend/nodeone/core/eposone_domain/link_en1.py` |

---

## 1. Objetivo

Asistente **Local → Plataforma** sin reinstalar ni perder datos.

```text
Configuración → Vincular con EasyNodeOne
  → Login EN1
  → Organización
  → Empresa (crear EN1 | vincular existente)
  → Sucursal → Caja
  → Transferir datos locales
  → Listo (Modo Plataforma)
```

**No** confundir con Sprint 4 *Conectar con EasyNodeOne* (primer inicio ya en Plataforma).

---

## 2. Copy

| UI | Valor |
|----|--------|
| Label | **Vincular con EasyNodeOne** |
| Prohibido | «migración», «migrar» |

Visible solo si `operating_mode=local`.

---

## 3. Fases (`LinkEn1State.phase`)

| Phase | Notas |
|-------|--------|
| `idle` | Disponible en Local |
| `awaiting_login` | Cliente obtiene token fuera de este módulo |
| `select_organization` | |
| `select_enterprise` | `create_en1` \| `link_existing` |
| `select_branch` / `select_register` | |
| `transferring` | Subida / reconciliación |
| `completed` | Modo Plataforma; asistente deshabilitado |
| `failed` | Reanudable vía `resume()` → `awaiting_login` |

---

## 4. Identidad y conflictos (v1)

| Tema | Comportamiento |
|------|----------------|
| IDs | `IdMappingTable`: `local_id` ↔ `en1_id` por entidad |
| SKU duplicado | Política `merge` (default) / `rename` / `supervisor` |
| Clientes / empleados | Match preferido por **email** |
| Pedidos | Remap + `idempotency_key=link:{local_id}` |
| Fallo a mitad | `phase=failed`; no cortar a Plataforma hasta `completed` |

---

## 5. Datos transferidos (v1)

Productos, clientes, empleados, pedidos, saldos de inventario, mapeo business/branch/register.

Envelope de auditoría: `build_export_envelope()` / `export_local_envelope()` (schema_version 1).

---

## 6. API

```python
from nodeone.core.eposone_domain.link_en1 import assistant_from_memory_bundles

asst = assistant_from_memory_bundles(local_bundle, target_bundle)
asst.start()
asst.grant_access(access_granted=True)
asst.select_organization('99')
asst.select_enterprise('create_en1')  # o link_existing + en1_business_id
asst.select_branch()
asst.select_register()
result = asst.run_transfer()
# result.first_start_state.operating_mode == 'platform'
```

---

## 7. Criterio de hecho

- [x] Solo habilitado en Modo Local  
- [x] Flujo por fases + reanudación tras `failed`  
- [x] Crear empresa EN1 \| vincular existente  
- [x] Mapa de IDs + transferencia catálogo/clientes/empleados/órdenes/inventario  
- [x] Política SKU merge  
- [x] Cutover a `operating_mode=platform`  
- [x] Tests  
- [x] Sin OAuth embebido, sin APK, sin cambios a `core/sync/` (Sprint 7)

---

## 8. Fuera de alcance

- UI Android  
- OAuth / tokens reales  
- Dispositivos POS (Sprint 6)  
- Cablear sync offline § 6.9 (Sprint 7)
