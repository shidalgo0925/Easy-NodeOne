# Login auth gate — mapa de assets oficiales (no regenerar logos)

Fuente de verdad de UI: `static/images/auth/login-master.png`
Los logos/marcas salen solo de estos archivos (nunca recrear desde el mockup).

| Objeto | Asset oficial | Notas |
|--------|---------------|--------|
| Logo header ETS | `images/auth/ets-logo.png` | Easy Technology Services |
| Logo header EN1 | `images/auth/en1-logo.png` | Easy NodeOne |
| Card 01 EPosOne | `images/auth/card-eposone.png` | Visual POS + impresora (fondo blanco, card `--visual`) |
| Card 02 EPayRoll | `images/auth/card-epayroll.png` | Marca oficial EPayRoll (logo completo, card `--lg`) |
| Card 03 Easy Class One | `images/auth/card-easyclassone.png` | Robot mascota (crop banner oficial, card `--visual`) |
| Card 04 EM+acción | `images/auth/card-em.png` | Marca oficial EM+acción (emblema + wordmark) |
| Card 05 EasyIA | `images/auth/card-easyia.png` | Marca oficial EasyIA (capa IA transversal) |
| Card 06 Easy Thesis | `images/auth/card-easythesis.png` | Marca oficial Easy Thesis |

Layout (desktop ≥992px):
- Página navy; columna login ~42% con card blanca; ecosistema ~58%.
- Móvil: solo card de acceso; panel ecosistema oculto.
- Cards del ecosistema: vitrina informativa (`pointer-events: none`), no navegación.
