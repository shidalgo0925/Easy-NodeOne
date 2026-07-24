# ADR-012 — Arquitectura del Ecosistema Easy Technology Services (ETS)

| Campo | Valor |
|-------|--------|
| ID | ADR-012 |
| Título | Arquitectura del Ecosistema Easy Technology Services (ETS) |
| Estado | **Aprobado (GO)** — 24 jul 2026 |
| Ámbito | EN1 · Portal ETS · EPosOne · EPayRoll · EClassOne · ETesis · futuros productos |
| Relacionados | [ADR-011 BrandContext/ProductContext](ADR-011-PORTAL-ETS-PUNTO-ENTRADA.md) · [ADR-013 Portal ETS](ADR-013-PORTAL-ETS-PUNTO-ENTRADA.md) · ContextResolver |

---

## Objetivo

Definir oficialmente la arquitectura del ecosistema de productos de Easy Technology Services.

A partir de este ADR, **EN1 deja de verse como el producto principal** y pasa a ser la **plataforma tecnológica** que soporta todo el ecosistema ETS.

---

## Principios

### 1. ETS es el ecosistema

Easy Technology Services (ETS) es la marca bajo la cual se ofrecen todos los productos.

Los clientes establecen su relación comercial con **ETS**.

- No con EN1.
- No con EPosOne (como marca comercial de entrada).

### 2. EN1 es la plataforma

Easy NodeOne (EN1) es el **Core Platform**.

Responsabilidades:

- Autenticación
- Organizaciones
- Usuarios
- Seguridad
- Licencias
- Suscripciones
- Provisionamiento
- Auditoría
- APIs comunes
- Servicios compartidos

EN1 **no** es la experiencia comercial del cliente.

### 3. Los productos son independientes

Cada solución del ecosistema constituye un producto independiente.

Ejemplos: EPosOne · EPayRoll · EClassOne · ETesis · Relatic · futuros productos.

Cada uno tendrá:

- identidad propia;
- dominio propio;
- experiencia propia;
- navegación propia;
- funcionalidades propias.

### 4. Los clientes pertenecen a un producto

Cada cliente (tenant) existe dentro del contexto de un producto.

```text
ETS → EPosOne → Restaurante ABC
ETS → EPayRoll → Empresa XYZ
```

No existe un tenant global para todos los productos.

### 5. EN1 comparte servicios

Todos los productos reutilizan: autenticación, licencias, organizaciones, auditoría, dispositivos, sincronización, bootstrap y servicios comunes.

No se duplicará infraestructura.

---

## Jerarquía oficial

```text
Internet
    ↓
Easy Technology Services (ETS)
    ↓
Portal ETS
    ↓
Productos
    ↓
Tenant del producto
    ↓
Usuarios
```

### Decisión

Se adopta oficialmente:

```text
ETS → Productos → Tenant → Usuarios
```

EN1 es la plataforma transversal que soporta todos los niveles.

---

## Resultado esperado

Agregar un nuevo producto **no** requerirá crear una nueva plataforma.

Únicamente:

1. Registrar el producto
2. Asignar un dominio
3. Configurar BrandContext
4. Configurar ProductContext

Todo lo demás se reutiliza desde EN1 (ContextResolver + `host_product_map.json` + apps/SaaS existentes).

---

## Notas de implementación (Dev)

| Concepto | Estado actual |
|----------|----------------|
| Host → Product/Brand | `ContextResolver` + `backend/nodeone/core/platform/data/host_product_map.json` |
| Tenant por producto | Principio aprobado; modelo de datos / scoping = fases posteriores |
| Portal comercial | [ADR-013](ADR-013-PORTAL-ETS-PUNTO-ENTRADA.md) — dominio `app.easytech.services` |

---

## Historial

| Fecha | Nota |
|-------|------|
| **2026-07-24** | Aprobado (GO) |
