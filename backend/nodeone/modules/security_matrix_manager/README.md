# security_matrix_manager (Fase 1)

Gobierno de permisos Odoo: catálogo `en1_connector`, matriz XLS, validación, preview e IA. **No ejecuta cambios en Odoo.**

## Variables `.env`

```bash
ODOO_CATALOG_URL=https://erp.modecosa.com/api/en1/v1/security-catalog
ODOO_CATALOG_API_KEY=...
ODOO_DB=modecosa
ODOO_CATALOG_TIMEOUT=30
```

## Rutas

- `GET /admin/security-matrix`
- `POST /admin/security-matrix/sync-catalog`
- `GET /admin/security-matrix/template`
- `POST /admin/security-matrix/upload`
- `GET /admin/security-matrix/imports/<id>`
- `POST .../analyze-ai`, `/approve`, `/reject`, `/execute` (501)
- `GET .../report` (`?format=json`)

## Permiso

`security_matrix.admin` (semilla SA/AD en primer request o `migrate_security_matrix_module.py`).

## Desactivar

`NODEONE_SKIP_SECURITY_MATRIX_MODULE=1`
