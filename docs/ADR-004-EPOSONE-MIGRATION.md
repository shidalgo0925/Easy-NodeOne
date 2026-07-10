# ADR-004 — Vincular EPosOne con EasyNodeOne

| Campo | Valor |
|-------|--------|
| ID | ADR-004 |
| Título | Asistente «Vincular con EasyNodeOne» (Local → Plataforma) |
| Estado | **Aprobado (congelado)** — 9 jul 2026 |
| Roadmap | [`EN1_PLATFORM_EPOSONE_V4_ROADMAP.md`](EN1_PLATFORM_EPOSONE_V4_ROADMAP.md) |
| Relacionados | [ADR-001](ADR-001-EPOSONE-STANDALONE.md) · [ADR-002](ADR-002-EPOSONE-DOMAIN.md) · [ADR-003](ADR-003-EPOSONE-SYNC.md) |
| Alcance de esta fase | **Documentado + implementado Sprint 5** — ver [`EN1_PLATFORM_EPOSONE_V4_LINK_EN1.md`](EN1_PLATFORM_EPOSONE_V4_LINK_EN1.md) |

---

## Contexto

Un cliente puede empezar en **Modo Local** y, meses o años después, necesitar CRM, multiempresa, FE, etc. Debe poder **vincular** el negocio a EN1 **sin reinstalar** y **sin perder información**.

En UI y documentación de producto se usa **«Vincular con EasyNodeOne»**, no «Migración» (el usuario no cambia de producto).

---

## Decisión

### Entrada

```text
Configuración
  → Vincular con EasyNodeOne
```

Solo visible / habilitado si el dispositivo/empresa está en **Modo Local**.

### Flujo del asistente (congelado)

```text
Configuración
  → Vincular con EasyNodeOne
  → Login EN1
  → Seleccionar organización
  → Empresa (crear en EN1  |  vincular existente)
  → Sucursal
  → Caja
  → Sincronizar / subir datos locales
  → Listo (Modo Plataforma)
```

### Opciones de empresa

| Opción | Efecto |
|--------|--------|
| **Crear empresa EN1** | Nueva organización/empresa en plataforma a partir de datos locales |
| **Vincular empresa existente** | Mapear empresa local a org/empresa ya existente en EN1 |

### Datos a transferir (mínimo v1 del asistente)

| Dominio | Acción |
|---------|--------|
| Productos | Subir / reconciliar |
| Clientes | Subir / reconciliar |
| Ventas / pedidos (historial) | Subir según política de retención v1 |
| Inventario | Subir saldos / alertas |
| Usuarios / cajeros | Mapear a usuarios EN1 o invitar |
| Configuración | Impuestos, moneda, preferencias POS |
| Cajas / sucursales / terminales | Crear o vincular unidades |

### Resultado

```text
Modo Local  →  Modo Plataforma
```

- Misma APK.
- Proveedor de datos = EN1 API.
- A partir de ahí aplica **§ 6.9** (sync offline, fuente de verdad servidor).
- El usuario **no reinstala**, **no cambia de producto**, **no pierde información** (regla 8).

### Identidad y conflictos (principios)

| Tema | Principio v1 (a detallar en Sprint 5) |
|------|--------------------------------------|
| IDs | Tabla de mapeo `local_id` ↔ `en1_id` por entidad |
| SKU / código producto duplicado | Política explícita: merge / renombrar / supervisor |
| Usuarios | Email como clave preferida de vínculo |
| Fallo a mitad | Asistente reanudable; no dejar modo híbrido indefinido sin estado “vinculando” |

---

## Consecuencias

| Positivo | Riesgo / mitigación |
|----------|---------------------|
| Upsell sin fricción | Asistente debe ser idempotente y auditable |
| Refuerza dominio único (ADR-002) | Contratos portables antes de implementar (Sprint 2) |
| Copy “Vincular” vs “Migrar” | Evita sensación de cambio de software |

---

## Fuera de alcance de este ADR

- Implementación del asistente — **hecha en Sprint 5** ([`EN1_PLATFORM_EPOSONE_V4_LINK_EN1.md`](EN1_PLATFORM_EPOSONE_V4_LINK_EN1.md)).
- Módulo «Dispositivos POS» en EN1 (Sprint 6).
- Cambios al código de sync (Sprint 7 solo conecta Modo Plataforma).

---

## Reglas congeladas (extracto)

Ver reglas 6, 7 y 8 en el [Roadmap V4](EN1_PLATFORM_EPOSONE_V4_ROADMAP.md#reglas-congeladas).
