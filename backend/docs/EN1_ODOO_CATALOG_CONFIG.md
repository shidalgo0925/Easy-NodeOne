# EN1 — Configuración catálogo Odoo (Fase 1 entregada)

**Estado Modecosa:** módulo `en1_connector` **19.0.1.0.0** instalado.

---

## Variables en `.env` del silo (no commitear)

```bash
ODOO_CATALOG_URL=https://erp.modecosa.com/api/en1/v1/security-catalog
ODOO_CATALOG_API_KEY=<generar en Odoo: Ajustes → EN1 Connector>
ODOO_DB=modecosa
```

La API key se recibe por **canal seguro** (no chat, no git).

---

## Prueba desde EN1

```bash
cd /opt/easynodeone/dev/app/backend
/opt/easynodeone/dev/venv/bin/python3 nodeone/integrations/odoo/test_odoo_catalog.py
echo exit=$?
```

Referencia Modecosa: ~22 KB, 28 usuarios, 111 grupos, 153 membresías, HTTP 200.

---

## Qué usar / qué no usar

| Usar | No usar en producción |
|------|------------------------|
| `GET` + Bearer + `X-Odoo-Database: modecosa` | XML-RPC desde VPS EN1 |
| `ODOO_CATALOG_API_KEY` solo lectura | Usuario `shidalgo@...` + contraseña |
| `catalog_client.fetch_security_catalog()` | `test_odoo_connection.py` salvo diagnóstico |

---

## Código EN1

| Archivo | Rol |
|---------|-----|
| `nodeone/integrations/odoo/catalog_client.py` | Cliente + validación mínima v1 |
| `nodeone/integrations/odoo/test_odoo_catalog.py` | Prueba de aceptación |
| `docs/schemas/en1_security_catalog_v1.*` | Contrato JSON |

**Módulo EN1:** `nodeone/modules/security_matrix_manager/` — `/admin/security-matrix` (Fase 1 implementado).

**Fase 2 Odoo:** `POST /api/en1/v1/security-matrix/apply` — body en `ODOO_MODULO_EN1_ESPECIFICACION.md` §8; avisar a Modecosa cuando EN1 confirme.

---

## Pagos (sin cambios)

Webhooks EN1 → Odoo siguen con `ODOO_API_URL`, `ODOO_API_KEY`, `ODOO_HMAC_SECRET` (`odoo_integration_service.py`).
