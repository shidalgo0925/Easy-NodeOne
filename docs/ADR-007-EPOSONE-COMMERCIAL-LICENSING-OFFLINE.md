# ADR-007 — Licenciamiento comercial automatizado y continuidad offline

| Campo | Valor |
|-------|-------|
| ID | ADR-007 |
| Título | Licenciamiento comercial automatizado y continuidad offline |
| Estado | **Aprobado (congelado)** — 18 jul 2026 |
| Ámbito | EN1 (Prog1) + EPosOne APK (Prog2) |
| Hito comercial | Inicio de fase comercial EPosOne — 18 jul 2026 |
| Relacionados | [ADR-003 Sync](ADR-003-EPOSONE-SYNC.md) · [ADR-005](ADR-005-EPOSONE-LICENSING-POS.md) · [ADR-006](ADR-006-EPOSONE-OPERATION-VS-ADMIN.md) |
| Implementación vigente | [Licenciamiento y Provisioning V1.0](EPOSONE_LICENSING_PROVISIONING_V1.md) |
| Alcance de este ADR | Decisión arquitectónica; no implementa pagos, portal ni cambios de protocolo |

---

## Contexto

EPosOne ya dispone de la base técnica para operar como POS: provisioning, bootstrap,
sincronización, pedidos, inventario, pagos, operación offline y BackOffice.

La etapa iniciada el **18 de julio de 2026** cambia la prioridad del producto:

> EPosOne debe convertirse en un SaaS de ingresos recurrentes que pueda vender,
> activar y renovar miles de licencias sin aumentar proporcionalmente el trabajo
> administrativo.

No escala un proceso basado en cobros por WhatsApp, revisión manual de transferencias,
envío de códigos comerciales o activaciones realizadas por personal de soporte.

Al mismo tiempo, una interrupción de Internet no puede detener las ventas de un comercio.
La continuidad operativa es una condición del producto, no una excepción.

---

## Principios rectores

1. **Offline First:** vender no depende de una conexión permanente.
2. **Licencia transparente:** el cliente no ejecuta acciones para validar su licencia.
3. **Automatización total:** pago confirmado implica renovación automática e idempotente.
4. **Sync inteligente:** toda comunicación autenticada con EN1 puede refrescar el estado comercial.
5. **Fuente única:** EN1 decide la licencia; la APK conserva una copia local temporal.
6. **Escalabilidad SaaS:** los procesos se diseñan para miles de organizaciones y cajas.
7. **Separación de conceptos:** provisioning identifica el dispositivo; la licencia autoriza la Caja.

> **La Caja es la unidad comercial; EN1 es la fuente de verdad; Sync es el canal; el humano no activa nada.**

---

## Decisiones

### 1. Unidad comercial = Caja

La jerarquía oficial es:

```text
Organización
  └── Sucursal
        └── POS
              └── Caja                    ← unidad de licencia
                    └── Dispositivo       ← reemplazable; consume la licencia de la Caja
```

La licencia:

- pertenece a `organization_id + register_ref`;
- no pertenece al usuario, correo, dispositivo ni instalación de la APK;
- permanece al reemplazar o reinstalar una tablet;
- es consumida por el dispositivo actualmente vinculado a la Caja.

Este ADR **reemplaza** la decisión de ADR-005 que definía el POS como unidad de
licenciamiento. ADR-005 conserva vigencia en su principio de separar dominio, planes y
límites, pero no en la unidad comercial.

### 2. Provisioning y licencia no se mezclan

| Concepto | Responde | Mecanismo |
|----------|----------|-----------|
| Provisioning | ¿Qué dispositivo pertenece a esta Caja? | Código temporal, de un uso, con TTL |
| Licencia | ¿Puede operar comercialmente esta Caja? | Estado emitido por EN1 y cacheado por la APK |
| Permisos | ¿Qué puede hacer este usuario? | RBAC / autorización |

La eliminación de “códigos manuales” se refiere a **códigos comerciales de activación o
renovación**. Los códigos técnicos de provisioning siguen existiendo porque resuelven una
responsabilidad distinta.

### 3. APK pública

La distribución de la APK no requiere intervención de ventas. Debe poder descargarse desde
un canal público oficial.

Publicar la APK no elimina los controles de integridad:

- artefacto firmado;
- checksum y versión publicados;
- canal oficial identificable;
- actualización compatible con rollback;
- ninguna credencial o secreto comercial embebido.

Descargar o instalar la APK no crea una licencia ni reinicia un trial.

### 4. Trial automático

Una Caja elegible recibe trial automáticamente conforme a la política definida en EN1.
La política inicial de producto es **45 días**, configurable en EN1.

Reglas obligatorias:

- el inicio ocurre según la política oficial (`on_first_provision` por defecto);
- `trial_used` impide reiniciar el trial de la misma Caja;
- reinstalar o reemplazar la tablet no reinicia el trial;
- crear otro usuario o cambiar el correo no reinicia el trial;
- EN1 registra inicio, vencimiento y consumo del trial.

El control antiabuso entre organizaciones nuevas requiere señales adicionales de riesgo
(identidad fiscal/comercial, método de pago, historial de dispositivos u otras). Una huella
de dispositivo por sí sola no es prueba suficiente y no debe bloquear clientes legítimos.

### 5. Renovación automática posterior al pago

Flujo comercial oficial:

```text
Cliente elige plan / renovación
  → pasarela procesa el pago
  → EN1 recibe confirmación verificable
  → EN1 registra el evento de cobro de forma idempotente
  → License Manager extiende o activa la licencia de la Caja
  → próxima comunicación autenticada entrega el nuevo snapshot
  → la APK actualiza su License Store local
```

No existe un paso de “copiar código e ingresarlo en la tablet”.

Requisitos del cobro:

- webhook autenticado y verificable;
- idempotencia por proveedor + identificador de transacción;
- conciliación y trazabilidad completa;
- renovación aplicada solo ante estado de pago definitivo;
- reintentos seguros;
- reversos, contracargos y reembolsos representados como eventos, no como edición manual;
- activaciones manuales limitadas a soporte excepcional, autorizadas y auditadas.

Tarjeta, Yappy, ACH y transferencia son adaptadores comerciales. Este ADR no congela un
proveedor de pagos específico.

### 6. Portal Comercial separado de la operación POS

El cliente tendrá un Portal Comercial de autoservicio para:

- empresa y plan;
- Cajas licenciadas;
- estado y vencimiento;
- historial y facturas;
- renovación;
- métodos de pago.

El Portal Comercial pertenece a EN1/plataforma SaaS. No forma parte de la operación diaria
de pedidos, cobros o turnos en la APK.

El BackOffice técnico de `Infraestructura → Licencias` puede mostrar diagnóstico y estado,
pero no debe convertirse en el flujo comercial del cliente.

### 7. Licencia como atributo del protocolo

No se crea una llamada obligatoria exclusiva para validar licencias.

Las respuestas autenticadas de los flujos existentes pueden incluir el mismo snapshot:

- provisioning/config inicial;
- bootstrap;
- sync;
- heartbeat integrado;
- pedidos e inventario sincronizados;
- configuración;
- Facturación Electrónica;
- comprobación de actualizaciones.

El snapshot debe tener un contrato único y versionado. Como mínimo:

```json
{
  "license": {
    "register_ref": "caja-01",
    "status": "active",
    "license_type": "subscription",
    "plan": "eposone-pro",
    "starts_at": "2026-07-18T00:00:00Z",
    "expires_at": "2026-08-18T23:59:59Z",
    "validated_at": "2026-07-18T15:00:00Z",
    "refresh_required_at": "2026-08-17T15:00:00Z",
    "offline_grace_until": "2026-08-17T15:00:00Z",
    "can_operate": true,
    "reason": null,
    "version": 1
  }
}
```

Los nombres y formatos definitivos se congelarán en el contrato HTTP correspondiente.
Todas las rutas deben usar el mismo serializador; no pueden producir interpretaciones
diferentes del estado comercial.

### 8. Heartbeat integrado

Heartbeat es una capacidad transversal, no una pantalla ni una validación comercial
separada.

Cada comunicación autenticada de la tablet puede actualizar en EN1:

- última conexión;
- Caja y dispositivo;
- versión de APK/build;
- plataforma;
- estado de sync;
- último snapshot entregado.

La respuesta puede incluir:

- snapshot de licencia;
- configuración efectiva;
- próxima fecha recomendada de contacto;
- versión mínima/recomendada de la APK.

No debe generarse tráfico artificial si la tablet ya sincroniza con frecuencia. Un
heartbeat liviano solo se justifica durante periodos sin eventos de negocio.

### 9. License Store local

La APK mantiene un License Store local por Caja con el último snapshot aceptado.

Reglas:

- EN1 es la única fuente que emite estado;
- la APK no calcula un trial nuevo ni extiende vencimientos;
- el snapshot se reemplaza solo con una versión válida y más reciente;
- el reloj local no puede conceder más tiempo;
- cambios anómalos del reloj se registran y aplican una política conservadora;
- el almacenamiento debe resistir manipulación casual y estar vinculado a la identidad
  provisionada de la Caja/dispositivo;
- borrar datos o reinstalar la APK obliga a recuperar estado desde EN1, no crea derechos.

### 10. Grace Offline Window

La licencia no se valida en cada venta.

La APK puede operar con el último snapshot válido hasta `offline_grace_until`. La duración
es una política configurable de EN1; no se hardcodea en la APK. El valor exacto se aprueba
como política comercial separada.

Dentro de la ventana:

- crear y modificar pedidos;
- cobrar;
- abrir y cerrar turnos;
- imprimir;
- almacenar eventos en la cola local;
- seguir vendiendo aunque no haya Internet.

La Facturación Electrónica puede quedar pendiente o seguir su propio modo de contingencia.
Un fallo de FE no equivale a una licencia inválida.

Al aproximarse el límite, la APK muestra avisos progresivos sin interrumpir la venta:

1. informativo;
2. advertencia;
3. crítico;
4. vencido conforme a la política recibida.

Después de `offline_grace_until`, la conducta debe venir explícitamente en el snapshot o en
la política versionada. No se inventa localmente. El bloqueo, si aplica, se evalúa al entrar
a una operación controlada y **nunca a mitad de un cobro ya iniciado**.

### 11. Estados y transiciones

Estados comerciales mínimos:

```text
unlicensed
pending
trial
active
courtesy
promotion
demo
perpetual
expired
suspended
cancelled
```

`can_operate` es la decisión efectiva emitida por EN1. La APK puede mostrar el estado, pero
no reconstruye reglas comerciales a partir del nombre del estado.

Toda transición registra:

- organización y Caja;
- estado anterior y nuevo;
- motivo;
- actor o evento automático;
- pago relacionado, cuando corresponda;
- fecha efectiva;
- timestamp de auditoría.

---

## Fuente de verdad y consistencia

| Dato | Fuente oficial |
|------|----------------|
| Plan, precio, suscripción | EN1 License Manager / Billing |
| Pago y factura | EN1 Billing + proveedor |
| Estado efectivo de licencia | EN1 License Manager |
| Vínculo dispositivo ↔ Caja | EN1 Provisioning |
| Copia para operación offline | License Store de la APK |
| Permisos del usuario | EN1 RBAC |

Si dos respuestas de EN1 contienen licencia, ambas deben provenir del mismo servicio y
serializador. Ningún módulo de pedidos, FE o inventario implementa reglas de licencia.

---

## Responsabilidades

### Prog1 — EN1

1. License Manager por `organization_id + register_ref`.
2. Política de trial, grace, suspensión y renovación.
3. Contrato único de snapshot dentro de bootstrap/sync/config.
4. Registro de heartbeat y salud de dispositivos.
5. Portal Comercial y facturación.
6. Adaptadores de pago, webhooks e idempotencia.
7. Renovación automática posterior al pago.
8. Auditoría y métricas comerciales.
9. Herramientas excepcionales de soporte con RBAC y trazabilidad.

### Prog2 — EPosOne APK

1. License Store local.
2. Consumir el snapshot recibido en comunicaciones existentes.
3. Mostrar estado, días restantes, última validación y próxima requerida.
4. Avisos progresivos antes del límite offline.
5. Mantener operación offline dentro de la autorización recibida.
6. No crear un endpoint o botón obligatorio de “validar licencia”.
7. No hardcodear trial, grace, planes ni precios.
8. Reportar versión, estado y última sync mediante tráfico normal.

---

## Dashboard comercial EN1

Las métricas son administrativas para el proveedor SaaS, no para el cajero:

- Cajas licenciadas activas;
- trials activos y conversión;
- próximas a vencer;
- vencidas/suspendidas;
- MRR/ARR y renovaciones fallidas;
- tablets sin conexión;
- última conexión;
- distribución de versión de APK;
- grace próximo a agotarse;
- pagos pendientes de conciliación;
- excepciones manuales y su actor.

Las métricas derivan de eventos auditables; no se mantienen como contadores manuales.

---

## Modos de falla

| Falla | Comportamiento |
|-------|----------------|
| Sin Internet dentro del grace | Operación completa; eventos quedan en cola |
| EN1 temporalmente caído | Igual que sin Internet; no invalidar snapshot vigente |
| Pago confirmado, webhook retrasado | Reintento/conciliación; no duplicar renovación |
| Respuesta sin bloque `license` | Conservar último snapshot; registrar diagnóstico |
| Snapshot antiguo o fuera de orden | Ignorar si su versión/fecha es anterior |
| Reloj local retrocede | No ampliar derechos; registrar anomalía |
| Reinstalación o nuevo dispositivo | Reprovisionar y recuperar licencia de la Caja |
| FE sin conexión | Flujo de contingencia FE; no confundir con licencia |

---

## Decisiones rechazadas

- Licenciar usuario, correo o dispositivo.
- Reiniciar trial al reinstalar APK o crear otra cuenta.
- Validar licencia contra EN1 en cada venta.
- Exigir Internet para cobrar.
- Renovar mediante códigos comerciales ingresados en la tablet.
- Crear reglas de planes o precios dentro de la APK.
- Usar FE como única forma de refrescar licencia.
- Conceder días adicionales por cálculo local.
- Activaciones manuales como proceso comercial normal.
- Mezclar Portal Comercial con el menú operativo del POS.

---

## Consecuencias

### Positivas

- Renovación y activación sin intervención humana.
- Reemplazo de tablet sin perder la licencia.
- Continuidad de ventas ante fallos de conectividad.
- Un solo estado comercial consistente en todos los canales.
- Menor carga de soporte al crecer.
- Métricas suficientes para soporte preventivo y gestión SaaS.

### Costos y riesgos

- Billing y webhooks requieren idempotencia, conciliación y auditoría rigurosas.
- La operación offline obliga a diseñar expiración, reloj y almacenamiento resistente.
- La política antiabuso no puede basarse únicamente en correo o dispositivo.
- Debe versionarse el contrato de licencia para evitar incompatibilidades con APK antiguas.
- La suspensión comercial requiere UX cuidadosa y reglas legales/comerciales explícitas.

---

## Fuera de alcance

- Elegir proveedor definitivo de pagos.
- Definir precios y catálogo final de planes.
- Fijar en este ADR la cantidad exacta de días de grace.
- Implementar el Portal Comercial.
- Implementar License Store en la APK.
- Modificar APIs, base de datos, sync, provisioning o licencias existentes.
- Definir el tratamiento fiscal/contable específico de cada país.

---

## Criterios de aceptación arquitectónica

La implementación futura cumple este ADR cuando:

1. toda licencia se identifica por Organización + Caja;
2. provisioning y licenciamiento permanecen separados;
3. ningún flujo normal exige código comercial manual;
4. un pago confirmado renueva de forma automática, idempotente y auditable;
5. bootstrap/sync entregan un snapshot único y versionado;
6. la APK opera offline dentro de una ventana emitida por EN1;
7. la APK no calcula ni extiende derechos comerciales;
8. reinstalar o cambiar tablet conserva la licencia de la Caja;
9. el Portal Comercial está separado de la operación del POS;
10. EN1 puede medir licencia, conexión, versión y salud sin llamadas de soporte.

---

## Orden recomendado de implementación

### Fase A — Contrato y continuidad

1. Congelar contrato HTTP del snapshot.
2. Incorporar snapshot al sync/bootstrap existente.
3. Implementar License Store APK.
4. Implementar avisos y Grace Offline Window.
5. Añadir telemetría/heartbeat integrado.

### Fase B — Automatización comercial

1. Consolidar License Manager y eventos auditables.
2. Implementar Portal Comercial.
3. Integrar primera pasarela y webhook idempotente.
4. Renovación automática + conciliación.
5. Dashboard comercial y alertas preventivas.

No se inicia Fase B sin pruebas E2E de Fase A para pérdida de red, reloj, reinstalación,
respuestas fuera de orden y recuperación posterior.

