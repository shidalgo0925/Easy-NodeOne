# EIS-011 — Security

| Campo | Valor |
|-------|--------|
| ID | **EIS-011** |
| Versión | **1.0.0** |
| Estado | **Frozen / Approved** |
| Padre | EIS-000 |
| Relacionado | EIS-005 Authentication |

---

## 1. Propósito

Controles de seguridad del **canal Connector ↔ EasyAI Core**. No sustituye la Security Foundation interna de ARP (prompts, gateway, etc.).

---

## 2. Amenazas fuera de alcance del Connector

| Amenaza | Mitigación |
|---------|------------|
| Producto llama LLM directo | **Prohibido** (P11/P12) — no es canal EIS |
| Prompt injection hacia BD | Connector no acepta SQL; solo Tools tipados |
| Exfiltración masiva | Tools read con límites; sin dumps de tabla |
| Impersonación cross-tenant | Tenant claim obligatorio; validación Connector |

---

## 3. Controles obligatorios

1. **Auth** según EIS-005 en todo invoke mutante y, por defecto, en Contexts.
2. **TLS** en tránsito (ambientes no-local).
3. **Secrets** nunca en Manifest, Contexts ni respuestas Tool.
4. **PII:** documentar campos sensibles; preferir redaction en EasyAI; Connector no loguea cuerpos full por defecto (audit `metadata`).
5. **Least privilege:** capabilities mínimas en Session.
6. **Idempotency-Key** recomendada en Tools `write`.
7. **Firmas** en webhooks de Events (EIS-004 + EIS-005).
8. **Health** no expone secretos ni inventario interno sensible.

---

## 4. Separación de deberes

| Componente | Responsabilidad de seguridad |
|------------|------------------------------|
| EasyAI Core (ARP) | Gateway modelos, conversation safety, quota LLM |
| Connector (producto) | AuthZ de negocio, tenant isolation, audit de Tools |
| EIS | Contratos — no runtime |

---

## 5. Prohibiciones explícitas

- Connection strings o credenciales DB en cualquier payload EIS.
- Endpoints “raw query” o “admin sql”.
- Reenviar tokens de EasyAI a terceros.
- Usar el Connector como proxy OpenAI/Ollama.

---

## 6. Conformidad

Ver checklist §§ Security.
