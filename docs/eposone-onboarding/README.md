# EPosOne Onboarding — Pack P0 (contratos oficiales)

| Campo | Valor |
|-------|--------|
| Estado | **P0 contratos** — 6 ago 2026 · **sin implementación de código** |
| ADR marco | [`ADR-027`](../ADR-027-EPOSONE-ONBOARDING-UNIFICADO-V1.md) |
| As-is previo | [`EPOSONE_EP1_INSTALLATION_ACTIVATION_AS_IS_V1.md`](../EPOSONE_EP1_INSTALLATION_ACTIVATION_AS_IS_V1.md) |
| Implementa UI | **LOCAL** (APK) tras GO |
| Exposición API | **EN1** P1 (modality, login onboarding, portal) |

---

## Índice de contratos

| Doc | Contenido |
|-----|-----------|
| [DEVICE_LIFECYCLE_V1.md](DEVICE_LIFECYCLE_V1.md) | Estados + eventos device |
| [ONBOARDING_CONTRACT_V2.md](ONBOARDING_CONTRACT_V2.md) | Ciclo único + caminos A–D |
| [LOGIN_CONTRACT_V1.md](LOGIN_CONTRACT_V1.md) | Login EN1 = resolver contexto |
| [RESTORE_CONTRACT_V1.md](RESTORE_CONTRACT_V1.md) | Camino D |
| [QR_CONTRACT_V1.md](QR_CONTRACT_V1.md) | QR → solo provision code |

---

## Modelo de producto (congelado)

```text
Cuenta EN1 → Organización → Suscripción EPosOne → Modalidad
                                              ├─ Standalone  (sin sync cloud operativa)
                                              └─ Connected   (con sync)
```

**Eliminado como flujo de usuario:** “Modo Local” / crear negocio sin EN1.

---

## Diagrama oficial — convergencia

```mermaid
flowchart TB
  subgraph Comercial["EN1 comercial"]
    L[Landing] --> S["/start"]
    S --> Acc[Cuenta + Org + Plan + Modalidad]
    Acc --> Portal[Portal instalación]
  end
  subgraph APK["EP1 APK"]
    Gate{Device Active?}
    Gate -->|Sí| PIN[PIN cajero]
    Gate -->|No| Asist[Asistente]
    Asist --> B[B Login cuenta]
    Asist --> C[C Código]
    Asist --> D[D Restore]
    Asist --> Q[QR → C]
  end
  Portal -->|código / QR| C
  B --> Core[Register + Bootstrap]
  C --> Core
  D --> Core
  Q --> C
  Core --> PIN
  PIN --> Op[Operar]
```

---

## Gates de implementación

### Gate 0 — Contratos (este P0)

| Criterio | Owner |
|----------|-------|
| ADR-027 aprobado / pack publicado | CODITO |
| ADR-014 enmendado (modalidad) | CODITO |
| LOCAL acusa recibo del pack | LOCAL |
| Sin quinto flujo Local en specs APK | LOCAL |

### Gate 1 — EN1 exposición

| Criterio | Owner | Estado |
|----------|-------|--------|
| `modality` + `plan_code` comercial en Device `/config` (+ bootstrap) | EN1 | ✅ 6 ago 2026 — ver [DEVICE_CONFIG_COMMERCIAL_V1.md](DEVICE_CONFIG_COMMERCIAL_V1.md) |
| Portal instalación mínimo (código, QR, regenerar, devices) | EN1 | ✅ 6 ago 2026 — `/admin/eposone/install` |
| API Login onboarding (payload § Login Contract) | EN1 | ⏸ pendiente (contrato listo) |
| Trial 15 / Grace 7 sin tercer período | EN1 | ✅ (sin cambio) |

### Gate 2 — APK onboarding (LOCAL)

| Criterio | Owner |
|----------|-------|
| Gate Active → cajero | LOCAL |
| Caminos B, C, D (+ QR→C) | LOCAL |
| Sin UI “crear negocio sin EN1” | LOCAL |
| Register + Bootstrap reutilizados 100 % | LOCAL |

### Gate 3 — Operar

| Criterio | Owner |
|----------|-------|
| PIN + turno + cobro (Hito 4) | LOCAL + EN1 ya listo |
| Manual instalación alineado a V2 | Docs |

---

## Qué no hace este P0

- Código  
- Hosting APK en EN1  
- Pasarela  
- Cambiar tablas salvo lo que P1 decida al mapear lifecycle enums  

---

## Confirmación de recepción (LOCAL)

*Onboarding Contract V2 + Device Lifecycle + Login/Restore/QR recibidos — ADR-027.*
