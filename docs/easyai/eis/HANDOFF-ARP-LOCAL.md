# Handoff oficial — EIS v1.0 Frozen → ARP & LOCAL

| Campo | Valor |
|-------|--------|
| Emisor | **CODITO** |
| Destinatarios | **ARP** (EasyAI Core) · **LOCAL** (EPOSOne Operations Connector) |
| Estado programa | Integración — sin más arquitectura |
| Norma | Easy Integration Specification **v1.0.0 Frozen** |
| Fecha entrega | 5 ago 2026 |

---

## Referencia Git (fuente de verdad)

| Item | Valor |
|------|--------|
| Repo | `Easy-NodeOne` (mismo remoto CODITO) |
| Commit | `1fa359e` (`1fa359e1b133e729669392fc2d6ed8988cf49f66`) |
| Rama | `develop` (y `main` tras merge de entrega) |
| Tag | `eis-v1.0.0` |

```bash
git fetch origin
git checkout eis-v1.0.0
# o: git show 1fa359e:docs/easyai/eis/README.md
```

---

## Contenido del paquete

### Raíz ADR

- `docs/ADR-026-EASY-INTEGRATION-SPECIFICATION-V1.md`

### Pack normativo

- `docs/easyai/eis/` — índice [`README.md`](README.md) · sello [`FROZEN.md`](FROZEN.md)

| Bloque | Archivos |
|--------|----------|
| SPECs | `EIS-000` … `EIS-011` |
| Catálogos | `catalogs/*` |
| Diagramas | `diagrams/*` |
| Conformidad | `CONFORMITY-CHECKLIST.md` |
| Validación cruzada | `VALIDATION-CROSS-ARP-CODITO-LOCAL.md` |

### Índice comercial/pack

- `docs/easyai/README.md` → apunta al EIS Frozen

---

## Qué debe hacer cada servidor

### ARP

1. Sincronizar el commit/tag anterior.
2. Implementar / alinear runtime (Gateway, Context Builder, Tool Dispatcher, Session, Errors) **consumiendo** el EIS — sin redefinir contratos.
3. Usar `CONFORMITY-CHECKLIST.md` solo como referencia de lo que exigirá a Connectors.

### LOCAL

1. Sincronizar el mismo commit/tag.
2. Desarrollar **EPOSOne Operations Connector** conforme a EIS-001…011.
3. Completar checklist de conformidad antes de certificación funcional EPOSOne.

### CODITO

Tras esta entrega: **en espera**. Solo mantenimiento versionado del EIS si hay RFC aprobado.

---

## Qué no incluye este paquete

- Código runtime ARP  
- Código Connector LOCAL  
- Cambios EN1 de producto  
- Certificación funcional EPOSOne (pendiente)

---

## Confirmación de recepción (opcional)

ARP / LOCAL pueden responder: *EIS v1.0 recibido — commit/tag `eis-v1.0.0`.*
