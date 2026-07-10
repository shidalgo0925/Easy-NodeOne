# EPosOne V4 — Etapa 2 Android (Producto)

| Campo | Valor |
|-------|--------|
| Estado | **Documentado** — 9 jul 2026 · **código APK fuera de este servidor** |
| Etapa previa | Infra EN1 (POS, LicensePolicy, provisionamiento, sync base) — **cerrada** (`18f6593`) |
| Roadmap V4 | [`EN1_PLATFORM_EPOSONE_V4_ROADMAP.md`](EN1_PLATFORM_EPOSONE_V4_ROADMAP.md) |
| Primer inicio (dominio EN1) | [`EN1_PLATFORM_EPOSONE_V4_FIRST_START.md`](EN1_PLATFORM_EPOSONE_V4_FIRST_START.md) · `first_start.py` |
| Foco | Experiencia de la **APK** que ve el cliente — no más infra de servidor en esta etapa |

---

## Cambio de foco

| Hasta ahora | Ahora |
|-------------|--------|
| Servidor EN1 / dominio / sync base | Producto Android (flujo de usuario) |
| Provisionar POS en web | Onboarding en tablet en &lt; 5 minutos |

**No** empezar por sync fino. Empezar por **flujo de usuario** (Sprint A).

---

## Ubicación del código APK

| Dónde | Qué |
|-------|-----|
| Servidor Dev EN1 (`/opt/easynodeone/dev/app`) | Solo backend + docs. **No** hay proyecto Gradle/Kotlin aquí. |
| Máquina del desarrollador | `C:\Users\shidalgo\Documents\0. Tecnologia\EPosOne\eposone` |

La implementación de pantallas Android **requiere** abrir ese proyecto en Cursor (workspace local) o clonar el repo en una ruta visible al agente. Sin eso, solo se documenta el contrato.

---

## Sprints Etapa 2

| Sprint | Entregable | Estado |
|--------|------------|--------|
| **A** | Primer inicio (onboarding) — Bienvenida + Local / Plataforma | 📋 doc · ⏳ APK |
| **EN1-01** | APIs provisioning (`/api/v1/devices/*`) | ✅ EN1 (contrato + código) · ⏳ E2E tablet |
| **B** | Registro automático del dispositivo (UUID, modelo, POS, caja…) | ⏳ APK contra EN1-01 |
| **C** | Configuración automática post-registro (catálogo, impuestos, etc.) | ⏳ |
| **D** | Sync fino (solo empresa → sucursal → POS) | ⏳ |
| **E** | Pantalla «Este dispositivo» | ⏳ |
| **F** | Vincular con EN1 (solo Modo Local) | ⏳ |

### Sprint A — Primer inicio

**Pantalla 1 — Bienvenido a EPosOne**

- Logo + descripción.
- Solo dos opciones:
  1. **Crear un nuevo negocio** → Modo Local  
  2. **Conectar con EasyNodeOne** → Modo Plataforma  

**Opción 1 — Local:** Nombre negocio → Sucursal → Caja → Administrador → Finalizar.

**Opción 2 — Plataforma:** Login → Organización → Empresa → Sucursal → **POS** → Caja → Sincronizar → Entrar.

Contrato de dominio ya existe en EN1 (`first_start.py`); la APK debe consumirlo / espejarlo.

### Sprint B — Registro dispositivo

Al terminar el wizard, registrar en EN1 (o local): UUID, modelo, Android, versión APK, empresa, sucursal, POS, caja (`pos_ref` + `register_ref`).

### Sprint C — Config automática

Tras registro: descargar productos, categorías, clientes, impuestos, promociones, config, usuarios, permisos.

### Sprint D — Sync fino

No descargar todo el tenant: solo alcance empresa → sucursal → POS. Sin productos/promos/usuarios de otro ámbito.

### Sprint E — Este dispositivo

Configuración → Este dispositivo: nombre, UUID, POS, caja, última sync, versión, estado.

### Sprint F — Vincular EN1

Solo en Modo Local: acción «Vincular con EasyNodeOne» (ADR-004 / `link_en1.py`).

---

## Fuera de alcance (apagado)

- Planes, licencias, cupos, límites de POS/usuarios (`LicensePolicy` sigue permitiendo todo).
- Facturación electrónica, CRM, inventario avanzado, IA.
- Despliegue a staging / prod / relatic (salvo GO explícito en otro chat).

---

## Objetivo de producto

Quien descargue EPosOne debe **poder vender en menos de cinco minutos**, sin manual.

---

## Protocolo

1. Infra servidor = **cerrada** para esta etapa.  
2. Código APK = workspace del proyecto Android (no este repo solo).  
3. Orden: **A → B → C → D → E → F**.  
4. 1 chat = 1 sprint (o subtarea acordada).  
5. Commit/push del APK en su propio repo; docs de contrato pueden vivir en Easy-NodeOne.
