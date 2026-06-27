# Entrega analista — Certificados EN1 + limpieza deploy (jun 2026)

**Audiencia:** analista funcional, QA, operación, gestión de release.  
**Rama de trabajo:** `develop` · **Referencia:** `33dde91`.  
**Entorno dev:** https://appdev.easynodeone.com · BD `easynodeone_dev`.  
**Relatic:** pull `33dde91` aplicado · servicio `easynodeone-relatic` reiniciado.

---

## 1. Resumen ejecutivo

Se corrigió y reorganizó el **módulo de certificados de eventos** (seminarios) en Easy NodeOne, y se añadió **regeneración masiva** de PDF emitidos.

| Problema | Solución |
|----------|----------|
| Botón **Formato** en Eventos→Certificados no respondía | Editor único de formato con enlace directo |
| Dos pantallas editaban el mismo certificado | Eliminado modal duplicado |
| Operador perdido al salir de Formato/Plantilla | Parámetro `?return=` vuelve al evento |
| Código disperso | Módulo `certificates` + servicios compartidos + tests |
| Confusión builder vs editor de plantillas | Editor canónico; builder legacy redirige |
| Deploy sin limpieza de restos en disco | Scripts post-pull documentados (todos los silos) |
| Tras cambiar plantilla/formato, había que regenerar **uno por uno** | Botón **Regenerar todos (N)** en Eventos→Certificados |

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
- **Regenerar:** reemplaza PDF existente con plantilla/formato **vigentes**; no crea certificados nuevos.

---

## 3. Cambios visibles (operador admin)

| Botón | Destino / acción | Cuándo aparece |
|-------|------------------|----------------|
| Formato | `/admin/certificate-events?edit=N&return=/admin/events/E/certificates` | Evento con certificado |
| Plantilla | `/admin/certificate-templates/editor/T?return=...` | Hay plantilla vinculada |
| Vista previa | PDF ejemplo (no persiste) | Evento con certificado |
| Generar todos los elegibles | POST generación en lote | Hay participantes elegibles sin PDF |
| **Regenerar todos (N)** | POST regeneración en lote | Hay al menos 1 certificado emitido (no revocado) |
| Sync (por fila) | Regenera un solo PDF | Cada fila en tabla Emitidos |

**Regenerar todos (N):**

- Ubicación: toolbar superior (junto a Exportar) **y** cabecera de la tarjeta **Emitidos**.
- Pide confirmación antes de ejecutar.
- Omite certificados **revocados** o **inactivos**.
- Mensaje flash al terminar: regenerados, omitidos y hasta 4 errores.

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
| `2bd6dc9` | Entrega analista (documentación jun 2026) |
| **`33dde91`** | **Regenerar todos los certificados del evento** |

---

## 5. Pruebas automatizadas

13 tests OK en `test_event_certificates` (+ verify/render en suite certificados).

Nuevo: `test_regenerate_bulk_skips_revoked` — valida que la regeneración masiva omite revocados.

### Checklist QA manual

1. Evento con certificado → Guardar → formato creado visible.
2. Eventos→Certificados → Formato → editar → volver al evento.
3. Plantilla → subir imagen → guardar → volver al evento.
4. Check-in → Generar PDF → verificar enlace `/verify/<código>`.
5. `/admin/certificates-builder` redirige al editor de plantillas.
6. **Con certificados emitidos:** aparece **Regenerar todos (N)** en toolbar y en Emitidos.
7. **Regenerar todos:** confirmar → flash con conteo → PDF descargables actualizados.
8. **Regenerar todos** no aparece si no hay emitidos (solo elegibles pendientes).

---

## 6. Despliegue y limpieza

Tras `git pull` en cada silo:

```bash
bash app/scripts/post_deploy_cleanup.sh <dev|staging|prod|relatic|iius>
sudo systemctl restart easynodeone-<silo>
```

**Relatic (jun 2026):** `git pull origin develop` hasta `33dde91` + `systemctl restart easynodeone-relatic`.

Documentación: [`EN1_DEPLOY_LIMPIEZA_CONTEXTO.md`](EN1_DEPLOY_LIMPIEZA_CONTEXTO.md).

**No toca:** uploads de usuario, `.env`, base de datos.

---

## 7. Documentación técnica

| Documento | Uso |
|-----------|-----|
| [`EN1_CERTIFICADOS_EVENTOS_CONTEXTO.md`](EN1_CERTIFICADOS_EVENTOS_CONTEXTO.md) | Detalle técnico certificados (incl. regeneración masiva) |
| [`EN1_DEPLOY_LIMPIEZA_CONTEXTO.md`](EN1_DEPLOY_LIMPIEZA_CONTEXTO.md) | Limpieza post-deploy |
| [`CHECKLIST_ACTUALIZACION_Y_CLIENTES.md`](CHECKLIST_ACTUALIZACION_Y_CLIENTES.md) | Deploy y clientes |
| [`MANUAL_OPERATIVO_RELATIC_CERTIFICADOS_EVENTOS.md`](MANUAL_OPERATIVO_RELATIC_CERTIFICADOS_EVENTOS.md) | Operación Relatic |

---

## 8. Pendientes conocidos

- Fase 6 (epic `app.py`): reducir monolito y shims legacy.
- Template `certificates_builder/editor.html` aún en repo (ruta redirige).
- Auto-emitir PDF al check-in: no acordado.
- Validar cron `repair_certificates_job` en servidor si aplica.
- Staging/prod: pendiente pull de `33dde91` si aún no desplegado.

---

## 9. Criterio de cierre release

- [ ] QA manual en entorno destino (mínimo checklist §5).
- [ ] `post_deploy_cleanup.sh` ejecutado tras pull.
- [ ] Servicio `active` y smoke test login + pantalla certificados evento.
- [ ] Probar **Regenerar todos** en evento con ≥2 PDF emitidos.
- [ ] Commit/tag registrado en bitácora de release.

---

## 10. Nota operativa Relatic (evento revisores)

Contexto de datos (fuera del código, jun 2026):

- Evento **id=3** «Certificados para revisores» — 51 certificados emitidos en BD operativa.
- Lista maestra XLS: 41 revisores; UPDATE masivo de documento/teléfono aplicado; 12 participantes sin match al XLS (no insertados por decisión de negocio).

Tras cambios de plantilla en Relatic, usar **Regenerar todos** para actualizar los 51 PDF de una vez.
