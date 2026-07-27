# ADR-005 — Licenciamiento por Puntos de Venta

| Campo | Valor |
|-------|--------|
| ID | ADR-005 |
| Título | Licenciamiento por Puntos de Venta (POS) |
| Estado | **Parcialmente reemplazado** por [ADR-007](ADR-007-EPOSONE-COMMERCIAL-LICENSING-OFFLINE.md) — 18 jul 2026 |
| Roadmap | [`EN1_PLATFORM_EPOSONE_V4_ROADMAP.md`](EN1_PLATFORM_EPOSONE_V4_ROADMAP.md) |
| Master Plan | [`EN1_PLATFORM_MASTER_PLAN.md`](EN1_PLATFORM_MASTER_PLAN.md) |
| Relacionados | [ADR-001](ADR-001-EPOSONE-STANDALONE.md) · [ADR-002](ADR-002-EPOSONE-DOMAIN.md) · [ADR-003](ADR-003-EPOSONE-SYNC.md) · [ADR-004](ADR-004-EPOSONE-MIGRATION.md) · Etapa 6 § 6.1 |
| Alcance de esta fase | **Solo documentación** — **sin** restricciones en código |

---

> **Nota de precedencia (18 jul 2026):** ADR-007 reemplaza la decisión de este
> documento que ubicaba la unidad comercial en el POS. La unidad vigente es la
> **Caja** (`organization_id + register_ref`). Se mantienen vigentes la separación
> entre dominio/licenciamiento, la ausencia de lógica de planes en EPosOne y el
> principio de que los dispositivos no son la unidad comercial.

---

## Contexto

EPosOne se comercializará por **planes** (Inicio / Profesional / Enterprise, etc.). Si los límites viven en el dominio o en la app POS, cada cambio de plan obliga a reescribir la aplicación.

Hay que congelar tres capas que **no se mezclan**:

| Capa | Responsabilidad |
|------|-----------------|
| **Dominio** | Cómo funciona el negocio (empresas, sucursales, POS, cajas, dispositivos) |
| **Infraestructura** | Cómo sincroniza EPosOne con EN1 (ADR-003 / Sprint 7) |
| **Licenciamiento** | Qué cantidad de recursos puede usar el cliente según el plan |

---

## Principio (congelado)

> **El dominio del sistema no debe estar limitado por el plan comercial.**

La arquitectura **siempre** permite crear múltiples:

- Empresas  
- Sucursales  
- Puntos de Venta (POS)  
- Cajas  
- Dispositivos  

El **licenciamiento** decide qué puede utilizar el cliente.  
**Nunca** el modelo de datos.

---

## Decisión

### Jerarquía de dominio (siempre presente)

```text
Tenant
  └── Empresa
        └── Sucursal
              └── Punto de Venta (POS)     ← unidad de licenciamiento
                    └── Caja
                          └── Dispositivos (N)   ← no consumen licencia POS
```

Alineado a Etapa 6.1 (`org_unit` branch / pos / register + `core_pos_terminal`).

### Unidad comercial = Punto de Venta

**No confundir POS con Dispositivo.**

Ejemplo — un solo POS de la licencia:

```text
POS 01
  └── Caja Principal
        ├── Samsung Tablet
        ├── Lenovo Tablet
        ├── PC Windows
        └── KDS Cocina
```

El cliente consume **1 licencia POS**, aunque tenga varios dispositivos.  
Eso es fácil de explicar y competitivo frente a otras soluciones.

### Dónde vive el límite

| Qué | Dónde |
|-----|--------|
| Límites del plan | **EN1 Core** (licencia del tenant) |
| Lógica de planes / precios | **EN1** — no en EPosOne |
| Respuesta al crear el N+1 recurso | Core: denegación + mensaje de upsell |

Flujo conceptual (fase futura):

```text
Tenant → Licencia → máx. POS = 5
Usuario intenta crear el 6.º POS
EN1 Core: «No disponible. Su plan permite 5 puntos de venta. ¿Desea ampliar?»
EPosOne: solo muestra el resultado; no conoce el plan
```

### Planes de ejemplo (referencia comercial — no código)

| Recurso | Plan Inicio | Plan Profesional | Plan Enterprise |
|---------|-------------|------------------|-----------------|
| Empresas | 1 | 1 | Ilimitadas |
| Sucursales | 1 | 3 | Ilimitadas |
| **Puntos de Venta** | **1** | **5** | **Ilimitados** |
| Cajas | 1 | 10 | Ilimitadas |
| Dispositivos | Ilimitados | Ilimitados | Ilimitados |
| Usuarios | 3 | 20 | Ilimitados |

Otros límites futuros posibles vía misma capa Core: almacenamiento, integraciones, FE, IA, reportes avanzados.

### Etapa actual (obligatorio)

| Regla | Valor |
|-------|--------|
| Límites activos | **Ninguno** — todo ilimitado |
| Validaciones en EPosOne | **Prohibidas** |
| Validaciones en Core | **No activar** aún |
| Preparación | Identificar **hooks** donde el Core consultará políticas más adelante |

---

## Puntos futuros de consulta al Core (hooks — sin implementar)

Identificados para una fase posterior de licenciamiento. **No hay validación en esta etapa.**

| Momento | Entidad | Hook conceptual (Core) |
|---------|---------|------------------------|
| Crear / activar empresa | Empresa | `license.can_create('company')` |
| Crear sucursal | Sucursal | `license.can_create('branch')` |
| Crear punto de venta | **POS** | `license.can_create('pos')` ← principal |
| Crear caja | Caja / register | `license.can_create('register')` |
| Alta usuario operativo | Usuario | `license.can_create('user')` |
| Registrar dispositivo | Dispositivo | **No consume cupo POS**; opcional cupo device solo si el plan lo define después |
| Activar FE / IA / reportes | Feature flags | `license.has_feature(...)` |

EPosOne (y cualquier app) **solo** consume la API/política del Core; **no** duplica tablas de planes ni hardcodea cupos.

En **Modo Local** (ADR-003): sin EN1 no hay licencia de plataforma; al **Vincular** (ADR-004) el tenant entra bajo la licencia EN1 y los hooks aplican en Modo Plataforma.

---

## Consecuencias

| Positivo | Riesgo / mitigación |
|----------|---------------------|
| Dominio estable al cambiar planes | Disciplina: cero `if plan ==` en EPosOne |
| Upsell claro («ampliá puntos de venta») | Copy y UX de denegación viven en Core / shell plataforma |
| 1 POS + N tablets = 1 licencia | Documentar en ventas y onboarding |
| Preparado sin frenar adopción ahora | Etapa actual = ilimitado |

---

## Fuera de alcance de este ADR

- Implementar cupos, guards o UI de upsell.  
- Catálogo comercial definitivo de SKUs / precios.  
- Cambiar el modelo de datos de Etapa 6.  
- Limitar dispositivos por plan en v1 (permanecen ilimitados salvo decisión futura explícita).

---

## Reglas congeladas (extracto)

Añadidas al [Roadmap V4](EN1_PLATFORM_EPOSONE_V4_ROADMAP.md#reglas-congeladas):

9. El dominio **no** se limita por el plan comercial.  
10. El **Punto de Venta** es la unidad de licenciamiento; los **dispositivos** no consumen licencia POS adicional.  
11. EPosOne **no** contiene lógica de planes; los límites viven en **EN1 Core**.  
12. En la versión actual los cupos están **ilimitados**; la arquitectura queda preparada vía hooks.
