# Constitución EN1-POS V1.0

| Campo | Valor |
|-------|--------|
| Estado | **Borrador Release 0** — 19 jul 2026 |
| Rol | **Documento rector del producto** EN1-POS / EPosOne |
| Paquete | Release 0 — [`EN1_POS_V7_ROADMAP.md`](EN1_POS_V7_ROADMAP.md) |
| Relacionados | [ADR-006](ADR-006-EPOSONE-OPERATION-VS-ADMIN.md) · [Domain Model](EN1_POS_DOMAIN_MODEL_V1.md) · [DoD](EN1_POS_DEFINITION_OF_DONE_V1.md) · [Ownership](EN1_POS_OWNERSHIP_MATRIX_V1.md) |

---

## 1. Qué es el producto

| Nombre | Rol |
|--------|-----|
| **EPosOne** | Cliente operativo (APK / tablet): vende, cobra, caja, offline, ejecuta políticas, emite eventos, recibe configuración. |
| **EN1-POS** | Back Office en Easy NodeOne: configura, controla, sincroniza, audita, consolida, reporta, administra maestros y licencias. |
| **Dual Mode** | Misma lógica de negocio. Cambia solo el origen de los datos maestros. |

No son dos productos distintos (Lite/Pro). Es **operación vs administración** (ADR-006).

---

## 2. Modos de operación

| Modo | Fuente de verdad | EPosOne | EN1-POS |
|------|------------------|---------|---------|
| **Standalone** | Local en dispositivo | Opera + admin básica | Opcional / ausente |
| **Integrado** | EN1 | Réplica operativa local | SoT de maestros + consolidación |
| **Vincular** | Transición Standalone → Integrado | Sin reinstalar APK; migra/concilia | Asume administración |

---

## 3. Jerarquía operativa

```text
Empresa (organización)
  → Sucursal
    → Punto de venta (POS)
      → Caja (register)
        → Dispositivo
        → Turno (cash shift)
          → Pedido → Venta → Pago → Recibo → Documento fiscal → Reporte
```

Toda operación comercial debe poder atribuirse a esta jerarquía (más cajero/empleado y, si aplica, cliente).

---

## 4. Responsabilidades (no negociables)

### EPosOne ejecuta

- Pedidos, cobros, turnos, impresión, offline, cola de sync.
- Aplicación de políticas comerciales recibidas (versión conocida).
- Emisión de eventos de negocio hacia EN1 (modo Integrado).

### EN1-POS administra

- Datos maestros, políticas versionadas, dispositivos, licencias.
- Consolidación de ventas/pagos/caja, auditoría, reportes.
- Inventario oficial, empleados, clientes (según release).
- Facturación electrónica (configuración, envío, auditoría) — **parte de la cadena comercial en Panamá**, no módulo cosmético.

### Regla de conflicto

Si una pantalla o API no tiene **owner** en la [Ownership Matrix](EN1_POS_OWNERSHIP_MATRIX_V1.md), **no se implementa**.

---

## 5. Regla de implementación

Ninguna capacidad nueva sin identificar antes:

1. Entidad(es) del [Domain Model](EN1_POS_DOMAIN_MODEL_V1.md)
2. Owner (local / EN1 / generado)
3. Contrato (payload / eventos)
4. API
5. Permisos
6. Sync
7. Auditoría
8. Criterio de cierre ([DoD](EN1_POS_DEFINITION_OF_DONE_V1.md))

**Prohibido:** stubs presentados como “listo”; features aisladas fuera de la cadena del release activo.

---

## 6. Criterio de “terminado”

Una capacidad **no** está terminada porque exista tabla, endpoint o pantalla.

Está terminada solo si cumple el [Definition of Done](EN1_POS_DEFINITION_OF_DONE_V1.md) completo. Si falta un ítem → estado **Parcial**.

---

## 7. Releases (visión)

| Release | Enfoque |
|---------|---------|
| **0** | Constitución, dominio, ownership, gap, backlog, DoD, arquitectura — **sin código de features** |
| **1** | Cadena operativa comercial cerrada **incluye FE Panamá** (venta → pago → recibo → FE → sync → reporte) |
| **2** | Control del negocio (inventario avanzado, compras, crédito, fidelización, rentabilidad) |
| **3** | Restaurante / ecosistema (KDS, canales, APIs públicas, marketplace) |

Detalle: [`EN1_POS_V7_ROADMAP.md`](EN1_POS_V7_ROADMAP.md).

---

## 8. Precedencia documental

| Conflicto | Gana |
|-----------|------|
| Feature vs Constitución | Constitución |
| Parche vs DoD | DoD |
| V4/V5/V6 roadmaps vs V7 | **V7** para planificación de producto |
| Contratos comerciales V6 vs Domain Model | Domain Model define entidades; contratos V6 siguen como inputs técnicos a aprobar |

---

## 9. Aprobación

| Rol | Firma | Fecha |
|-----|-------|-------|
| Producto / Analista | Pendiente | — |
| Prog1 (EN1) | **Aceptado** — docs R0 coherentes con código Dev; sin features R1 hasta cierre total | 19 jul 2026 |
| Prog2 (EPosOne) | Pendiente | — |

Al aprobarse por los tres, este documento es la **referencia obligatoria** antes de abrir código de Release 1.
