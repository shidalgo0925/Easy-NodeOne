# Handoff CODITO → LOCAL (Onboarding)

| Item | Valor |
|------|--------|
| Tag Gate 2 (HTTP freeze) | **`eposone-onboarding-p0-v1.3`** |
| Remoto | `git@github.com:shidalgo0925/Easy-NodeOne.git` |
| Leer primero | **[`GATE1_HTTP_FROZEN_FOR_LOCAL.md`](GATE1_HTTP_FROZEN_FOR_LOCAL.md)** |

```bash
git remote add en1-codito git@github.com:shidalgo0925/Easy-NodeOne.git 2>/dev/null || true
git fetch en1-codito tag eposone-onboarding-p0-v1.3
git checkout eposone-onboarding-p0-v1.3 -- Doc/EN1_ONBOARDING_P0
git add Doc/EN1_ONBOARDING_P0
git commit -m "docs(onboarding): import CODITO Gate1 HTTP freeze (eposone-onboarding-p0-v1.3)"
```

Tags anteriores (`v1`, `v1.1`, `v1.2`) quedan históricos; **Gate 2 usa v1.3**.
