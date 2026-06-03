# Campus académico cerrado (`academic_closed`)

## Política

- Valor en `saas_organization.registration_policy`: **`academic_closed`**
- IIUS (org 1): activar en Plataforma → Empresas → Editar, o:

```bash
cd backend && python3 -c "
from app import app, db
from models.saas import SaasOrganization
with app.app_context():
    o = SaasOrganization.query.get(1)
    o.registration_policy = 'academic_closed'
    db.session.commit()
    print('OK', o.registration_policy)
"
```

## Comportamiento

| Quién | Qué ve |
|-------|--------|
| Admin / RBAC admin | Sin bloqueo (menú tenant completo) |
| Miembro **sin** matrícula `paid`/`confirmed` | Dashboard + inscripción/checkout; **no** Explorar/catálogo abierto |
| Miembro **con** matrícula | Campus + servicios según módulos SaaS |

## Matrícula

Tabla `academic_program_enrollment`, estados activos: `paid`, `confirmed`.

## Código

- `nodeone/services/academic_access.py` — middleware y helpers
- `nodeone/services/registration_policy.py` — política y registro público
- Ruta **`/mi-campus`** → dashboard `#campus-academico`

## Validación automática

```bash
cd backend && source ../.venv/bin/activate
python3 scripts/test_academic_enrollment_iius.py
python3 scripts/test_academic_gate_iius.py
```

## Reconciliar pagos completados → matrícula

```bash
python3 scripts/reconcile_academic_enrollments_paid.py
```
