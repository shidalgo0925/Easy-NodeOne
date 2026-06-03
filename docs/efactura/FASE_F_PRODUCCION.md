# Fase F — Producción y hardening

**Dependencias:** Fases A–E según alcance acordado para go-live.

## Objetivo

Cifrado de tokens, migraciones limpias, pruebas multitenant, sandbox vs producción, documentación usuario final.

---

## F.1 Cifrado `api_token_encrypted`

Opciones (elegir una con arquitectura EN1):

1. **Fernet** con clave `EFACTURA_TOKEN_ENCRYPTION_KEY` en env del servidor
2. Reutilizar patrón de secretos de pagos si existe columna cifrada

Implementar:

- `encrypt_token(plain) -> str`
- `decrypt_token(cipher) -> str`
- Nunca serializar token en `request_payload` / logs

Migración: script one-shot para cifrar tokens en claro existentes en staging.

---

## F.2 Ambientes

| `environment` | Comportamiento |
|---------------|----------------|
| `sandbox` | Token de pruebas; validar `iAmb=2` en respuestas |
| `production` | Token producción; bloquear emisión test desde UI prod (flag) |

Validar en config UI que no se mezclen URLs.

---

## F.3 Permisos RBAC

Permiso sugerido: `efactura.manage` (config + emisión manual)

`efactura.view` (solo lectura emisiones/logs)

Integrar con `nav_can` / matriz de seguridad si aplica tenant.

Admin plataforma: todas las orgs con scope selector.

---

## F.4 Migraciones

- Script SQL versionado en `nodeone/services/migrations/` (patrón PG del proyecto)
- Rollback documentado
- Índices revisados con EXPLAIN en listados

---

## F.5 Pruebas

| Tipo | Qué |
|------|-----|
| Unit | mapper, validation |
| Integración | adapter mock + adapter sandbox (token CI secreto) |
| Manual | checklist staging con org real de prueba |

No commitear tokens en repo; usar CI secrets.

---

## F.6 Documentación usuario

Crear `docs/efactura/MANUAL_USUARIO.md` (admin tenant):

- Activar módulo en SaaS
- Configurar token efacturapty
- Probar conexión
- Emitir primera FE
- Qué hacer si error / reintento

---

## F.7 Go-live checklist

- [ ] `NODEONE_EFACTURA_MODULE_ENABLED=1` en prod
- [ ] Solo orgs acordadas con `efactura` ON en SaaS
- [ ] Tokens producción en vault/env
- [ ] Token de prueba revocado si se filtró
- [ ] Backup BD antes de migración
- [ ] Monitoreo: alertas si `status=error` > umbral
- [ ] Rollback: desactivar módulo global=0 sin perder datos

---

## F.8 Post go-live

- Métricas en analytics (opcional): FE emitidas por mes
- Evaluar segundo PAC: implementar `adapters/hka.py` sin cambiar servicios
