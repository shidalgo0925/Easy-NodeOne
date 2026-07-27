# ADR-013 — Portal ETS como Punto Único de Entrada

| Campo | Valor |
|-------|--------|
| ID | ADR-013 |
| Título | Portal ETS como Punto Único de Entrada |
| Estado | **Aprobado (GO)** — 24 jul 2026 |
| Ámbito | Portal ETS · EN1 (servicios comunes) · todos los productos |
| Relacionados | [ADR-012 Arquitectura ETS](ADR-012-ETS-ECOSYSTEM-ARCHITECTURE.md) · [ADR-011 Brand/ProductContext](ADR-011-PORTAL-ETS-PUNTO-ENTRADA.md) · [ADR-014 Subscription Registry](ADR-014-SUBSCRIPTION-REGISTRY.md) |
| Dominio oficial | **`app.easytech.services`** |

---

## Objetivo

Definir el **Portal ETS** como la puerta de entrada oficial del ecosistema Easy Technology Services.

El portal representa la **relación comercial** entre el cliente y ETS. No representa un producto específico.

> **Nota:** ADR-011 introdujo el concepto de portal y BrandContext. Este ADR fija el dominio oficial (`app.easytech.services`) y el alcance funcional del portal. El host legado `portal.easytech.services` puede permanecer como alias de resolución.

---

## Dominio oficial

```text
app.easytech.services
```

---

## Responsabilidades del Portal

- Registro de clientes
- Inicio de sesión
- Gestión de cuenta
- Productos contratados
- Marketplace de productos
- Suscripciones
- Licencias
- Facturación
- Métodos de pago
- Descargas
- Soporte
- Perfil

## Lo que NO hace

El Portal ETS **no** ejecuta la lógica funcional de los productos.

Ejemplos: no vende en POS, no factura ventas de restaurante, no administra inventarios ni nóminas. Eso pertenece a cada producto.

---

## Flujo

```text
Cliente
    ↓
app.easytech.services
    ↓
Iniciar sesión
    ↓
Mis Productos
    ↓
Seleccionar producto
    ↓
Abrir producto
    ↓
Dominio del producto
    ↓
Tenant
    ↓
Operación
```

### Ejemplos

```text
Cliente → Portal ETS → EPosOne → eposone.easytech.services → Restaurante ABC → Operación POS

Cliente → Portal ETS → EPayRoll → epayroll.easytech.services → Empresa XYZ → Nómina
```

---

## Relación con EN1

El Portal ETS utiliza los servicios comunes de EN1.

No duplica: autenticación, licencias, organizaciones, auditoría, APIs.

---

## Mapa arquitectónico oficial ETS

```text
                           INTERNET
                               │
                               ▼
                    app.easytech.services
                      Portal del Ecosistema
                               │
        ┌──────────────────────┼──────────────────────┐
        │                      │                      │
        ▼                      ▼                      ▼
     EPosOne              EPayRoll             EClassOne
eposone.easytech...  epayroll.easytech... eclassone.easytech...
        │                      │                      │
        ▼                      ▼                      ▼
   Tenant Cliente A      Tenant Empresa B      Tenant Colegio C
        │                      │                      │
        ▼                      ▼                      ▼
      Usuarios              Usuarios              Usuarios

──────────────────────────────────────────────────────────────

                 Plataforma Compartida (EN1)

• Autenticación · Organizaciones · Licencias · Suscripciones
• Provisionamiento · Bootstrap · Sincronización · Auditoría
• APIs · Seguridad
• ContextResolver · BrandContext · ProductContext
```

---

## Decisión final

Queda establecida la arquitectura oficial del ecosistema:

1. **ETS** es la marca y el ecosistema.
2. **Portal ETS** (`app.easytech.services`) es el punto único de entrada.
3. **EN1** es la plataforma compartida.
4. Cada producto (EPosOne, EPayRoll, EClassOne, ETesis, etc.) tiene su propio dominio, identidad y experiencia.
5. Cada producto administra sus propios tenants, reutilizando los servicios comunes de EN1.

---

## Resultado esperado

El cliente percibe una experiencia uniforme bajo ETS, mientras que cada producto mantiene su propia identidad y funcionalidad.

Implementación de pantallas Marketplace / facturación = **fases posteriores**.

### Portal ETS MVP (Dev)

- Rutas: `/portal/` · `/portal/products` · `/portal/open/<product_code>`
- Servicio: `PortalService.list_products_for_current_tenant()`
- Fuentes: solo `SubscriptionRegistry` + `ProductRegistry`
- Post-login en Host portal → `/portal/`
- Abrir producto → `https://{ProductRegistry.primary_domain}` (sin hardcode)

---

## Historial

| Fecha | Nota |
|-------|------|
| **2026-07-24** | Aprobado (GO) — dominio oficial `app.easytech.services` |
