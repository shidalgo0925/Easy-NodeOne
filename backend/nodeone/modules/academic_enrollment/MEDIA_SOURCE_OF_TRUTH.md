# Media de programas de inscripción (IIUS / Apps)

## Campos oficiales

| Uso | Ruta pública | Campo ORM | Admin (slot) | Upload `kind` |
|-----|----------------|-----------|--------------|----------------|
| Catálogo | `/programas` | `image_url` | ② Catálogo | `image` |
| Inscripción | `/inscripcion/<slug>` | `flyer_url` | ③ Inscripción | `flyer` |
| WordPress | `/diplomados/` (externo) | `image_wp_landing` | ① Landing WP | `wp_landing` |

## Reglas

1. **Sin fallback** entre `image_url` y `flyer_url` en vitrina ni inscripción.
2. **Sin overrides** por slug ni rutas hardcodeadas en código de render.
3. Estado **`published`** exige `image_url` y `flyer_url` no vacíos y accesibles (validación en admin).
4. Subidas admin → `save_program_media_upload` → persisten en el campo del slot (`admin_routes._save_program_from_form`).

## Código de referencia

- Lectura pública: `program_display_media.py`
- Paths por slot: `uploads.program_media_path`
- Validación al guardar: `validate_published_program_media`
- Auditoría: `scripts/audit_program_media.py`
