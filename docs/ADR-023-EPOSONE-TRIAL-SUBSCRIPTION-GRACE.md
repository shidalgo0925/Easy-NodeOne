# ADR-023 — Modelo de Trial, Suscripción y Grace Period (EPosOne)

| Campo | Valor |
|-------|--------|
| ID | **ADR-023** |
| Título | Trial · Suscripción activa · Grace Period · Suspensión (EPosOne) |
| Estado | **Propuesto** — 2 ago 2026 · pendiente aprobación Ana / Prog1 / producto |
| Fecha | 2026-08-02 |
| Producto | EPosOne (política comercial); motor en **EN1** |
| Arquitectura | EN1 + EPosOne |
| Autor | ETS |
| Relacionados | [ADR-024 Asistente de Inicio](ADR-024-EPOSONE-START-ASSISTANT.md) ·  [`EN1_PLATFORM_CONSTITUTION_V1.md`](EN1_PLATFORM_CONSTITUTION_V1.md) · [ADR-014](ADR-014-SUBSCRIPTION-REGISTRY.md) · [ADR-016](ADR-016-COMMERCIAL-LICENSING-V2-ENTITLEMENT.md) · [ADR-017](ADR-017-CUSTOMER-ENTRY-POINT-PRODUCT-PORTAL.md) · [ADR-021](ADR-021-EPOSONE-INSTALLATION-LIFECYCLE.md) · [ADR-022](ADR-022-EN1-MULTIPRODUCT-COMMERCIAL-MODEL.md) |
| Numeración | **No** es ADR-018 (ese ID es [Release Management](ADR-018-RELEASE-MANAGEMENT.md)). El borrador de producto titulado “ADR-018 Trial…” se formaliza aquí como **ADR-023**. |
| No implementa | Checkout, pasarela, jobs de notificación, UI de avisos — solo política y modelo de estados |

---

## 1. Contexto

EPosOne es un producto SaaS cuya instalación, licenciamiento y operación comercial son administrados por **EN1**.

El Trial permite que el cliente valide el producto **completo** antes de pagar, sin romper la continuidad operativa ni complicar el proceso comercial.

La política equilibra:

- experiencia del cliente;
- conversión a pago;
- protección de ingresos;
- simplicidad operativa.

Alineado a la Constitución EN1: el cliente **configura una suscripción**; la **licencia técnica** es el resultado. EN1 es la única autoridad del ciclo comercial.

---

## 2. Decisión

Se adopta un ciclo comercial compuesto:

```text
TRIAL
  ↓  (pago confirmado)
ACTIVE
  ↓  (vence sin pago / no renueva)
GRACE  (= PAST_DUE en Subscription Registry)
  ↓  (fin de grace sin pago)
SUSPENDED
  ↓  (pago confirmado)
ACTIVE
```

Estados terminales / especiales: `REVOKED`, `EXPIRED` (ver §12).

---

## 3. Trial

### Duración

**15 días calendario.**

### Cuándo inicia el reloj (decisión)

El Trial **inicia** cuando el usuario elige explícitamente **«Probar 15 días»** en el Portal / flujo comercial EN1 (tras cuenta + organización; ver Constitución).

En ese momento EN1:

1. crea/activa la **suscripción** EPosOne en estado `TRIAL`;
2. materializa **entitlement** del plan **recomendado** (o el configurado);
3. habilita generación de recursos y códigos de aprovisionamiento según el plan.

**No** se exige tarjeta de crédito.

**No** se usa como reloj principal: “primer dispositivo aprovisionado”.  
Motivo: evitar trials indefinidos si nunca instalan, y alinear el CTA comercial «Probar» con el contador.

El aprovisionamiento del primer dispositivo ocurre **dentro** de la ventana de Trial (o de Active), no lo dispara.

### Durante el Trial

Producto **completo** del plan seleccionado/recomendado. **Sin** restricciones funcionales artificiales.

Puede: vender, abrir/cerrar cajas, sincronizar, imprimir, administrar productos y cajeros, reportes, y todas las capacidades del plan.

El Trial evalúa el producto real, no una versión reducida.

### Reloj y org

La **Organización existe antes** del Trial (Constitución). Crear org ≠ iniciar Trial.  
Sin pulsar «Probar» / «Comprar», no corre el contador de 15 días.

---

## 4. Notificaciones

EN1 notifica automáticamente (canal: email / in-app Portal — implementación posterior).

| Día | Mensaje | CTA |
|-----|---------|-----|
| **10** | Restan 5 días de prueba | Activar suscripción |
| **13** | Tu período de prueba termina en 2 días | Activar suscripción |
| **15** | Fin de Trial | Si pagó → Active; si no → Grace |

Si el cliente paga durante el Trial:

```text
TRIAL → ACTIVE
```

- La autorización cambia automáticamente.
- **No** reinstalar.
- **No** pierde información.
- **No** requiere nuevo código de aprovisionamiento.

---

## 5. Grace Period

Si al finalizar el Trial (o al vencer un ciclo de pago) **no** hay pago confirmado:

Estado operativo: **GRACE**  
Mapeo Subscription Registry (ADR-014): **`PAST_DUE`**

Duración: **7 días calendario.**

Durante Grace:

- el sistema **sigue funcionando**;
- avisos **persistentes**;
- puede pagar en cualquier momento → `ACTIVE`.

Objetivo: no cortar un negocio por fin de semana, feriado, demora bancaria o aprobación administrativa.

---

## 6. Suspensión

Al terminar Grace sin pago:

Estado: **`SUSPENDED`**

Efecto:

- **No** permite iniciar nuevas operaciones comerciales (venta/caja según enforcement de licencia).
- **Conserva** productos, clientes, ventas, configuraciones, historial.
- **No** elimina datos.

---

## 7. Reactivación

Pago confirmado:

```text
SUSPENDED → ACTIVE
```

(o `PAST_DUE`/`GRACE` → `ACTIVE`)

- Reactivación **inmediata** (cuando EN1 confirma el pago).
- No reinstalar, no re-registrar, no nuevo código.

---

## 8. Facturación

La facturación **inicia al finalizar el Trial** (primer cobro = fin del Trial o al activar suscripción de pago antes).

Ejemplo:

```text
01 Ago  — inicio Trial («Probar»)
15 Ago  — fin Trial / primer pago
16 Ago  — inicio primer ciclo mensual
16 Sep  — siguiente vencimiento
```

**No** se cobran los días del Trial.

---

## 9. Política de datos

El vencimiento o suspensión de la autorización **nunca elimina** información.

Los datos pertenecen al cliente.  
La suspensión solo afecta **autorización para operar**.

---

## 10. Modalidades y planes

Esta política aplica a planes comerciales:

- Starter  
- Business  
- Enterprise  

en modalidad **Integrada** (“Sincronizado con EN1”) y, por defecto, también cuando el configurador eligió operar “solo en esta tablet”, **si** la suscripción fue creada vía Trial EN1.

**Standalone / solo tablet** no es un plan distinto (Constitución). Es modalidad de despliegue.

Política por defecto para activación **sin** pasar por Trial EN1 (p. ej. contrato standalone puro fuera del flujo Portal):

- sin Trial automático;
- se activa en `ACTIVE` al contratarse.

Esa variante podrá revisarse después; no redefine Starter/Business/Enterprise.

---

## 11. Beneficios

**Comerciales:** menor barrera; conversión; prueba completa; sin tarjeta.  
**Operativos:** sin reinstalación, migración ni pérdida de datos.  
**Técnicos:** Trial y Active **no** diferencian capacidades de producto; solo cambia el **estado** de suscripción/autorización.

---

## 12. Estados

### Suscripción (ADR-014 — fuente de verdad comercial)

| Estado ADR-014 | Uso en esta política |
|----------------|----------------------|
| `TRIAL` | Período de prueba 15 días |
| `ACTIVE` | Suscripción de pago al día |
| `PAST_DUE` | **Grace** (7 días) |
| `SUSPENDED` | Sin operar tras grace |
| `CANCELLED` / `EXPIRED` | Fin de relación / vencido sin reactivar |
| `PENDING` | Prepago / pendiente de activación (si aplica) |

### Licencia técnica / entitlement (resultado)

Hereda el estado efectivo de la suscripción/entitlement.  
Vocabulario operativo permitido en UI/docs de producto:

`TRIAL` · `ACTIVE` · `GRACE` · `SUSPENDED` · `REVOKED` · `EXPIRED`

donde **`GRACE` ≡ `PAST_DUE`** en el registry.

No crear un segundo motor de estados desacoplado del Subscription Registry.

---

## 13. Principios

1. El Trial demuestra el valor **completo** de EPosOne.  
2. El cliente **nunca** pierde información por falta de pago.  
3. Las transiciones de estado son **automáticas** (jobs EN1).  
4. La autorización controla el **acceso**, no los datos.  
5. Trial → Suscripción de pago **sin** intervención técnica en dispositivo.  
6. **EN1** es la única autoridad del ciclo de vida comercial y de licenciamiento de EPosOne.  
7. El cliente no “compra una licencia”; configura/activa una **suscripción** (Constitución).

---

## 14. Relación con instalación (ADR-021)

- Códigos de aprovisionamiento: **después** de suscripción Trial o Active + recursos (p. ej. caja).  
- Installation lifecycle no redefine el reloj comercial; opera bajo una suscripción ya `TRIAL` o `ACTIVE` (o `PAST_DUE` en grace).

---

## 15. Fuera de alcance (este ADR)

- Implementación de pasarela / webhooks de pago.  
- Templates exactos de email.  
- Enforcement fino en APK offline (ver ADR-007; coherente: grace/suspend lo decide EN1 al sync/heartbeat).  
- Política fiscal/facturas legales.

---

## 16. Criterio de aprobación

Aprobado cuando producto confirma:

1. Reloj Trial = CTA **«Probar 15 días»** (no primer device).  
2. Grace = 7 días = `PAST_DUE`.  
3. Trial = producto completo del plan.  
4. Sin borrado de datos en suspensión.  
5. ID **ADR-023** (no reutilizar 018).

---

*Propuesto 2 ago 2026 — política Trial/Grace EPosOne. Sin implementación.*
