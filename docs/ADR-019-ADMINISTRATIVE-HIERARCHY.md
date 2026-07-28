# ADR-019 — Jerarquía Administrativa EN1

| Campo | Valor |
|-------|--------|
| ID | ADR-019 |
| Título | Jerarquía Administrativa (Plataforma / Empresa / Producto / Operación) |
| Estado | **Aprobado (GO)** — 28 jul 2026 · menú Fase 1 en Dev |
| Ámbito | EN1 Platform · shell ERP · RBAC · visibilidad de menú |
| Relacionados | [`RBAC_Y_ROLES.md`](RBAC_Y_ROLES.md) · [ADR-006](ADR-006-EPOSONE-OPERATION-VS-ADMIN.md) · [ADR-015](ADR-015-EN1-NAVIGATION-ARCHITECTURE.md) · [`nav_menu.py`](../backend/nodeone/core/nav_menu.py) · [ADR-012](ADR-012-ETS-ECOSYSTEM-ARCHITECTURE.md) |
| Implementación | **Fase 1:** etiquetas/grupos menú + gates SaaS existentes · **Backlog:** Product Admin UI, split rutas Usuarios globales vs tenant |

---

## Pregunta rectora

> **¿Quién puede administrar qué en EN1, sin mezclar la plataforma SaaS de ETS con la empresa del cliente?**

---

## Decisión

Existen **cuatro niveles** claramente diferenciados. Cada uno administra **solo** lo que le corresponde.

```text
ETS (Super Admin)
        │
        ▼
Plataforma EN1
        │
        ▼
Organización (Tenant)
        │
        ▼
Productos contratados
        │
        ▼
Operación
```

| Nivel | Quién | Alcance | Señal en código (hoy) |
|-------|--------|---------|------------------------|
| **Super Admin (ETS)** | EasyTech / ops plataforma | Toda la plataforma: orgs, catálogo SaaS, módulos, sistema | `User.is_admin` · rol **SA** · `show_platform_admin_nav` |
| **Tenant Admin** | Admin de la empresa cliente | Solo su organización: perfil, usuarios de la org, fiscal, preferencias | Rol **AD** · `show_tenant_admin_menu` · **sin** `is_admin` de plataforma |
| **Product Admin** | Admin del producto dentro del tenant | Config del producto contratado (p. ej. EPosOne) respetando el plan | Ver [ADR-006](ADR-006-EPOSONE-OPERATION-VS-ADMIN.md) · backlog UI dedicada |
| **Operadores** | Cajeros, staff, etc. | Uso operativo del producto; sin config global de plataforma ni de empresa | Roles ST/TE/MI · permisos finos RBAC |

**Prohibido:** que un Tenant Admin vea o mute Organizaciones / Catálogo SaaS / Módulos SaaS / Logs globales / Respaldos / Usuarios globales.

---

## Menú objetivo (Fase 1)

### Plataforma (solo ETS)

```text
PLATAFORMA
├── SaaS
│   ├── Organizaciones
│   ├── Catálogo SaaS
│   └── Módulos SaaS
│   └── (backlog) Productos · Planes · Licencias · Features · Marketplace
└── Sistema
    ├── Usuarios globales
    ├── Logs
    ├── Respaldos
    └── Guía (setup plataforma)
```

### Empresa (Tenant Admin — y SA cuando opera una org activa)

```text
EMPRESA
├── Perfil          (branding / company setup)
├── Fiscal          (impuestos, pagos, efactura config)
└── Acceso          (Usuarios de la org · comunicación)
```

Roles/matriz RBAC del tenant viven en la zona **Permisos** (ya existente), no bajo Sistema ETS.

---

## Relación con ADR-015

En [ADR-015](ADR-015-EN1-NAVIGATION-ARCHITECTURE.md), el agrupador genérico **«Sistema»** del launcher v1 (dominios de negocio) **desaparece**.

En este ADR-019, **«Sistema»** bajo **Plataforma** significa **ops ETS** (logs, respaldos, usuarios globales). Son conceptos distintos:

| Término | ADR | Significado |
|---------|-----|-------------|
| Sistema (v1 launcher) | ADR-015 | Agrupador de negocio a eliminar |
| Sistema (bajo Plataforma) | ADR-019 | Operaciones de plataforma ETS |

---

## Código y gates

| Superficie | Menú | Gate típico |
|------------|------|-------------|
| SaaS (orgs, catálogo, módulos) | Plataforma → SaaS | `platform_admin_required` · área `plataforma` (`_v_plataforma`) |
| Sistema (usuarios globales, logs, respaldos) | Plataforma → Sistema | Misma área `plataforma` (solo SA) |
| Empresa (perfil, fiscal, acceso) | Área `config` label **Empresa** | `show_tenant_admin_menu` |
| Usuarios de la org | Empresa → Acceso → Usuarios | `users.view` · mismo endpoint `admin_users` con scope de org |
| Usuarios globales | Plataforma → Sistema | SA · mismo endpoint `admin_users` (sin split de ruta en Fase 1) |

**Nota Fase 1:** `admin_users` es compartido; el menú aclara «Usuarios globales» vs «Usuarios». Split físico de rutas queda en backlog.

---

## Backlog (fuera de Fase 1)

- Entradas SaaS: Productos, Planes, Licencias, Features, Marketplace (cuando existan pantallas).
- Shell **Product Admin** por producto.
- Rutas distintas: Usuarios globales vs Usuarios tenant.
- Sistema: Workers, colas, auditoría avanzada, migraciones, monitoreo.

---

## Historial

| Fecha | Nota |
|-------|------|
| **2026-07-28** | Aprobado (GO) — ADR + renombre menú Plataforma (SaaS/Sistema) y Configuración → Empresa |
