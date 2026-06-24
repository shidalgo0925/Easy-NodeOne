# Entrega analista — Certificados EN1 + limpieza deploy (jun 2026)

**Audiencia:** analista funcional, QA, operación, gestión de release.  
**Rama de trabajo:** `develop` · **Referencia:** `be7f76a` (y merges posteriores en `main`).  
**Entorno dev:** https://appdev.easynodeone.com · BD `easynodeone_dev`.

---

## 1. Resumen ejecutivo

Se corrigió y reorganizó el **módulo de certificados de eventos** (seminarios) en Easy NodeOne.

| Problema | Solución |
|----------|----------|
| Botón **Formato** en Eventos→Certificados no respondía | Editor único de formato con enlace directo |
| Dos pantallas editaban el mismo certificado | Eliminado modal duplicado |
| Operador perdido al salir de Formato/Plantilla | Parámetro `?return=` vuelve al evento |
| Código disperso | Módulo `certificates` + servicios compartidos + tests |
| Confusión builder vs editor de plantillas | Editor canónico; builder legacy redirige |
| Deploy sin limpieza de restos en disco | Scripts post-pull documentados (todos los silos) |

---

## 2. Modelo funcional (tres capas)

```
Evento (has_certificate = true)
├── FORMATO   → certificate_events      (datos institucionales)
├── PLANTILLA → certificate_templates   (diseño PDF)
└── PDF       → event_certificate       (emitido por participante)
```

**Reglas de negocio:**

- **Formato:** automático al guardar evento con certificado; editable desde Eventos→Certificados→Formato.
- **Plantilla:** solo se crea si no existe; no se sobrescribe diseño ya editado por el usuario.
- **PDF:** requiere check-in (o revisor) + acción Generar; no se emite solo.

---

## 3. Cambios visibles (operador admin)

| Botón | Destino | Al guardar / volver |
|-------|---------|---------------------|
| Formato | `/admin/certificate-events?edit=N&return=/admin/events/E/certificates` | Vuelve a certificados del evento |
| Plantilla | `/admin/certificate-templates/editor/T?return=...` | Vuelve al evento |
| Vista previa | PDF ejemplo (no persiste) | — |

- `/admin/certificates-builder` redirige al editor oficial de plantillas.
- Subida de imágenes en editor: `POST /api/templates/upload-image`.

---

## 4. Commits del release

| Commit | Contenido |
|--------|-----------|
| `1d878d4` | Navegación formato único + `?return=` |
| `314d1f7` | Refactor certificados fases 0–4 |
| `42c20b7` | Fase 5: upload unificado, redirect builder |
| `be7f76a` | Scripts limpieza post-deploy + documentación |

---

## 5. Pruebas automatizadas

20 tests OK: `test_event_certificates`, `test_certificate_verify`, `test_certificate_render`.

### Checklist QA manual

1. Evento con certificado → Guardar → formato creado visible.
2. Eventos→Certificados → Formato → editar → volver al evento.
3. Plantilla → subir imagen → guardar → volver al evento.
4. Check-in → Generar PDF → verificar enlace `/verify/<código>`.
5. `/admin/certificates-builder` redirige al editor de plantillas.

---

## 6. Despliegue y limpieza

Tras `git pull` en cada silo:

```bash
bash app/scripts/post_deploy_cleanup.sh <dev|staging|prod|relatic|iius>
sudo systemctl restart easynodeone-<silo>
```

Documentación: [`EN1_DEPLOY_LIMPIEZA_CONTEXTO.md`](EN1_DEPLOY_LIMPIEZA_CONTEXTO.md).

**No toca:** uploads de usuario, `.env`, base de datos.

---

## 7. Documentación técnica

| Documento | Uso |
|-----------|-----|
| [`EN1_CERTIFICADOS_EVENTOS_CONTEXTO.md`](EN1_CERTIFICADOS_EVENTOS_CONTEXTO.md) | Detalle técnico certificados |
| [`EN1_DEPLOY_LIMPIEZA_CONTEXTO.md`](EN1_DEPLOY_LIMPIEZA_CONTEXTO.md) | Limpieza post-deploy |
| [`CHECKLIST_ACTUALIZACION_Y_CLIENTES.md`](CHECKLIST_ACTUALIZACION_Y_CLIENTES.md) | Deploy y clientes |
| [`MANUAL_OPERATIVO_RELATIC_CERTIFICADOS_EVENTOS.md`](MANUAL_OPERATIVO_RELATIC_CERTIFICADOS_EVENTOS.md) | Operación Relatic |

---

## 8. Pendientes conocidos

- Fase 6 (epic `app.py`): reducir monolito y shims legacy.
- Template `certificates_builder/editor.html` aún en repo (ruta redirige).
- Auto-emitir PDF al check-in: no acordado.
- Validar cron `repair_certificates_job` en servidor si aplica.

---

## 9. Criterio de cierre release

- [ ] QA manual en entorno destino (mínimo checklist §5).
- [ ] `post_deploy_cleanup.sh` ejecutado tras pull.
- [ ] Servicio `active` y smoke test login + pantalla certificados evento.
- [ ] Commit/tag registrado en bitácora de release.
