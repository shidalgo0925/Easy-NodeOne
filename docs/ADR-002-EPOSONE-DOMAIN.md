# ADR-002 — Modelo de dominio único EPosOne

| Campo | Valor |
|-------|--------|
| ID | ADR-002 |
| Título | Un solo dominio; proveedores de datos intercambiables |
| Estado | **Aprobado (congelado)** — 9 jul 2026 |
| Roadmap | [`EN1_PLATFORM_EPOSONE_V4_ROADMAP.md`](EN1_PLATFORM_EPOSONE_V4_ROADMAP.md) |
| Relacionados | [ADR-001](ADR-001-EPOSONE-STANDALONE.md) · [ADR-003](ADR-003-EPOSONE-SYNC.md) · [ADR-004](ADR-004-EPOSONE-MIGRATION.md) |
| Dominio comercial EN1 | [`EN1_PLATFORM_ETAPA6_DOMINIO_COMERCIAL.md`](EN1_PLATFORM_ETAPA6_DOMINIO_COMERCIAL.md) |
| Alcance de esta fase | **Solo documentación** — sin código |

---

## Contexto

Si Standalone y Plataforma usan modelos distintos (p. ej. “producto local” vs “producto Core”), la vinculación a EN1 se vuelve una reescritura. El costo de corregirlo después es alto.

---

## Decisión

**No existen dos modelos de negocio.** Existe **un único dominio** EPosOne / comercial.

### Entidades del dominio (núcleo)

| Entidad | Rol |
|---------|-----|
| Producto | Catálogo vendible |
| Cliente | Comprador / contacto comercial |
| Pedido | Centro del sistema (Etapa 6.3) |
| Caja / turno | Operación de caja |
| Sucursal | Unidad operativa |
| Empleado / cajero | Operador |
| Impuesto | Reglas fiscales de línea |
| Pago | Captura / reembolso ligado al pedido |
| Promoción | Descuentos / reglas comerciales |
| Empresa / organización | Contenedor del negocio |
| Terminal / dispositivo | Punto de venta físico |

El detalle de estados, flujos y eventos sigue el dominio comercial congelado en Etapa 6; este ADR fija la **regla de portabilidad**, no reabre 6.1–6.8.

### Separación dominio ↔ almacenamiento

```text
Capa de aplicación (UI / casos de uso)
            │
     Repositorios / puertos (dominio)
            │
     ┌──────┴──────┐
     │             │
  SQLite        EN1 API
 (proveedor)   (proveedor)
```

Ejemplo conceptual (no implementación):

```text
ProductoRepository  →  SQLiteProductRepository
ProductoRepository  →  ApiProductRepository
```

**La aplicación nunca conoce el origen** de los datos en la capa de dominio. SQLite y EN1 son **únicamente proveedores de datos**, no modelos distintos.

### Contratos portables (Sprint 2 del Roadmap V4)

**Documento normativo:** [`EN1_PLATFORM_EPOSONE_V4_DOMAIN_CONTRACTS.md`](EN1_PLATFORM_EPOSONE_V4_DOMAIN_CONTRACTS.md).

Los contratos de Producto, Cliente, Venta/Pedido, Caja, Inventario, Empleado y Configuración:

- **No** referencian SQLite.
- **No** referencian EN1 / Flask / tablas Core por nombre de infraestructura.
- Son serializables para vinculación (ADR-004).
- Usan **IDs opacos string**; el adapter Plataforma mapea a ids internos EN1.

---

## Consecuencias

| Positivo | Riesgo / mitigación |
|----------|---------------------|
| Vinculación = cambio de proveedor, no de producto | Mapear IDs locales ↔ IDs EN1 en ADR-004 |
| Una sola lógica de negocio en app | Disciplina: prohibido filtrar `if (mode == local)` dentro del dominio |
| Alineado a Etapa 6 (Pedido al centro) | Scaffold actual (`core/commerce`) se trata como implementación Connected; el contrato portable se formaliza en Sprint 2 |

---

## Reglas congeladas (extracto)

Ver reglas 2, 3 y 4 en el [Roadmap V4](EN1_PLATFORM_EPOSONE_V4_ROADMAP.md#reglas-congeladas).
