# ADR-031 — EN1 Commercial Domain Architecture

| Campo | Valor |
|-------|--------|
| ID | **ADR-031** |
| Título | Modelo Comercial de EN1 — Arquitectura Base (Dominio Comercial) |
| Estado | **PROPOSED** — pendiente aprobación Arquitectura / Ana / Prog1 |
| Fecha | Agosto 2026 |
| Autor | Arquitectura EN1 |
| Implementación | **NO autorizada** hasta aprobación formal |
| Nota de numeración | El borrador de Arquitectura se etiquetó “ADR-029”; en este repo **ADR-029** ya es [Organization Context Resolver](ADR-029-ORGANIZATION-CONTEXT-RESOLVER-V2.md). Este ADR queda como **031**. |
| Complementa | [EN1_MODELO_COMERCIAL_V1.md](EN1_MODELO_COMERCIAL_V1.md) |
| A enmendar *después* de aprobación | [ADR-022](ADR-022-EN1-MULTIPRODUCT-COMMERCIAL-MODEL.md) · [ADR-014](ADR-014-SUBSCRIPTION-REGISTRY.md) · [ADR-016](ADR-016-COMMERCIAL-LICENSING-V2-ENTITLEMENT.md) · [ADR-024](ADR-024-EPOSONE-START-ASSISTANT.md) · [ADR-027](ADR-027-EPOSONE-ONBOARDING-UNIFICADO-V1.md) · [ADR-028](ADR-028-EPOSONE-PLAN-DEFAULTS-COMMERCIAL-OVERRIDES.md) · [ADR-017](ADR-017-CUSTOMER-ENTRY-POINT-PRODUCT-PORTAL.md) |

---

## 1. Objetivo

Definir el **dominio comercial oficial de EN1** sobre el cual se administrarán todos los clientes, contratos, suscripciones, licencias e implementaciones de los productos y servicios ofrecidos por Easy Technology Services (ETS).

Este documento constituye la base arquitectónica del dominio comercial y deberá servir como referencia para la evolución de ADR y productos relacionados con:

- Portal ETS  
- EPosOne  
- EM+Acción  
- Relatic  
- Productos SaaS futuros  
- Licenciamiento  
- Billing  
- Provisioning  

---

## 2. Problema identificado

Durante el desarrollo de EPosOne se detectó que el proceso comercial y el proceso de implementación del producto fueron tratados como un único flujo.

Modelo conceptual actual (problemático):

```text
Registro → Organización → Provisioning → Bootstrap → Operación
```

Este flujo funciona para productos completamente conectados, pero introduce complejidad innecesaria para modalidades como Standalone y dificulta la incorporación de nuevos productos SaaS.

El verdadero problema **no** es el bootstrap ni el aprovisionamiento: es que el **dominio comercial** y el **dominio operacional** fueron mezclados.

---

## 3. Principio arquitectónico principal

```text
Registro ≠ Implementación
```

- Registrar un cliente **no** significa implementar un producto.  
- Implementar un producto **no** significa registrar un cliente.  
- Ambos procesos pertenecen a **dominios diferentes**.

---

## 4. Separación de dominios

EN1 queda dividido conceptualmente en dos grandes dominios.

### 4.1 Dominio Comercial

Responsable de la relación entre Easy Technology Services y sus clientes.

Incluye: Prospectos · Clientes · Organizaciones · Contratos · Suscripciones · Licencias · Facturación · Pagos · Renovaciones · Expediente Comercial · Soporte Comercial.

Este dominio existe aunque el cliente **nunca** implemente un producto.

**Proveedor comercial en producción (tenant ETS / EN1):**

| Campo | Valor |
|-------|--------|
| `saas_organization.id` | **1** |
| Nombre | **Easy NodeOne Producción** |
| `subdomain` | `none` |
| Marca | Easy Technology Services |

La org #1 administra el dominio comercial; **no** concentra la operación de los clientes finales.

### 4.2 Dominio Operacional

Representa la implementación técnica de un producto contratado. Incluye únicamente los recursos necesarios para operar dicho producto.

Ejemplos:

| Producto | Recursos operacionales (ejemplos) |
|----------|-----------------------------------|
| EPosOne | Sucursales, POS, cajas, cajeros, inventario, sincronización, dispositivos |
| EM+Acción | Programas, cursos, participantes, actividades |
| Relatic | Comunidades, capítulos, membresías, eventos |

Cada producto define sus propios recursos operacionales.

---

## 5. Organización

La Organización representa la **entidad empresarial del cliente** dentro de EN1.

- La existencia de una Organización **NO** implica recursos operacionales.  
- Puede existir únicamente como entidad comercial.  
- Los recursos operacionales se crean **solo** cuando la implementación del producto lo requiere.

**No existirán** conceptos “Organización ligera” / “Organización pesada”.  
Existe un **único** tipo de Organización; lo que cambia son los **recursos asociados**.

---

## 6. Ciclo comercial

Todo cliente sigue el mismo flujo (común a todos los productos ETS):

```text
Prospecto
  → Registro
  → Correo verificado
  → Cliente
  → Organización
  → Contrato
  → Suscripción
  → Licencia
  → Implementación
  → Activo
```

---

## 7. Prospecto

Representa una oportunidad comercial. Puede existir sin contrato, sin organización, solo con información básica.

Ejemplos de origen: formulario web, landing, llamada, referencia, feria, redes sociales.

---

## 8. Registro

Formaliza el interés del prospecto. Debe capturar como mínimo: nombre, empresa, correo, teléfono, país.

Al finalizar el registro:

1. Se crea el expediente comercial (inicial).  
2. Se envía correo de verificación.  
3. Se notifica automáticamente al equipo comercial de Easy Technology Services.

---

## 9. Verificación del correo

Todo cliente deberá verificar su correo antes de continuar el proceso comercial.

Estados: **Pendiente** · **Verificado** · **Actualizado**.

Mientras el correo no esté verificado:

- no podrán emitirse licencias;  
- no podrá finalizarse una contratación;  
- no podrá activarse un producto.

Cada registro genera correo interno a ETS notificando el nuevo cliente.

---

## 10. Cliente

Persona natural o jurídica con relación comercial con Easy Technology Services. Puede contratar uno o múltiples productos.

```text
Cliente → EPosOne · Hosting · EM+Acción · Relatic · …
```

---

## 11. Organización (identidad empresarial)

Toda empresa contratante tendrá una Organización. Representa **exclusivamente** la identidad empresarial, **no** la implementación del producto.

---

## 12. Contrato

El Contrato es el documento **jurídico y comercial principal** entre ETS y el cliente. Todo lo demás deriva del Contrato.

Deberá almacenar, entre otros:

| Bloque | Contenido |
|--------|-----------|
| Datos generales | Número, fecha, estado, ejecutivo comercial |
| Cliente | Organización, responsable, datos fiscales |
| Productos | Producto, plan, modalidad, precio, cantidad |
| Servicios | Instalación, capacitación, migración, configuración, asesoría |
| Condiciones | Mensual/anual, renovación, descuentos, observaciones |
| Firmas | Cliente · Easy Technology Services |

---

## 13. Expediente Comercial

Cada Contrato genera un Expediente Comercial con documentación relacionada: contrato firmado, cotización, OC, RUC, cédula, fotografías, evidencias, comprobantes, anexos — asociados al cliente.

---

## 14. Suscripción

Representa **únicamente** el ciclo comercial del producto (Trial, Activa, Suspendida, Vencida, Cancelada).

- **NO** representa el contrato.  
- **Depende** del Contrato.

---

## 15. Licencia

Representa el derecho efectivo de uso (dispositivos, cajas, sucursales, módulos, funcionalidades, vigencia). Depende de la Suscripción.

---

## 16. Implementación

Proceso mediante el cual un producto contratado **materializa** sus recursos operacionales. **No** forma parte del registro comercial. Cada producto define su propia implementación.

Ejemplos: EPosOne (provisioning, bootstrap, sucursal, POS, caja, dispositivos); Hosting (servidor, DNS, SSL); EM+Acción (programas, estructuras académicas).

---

## 17. Recursos operacionales

Solo existen cuando un producto requiere ser implementado.

Ejemplo EPosOne:

```text
Organización → Sucursal → POS → Caja → Dispositivo → Sincronización
```

La creación de estos recursos **es** la Implementación, no el registro del cliente.

---

## 18. Standalone

Standalone **NO** significa: cliente anónimo, sin cuenta, sin organización, sin licencia.

Standalone **sí** significa: cliente registrado, organización creada, contrato, suscripción, licencia.

La diferencia: la implementación operacional puede ser **mínima o diferida**.

---

## 19. Connected

Connected sigue el flujo completo:

```text
Cliente → Contrato → Suscripción → Licencia
  → Implementación → Provisioning → Bootstrap → Operación
```

---

## 20. Portal ETS

El Portal Easy Technology Services es el responsable del **dominio comercial**: prospectos, clientes, contratos, suscripciones, licencias, pagos, renovaciones, expediente.

Los portales específicos de cada producto **consumen** este dominio.

---

## 21. Beneficios

- Separación clara entre negocio e implementación  
- Incorporación sencilla de nuevos productos  
- Un único modelo comercial  
- Contratos independientes del producto  
- Mejor control comercial y licenciamiento  
- Menor complejidad en el onboarding  
- Mayor reutilización entre productos  

---

## 22. Impacto esperado (post-aprobación)

Revisar en fases: ADR-022, ADR-014, ADR-016, ADR-024, ADR-027, ADR-028 (y alineación con Portal / `/start` / licenciamiento / provisioning / bootstrap).

**Este ADR no autoriza** esos cambios hasta aprobación formal.

---

## 23. Principios arquitectónicos

1. Registro ≠ Implementación.  
2. Comercial ≠ Operacional.  
3. El Contrato es el documento comercial principal.  
4. La Suscripción depende del Contrato.  
5. La Licencia depende de la Suscripción.  
6. La Organización representa la empresa del cliente, no la implementación del producto.  
7. Los recursos operacionales se crean únicamente durante la implementación cuando la modalidad lo requiere.  
8. Todo cliente ETS sigue el mismo ciclo comercial, independientemente del producto.  
9. Todo registro requiere correo verificado antes de emitir licencias o activar productos.  
10. Todo nuevo registro genera notificación automática al equipo comercial ETS.  

---

## 24. Estado

**PROPOSED**

Define la arquitectura conceptual del Dominio Comercial de EN1.  
**No** autoriza cambios en código, contratos HTTP, modelos de datos ni ADR existentes hasta aprobación formal por Arquitectura.
