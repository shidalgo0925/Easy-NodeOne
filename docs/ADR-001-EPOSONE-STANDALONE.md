# ADR-001 — EPosOne como producto (Standalone + Platform)

| Campo | Valor |
|-------|--------|
| ID | ADR-001 |
| Título | EPosOne como producto independiente |
| Estado | **Aprobado (congelado)** — 9 jul 2026 |
| Roadmap | [`EN1_PLATFORM_EPOSONE_V4_ROADMAP.md`](EN1_PLATFORM_EPOSONE_V4_ROADMAP.md) |
| Relacionados | [ADR-002](ADR-002-EPOSONE-DOMAIN.md) · [ADR-003](ADR-003-EPOSONE-SYNC.md) · [ADR-004](ADR-004-EPOSONE-MIGRATION.md) · [ADR-005](ADR-005-EPOSONE-LICENSING-POS.md) |
| Alcance de esta fase | **Solo documentación** — sin código |

---

## Contexto

EPosOne nació como app de plataforma dentro de EasyNodeOne. Si se obliga a todo cliente a adoptar EN1 completo, se limita la adopción (cafeterías, kioscos, micro-negocios que solo quieren vender).

La decisión comercial y de producto es: **EPosOne debe poder vivir solo** y, cuando el cliente crezca, **vincularse a EN1** sin reinstalar ni perder datos.

---

## Decisión

```text
EasyNodeOne Platform
        │
   Aplicaciones (productos)
        │
     EPosOne
```

1. **EPosOne es un producto**, no un módulo del ERP.
2. **No depende obligatoriamente de EN1** para operar.
3. **Una sola APK** / un solo producto de aplicación (Android). No hay dos builds “lite” vs “EN1”.
4. **EN1 agrega capacidades** (CRM, multiempresa, FE, portal, RBAC central, etc.). **No reemplaza** EPosOne.
5. El mensaje comercial preferido: *Empezá con EPosOne. Cuando tu empresa crezca, activá EasyNodeOne sin perder tus datos.*

---

## Consecuencias

| Positivo | Riesgo / mitigación |
|----------|---------------------|
| Baja barrera de entrada (competir con Loyverse / Square / Poster) | Dos proveedores de datos → ver ADR-002 (dominio único) |
| Upsell natural a EN1 | Asistente de vinculación → ADR-004 |
| Misma UX de producto en Local y Plataforma | Modos operativos → ADR-003 |

---

## Fuera de alcance de este ADR

- Implementación Android / SQLite / APIs.
- Cambios al sync engine actual (`nodeone/core/sync/`).
- Licenciamiento comercial detallado → **[ADR-005](ADR-005-EPOSONE-LICENSING-POS.md)** (congelado; sin cupos activos).

---

## Reglas congeladas (extracto)

Ver reglas 1, 5, 6 y 8 en el [Roadmap V4](EN1_PLATFORM_EPOSONE_V4_ROADMAP.md#reglas-congeladas).
