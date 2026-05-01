# QR tools (simple link → PNG)

Herramienta mínima **sin base de datos**, sin SaaS.

- **API:** `POST /api/tools/qr/generate` — JSON `{ "url": "https://…" }` → PNG (`Content-Type: image/png`, adjunto `qr.png`).
- **UI:** `GET /tools/qr/simple` (usuario autenticado con Flask-Login).

La ruta **`/tools/qr`** está reservada al módulo **Generador QR** (`qr_generator`). Esta pantalla usa **`/tools/qr/simple`** para no solaparse.

- `NODEONE_SKIP_QR_TOOLS_MODULE=1` — no registrar blueprint ni página.

`qrcode[pil]` está en `requirements.txt` del proyecto.
