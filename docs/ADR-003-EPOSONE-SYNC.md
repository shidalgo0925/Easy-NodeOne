# ADR-003 — Modos operativos EPosOne (Local / Plataforma / Vincular)

| Campo | Valor |
|-------|--------|
| ID | ADR-003 |
| Título | Tres modos operativos; un solo producto |
| Estado | **Aprobado (congelado)** — 9 jul 2026 |
| Roadmap | [`EN1_PLATFORM_EPOSONE_V4_ROADMAP.md`](EN1_PLATFORM_EPOSONE_V4_ROADMAP.md) |
| Relacionados | [ADR-001](ADR-001-EPOSONE-STANDALONE.md) · [ADR-002](ADR-002-EPOSONE-DOMAIN.md) · [ADR-004](ADR-004-EPOSONE-MIGRATION.md) |
| Sync / offline EN1 | [`EN1_PLATFORM_ETAPA6_DOMINIO_COMERCIAL.md`](EN1_PLATFORM_ETAPA6_DOMINIO_COMERCIAL.md) § 6.9 |
| Alcance de esta fase | **Documentado + Sprint 7:** bridge [`EN1_PLATFORM_EPOSONE_V4_SYNC.md`](EN1_PLATFORM_EPOSONE_V4_SYNC.md) |

---

## Contexto

Etapa 6.9 (v1) asumió **fuente de verdad = servidor EN1** y cliente = caché + cola. Eso describe el **Modo Plataforma** (y offline temporal), no el producto completo.

Hay que congelar tres modos sin romper el sync ya scaffolded.

---

## Decisión — tres modos

### Terminología

| Nombre oficial | Evitar |
|----------------|--------|
| **Modo Local** | “Standalone” en UI (puede usarse en docs técnicos) |
| **Modo Plataforma** | “Connected” en UI |
| **Vincular con EN1** | **“Migración”** en copy de usuario |

El usuario **sigue usando EPosOne**. Solo cambia el backend / proveedor.

---

### Modo Local

| Aspecto | Valor |
|---------|--------|
| Objetivo | Competir con Loyverse: vender sin EN1 |
| Fuente de verdad | **SQLite (local)** |
| EN1 | No requerido |
| Internet | No permanente |
| Sync engine EN1 | **Inactivo** |
| Ideal para | Micro y pequeños negocios |

Primer inicio (Sprint 4): *Crear un nuevo negocio* → empresa, sucursal, caja, admin **locales**.

---

### Modo Plataforma

| Aspecto | Valor |
|---------|--------|
| Objetivo | Empresa ya en EN1; POS como app del ecosistema |
| Fuente de verdad | **EasyNodeOne (servidor)** |
| Cliente | Caché + cola de escritura (offline temporal) |
| Sync | **Activo** — motor actual (`nodeone/core/sync/`, handlers EPosOne) |
| Ideal para | Empresas que ya usan EN1 / multi-sucursal |

Primer inicio: *Conectar con EasyNodeOne* → login → org / empresa / sucursal / caja → descarga de configuración.

**§ 6.9 aplica íntegramente a este modo** (principios, prioridades, conflictos, idempotencia).

---

### Vincular con EN1 (transición)

| Aspecto | Valor |
|---------|--------|
| Objetivo | Pasar de Modo Local → Modo Plataforma **sin reinstalar** |
| Naturaleza | Asistente one-shot / por lotes (no sync continuo previo) |
| Resultado | Misma APK; proveedor = EN1; datos locales subidos o reconciliados |
| Detalle | [ADR-004](ADR-004-EPOSONE-MIGRATION.md) |

No es un cuarto “modo estable” de operación diaria: es el **puente** entre Local y Plataforma.

---

## Relación con Etapa 6.9

```text
§ 6.9 (sync offline)     →  Modo Plataforma (+ offline temporal)
Modo Local               →  Sin EN1; SQLite es fuente de verdad
Vincular con EN1         →  Cutover / importación; luego entra § 6.9
```

El scaffold de sync **no cambia su arquitectura**. Sprint 7 lo **conecta** al Modo Plataforma vía [`EN1_PLATFORM_EPOSONE_V4_SYNC.md`](EN1_PLATFORM_EPOSONE_V4_SYNC.md) (`platform_sync.py`) sin reescribir el motor.

---

## Consecuencias

| Positivo | Riesgo / mitigación |
|----------|---------------------|
| Claridad producto vs infra sync | Documentar en Master Plan que 6.9 = Plataforma |
| Una APK, tres caminos de inicio/vinculación | Wizard único (Sprint 4–5) |
| Reutiliza sync existente | No reescribir sync para Local |

---

## Reglas congeladas (extracto)

Ver reglas 5, 6 y 7 en el [Roadmap V4](EN1_PLATFORM_EPOSONE_V4_ROADMAP.md#reglas-congeladas).
