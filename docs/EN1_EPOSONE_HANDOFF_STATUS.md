# EPosOne ↔ EN1 — Dónde quedamos (handoff)

| Campo | Valor |
|-------|--------|
| Fecha | **14 jul 2026** |
| Roadmap | **V5** — [`EN1_PLATFORM_EPOSONE_V5_ROADMAP.md`](EN1_PLATFORM_EPOSONE_V5_ROADMAP.md) |
| **Hito 3B** | **PUBLICADO** — paquete [`handoff-eposone/`](handoff-eposone/) |
| Contrato HTTP | [`EN1_EPOSONE_HITO3_ORDER_HTTP_CONTRACT.md`](EN1_EPOSONE_HITO3_ORDER_HTTP_CONTRACT.md) (ejemplos completos) |
| Spec | [`EN1_EPOSONE_ORDER_DOMAIN_SPEC_V1.md`](EN1_EPOSONE_ORDER_DOMAIN_SPEC_V1.md) **v1.0 CONGELADA** |
| Tag código | `eposone-order-domain-v1.0` → `36a0eb1` |
| **Quién ahora** | **P2** — copiar a `Doc/` y cablear HTTP (quitar stubs) |

---

## Una frase

Hito **3B** entregado: contrato + Spec publicados con ejemplos request/response. P2 deja stubs y implementa HTTP.

---

## Paquete para `Doc/` (EPosOne)

Desde `docs/handoff-eposone/` (o mismos nombres en `docs/`):

1. `EN1_EPOSONE_HITO3_ORDER_HTTP_CONTRACT.md`  
2. `EN1_EPOSONE_ORDER_DOMAIN_SPEC_V1.md`  

Origen Git: `develop` en Easy-NodeOne.

---

## Política permanente — cierre de hito (4 entregables)

Ningún hito se considera terminado sin:

1. Código implementado  
2. Contrato (API/integración) congelado  
3. Documentación de handoff actualizada  
4. Ejemplos completos request/response  

---

## Chat nuevo

**P2** — implementar HTTP real según contrato 3B.  
EN1: no más código Hito 3 salvo bug.
