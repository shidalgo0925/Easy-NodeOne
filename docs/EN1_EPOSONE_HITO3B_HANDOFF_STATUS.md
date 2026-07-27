# EPosOne ↔ EN1 — Handoff Hito 3B (estados)

| Campo | Valor |
|-------|--------|
| Fecha | **14 jul 2026** |
| Hito | **3B** — entrega oficial contrato Order Domain |
| Código EN1 | tag `eposone-order-domain-v1.0` · `36a0eb1` |
| Docs | Order Domain Spec v1.0 + Contrato HTTP (ejemplos) |

---

## Estados del handoff (regla permanente)

| # | Estado | Quién | Significado |
|---|--------|-------|-------------|
| 1 | **Preparado** | P1 | Documentos generados |
| 2 | **Publicado** | P1 | Disponibles para P2 (Git / carpeta / zip / canal) |
| 3 | **Recibido** | P2 | Confirma que existen y puede abrirlos |
| 4 | **Aceptado** | P2 | Empieza a trabajar con ellos (sin inventar contrato) |

**Cierre real del handoff = estado 4.**

Frase de cierre de P2 (obligatoria):

> Documentos recibidos. Comienzo implementación HTTP.

Hasta entonces el hito está: **Entregado pendiente de recepción** (entre Publicado y Recibido).

---

## Contenido a dejar en APK `Doc/`

```text
Doc/
├── EN1_EPOSONE_HITO3_ORDER_HTTP_CONTRACT.md
└── EN1_EPOSONE_ORDER_DOMAIN_SPEC_V1.md
```

---

## Dónde está publicado (P1 — 14 jul 2026)

| Canal | Ruta |
|-------|------|
| Git Easy-NodeOne `develop` | `docs/handoff-eposone/` |
| Copia servidor handoff | `/opt/handoff-plataformas/eposone-hito3b-Doc/` |
| Zip | `/opt/handoff-plataformas/eposone-hito3b-Doc.tar.gz` |
| Estático appdev | `https://appdev.easynodeone.com/static/handoff-eposone/` |

**Repo Flutter no está en este servidor** — P2 debe copiar a su `Doc/` local (o commit en su repo).

### Instrucción corta para Teams / P2

```text
Hito 3B — documentos oficiales Order Domain v1.0

1) EN1_EPOSONE_HITO3_ORDER_HTTP_CONTRACT.md
2) EN1_EPOSONE_ORDER_DOMAIN_SPEC_V1.md

Fuentes:
- GitHub Easy-NodeOne develop → docs/handoff-eposone/
- O tar: `/opt/handoff-plataformas/eposone-hito3b-Doc.tar.gz`
- O URL: https://appdev.easynodeone.com/static/handoff-eposone/


Copiar a: <repo eposone>/Doc/

Cuando los tengas locales, responder exactamente:
"Documentos recibidos. Comienzo implementación HTTP."
```

---

## Estado actual

| Estado | Sí/No |
|--------|-------|
| Preparado | ✅ |
| Publicado | ✅ |
| Recibido | ⏳ espera confirmación P2 |
| Aceptado | ⏳ |

Hito 3A/3B EN1: **Entregado pendiente de recepción**.
