# Handoff IIUS ↔ DEV (cerrado 2026-05-22)

## Git — alineado

| Ref | Commit |
|-----|--------|
| `develop` / `origin/develop` | `9330cfc` |
| Tag `iius-go-20260522` | `9330cfc` |
| IIUS prod HEAD | `9330cfc` (checkout tag) |

Rama `release/iius-go-20260522` mergeada en DEV. **Tarball / scp:** no obligatorio.

## IIUS prod — hecho

- `git checkout iius-go-20260522` + `nodeone.service` active
- Migraciones runbook §3 (idempotentes)
- Semillas: `seed_academic_programs_iius_all.py`, taller, `bootstrap_iius_org_host.py`
- `go_iius_validate_all.sh` → OK (gate OK en IIUS; en DEV multi-tenant el gate puede FAIL — esperable)

## DEV — referencia

- `.env`: `/opt/easynodeone/dev/.env` (no `app/.env`)
- `run_etapa1_dev_validation.py`: 22 OK con Postgres

## Siguiente (Fase 3)

Ver **`IIUS_FASE3_PAYPAL_Y_QA.md`**: PayPal live + pruebas en `apps.internationalinstitute.us`.
