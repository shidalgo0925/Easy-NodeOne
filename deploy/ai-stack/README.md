# AI stack (CODITO)

LiteLLM + PostgreSQL (virtual keys) + Ollama en host. Expuesto por HTTPS vía nginx en `api-ai.easynodeone.com`.

## Rutas en servidor

| Ruta | Uso |
|------|-----|
| `/opt/ai-stack` | Despliegue activo |
| `/opt/ai-stack/litellm/config.yaml` | Config real (no en git) |
| `/opt/ai-stack/litellm/EM_ACCION_KEY.txt` | Virtual key EM+Acción (no en git) |

## nginx

- Upstream: `127.0.0.1:4000` (`/etc/nginx/conf.d/10-litellm-upstream.conf`)
- Vhost: `api-ai.easynodeone.com` → `/v1/*` al proxy LiteLLM

## Variables cliente (EM+Acción / ARROZCONPOLLO)

```env
ACCIO_AI_PROVIDER=litellm
ACCIO_AI_BASE_URL=https://api-ai.easynodeone.com
ACCIO_AI_MODEL=qwen2.5-coder:7b
ACCIO_AI_API_KEY=<virtual key en servidor>
ACCIO_AI_ENABLED=true
AI_ASSISTANT_ENABLED=true
ACCIO_AI_TIMEOUT=120
```

`ACCIO_AI_BASE_URL` sin `/v1` al final.

## Validación

```bash
# Sin key → 401
curl -sS -o /dev/null -w "%{http_code}\n" https://api-ai.easynodeone.com/v1/models

# Con key → 200
curl -sS https://api-ai.easynodeone.com/v1/models \
  -H "Authorization: Bearer <KEY>"
```

## Generar virtual key (en CODITO, con master key)

```bash
curl -X POST http://127.0.0.1:4000/key/generate \
  -H "Authorization: Bearer <MASTER_KEY>" \
  -H "Content-Type: application/json" \
  -d '{"key_alias":"cliente","models":["qwen2.5-coder:7b"],"duration":"365d"}'
```

## SSL

`scripts/issue-api-ai-letsencrypt.sh` — Let's Encrypt para `api-ai.easynodeone.com`.
