# ADR-035 — Activation Model (Licencia → Token → QR)

| Campo | Valor |
|-------|--------|
| ID | **ADR-035** |
| Título | Modelo de activación — Licencia, Token y medios de transporte |
| Estado | **PROPOSED** — pendiente revisión / aprobación Arquitectura |
| Versión | 1.0 |
| Fecha | Agosto 2026 |
| Autor | Arquitectura EN1 / EPosOne |
| Impacto | EN1 (emisión) · Portal ETS · EPosOne APK (consumo) |
| Implementación de código | **NO autorizada** — documento de arquitectura únicamente |
| Pregunta rectora | **¿Qué es la orden de activación y cómo llega al dispositivo?** |
| Complementa | [ADR-032](ADR-032-PRODUCT-IMPLEMENTATION-MODEL.md) · [ADR-031](ADR-031-EN1-COMMERCIAL-DOMAIN-ARCHITECTURE.md) |
| Consumidores | [ADR-033](ADR-033-STANDALONE-ONBOARDING-ASSISTANT.md) · [ADR-034](ADR-034-CONNECTED-PROVISIONING-FLOW.md) |
| Relacionados | [ADR-016](ADR-016-COMMERCIAL-LICENSING-V2-ENTITLEMENT.md) · [ADR-021](ADR-021-EPOSONE-INSTALLATION-LIFECYCLE.md) · [ADR-007](ADR-007-EPOSONE-COMMERCIAL-LICENSING-OFFLINE.md) |

---

## 1. Objetivo

Definir el **modelo de activación** desacoplado del QR:

```text
Contrato
  → Suscripción
  → Licencia                 ← derecho / orden de activación
  → Token de Activación      ← referencia operable
  → Medio de transporte      ← QR | correo | enlace | copia manual
  → APK
```

**Única responsabilidad:** semántica de Licencia, Token y transporte.  
No define pantallas del asistente Standalone ni el árbol Connected.

---

## 2. Principios

1. La **Licencia** es la orden de activación (no el QR).  
2. El **Token** es la referencia usable derivada de (o anclada a) la Licencia.  
3. El **QR** es solo una representación gráfica del token o de una URL que lo contiene.  
4. El mismo token debe poder entregarse por correo, deep link o copia manual.  
5. La APK **no** pregunta la modalidad; la obtiene de la activación (payload del token / licencia).  
6. Un canal de entrega no debe acoplarse al modelo de dominio.

---

## 3. Licencia (orden)

Porta al menos (lógico):

| Campo | Rol |
|-------|-----|
| producto | p. ej. EPosOne |
| modalidad | Standalone \| Connected |
| estrategia de implementación | Autogestionada \| Asistida |
| organization / contract / subscription refs | anclaje comercial |
| vigencia | starts / ends |
| estado | emitida, activa, revocada, expirada |
| firma / integridad | autenticidad EN1 |

La Licencia expresa **qué** se puede activar y bajo qué reglas. No es el string que el usuario pega en la APK (eso es el Token).

---

## 4. Token de activación

Referencia operable para el dispositivo:

| Campo (mínimo lógico) | Rol |
|----------------------|-----|
| token_id / código | valor que el usuario ingresa o escanea |
| license_id (o claim firmado) | enlace a la orden |
| producto | coherencia |
| modalidad + estrategia | ramifica flujo APK |
| expiración | ventana de uso del token |
| política de uso | p. ej. un solo uso / multi-dispositivo según plan |
| firma | verificación offline/online según contrato futuro |

### Canales de entrega (equivalentes)

- QR (imagen)  
- Correo (texto / botón)  
- Enlace / deep link  
- Copia manual  

Todos transportan el **mismo** token (o URL que resuelve al token).

---

## 5. QR (transporte)

- No es la orden.  
- No es obligatorio.  
- Debe ser regenerable a partir del token mientras el token sea válido.  
- Contenido típico: URL HTTPS de activación **o** payload compacto del token — decisión de implementación futura (GO), no de este ADR.

---

## 6. Comportamiento APK al activar

1. Recibe token (pegar / escanear / deep link).  
2. Valida firma / vigencia / producto (online u offline según fase).  
3. Materializa licencia/entitlement local.  
4. Lee modalidad + estrategia.  
5. Enruta:  
   - **Standalone / Autogestionada** → [ADR-033](ADR-033-STANDALONE-ONBOARDING-ASSISTANT.md)  
   - **Connected / Asistida** → provisioning/bootstrap ([ADR-034](ADR-034-CONNECTED-PROVISIONING-FLOW.md))  

Errores tipados: inválido, expirado, usado, producto incorrecto, modalidad incompatible con estado EN1 (p. ej. Connected sin caja).

---

## 7. Emisión (EN1)

| Modalidad | Cuándo emitir token |
|-----------|---------------------|
| Standalone | Tras Licencia comercial; **sin** exigir árbol ops |
| Connected | Tras Licencia **y** materialización mínima ops (ADR-034 fase B), salvo política explícita en contrario |

Revocación de Licencia debe invalidar tokens pendientes asociados.

---

## 8. Relación con códigos legacy

Códigos de provisioning / instalación actuales pueden evolucionar hacia este modelo o coexistir en transición.  
Este ADR **no** manda borrar el código legado; la convergencia requiere GO de implementación.

---

## 9. Impacto (analizar, no implementar)

### CODITO

- Modelo de datos Licencia ↔ Token  
- Emisión, expiración, un solo uso  
- APIs de validación  
- Generación QR como vista del token  

### LOCAL

- UX multi-canal de ingreso de token  
- Enrutado post-activación sin pregunta de modalidad  

---

## 10. Fuera de alcance

- Esquema JSON/JWT definitivo  
- Endpoints HTTP versionados  
- UI Portal  
- Código APK/EN1  
- Ampliación de ADR-032  

---

## 11. Estado

**PROPOSED**

Base compartida CODITO/LOCAL. Aprobación Arquitectura + **GO de implementación** por fases antes de código.
