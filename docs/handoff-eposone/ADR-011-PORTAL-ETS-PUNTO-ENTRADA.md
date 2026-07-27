# ADR-011 — Portal ETS como punto único de entrada del ecosistema

| Campo | Valor |
|-------|--------|
| ID | ADR-011 |
| Título | Portal ETS como Punto Único de Entrada del Ecosistema |
| Estado | **Aprobado (GO)** — 24 jul 2026 |
| Ámbito | Codito (EN1) · Local (EPosOne) · resto productos ETS |
| Relacionados | [ADR-012 Arquitectura ETS](ADR-012-ETS-ECOSYSTEM-ARCHITECTURE.md) · [ADR-013 Portal ETS](ADR-013-PORTAL-ETS-PUNTO-ENTRADA.md) · [ADR-007 Licenciamiento offline](ADR-007-EPOSONE-COMMERCIAL-LICENSING-OFFLINE.md) · [ADR-009 Caja EN1](ADR-009-EN1-CAJA-CENTRO-COBRO.md) · Brand/Host (BrandContext) |
| Destinatarios | Codito (EN1) y Local (EPosOne) |

---

## Objetivo

Definir la arquitectura oficial del **Portal ETS** como punto único de entrada para todos los productos del ecosistema Easy Technology Services: registro de clientes, adquisición de productos e interacción posterior con cada solución.

---

## Principios

### 1. EN1 es el núcleo del ecosistema

Easy NodeOne (EN1) es el **Core Platform** de todos los productos ETS.

Vive en EN1 (ningún producto lo administra por su cuenta):

- Usuarios · Organizaciones · Empresas  
- Suscripciones · Licencias  
- Seguridad · Auditoría  
- Dispositivos · Provisionamiento  
- Facturación (futuro) · Marketplace (futuro)

### 2. Portal ETS

El cliente **siempre** inicia desde un único portal. Dominio oficial ([ADR-013](ADR-013-PORTAL-ETS-PUNTO-ENTRADA.md)):

```text
app.easytech.services
```

Alias de resolución legacy: `portal.easytech.services`.

Desde ahí: registro, login, productos contratados, compra, suscripciones, facturas, descargas, dispositivos, soporte.

Equivalente conceptual a un Customer Portal (Contabo / Microsoft 365 / Google Workspace).

> **ADR-012 / ADR-013 (24 jul 2026):** jerarquía oficial ETS → Productos → Tenant → Usuarios; EN1 = plataforma compartida; portal = entrada comercial (no producto operativo).

### 3. Productos con identidad propia

Cada producto tiene identidad visual y subdominio bajo `easytech.services` (sin dominios independientes en esta etapa):

| Producto | Host (ejemplo) |
|----------|----------------|
| Portal ETS | `app.easytech.services` (alias: `portal.easytech.services`) |
| EPosOne | `eposone.easytech.services` |
| EPayRoll | `epayroll.easytech.services` |
| EClassOne | `eclassone.easytech.services` |
| EThesis | `etesis.easytech.services` |

### 4. Una sola aplicación EN1

No hay múltiples instalaciones del Core. Una app; el comportamiento depende del dominio de entrada:

```text
Host → BrandContext → ProductContext → Experiencia
```

Ejemplo: `appprd.easynodeone.com` → tema EN1; `eposone.easytech.services` → tema EPosOne. **Sin duplicar código.**

### 5. BrandContext

Por dominio: logo, nombre comercial, colores, favicon, textos, navegación, layout, pantalla inicial.

### 6. ProductContext

Además del tema, el sistema sabe **qué producto** está activo y carga **solo** sus módulos (POS ≠ nómina ≠ cursos).

---

## Dos superficies

| Superficie | Rol | Incluye | No incluye |
|------------|-----|---------|------------|
| **Portal ETS** | Comercial | Marketplace, registro, login, productos, suscripciones, facturación, pagos, descargas, licencias, dispositivos, perfil | ERP completo / menús de otros productos |
| **Producto** | Operativo | Solo módulos del producto (ej. EPosOne: ventas, caja, clientes, inventario, reportes) | Módulos de otros productos |

---

## Flujo general

```text
Cliente
  → Portal ETS (registro / login)
  → Mis Productos
  → Marketplace (opcional)
  → Suscripción → Licencia → Provisionamiento
  → Descarga APK
  → Registro dispositivo → Bootstrap → Operación
```

### Licenciamiento

Toda licencia nace en EN1. La APK nunca crea, modifica, vende ni genera Trial comercial; solo descarga, almacena, valida local y aplica permisos ([License Engine V1](EN1_EPOSONE_LICENSE_ENGINE_V1_CONTRACT.md)).

### Aprovisionamiento

EN1 crea Organización, Empresa, Sucursal, POS, Caja, Licencia. La app solo se registra contra una **Caja** existente (ADR-007).

### Marketplace

Pertenece al **Portal ETS**, no a EPosOne.

---

## Estado del cliente

Tras el primer ingreso, la home muestra solo productos contratados (estado, plan, vencimiento, dispositivos, Administrar). Sin producto → adquirir en Marketplace.

---

## Responsabilidades

| Quién | Hace |
|-------|------|
| **Codito (EN1)** | Portal ETS, BrandContext, ProductContext, Marketplace, suscripciones, licencias, provisioning, bootstrap, dispositivos, APIs |
| **Local (EPosOne)** | Registro device, bootstrap, License Engine APK, Feature Manager, offline, sync, UX POS |

---

## Decisión

> Easy NodeOne será el núcleo común de todos los productos de Easy Technology Services. Los clientes accederán inicialmente al Portal ETS, desde donde administrarán sus productos, suscripciones y servicios. Cada producto contará con una identidad propia mediante subdominios y BrandContext, compartiendo una única plataforma tecnológica sin duplicar aplicaciones ni lógica de negocio.

Este ADR es la **base arquitectónica** para EPosOne y el resto del ecosistema ETS.

---

## Fuera de alcance inmediato (no bloquea el ADR)

- Pasarela de pago / facturación completa  
- Marketplace con catálogo comercial vivo  
- Dominios independientes por producto  
- Igualar appprd con appdev en un solo deploy  

---

## Plan de implementación sugerido (EN1)

| Fase | Entrega | Prod |
|------|---------|------|
| **0** | Este ADR publicado + enlaces AGENTS/handoff | **Hecho** 24 jul 2026 |
| **1** | `BrandContext` + `ProductContext` por Host | **Hecho en Dev** — `nodeone/core/platform/brand_context.py` · theme/nav/`data-product` · test Host · smoke con `X-EN1-Product` / Host |
| **2** | Superficie Portal ETS mínima (login, mis productos stub) | No |
| **3** | Wire Trial/License + provisioning desde portal | No |
| **4** | DNS `app` / `eposone` → staging → prod por tags | Controlado (`eposone` prod publicado; `app.easytech.services` pendiente) |

### Fase 1 — cómo probar en Dev (sin DNS)

```bash
# Opción A: header (FLASK_ENV=development o NODEONE_ALLOW_PRODUCT_HEADER=1)
curl -sS -H 'X-EN1-Product: eposone' -H 'Host: appdev.easynodeone.com' \
  https://appdev.easynodeone.com/login | grep -o 'data-product="[^"]*"'

# Opción B: Host futuro (cuando nginx apunte)
# Host: eposone.easytech.services → BrandContext EPosOne
```

Env opcional: `NODEONE_PRODUCT_FORCE=eposone` (solo silo de prueba).

---

## Changelog

| Fecha | Cambio |
|-------|--------|
| **2026-07-24** | Aprobado (GO) — Portal ETS como entrada única; EN1 core; Brand/ProductContext; subdominios `*.easytech.services` |
| **2026-07-24** | Alineado con [ADR-012](ADR-012-ETS-ECOSYSTEM-ARCHITECTURE.md) / [ADR-013](ADR-013-PORTAL-ETS-PUNTO-ENTRADA.md): dominio portal oficial `app.easytech.services` |
