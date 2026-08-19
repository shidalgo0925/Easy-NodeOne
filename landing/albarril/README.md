# Al Barril — tenant + menú digital

| URL | Qué es |
|-----|--------|
| https://albarril.etsrv.site/ | Login EN1 (tenant `albarril`) |
| https://albarril.etsrv.site/menu | Menú digital (91 productos) |
| https://albarril.etsrv.site/login | Entrar a la app |

| Dato | Valor |
|------|--------|
| Org | `id=8` · Al Barril · subdomain `albarril` |
| Menú | `MENU-0001` · activo · desde `CoreProduct` |
| Nginx | proxy EN1 `9102` + `/menu` → `/m/eposone/<token>` |
| DNS | `A → 194.60.201.29` (Cloudflare OK) |

Para regenerar el menú desde productos (PRD):

```bash
cd /opt/easynodeone/prod/app/backend && ../venv/bin/python  # o script one-off
# DigitalMenuService.create_menu(8, name='Al Barril', items=[...])
```

Tras desplegar el código de `public_routes` (`/menu` por Host), se puede quitar el `return 302` fijo del nginx.
