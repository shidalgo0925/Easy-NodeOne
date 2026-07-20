# Hito 2.6 — Diagnóstico y Observabilidad (EN1 + EPosOne)

| Campo | Valor |
|-------|--------|
| Estado | **Planificado** — 19 jul 2026 (propuesta Analista, adoptada V7) |
| Objetivo | Soporte SaaS sin SSH/logs manuales |
| Antes de | Implementación Motor Comercial V6 (algoritmos) |
| Relacionado | B-R1-16 Sync demostrable · B-R1-19 Observabilidad · B-R1-02 Devices |
| E2E cajeros | [`EN1_EPOSONE_E2E_CHECKLIST_V1.md`](EN1_EPOSONE_E2E_CHECKLIST_V1.md) puede correr en paralelo |

---

## Por qué existe

No agrega venta. Reduce tiempo de soporte e implantación: en segundos se distingue conectividad vs sync vs licencia vs bootstrap vs datos.

---

## Alcance mínimo (DoD)

### A. Pantalla diagnóstico en dispositivo (EPosOne) — Prog2

| Campo | Requerido |
|-------|-----------|
| Estado provisioning | ✅ |
| Último bootstrap (fecha + resultado) | ✅ |
| Último sync (fecha + resultado) | ✅ |
| Eventos pendientes (cola) | ✅ |
| Estado de la cola | ✅ |
| Último error (sanitizado) | ✅ |
| Versiones: APK, esquema local, bootstrap, políticas, cashiers | ✅ |
| Estado licencia (snapshot) | ✅ |
| Conectividad con EN1 | ✅ |

### B. Panel técnico en EN1-POS (Back Office) — Prog1

| Capacidad | Requerido |
|-----------|-----------|
| Lista dispositivos + último seen / versión APK | ✅ |
| Último bootstrap / sync por device | ✅ |
| Eventos pendientes / fallidos + reintento / replay | ✅ |
| Licencia por caja (vigencia, estado) | ✅ |
| Versiones de políticas / cashiers / catálogo vistas | ✅ |
| Revocar / reprovisionar (flujo existente endurecido) | ✅ |
| Bitácora auditoría acciones sensibles (mínimo device/sync/license) | ✅ |

### C. Fuera de 2.6 (no bloquear)

- BI / métricas de negocio  
- APM completo  
- Alertas push (puede ser fase 2 del hito)

---

## Criterio de cierre

1. Un soporte puede explicar un incidente **solo** con panel EN1 + pantalla diagnóstico APK.  
2. Al menos 1 caso E2E: forzar error de sync → visible en ambos lados → reintento → OK.  
3. Documentado en handoff + DoD 11 puntos aplicables (Flutter N/A en panel solo EN1 y viceversa).

---

## Orden respecto al Motor V6

```text
E2E Hito 2.5 (checklist A–E)
  → Hito 2.6 Observabilidad (mínimo operable)
  → Freeze contratos V6 + T1
  → Motor Totales / Comercial
```

2.6 puede solaparse con E2E 2.5 si no roba foco a la tablet; **no** se salta antes de declarar infra “terminada”.
