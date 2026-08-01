# ADR-021 — Ciclo de vida de instalación integrada (EPosOne ↔ EN1)

| Campo | Valor |
|-------|--------|
| ID | ADR-021 |
| Título | Installation Lifecycle — bootstrap obligatorio antes de operar (modo integrado) |
| Estado | **Propuesto** — 1 ago 2026 · pendiente aprobación Prog1 + Prog2 |
| Ámbito | EN1 (Prog1) · EPosOne APK (Prog2) · modo **integrado** únicamente |
| Relacionados | [EN1-02 Provisioning](EPOSONE_EN1_HITO1_PROVISIONING_CONTRACT.md) · [Hito 2 Bootstrap](EN1_EPOSONE_HITO2_DEVICE_BOOTSTRAP_SYNC_DOWN.md) · [**Contrato Installation v1**](EN1_EPOSONE_INSTALLATION_LIFECYCLE_CONTRACT_V1.md) · [ADR-007 Licencia](ADR-007-EPOSONE-COMMERCIAL-LICENSING-OFFLINE.md) · [License Engine V1](EN1_EPOSONE_LICENSE_ENGINE_V1_CONTRACT.md) · [ADR-003 Sync](ADR-003-EPOSONE-SYNC.md) · [ADR-006 Op/Admin](ADR-006-EPOSONE-OPERATION-VS-ADMIN.md) |
| No implementa | Endpoints, columnas, gates HTTP — ver contrato Installation v1 (propuesto) |
| Standalone | **Fuera de alcance** — wizard local sin EN1; sin cambios |
| Contrato wire | [`EN1_EPOSONE_INSTALLATION_LIFECYCLE_CONTRACT_V1.md`](EN1_EPOSONE_INSTALLATION_LIFECYCLE_CONTRACT_V1.md) — **PROPUESTO** |

---

## Pregunta rectora

> **¿El provisioning (EN1-02) basta para habilitar un POS integrado, o el primer bootstrap es el verdadero inicio del ciclo de vida de una instalación?**

---

## Contexto

Durante la revisión P0 quedó claro que el provisioning se venía tratando solo como “registrar dispositivo”. En instalaciones **integradas**, el flujo real es más amplio:

```text
Instalar APK
  → Código de aprovisionamiento
  → Register Device + Device Token
  → Bootstrap obligatorio
  → Descarga completa de configuración
  → Validación licencia
  → Validación versión
  → Migraciones locales
  → POS habilitado
```

**EN1-02** (congelado) resuelve identidad y destino (código → Caja → token).  
**Hito 2** entrega el snapshot operativo.  
**License Engine** autoriza la Caja.

Falta formalizar la **orquestación**: cuándo una instalación está *ready* y qué está prohibido antes.

---

## Decisión

1. **Provisioning ≠ instalación lista.** EN1-02 solo vincula dispositivo ↔ Caja y emite token.  
2. **El primer bootstrap exitoso es el hito de “instalación operativa”** en modo integrado.  
3. **Hasta bootstrap OK, la APK integrada no opera:** no abrir caja, no turno, no vender, no imprimir, no cobrar.  
4. **Licenciado ≠ install-ready.** Una Caja puede tener licencia ACTIVE y el dispositivo aún no estar listo (bootstrap incompleto).  
5. **Standalone no cambia:** wizard local; sin dependencia de EN1; sin este ADR.  
6. **EN1-02 no se infla** con catálogo/licencia/versión: addendum de semántica + [Contrato Installation v1](EN1_EPOSONE_INSTALLATION_LIFECYCLE_CONTRACT_V1.md) (propuesto).  
7. **Compatibilidad:** wire actual de `register` / `config` / `bootstrap` se mantiene hasta el contrato Installation v1 **aceptado** + GO de implementación (fase C).

```text
                    ┌──────────────────────────┐
                    │   Instalación integrada  │
                    └────────────┬─────────────┘
                                 │
           ┌─────────────────────┼─────────────────────┐
           ▼                     ▼                     ▼
     EN1-02                 Hito 2                 License
     Identidad              Sync Down              Autorización
     device↔Caja            snapshot               Caja
     Device Token           config/catálogo/…      (ADR-007)
           │                     │                     │
           └────────── Installation Lifecycle ─────────┘
                       (este ADR — orquestación)
```

---

## 1. Capas (no mezclar)

| Capa | Pregunta | Contrato hoy |
|------|----------|--------------|
| **Provisioning** | ¿Qué tablet pertenece a esta Caja? | EN1-02 |
| **Bootstrap / Sync Down** | ¿Qué configuración/datos necesita para operar? | Hito 2 (+ 2.5 cajeros, policies) |
| **Licencia** | ¿Puede operar *comercialmente* esta Caja? | ADR-007 + License Engine V1 |
| **Installation Lifecycle** | ¿Completó el onboarding integrado? | **Este ADR** · wire: [Contrato Installation v1](EN1_EPOSONE_INSTALLATION_LIFECYCLE_CONTRACT_V1.md) (**propuesto**) |

---

## 2. Estados lógicos (APK — SoT de UX)

Estados conceptuales (nombres finales en contrato Installation v1):

| Estado | Significado |
|--------|-------------|
| `unprovisioned` | Sin token EN1 (wizard código / standalone) |
| `registered` | Register OK; token válido; **aún no operar** |
| `bootstrapping` | Bootstrap en curso (descarga / migraciones) |
| `ready` | Bootstrap OK + chequeos locales OK → POS habilitado |
| `blocked` | Licencia/versión/política impiden operar (distinto de “aún no bootstrap”) |
| `failed` | Bootstrap falló; reintentar; no operar |

EN1 **hoy** no persiste estos estados. La APK es responsable del gate hasta que exista contrato de ACK/estado server-side (post-GO).

---

## 3. Regla de negocio (integrado)

Una instalación integrada **NO puede**:

- abrir caja / iniciar turno  
- vender / cobrar / imprimir ticket de venta  

hasta alcanzar `ready`.

Re-bootstrap / refresh de catálogo **después** de `ready` no vuelve a `unprovisioned`; puede degradar a `bootstrapping` solo si la política local lo exige (detalle en contrato v1).

---

## 4. Register vs Bootstrap (reparto)

| Información | Register | Bootstrap |
|-------------|----------|-----------|
| `device_uuid`, modelo, `app_version` | Sí | Refresh opcional |
| Destino org / sucursal / POS / caja | En `config` de respuesta | En `config` del snapshot |
| Device Token | **Solo aquí** | No |
| Catálogo, stock, cajeros, policies | No | **Sí** |
| Snapshot `license` | Hoy también en `config` (compat) | **Canal canónico** + sync |
| `min_app_version` / schema gate | Hint futuro opcional | **Obligatorio** cuando se implemente |
| Descriptor / estado de instalación | Hint mínimo futuro | Checklist + estado |
| Políticas de sync | No | Sí |

---

## 5. Campos candidatos (no congelar nombres aún)

Para el futuro contrato Installation v1 (solo lista de intención):

- descriptor de instalación (timestamps, entorno, build)  
- políticas de sincronización  
- versión mínima requerida de APK / schema  
- capabilities (integrado vs futuro)  
- bloque license (ya existe)  
- señal de bootstrap obligatorio / install-ready  
- metadatos de despliegue  

**No** se proponen nombres JSON ni endpoints en este ADR.

---

## 6. Impacto

| Área | Efecto |
|------|--------|
| EN1-02 | Addendum semántico; sin breaking change |
| Hito 2 | Criterio de “lista para vender” = solo tras bootstrap OK + gates locales |
| License | Sin cambio de unidad (Caja); install-ready es orthogonal |
| Sync | Primer bootstrap = Sync Down inicial obligatorio |
| Cash / Orders HTTP | Sin gate server hoy; opcional post-contrato (`installation_incomplete`) |
| Standalone | Ninguno |

---

## 7. Plan de adopción

| Fase | Qué | Quién |
|------|-----|-------|
| **A — Docs ADR** | ADR-021 + addendum EN1-02 + nota Hito 2 | Prog1 — **hecho** |
| **B — Contrato Installation v1** | Estados, checklist, bloque `installation`, errores | Prog1 — **borrador** [`EN1_EPOSONE_INSTALLATION_LIFECYCLE_CONTRACT_V1.md`](EN1_EPOSONE_INSTALLATION_LIFECYCLE_CONTRACT_V1.md) · falta aceptación Prog2 |
| **C — GO implementación** | Wire EN1/APK, ACK opcional, gates | Tras aprobación B |

Prohibido implementar C sin B aceptado.

---

## 8. Consecuencias

### Positivas

- Un solo modelo mental EN1 ↔ APK para onboarding.  
- EN1-02 permanece estable.  
- Reduce “tablet con token que vende sin catálogo/licencia fresca”.  

### Negativas / costos

- Gate fuerte en APK hasta que exista enforcement EN1.  
- Requiere disciplina de producto (no “atajos” de demo sin bootstrap).  

### Neutral

- Standalone intacto.  
- Reprovisionamiento de tablet sigue siendo EN1-02; licencia de Caja no se reinicia por sí sola (ADR-007).

---

## 9. Criterio de aceptación de este ADR

- [ ] Prog1 aprueba capas y regla “bootstrap antes de operar”.  
- [ ] Prog2 confirma estados APK y checklist de `ready`.  
- [ ] Queda explícito: **no código** hasta contrato Installation v1 + GO.  

---

*Propuesto 1 ago 2026 — análisis P0 provisioning / instalación integrada.*
