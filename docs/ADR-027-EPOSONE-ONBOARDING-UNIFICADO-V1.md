# ADR-027 — Onboarding unificado EPosOne V1 (Sin “Modo Local” de usuario)

| Campo | Valor |
|-------|--------|
| ID | **ADR-027** |
| Título | Onboarding e instalación unificados — Standalone / Connected bajo EN1 |
| Estado | **Aprobado (contrato P0)** — 6 ago 2026 · **Sin implementación de código en este ADR** |
| Ámbito | EN1 (comercial + Device API) · EP1/APK (LOCAL implementa UI) |
| Relacionados | [ADR-014](ADR-014-SUBSCRIPTION-REGISTRY.md) · [ADR-021](ADR-021-EPOSONE-INSTALLATION-LIFECYCLE.md) · [ADR-023](ADR-023-EPOSONE-TRIAL-SUBSCRIPTION-GRACE.md) · [ADR-024](ADR-024-EPOSONE-START-ASSISTANT.md) · [ADR-028](ADR-028-EPOSONE-PLAN-DEFAULTS-COMMERCIAL-OVERRIDES.md) · **[ADR-031](ADR-031-EN1-COMMERCIAL-DOMAIN-ARCHITECTURE.md)** · [ADR-001](ADR-001-EPOSONE-STANDALONE.md) · [ADR-003](ADR-003-EPOSONE-SYNC.md) |
| Pack contratos | [`eposone-onboarding/`](eposone-onboarding/README.md) |
| Enmienda | **7 ago 2026 — ADR-031:** registro comercial ≠ implementación; Standalone difiere árbol operativo |

---

## Enmienda ADR-031 (7 ago 2026)

```text
Cliente → Organización → Contrato → Suscripción EPosOne → Modalidad
                                                         ├─ Standalone (comercial activo; ops diferida OK)
                                                         └─ Connected (comercial + sync; implementación cuando se active)
```

| Antes | Ahora |
|-------|--------|
| Onboarding unificado = siempre camino a operar con min árbol | Unificado en **registro EN1**; implementación es fase aparte |
| Standalone = cuenta+org+sub sin sync | + puede **no** materializar árbol Sucursal→POS→Caja hasta implementación |

**Sigue válido:** una sola APK; no “Modo Local” sin EN1; Connected vs Standalone = sync, no otro producto.

---

## Contexto

Existían dos narrativas en conflicto:

1. **First Start / ADR-003 “Modo Local”:** crear negocio en la APK **sin EN1**.  
2. **Embudo `/start` + Plan Maestro Onboarding:** todo cliente se registra en EN1; Standalone = sin sync cloud, **no** “sin EN1”.

Eso duplicaba caminos y confundía Manual, LOCAL y soporte.

---

## Decisión

### 1. Modelo de producto oficial

```text
Cliente EN1 → Organización → Contrato → Suscripción EPosOne → Modalidad
                                                         ├─ Standalone
                                                         └─ Connected
```

| Modalidad | Significa | No significa |
|-----------|-----------|--------------|
| **Standalone** | Registro comercial en EN1; **sin sincronización cloud operativa** diaria; implementación operativa puede diferirse | “Sin EN1” / APK huérfana |
| **Connected** | Mismo registro comercial + **sync** cuando la implementación esté activa | Otro producto / otra APK |

- **Una sola APK.**  
- **EN1 es el único punto de entrada comercial** (`/start` / portal).  
- Se **elimina “Modo Local” como flujo de usuario** de onboarding/instalación.

### 2. Relación con ADR previos

| ADR | Efecto |
|-----|--------|
| **ADR-031** | **Prevalece** en dominio comercial: Cliente/Contrato; registro ≠ implementación; Standalone puede diferir árbol operativo |
| **ADR-014** | Modalidad comercial se ancla a suscripción/entitlement (enmienda; bajo Contrato) |
| **ADR-003** | “Modo Local / Plataforma” como **caminos de onboarding de usuario** → **supersedidos** por este ADR. El concepto técnico de sync on/off permanece como **comportamiento de modalidad** |
| **ADR-001** | EPosOne sigue siendo producto; “vivir solo” se reinterpreta como **Standalone bajo EN1**, no APK sin registro |
| **ADR-004** | “Vincular Local→Plataforma” deja de ser el upsell principal de onboarding; el upsell es **Standalone → Connected** (cambio de modalidad / sync), sin reinstalar |
| **ADR-021** | Sigue vigente para estados de instalación APK; se alinea con [Device Lifecycle](eposone-onboarding/DEVICE_LIFECYCLE_V1.md) |
| **First Start V4** | Caminos `create_business` (sin EN1) y copy “Modo Local” → **no oficiales** para producto; LOCAL no los implementa como onboarding |

### 3. Ciclo único de incorporación

```text
Nuevo negocio → Cliente EN1 → Organización → Contrato → Plan/Suscripción
              → (fase) Implementación → Provision → Bootstrap → PIN → Operar
```

El registro comercial puede completarse **antes** de la implementación operativa (ADR-031). Los caminos A–D de onboarding de dispositivo siguen Onboarding Contract V2 cuando arranca la fase de implementación.

### 4. Cuatro caminos oficiales (solo estos)

| ID | Nombre | Entrada |
|----|--------|---------|
| **A** | Crear negocio | `/start` (web) → portal → APK provision |
| **B** | Tengo cuenta | Login EN1 (resuelve org/suscripción/recursos) → provision/restore |
| **C** | Activar mediante código | Código o QR→código → register → bootstrap |
| **D** | Restaurar instalación | Login → org → POS/caja → bootstrap → operar |

**No existe** un quinto flujo “Local / sin EN1”.

### 5. QR, Login, Restore

Definidos en el pack:

- [QR Contract](eposone-onboarding/QR_CONTRACT_V1.md) — QR solo entrega **provisioning code**  
- [Login Contract](eposone-onboarding/LOGIN_CONTRACT_V1.md) — login ≠ solo auth  
- [Restore Contract](eposone-onboarding/RESTORE_CONTRACT_V1.md)

### 6. Licenciamiento (criterio único)

- **Trial: 15 días**  
- **Grace: 7 días**  
- No introducir un tercer período en este P0  

---

## Consecuencias

| Positivo | Riesgo |
|----------|--------|
| Un Manual / un asistente APK / un soporte | Clientes lab que usaban Local puro necesitan camino A/B |
| Reutiliza register/bootstrap/license | Exponer `modality` en Device API (P1 código) |
| Standalone comercial alineado a `/start` | ADR-004 copy “Vincular” a actualizar en P1 docs |

---

## Fuera de alcance de este ADR (P0)

- Código EN1 o APK  
- Hosting de APK en EN1  
- Pasarela de pago  
- Implementación UI portal  

---

## Historial

| Fecha | Nota |
|-------|------|
| **2026-08-06** | P0 contrato — Onboarding unificado; elimina Modo Local como flujo de usuario |
