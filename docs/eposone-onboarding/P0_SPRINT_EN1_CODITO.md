# EPosOne P0 — Sprint EN1 (CODITO)

| Campo | Valor |
|-------|--------|
| ID | **EPOSONE-P0-SPRINT-EN1-CODITO** |
| Emisor | Ana · instrucciones CODITO |
| Estado | **Oficial** — 6 ago 2026 |
| Audiencia | CODITO (EN1) |
| Contexto | [P0_CONTEXTO_EN1_LOCAL.md](P0_CONTEXTO_EN1_LOCAL.md) |
| Pack | [README.md](README.md) |

Instrucciones de sprint para cerrar los bloqueos que impiden declarar terminado el onboarding P0.

---

## 1. Estado de partida

**Ya implementado (base del sprint):**

- Portal de Instalación (mínimo)
- Login Onboarding / Session
- Issue Code
- Distribución de la APK en EN1 (`/static/apk/eposone/EPosOne.apk`)

El sprint se concentra en **P0.17–P0.30** y el gate de aceptación (§4).

---

## 2. Ítems del sprint + mapa EN1

| ID | Título | Criticidad | Estado EN1 | Doc / ancla |
|----|--------|------------|------------|-------------|
| **P0.17** | Reaprovisionamiento | CRÍTICO | Plan listo · **código incompleto** | [P0_17_REPROVISIONING.md](P0_17_REPROVISIONING.md) |
| **P0.18** | Asistente instalación Android + QR ayuda | CRÍTICO | Plan listo · **UI no existe** | [P0_18_ANDROID_INSTALL_ASSISTANT.md](P0_18_ANDROID_INSTALL_ASSISTANT.md) |
| **P0.19** | Organization Context Resolver | CRÍTICO | **Hecho** (ADR-029) · falta E2E gate | [ORGANIZATION_RESOLVER_V2.md](ORGANIZATION_RESOLVER_V2.md) · [ADR-029](../ADR-029-ORGANIZATION-CONTEXT-RESOLVER-V2.md) |
| **P0.20** | Modelo comercial sin precios | Alto | **Hecho** en `/start` | [ADR-028](../ADR-028-EPOSONE-PLAN-DEFAULTS-COMMERCIAL-OVERRIDES.md) |
| **P0.21** | Recursos por defecto del plan | Alto | **Parcial** (defaults + seed mínimo; no materializa N POS) | ADR-028 · commercial_plans |
| **P0.22** | Overrides comerciales | Alto | Contrato ADR-028 · **falta UI Admin + audit reason/contract** | [COMMERCIAL_OVERRIDE_MODEL.md](COMMERCIAL_OVERRIDE_MODEL.md) |
| **P0.23** | Portal = admin lifecycle devices | Alto | **Parcial** (código/QR; falta cupos + lista + reprovision) | [INSTALLATION_PORTAL_V2.md](INSTALLATION_PORTAL_V2.md) |
| **P0.24** | Password UX | Medio | Pendiente | `/start` |
| **P0.25** | Verificación de correo | Medio | Pendiente | post-`/start` → portal/APK |
| **P0.26** | Descarga APK con estados | Medio | Pendiente (hoy CTA directo) | solapa P0.18 |
| **P0.27** | UX instalación paso a paso | Medio | Pendiente | solapa P0.18 |
| **P0.28** | User Bearer ≠ Device Bearer | Crítico (mantener) | **Contratos Gate1** · no mezclar | [GATE1_HTTP_FROZEN_FOR_LOCAL.md](GATE1_HTTP_FROZEN_FOR_LOCAL.md) |
| **P0.29** | Auditoría completa | Alto | **Parcial** (events device); ampliar checklist Ana | AuditService / domain events |
| **P0.30** | Validación E2E Flyer → Primera venta | Gate | Pendiente (EN1 + LOCAL) | §4 |

### Orden de implementación recomendado

1. P0.17 → 2. P0.18 (+26/27) → 3. P0.23 (portal lifecycle) → 4. P0.22 → 5. P0.21 gaps → 6. P0.24/25 → 7. P0.29 → 8. P0.30  
P0.19 / P0.20 / P0.28: validar en E2E, no reabrir salvo regresión.

---

## 3. Detalle normativo (Ana)

### P0.17 — Reaprovisionamiento (CRÍTICO)

**Objetivo:** ciclo de vida completo; el comercio recupera operación sin soporte técnico.

**Casos obligatorios:** cambio de tablet · reinstalación APK · factory reset · perdido · robado · reemplazado · Device Bearer comprometido.

```text
Login → Org → Portal Instalación → Dispositivos → Reaprovisionar
  → Invalidar Device Bearer anterior → Nuevo Provision Code
  → Register → Bootstrap → Operar
```

**Reglas:** nunca reutilizar bearer revocado · auditoría completa · historial de dispositivos · limitar activos por entitlements · no perder relación con la org.

→ Plan: [P0_17_REPROVISIONING.md](P0_17_REPROVISIONING.md) · lifecycle [DEVICE_LIFECYCLE_V1.md](DEVICE_LIFECYCLE_V1.md).

### P0.18 — Asistente de instalación Android (CRÍTICO)

**Objetivo:** mínimo abandono al instalar APK (dolor real de prueba).

| Paso | Contenido |
|------|-----------|
| 1 | Cuenta creada |
| 2 | Correo verificado |
| 3 | Preparar descarga + progreso |
| 4 | Descargar APK + progreso |
| 5 | Instalar; si Android bloquea → guía visual |

**Ayuda OEM:** Samsung · Xiaomi · Redmi · Honor · Huawei · Motorola · Realme · Otros.

**QR de ayuda:** independiente del QR comercial y del QR técnico. Solo guía / video / FAQ / soporte. **Nunca** re-descargar APK.

→ Plan: [P0_18_ANDROID_INSTALL_ASSISTANT.md](P0_18_ANDROID_INSTALL_ASSISTANT.md).

### P0.19 — Resolver de organización (CRÍTICO)

Prioridad:

1. `organization_id` explícito  
2. Organización recién creada (`pending_initial_*`)  
3. Organización seleccionada  
4. Última organización  
5. Selector  
6. Única organización  

**Nunca** reutilizar automáticamente `last_selected` si hay creación reciente vigente.

### P0.20 — Modelo comercial

Sin precios en onboarding. Solo: Standalone · Starter · Business · Enterprise. Precio = contrato comercial (asesor/gerencia).

### P0.21 — Recursos por defecto

Cada plan crea automáticamente: POS incluidos · sucursales · features · licencias. Sin intervención admin.

### P0.22 — Overrides

No modificar el plan. Solo diferencias autorizadas por Gerencia (POS/sucursales/módulos/descuentos/vigencia), **auditadas**.

### P0.23 — Portal de instalación

Administrador oficial del lifecycle. Debe mostrar: plan · modalidad · recursos · POS contratados/instalados/disponibles · dispositivos · estado · provision code · QR técnico · reaprovisionamiento. **No** es solo descarga.

### P0.24 — Password

Fortaleza · sugerencia · generador · validación en vivo · requisitos visibles.

### P0.25 — Verificación de correo

No continuar automáticamente. Tras verificar → Portal + descarga APK.

### P0.26 / P0.27 — Descarga y UX install

Estados: preparando · descargando · finalizada. Luego guía paso a paso (sin asumir conocimiento técnico).

### P0.28 — Seguridad de tokens

| Bearer | Uso |
|--------|-----|
| **User** | Login · org · portal · administración |
| **Device** | Register · Bootstrap · operación POS |

Nunca intercambiarlos.

### P0.29 — Auditoría

Registrar: creación org · plan · suscripción · overrides · emisión códigos · register · bootstrap · reaprovisionamiento · reemplazo · revocaciones.

### P0.30 — E2E

```text
Flyer → QR comercial → /start → Cuenta → Contraseña → Correo verificado
  → Portal → Descarga APK → Instalación guiada → Register → Bootstrap
  → PIN → Abrir Caja → Primera Venta
```

No cerrar el sprint sin validar este recorrido.

---

## 4. Gate de aceptación (EN1 P0 terminado)

El sprint P0 EN1 se considera **terminado** cuando:

1. El Organization Resolver selecciona correctamente la organización recién creada.  
2. El reaprovisionamiento cubre todo el ciclo de vida del dispositivo (casos P0.17).  
3. El Asistente Android permite completar la instalación aunque Android bloquee la APK al inicio.  
4. El Portal administra dispositivos y recursos contratados (P0.23).  
5. Planes sin precios; overrides permiten a Gerencia ajustar lo negociado sin tocar el plan base.  
6. Un usuario completa Flyer → Primera venta **sin asistencia técnica**, salvo la confirmación de instalación que exige Android.

---

## 5. Restricciones de frontera

**CODITO / EN1 no** mueve lógica de operación del POS a EN1.

| EN1 | LOCAL |
|-----|-------|
| Identidad · orgs · suscripciones · planes · entitlements · overrides | Register · Bootstrap |
| Portal · aprovisionamiento · reaprovisionamiento | Licencias técnicas · PIN |
| Descarga APK · asistente Android · auditoría | Caja · operación |

---

## 6. Próximo GO de código

**Solo P0.17** (API + portal + contrato HTTP LOCAL), en chat dedicado.  
P0.18 y siguientes: chats separados (1 chat = 1 tarea).
