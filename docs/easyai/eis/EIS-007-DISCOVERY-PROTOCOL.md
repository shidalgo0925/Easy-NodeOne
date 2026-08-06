# EIS-007 — Discovery Protocol

| Campo | Valor |
|-------|--------|
| ID | **EIS-007** |
| Versión | **1.0.0** |
| Padre | EIS-000 |
| Estado | **Frozen / Approved** |

---

## 1. Propósito

Definir cómo EasyAI Core **descubre** Connectors disponibles automáticamente.

---

## 2. Mecanismos (V1)

### 2.1 Well-known (preferido por producto HTTP)

```http
GET /.well-known/easyai-connector.json HTTP/1.1
Host: {product-host}
```

Respuesta: **200** + Manifest (EIS-006) o documento índice:

```json
{
  "eis_version": "1.0.0",
  "connectors": [
    {
      "connector_id": "eposone",
      "manifest_url": "https://appprd.easynodeone.com/api/eis/v1/connectors/eposone/manifest"
    }
  ]
}
```

### 2.2 Registry estático (Connector Catalog)

EasyAI mantiene catálogo operacional (URL Manifest por ambiente). Obligatorio para productos sin HTTP público o air-gapped.

### 2.3 Push registration (opcional futuro)

Producto notifica a EasyAI Registration API — **fuera de S1**.

---

## 3. Flujo lógico

```text
1. EasyAI carga Connector Catalog (seed)
2. Para cada entrada: GET manifest_url / well-known
3. Valida Manifest (EIS-006)
4. Indexa capabilities, tools, contexts, events
5. Health check periódico GET …/health
6. Si falla N veces → lifecycle efectivo "unavailable" (no borra registro)
```

---

## 4. Caché

- Manifest cacheable (`Cache-Control` / ETag recomendados).
- TTL sugerido: 5–15 min en prod; invalidación al detectar `connector_version` nueva.

---

## 5. Seguridad

- Discovery endpoints pueden ser públicos **solo** para Manifest no secreto.
- Secrets nunca en Manifest.
- EasyAI autentica para invoke; Discovery de lectura puede ser anónimo o mTLS según producto.

---

## 6. No objetivos S1

- No implementar servidor Discovery en EN1.
- No implementar crawler en EasyAI.
- Solo dejar el protocolo listo para S2+.
