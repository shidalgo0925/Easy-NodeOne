# Handoff oficial — EIS v1.0 Frozen → ARP & LOCAL

| Campo | Valor |
|-------|--------|
| Emisor | **CODITO** |
| Destinatarios | **ARP** (EasyAI Core) · **LOCAL** (EPOSOne Operations Connector) |
| Estado programa | Integración — sin más arquitectura |
| Norma | Easy Integration Specification **v1.0.0 Frozen** |
| Fecha entrega | 5 ago 2026 |
| Sync cruzado | 6 ago 2026 — remoto + tag para repo **distinto** de EN1 |

---

## Referencia Git (fuente de verdad)

El paquete vive en el repositorio de CODITO / EN1. **LOCAL no comparte ese árbol de código**; debe **importar solo la documentación**.

| Item | Valor |
|------|--------|
| Remoto | `git@github.com:shidalgo0925/Easy-NodeOne.git` |
| HTTPS | `https://github.com/shidalgo0925/Easy-NodeOne.git` |
| Tag oficial (pack completo Gate 0) | **`eis-v1.0.1`** |
| Tag freeze SPECs | `eis-v1.0.0` (contenido normativo; `eis-v1.0.1` añade `EIS.md` + sync cruzado) |
| Commit freeze SPECs | `1fa359e` |

### Contenido que debe existir en el repo de LOCAL tras sync

| Artefacto | Ruta |
|-----------|------|
| Pack EIS | `docs/easyai/eis/` |
| Entrada Gate 0 | `docs/easyai/eis/EIS.md` |
| ADR | `docs/ADR-026-EASY-INTEGRATION-SPECIFICATION-V1.md` |
| SPECs | `docs/easyai/eis/EIS-000` … `EIS-011` |
| Checklist | `docs/easyai/eis/CONFORMITY-CHECKLIST.md` |
| Este handoff | `docs/easyai/eis/HANDOFF-ARP-LOCAL.md` |

---

## Sync para LOCAL (repo distinto — Gate 0)

Ejecutar **en el repositorio de LOCAL** (no hace checkout de toda la app EN1):

```bash
# 1) Remoto de solo lectura al pack oficial
git remote add en1-eis git@github.com:shidalgo0925/Easy-NodeOne.git 2>/dev/null || true
git fetch en1-eis tag eis-v1.0.1

# 2) Traer únicamente documentación normativa al working tree de LOCAL
git checkout eis-v1.0.1 -- \
  docs/easyai/eis \
  docs/ADR-026-EASY-INTEGRATION-SPECIFICATION-V1.md \
  docs/easyai/README.md

# 3) Commit en el repo LOCAL (sin tocar contratos)
git add docs/easyai docs/ADR-026-EASY-INTEGRATION-SPECIFICATION-V1.md
git commit -m "docs(eis): import official EIS v1.0 pack (eis-v1.0.1)"
```

Alternativa sin remote permanente:

```bash
git clone --depth 1 --branch eis-v1.0.1 \
  git@github.com:shidalgo0925/Easy-NodeOne.git /tmp/eis-v1.0.1
cp -a /tmp/eis-v1.0.1/docs/easyai "$(git rev-parse --show-toplevel)/docs/"
cp /tmp/eis-v1.0.1/docs/ADR-026-EASY-INTEGRATION-SPECIFICATION-V1.md \
  "$(git rev-parse --show-toplevel)/docs/"
# luego git add + commit en LOCAL
```

Verificación Gate 0:

```bash
test -f docs/easyai/eis/EIS.md \
  && test -f docs/ADR-026-EASY-INTEGRATION-SPECIFICATION-V1.md \
  && test -f docs/easyai/eis/CONFORMITY-CHECKLIST.md \
  && test -f docs/easyai/eis/HANDOFF-ARP-LOCAL.md \
  && ls docs/easyai/eis/EIS-0*.md | wc -l
# esperado: 12 SPECs
```

---

## Qué debe hacer cada servidor

### ARP

1. Sincronizar el mismo tag (`eis-v1.0.1`) o rutas equivalentes.
2. Alinear runtime consumiendo EIS — sin redefinir contratos.
3. Usar `CONFORMITY-CHECKLIST.md` como exigencia a Connectors.

### LOCAL

1. Importar el pack al **propio** repositorio (comandos arriba).
2. Ejecutar Gate 0 contra archivos locales (no inventar contratos).
3. Continuar Bridge / Facade / Harness / conformidad EIS.

### CODITO

Tras esta entrega: **en espera**. Solo mantenimiento versionado del EIS si hay RFC aprobado.  
CODITO **no** tiene el working tree de LOCAL en este host; la entrega oficial es **remoto + tag** + rutas anteriores.

---

## Qué no incluye este paquete

- Código runtime ARP  
- Código Connector LOCAL  
- Cambios EN1 de producto  
- Certificación funcional EPOSOne (pendiente)

---

## Confirmación de recepción

LOCAL puede responder: *EIS v1.0 recibido en repo LOCAL — tag origen `eis-v1.0.1`.*
