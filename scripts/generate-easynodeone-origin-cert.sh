#!/usr/bin/env bash
# Certificado TLS de origen para Nginx (Easy NodeOne + Moodle).
# Mismo par que usan todos los server { listen 443 ssl; } de nodeone/moodle.
#
# Uso (en el servidor):
#   sudo bash scripts/generate-easynodeone-origin-cert.sh
#
# Con Cloudflare en "Full (strict)", sustituí estos PEM por un Origin Certificate
# del panel (SSL/TLS → Origin Server) con al menos:
#   easynodeone.com, *.easynodeone.com
# (cubre cualquier subdominio de un nivel; no hace falta un .pem por host).
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
SSL_DIR="${EASYNODEONE_SSL_DIR:-/etc/nginx/ssl/easynodeone}"
KEY="${SSL_DIR}/app-origin-key.pem"
CRT="${SSL_DIR}/app-origin.pem"
DAYS="${EASYNODEONE_ORIGIN_CERT_DAYS:-3650}"

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Ejecutar con sudo: sudo $0"
  exit 1
fi

mkdir -p "$SSL_DIR"

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# SAN: raíz + wildcard + nombres explícitos (mismo estilo que app/apps/cursos).
cat >"$TMP/openssl.cnf" <<'EOF'
[req]
distinguished_name = req_distinguished_name
x509_extensions = v3_req
prompt = no

[req_distinguished_name]
CN = easynodeone.com

[v3_req]
keyUsage = digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth
subjectAltName = @alt_names

[alt_names]
DNS.1 = easynodeone.com
DNS.2 = *.easynodeone.com
DNS.3 = apps.easynodeone.com
DNS.4 = app1.easynodeone.com
DNS.5 = tonysonax.easynodeone.com
DNS.6 = cursos.easynodeone.com
EOF

openssl req -x509 -nodes -newkey rsa:2048 \
  -days "$DAYS" \
  -keyout "$KEY" \
  -out "$CRT" \
  -config "$TMP/openssl.cnf" \
  -extensions v3_req

chmod 640 "$KEY"
chmod 644 "$CRT"
chown root:root "$KEY" "$CRT"

echo "Generado:"
echo "  $CRT"
echo "  $KEY"
openssl x509 -in "$CRT" -noout -subject -dates
echo "SAN:"
openssl x509 -in "$CRT" -noout -text | sed -n '/Subject Alternative Name/,+2p'

if command -v nginx >/dev/null 2>&1; then
  nginx -t && systemctl reload nginx && echo "OK: nginx -t y reload."
else
  echo "nginx no encontrado; recargá manualmente tras copiar el conf."
fi
