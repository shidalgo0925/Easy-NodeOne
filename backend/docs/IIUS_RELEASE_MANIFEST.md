# IIUS — manifiesto de release (empaquetar en `develop`)

Silo origen: `/opt/easynodeone/app` · Base commit desplegado: `63203e6` · Tag rollback: `iius-pre-etapa2-20260522`

**Commit autorizado solo desde** `/opt/easynodeone/dev/app` (no existe en este host IIUS).

## Tag sugerido tras commit

```bash
git tag -a iius-go-20260522 -m "IIUS: pagos matriz, academic_closed, campus, branding"
```

## Áreas incluidas

| Área | Archivos clave |
|------|----------------|
| Pagos / matriz | `organization_payment_methods.py`, `payments_admin/routes.py`, `admin/payments.html`, `verify_payments_tenant_setup.py`, `run_etapa1_dev_validation.py` |
| Académico | `academic_enrollment/*`, `academic_access.py`, `registration_policy.py`, `payments/routes.py`, `session_helpers.py` |
| UI | `base.html`, `dashboard.html`, `program_enrollment.html`, `iius-enrollment-landings.css`, branding `app.py` |
| Docs | `ETAPA1_NORMALIZACION_CIERRE.md`, `IIUS_GO_CHECKLIST.md`, `EN1_IIUS_ACADEMIC_CLOSED.md`, `IIUS_PAYPAL_LIVE.md`, `IIUS_RELEASE_MANIFEST.md` |
| Scripts | `seed_academic_programs_iius_all.py`, `reconcile_academic_enrollments_paid.py`, `test_academic_*.py` |

## Post-deploy IIUS

```bash
cd backend && source ../.venv/bin/activate
export NODEONE_BRAND_PRESET=iius
python3 scripts/seed_academic_programs_iius_all.py 1
python3 scripts/seed_academic_program_iius_neuro.py 1  # no-op si ya existe
python3 scripts/bootstrap_iius_org_host.py 1
# migraciones según ETAPA2_IIUS_RUNBOOK.md
sudo systemctl restart nodeone.service
```

## Validación

```bash
cd backend && bash scripts/go_iius_validate_all.sh
```

Ver `IIUS_GO_CHECKLIST.md`.

## Lista de archivos (47 rutas en silo IIUS)

Generar de nuevo:

```bash
bash backend/scripts/export_iius_commit_paths.sh > /tmp/iius-commit-paths.txt
```

En **dev/app**: copiar esas rutas desde el silo o aplicar el mismo diff sobre `develop`, luego:

```bash
git add -A   # revisar que no entren secretos (.env)
git commit -m "IIUS: matriz pagos, campus academic_closed, programas BD, branding"
git tag -a iius-go-20260522 -m "Release IIUS operativo mayo 2026"
```

## Semillas post-deploy (catálogo)

```bash
python3 scripts/seed_academic_programs_iius_all.py 1
python3 scripts/seed_academic_program_iius_sample_taller.py 1   # opcional taller demo
```
