# EN1 Onboarding P0 — Freeze pack for LOCAL

| Campo | Valor |
|-------|--------|
| Emisor | **CODITO** |
| Destino | Repo **LOCAL** (EP1 / EPosOne APK) |
| Gate | Contratos P0 antes de Fases 1–7 |
| Estado | **Frozen para sync** — sin inventar HTTP en LOCAL |
| Fecha | 6 ago 2026 |

---

## Fuente Git (Easy-NodeOne)

| Item | Valor |
|------|--------|
| Remoto | `git@github.com:shidalgo0925/Easy-NodeOne.git` |
| HTTPS | `https://github.com/shidalgo0925/Easy-NodeOne.git` |
| Tag | **`eposone-onboarding-p0-v1`** |
| Carpeta canónica en EN1 | **`Doc/EN1_ONBOARDING_P0/`** (este pack) |
| Copia normativa EN1 | `docs/eposone-onboarding/` + `docs/ADR-027-…` |

### Sync al repo LOCAL

```bash
# En el repositorio LOCAL:
git remote add en1-codito git@github.com:shidalgo0925/Easy-NodeOne.git 2>/dev/null || true
git fetch en1-codito tag eposone-onboarding-p0-v1

# Traer el pack a Doc/ (ruta que espera el gate LOCAL)
git checkout eposone-onboarding-p0-v1 -- Doc/EN1_ONBOARDING_P0

git add Doc/EN1_ONBOARDING_P0
git commit -m "docs(onboarding): import CODITO P0 contracts (eposone-onboarding-p0-v1)"
```

Alternativa sin remote permanente:

```bash
git clone --depth 1 --branch eposone-onboarding-p0-v1 \
  git@github.com:shidalgo0925/Easy-NodeOne.git /tmp/en1-onboarding-p0
cp -a /tmp/en1-onboarding-p0/Doc/EN1_ONBOARDING_P0 "$(git rev-parse --show-toplevel)/Doc/"
# commit en LOCAL
```

### Verificación Gate 0 (LOCAL)

```bash
test -f Doc/EN1_ONBOARDING_P0/ONBOARDING_CONTRACT_V2.md
test -f Doc/EN1_ONBOARDING_P0/DEVICE_LIFECYCLE_V1.md
test -f Doc/EN1_ONBOARDING_P0/LOGIN_CONTRACT_V1.md
test -f Doc/EN1_ONBOARDING_P0/RESTORE_CONTRACT_V1.md
test -f Doc/EN1_ONBOARDING_P0/QR_CONTRACT_V1.md
test -f Doc/EN1_ONBOARDING_P0/ADR-027-EPOSONE-ONBOARDING-UNIFICADO-V1.md
test -f Doc/EN1_ONBOARDING_P0/ADR-014-SUBSCRIPTION-REGISTRY.md
```

---

## Contenido del pack (checklist LOCAL)

| Requisito gate LOCAL | Archivo en este pack |
|----------------------|----------------------|
| Contrato único onboarding | `ONBOARDING_CONTRACT_V2.md` |
| Device Lifecycle | `DEVICE_LIFECYCLE_V1.md` |
| Login EN1 formalizado | `LOGIN_CONTRACT_V1.md` |
| Restore formalizado | `RESTORE_CONTRACT_V1.md` |
| QR técnico (payload) | `QR_CONTRACT_V1.md` |
| Modalidad Standalone/Connected | `ADR-027-…` + enmienda en `ADR-014-…` + Onboarding V2 |
| ADR lifecycle / onboarding CODITO | **`ADR-027`** (marco) + Device Lifecycle — **no** confundir con ADR-014 solo |
| ADR-014 | Incluido **con enmienda de modalidad** (no es el as-is previo al P0) |

Índice / gates: ver también `README_GATES.md` si se añade; el índice largo está en la copia histórica `docs/eposone-onboarding/README.md` en EN1 (mismo contenido de gates en sección abajo).

### Gates (resumen)

- **Gate 0:** este pack en `Doc/` de LOCAL → luego Fases 1–7.  
- **Gate 1:** EN1 expone `modality` en Device API (código futuro).  
- Sin inventar HTTP: reutilizar Register + Bootstrap; Login/Restore payload = contrato lógico hasta GO EN1 API.

---

## Nota sobre ADR-014

LOCAL reportó “sigue ADR-014 as-is”. El freeze incluye **ADR-014 enmendado** (sección *Modalidad comercial*, 6 ago 2026) + **ADR-027** como ADR de onboarding/lifecycle de producto. Device Lifecycle no vive dentro de ADR-014.

---

## Confirmación

LOCAL puede responder: *Onboarding P0 recibido — tag `eposone-onboarding-p0-v1` en `Doc/EN1_ONBOARDING_P0/`.*
