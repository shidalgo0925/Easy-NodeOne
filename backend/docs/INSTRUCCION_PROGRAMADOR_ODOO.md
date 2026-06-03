# Instrucción al programador Odoo (Modecosa) — resumen ejecutivo

**Para:** desarrollador del ERP Odoo 19 (Modecosa)  
**De:** equipo EN1 (EasyNodeOne)  

**Estado Fase 1:** **ENTREGADA** — `en1_connector` **19.0.1.0.0** en `erp.modecosa.com`.  
Configuración EN1: `docs/EN1_ODOO_CATALOG_CONFIG.md`.

---

## Qué necesitamos (Fase 1 — cumplido)

Un **módulo Odoo** que exporte un **JSON estándar** con el catálogo de seguridad actual. EN1 lo descargará por HTTPS (una llamada) para validar Excel y mostrar preview. **No** queremos usuario/contraseña XML-RPC en el servidor EN1.

---

## Entregable mínimo (Fase 1)

1. **Módulo** `en1_connector` (nombre negociable).
2. **Endpoint** (solo lectura):

   ```
   GET https://erp.modecosa.com/api/en1/v1/security-catalog
   Authorization: Bearer <API_KEY_SOLO_LECTURA>
   X-Odoo-Database: modecosa
   ```
   (alternativa: `?db=modecosa`)

3. **Cuerpo de respuesta:** según especificación completa y ejemplos:

   | Documento | Ruta en repo EN1 |
   |-----------|------------------|
   | Especificación completa | `docs/ODOO_MODULO_EN1_ESPECIFICACION.md` |
   | JSON de ejemplo | `docs/schemas/en1_security_catalog_v1.example.json` |
   | JSON Schema | `docs/schemas/en1_security_catalog_v1.schema.json` |

4. **Datos obligatorios en el JSON:**

   - `users`: id, login, name, active, group_ids (+ email/departamento si hay HR).
   - `groups`: id, name, **`xml_id`** (imprescindible para la matriz Excel).
   - `memberships`: cada par usuario–grupo directo.
   - `critical_groups`: lista de grupos peligrosos (contabilidad manager, inventario manager, administrador, etc.).

5. **Seguridad:**

   - API key dedicada de **solo lectura** (no es la clave de un usuario humano).
   - Preferible: allowlist IP del VPS EN1 + rate limit.
   - No exponer contraseñas ni XML-RPC público para EN1.

6. **Prueba de aceptación:** enviar API key por canal seguro; EN1 ejecuta `test_odoo_catalog.py` (~28 users, 111 groups, 153 memberships, HTTP 200).

---

## Qué NO hacer en Fase 1

- No dar a EN1 credenciales de usuario admin de Odoo.
- No implementar cambios de ACL, reglas, menús ni creación de usuarios.
- No depender de que EN1 llame `search_read` modelo por modelo (lento e inseguro).

---

## Fase 2 (después, coordinado con EN1)

Endpoint separado con **otra** API key de ejecución:

```
POST /api/en1/v1/security-matrix/apply
```

Solo acciones `add` / `remove` de usuario en grupo (`res.groups`), con log en Odoo. EN1 solo llamará tras aprobación humana en pantalla admin.

Detalle del body: sección 8 de `ODOO_MODULO_EN1_ESPECIFICACION.md`.

---

## Integración de pagos (ya existe, no mezclar)

EN1 **envía** webhooks de pago **hacia** Odoo (`ODOO_API_URL`, HMAC). Eso sigue igual. Este trabajo es **Odoo → EN1** (catálogo de permisos).

---

## Preguntas frecuentes

**¿Por qué `xml_id` en grupos?**  
La matriz Excel de EN1 referencia grupos por ID externo estable, no solo por nombre (que puede repetirse o traducirse).

**¿Podemos entregar un archivo en lugar de API?**  
Sí, si el JSON es **idéntico** al del endpoint; EN1 puede importar archivo manualmente en una primera versión.

**¿Cuántos registros?**  
Modecosa ~100+ grupos y usuarios activos; respuesta única &lt; ~5 MB, tiempo &lt; 5 s objetivo.

---

## Contacto

Adjuntar al entregar: URL base, versión del módulo, fecha del snapshot de prueba, y captura o archivo `en1_security_catalog_v1.example.json` rellenado con datos reales (sin contraseñas).
