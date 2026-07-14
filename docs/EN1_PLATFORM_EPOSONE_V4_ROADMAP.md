# Roadmap — EPosOne V4 (Arquitectura definitiva)

| Campo | Valor |
|-------|--------|
| Estado | **Aprobado** — 9 jul 2026 · ADR-006 Op/Admin **14 jul 2026** |
| Fase actual | **Hito 2 E2E APK** 🟡 · luego **Hito 3 Operación del Pedido** (no ventas→stock) |
| Handoff | [`EN1_EPOSONE_HANDOFF_STATUS.md`](EN1_EPOSONE_HANDOFF_STATUS.md) |
| **ADR-006** | [`ADR-006-EPOSONE-OPERATION-VS-ADMIN.md`](ADR-006-EPOSONE-OPERATION-VS-ADMIN.md) |
| **Hito 3** | [`EN1_EPOSONE_HITO3_ORDER_LIFECYCLE.md`](EN1_EPOSONE_HITO3_ORDER_LIFECYCLE.md) |
| Master Plan | [`EN1_PLATFORM_MASTER_PLAN.md`](EN1_PLATFORM_MASTER_PLAN.md) |
| Dominio comercial | [`EN1_PLATFORM_ETAPA6_DOMINIO_COMERCIAL.md`](EN1_PLATFORM_ETAPA6_DOMINIO_COMERCIAL.md) |
| Contratos portables | [`EN1_PLATFORM_EPOSONE_V4_DOMAIN_CONTRACTS.md`](EN1_PLATFORM_EPOSONE_V4_DOMAIN_CONTRACTS.md) |
| Data providers | [`EN1_PLATFORM_EPOSONE_V4_PROVIDERS.md`](EN1_PLATFORM_EPOSONE_V4_PROVIDERS.md) · código `backend/nodeone/core/eposone_domain/` |
| Primer inicio | [`EN1_PLATFORM_EPOSONE_V4_FIRST_START.md`](EN1_PLATFORM_EPOSONE_V4_FIRST_START.md) |
| Vincular EN1 | [`EN1_PLATFORM_EPOSONE_V4_LINK_EN1.md`](EN1_PLATFORM_EPOSONE_V4_LINK_EN1.md) |
| Dispositivos POS | [`EN1_PLATFORM_EPOSONE_V4_DEVICES.md`](EN1_PLATFORM_EPOSONE_V4_DEVICES.md) |
| Sync Plataforma | [`EN1_PLATFORM_EPOSONE_V4_SYNC.md`](EN1_PLATFORM_EPOSONE_V4_SYNC.md) |
| POS + licenciamiento | [`EN1_PLATFORM_EPOSONE_V4_POS_LICENSING_ROADMAP.md`](EN1_PLATFORM_EPOSONE_V4_POS_LICENSING_ROADMAP.md) |
| Licenciamiento | [`ADR-005-EPOSONE-LICENSING-POS.md`](ADR-005-EPOSONE-LICENSING-POS.md) |
| **Etapa 2 Android** | [`EN1_PLATFORM_EPOSONE_V4_ANDROID_ETAPA2.md`](EN1_PLATFORM_EPOSONE_V4_ANDROID_ETAPA2.md) |
| **Hito EN1-01** | [`EPOSONE_EN1_HITO1_PROVISIONING_CONTRACT.md`](EPOSONE_EN1_HITO1_PROVISIONING_CONTRACT.md) (doc = **EN1-02** oficial; EN1-01 legacy) |
| **Handoff** | [`EN1_EPOSONE_HANDOFF_STATUS.md`](EN1_EPOSONE_HANDOFF_STATUS.md) |

---

## Objetivo

Convertir EPosOne en un **producto independiente** que opere:

1. de forma **autónoma** (Modo Local), y  
2. **integrado** con EasyNodeOne Platform (Modo Plataforma),

con **un único modelo de dominio** y **una sola aplicación Android**.

---

## ADRs (Sprint 1 — entregables)

| ADR | Archivo | Tema |
|-----|---------|------|
| ADR-001 | [`ADR-001-EPOSONE-STANDALONE.md`](ADR-001-EPOSONE-STANDALONE.md) | EPosOne como producto; una APK; EN1 no obligatorio |
| ADR-002 | [`ADR-002-EPOSONE-DOMAIN.md`](ADR-002-EPOSONE-DOMAIN.md) | Dominio único; SQLite/EN1 = proveedores |
| ADR-003 | [`ADR-003-EPOSONE-SYNC.md`](ADR-003-EPOSONE-SYNC.md) | Modo Local · Modo Plataforma · Vincular con EN1 |
| ADR-004 | [`ADR-004-EPOSONE-MIGRATION.md`](ADR-004-EPOSONE-MIGRATION.md) | Asistente Vincular con EasyNodeOne |
| ADR-005 | [`ADR-005-EPOSONE-LICENSING-POS.md`](ADR-005-EPOSONE-LICENSING-POS.md) | Licenciamiento por Punto de Venta; cupos en Core |
| ADR-006 | [`ADR-006-EPOSONE-OPERATION-VS-ADMIN.md`](ADR-006-EPOSONE-OPERATION-VS-ADMIN.md) | Operación (POS) vs Administración (EN1); modos org; Pedido |

**Sprint 1:** ADRs + Master Plan / § 6.9. **Sin código.** ✅

**Sprint 2:** contratos portables — [`EN1_PLATFORM_EPOSONE_V4_DOMAIN_CONTRACTS.md`](EN1_PLATFORM_EPOSONE_V4_DOMAIN_CONTRACTS.md). **Sin providers / sin Android.** ✅ (doc; pendiente firma)

**Sprint 3:** providers — [`EN1_PLATFORM_EPOSONE_V4_PROVIDERS.md`](EN1_PLATFORM_EPOSONE_V4_PROVIDERS.md) · `eposone_domain/` (Memory / SQLite / API). **Sin sync rewrite / sin Android APK.** ✅

**Sprint 4:** primer inicio — [`EN1_PLATFORM_EPOSONE_V4_FIRST_START.md`](EN1_PLATFORM_EPOSONE_V4_FIRST_START.md) · `first_start.py`. **Sin APK / sin OAuth embebido / sin Vincular.** ✅

**Sprint 5:** vincular — [`EN1_PLATFORM_EPOSONE_V4_LINK_EN1.md`](EN1_PLATFORM_EPOSONE_V4_LINK_EN1.md) · `link_en1.py`. **Sin APK / sin sync rewrite.** ✅

**Sprint 6:** dispositivos — [`EN1_PLATFORM_EPOSONE_V4_DEVICES.md`](EN1_PLATFORM_EPOSONE_V4_DEVICES.md) · `devices.py` + `core_pos_terminal` V4. **Sin sync rewrite.** ✅

**Sprint 7:** sync Plataforma — [`EN1_PLATFORM_EPOSONE_V4_SYNC.md`](EN1_PLATFORM_EPOSONE_V4_SYNC.md) · `platform_sync.py` + rutas. **Motor intacto.** ✅

**ADR-005:** licenciamiento por POS — [`ADR-005-EPOSONE-LICENSING-POS.md`](ADR-005-EPOSONE-LICENSING-POS.md). **Solo doc; sin cupos activos.** ✅

---

## Sprints / entregables

| Sprint | Nombre | Estado | Resumen |
|--------|--------|--------|---------|
| **1** | ADR | ✅ | ADR-001…004 + modos en § 6.9 |
| **2** | Contrato de dominio | ✅ doc | Producto, Cliente, Pedido, Caja, Inventario, Empleado, Config — IDs opacos |
| **3** | Data providers | ✅ | `*Repository` + Memory / SQLite / API; dominio intacto |
| **4** | Primer inicio | ✅ | Wizard: Crear negocio \| Conectar EasyNodeOne (`first_start.py`) |
| **5** | Vincular con EN1 | ✅ | Asistente Local → Plataforma (`link_en1.py`) |
| **6** | Dispositivos POS | ✅ | UUID, perfil, app, empresa, sucursal, caja, flag sync |
| **7** | Sincronización | ✅ | Bridge política Plataforma sobre `core/sync/` |
| **—** | Licenciamiento POS | ✅ | ADR-005 + stub `LicensePolicy` (sin cupos) · commit `18f6593` |
| **EN1-01** | Provisioning APIs (legacy) | ✅ | `847a09f` — refs en body + código por org |
| **EN1-02** | Código = destino | ✅ **CERRADO** | `82c68f7` · tag `eposone-provisioning-v1.0` · E2E tablet Itsmo |
| **Hito 2** | Device Bootstrap Sync Down | ✅ EN1 API · ⏳ E2E APK | [`EN1_EPOSONE_HITO2_DEVICE_BOOTSTRAP_SYNC_DOWN.md`](EN1_EPOSONE_HITO2_DEVICE_BOOTSTRAP_SYNC_DOWN.md) · **`b254735`** · APK debe usar `/api/v1/devices/bootstrap` |
| **Hito 3** | Operación del Pedido | 📋 brief | [`EN1_EPOSONE_HITO3_ORDER_LIFECYCLE.md`](EN1_EPOSONE_HITO3_ORDER_LIFECYCLE.md) — **reemplaza** “Ventas → Stock” |
| **Etapa 2** | Android (Producto) | 📋 | Cerrar H2 E2E → contrato H3 → Pedido offline-first |

### Etapa 2 — Android (resumen)

Orden: **Hito 1** ✅ → **Hito 2** bootstrap E2E → **Hito 3** ciclo de vida del Pedido + sync ↔ EN1 → inventario por eventos / caja / FE.  
Código APK: máquina local del equipo. Una sola APK; modos Solo POS / POS+BO / Corporativo (ADR-006).

---

## Reglas congeladas

1. Existe **una sola APK**.
2. Existe **un solo modelo de dominio**.
3. El dominio **nunca** conoce SQLite ni EN1.
4. SQLite y EN1 son **únicamente proveedores de datos**.
5. EPosOne puede operar **completamente solo**.
6. EasyNodeOne **agrega capacidades**; nunca reemplaza EPosOne.
7. Vincular con EN1 **no cambia la aplicación**; solo el backend.
8. El usuario **nunca reinstala**, **nunca cambia de producto**, **nunca pierde información**.
9. El dominio **no** se limita por el plan comercial (ADR-005).
10. El **Punto de Venta** es la unidad de licenciamiento; los **dispositivos** no consumen licencia POS adicional.
11. EPosOne **no** contiene lógica de planes; los límites viven en **EN1 Core**.
12. Hoy los cupos están **ilimitados**; la arquitectura queda preparada vía hooks de política Core.
13. **EPosOne opera; EN1 administra** (ADR-006). El POS no escribe tablas de inventario EN1; emite eventos.
14. **Una APK**; no Lite/Pro. Capacidades por **modo de organización** + nivel de usuario.
15. El **Pedido** es la entidad principal; el usuario hace acciones, el sistema cambia estados.
---

## Relación con trabajo Connected actual (appdev)

El shell UX, dashboard y analítica POS en EN1 web son trabajo de **Modo Plataforma**.  
No contradicen V4: Standalone/Local es otro modo de despliegue; al vincular, el cliente aterriza en el mismo producto.

El motor `nodeone/core/sync/` permanece; § 6.9 describe **Modo Plataforma**. Modo Local no usa ese motor hasta vincular.

---

## Protocolo

- **GO Sprint 1:** ADR — hecho.  
- **GO Sprint 2:** contratos portables — documento listo; **revisión humana** antes de Sprint 3.  
- **GO Sprint 3:** data providers — hecho en Dev (`eposone_domain/`).  
- **GO Sprint 4:** primer inicio — hecho (`first_start.py`; dominio; sin APK).  
- **GO Sprint 5:** vincular — hecho (`link_en1.py`; dominio; sin sync).  
- **GO Sprint 6:** dispositivos — hecho (`devices.py` + `core_pos_terminal` V4).  
- **GO Sprint 7:** sync — hecho (`platform_sync.py`; motor sin reescritura).  
- **GO ADR-005 + infra POS:** dominio POS/caja/dispositivo + `LicensePolicy` stub + admin provisionamiento — **cerrado** (`18f6593` en `develop`).  
- **GO EN1-01:** APIs provisioning (legacy) — `847a09f`.  
- **GO EN1-02 / Hito 1:** código = destino — **CERRADO** `82c68f7` · tag `eposone-provisioning-v1.0` · E2E tablet Itsmo.  
- **Hito 2 Device Bootstrap:** EN1 API lista · `b254735` · pendiente E2E APK (`bootstrap`, no `/api/eposone/products`).  
- **ADR-006 + Hito 3 brief:** aprobados 14 jul — **sin código** Hito 3 hasta contrato + GO.  
- Sin GO: no push staging/prod, no sync a flotas, no reabrir provisioning.
