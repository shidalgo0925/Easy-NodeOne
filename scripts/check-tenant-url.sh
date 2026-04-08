#!/usr/bin/env bash
# Comprueba manualmente qué falta para que un subdominio tenant responda.
# Uso: ./scripts/check-tenant-url.sh barber
#      PUBLIC_HOST=easynodeone.com ./scripts/check-tenant-url.sh barber
set -euo pipefail
SUB="${1:?Uso: $0 <subdominio_sin_puntos>}"
BASE="${PUBLIC_HOST:-easynodeone.com}"
FQDN="${SUB}.${BASE}"

echo "=== 1) DNS (desde esta máquina) ==="
if command -v getent >/dev/null && getent hosts "$FQDN" 2>/dev/null; then
  getent hosts "$FQDN"
else
  python3 -c "import socket; print(socket.gethostbyname('$FQDN'))" 2>/dev/null && echo "OK resolve" || echo "FALTA: $FQDN no resuelve → en Cloudflare: A o CNAME de barber (o *.${BASE}) al origen."
fi

echo ""
echo "=== 2) Nginx en este servidor (Host header) ==="
for port in 80; do
  code=$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:${port}/" -H "Host: ${FQDN}" --connect-timeout 3 || echo "000")
  echo "  :${port} Host=${FQDN} → HTTP ${code}"
done

echo ""
echo "=== 3) Flask directo (9001), sin Nginx ==="
code=$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:9001/" -H "Host: ${FQDN}" --connect-timeout 3 || echo "000")
echo "  9001 Host=${FQDN} → HTTP ${code} (302/login esperable si app vive)"

echo ""
echo "=== 4) Checklist manual ==="
echo "  [ ] Cloudflare DNS: ${FQDN} o *.${BASE} → IP/origen correcto"
echo "  [ ] Nginx: server_name *.${BASE} en :80 (y :443 si usás HTTPS directo al origen)"
echo "  [ ] Certificado origen: SAN *.${BASE} si querés HTTPS sin aviso (443 tenant)"
echo "  [ ] No abrir el portal tenant dentro de un iframe si la URL falla (Chrome → chrome-error)"
echo "  [ ] Preferir https://${FQDN}/ ; CSP ya permite http+https en frame-src para *.${BASE}"
