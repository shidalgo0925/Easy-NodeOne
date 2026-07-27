#!/usr/bin/env bash
# Emite Let's Encrypt para api-ai.easynodeone.com y apunta Nginx a los PEM correctos.
set -euo pipefail
DOMAIN="api-ai.easynodeone.com"
NGINX_SITE="/etc/nginx/sites-available/api-ai.easynodeone.com"
WEBROOT="/var/www/html"

if ! dig +short "$DOMAIN" @1.1.1.1 | grep -qE '^[0-9.]+$'; then
  echo "ERROR: $DOMAIN sin registro A público (NXDOMAIN o sin propagación)." >&2
  echo "Crea A -> IP del servidor; espera propagación; vuelve a ejecutar." >&2
  exit 1
fi

echo "Certbot webroot..."
sudo certbot certonly --webroot -w "$WEBROOT" -d "$DOMAIN" \
  --non-interactive --agree-tos --register-unsafely-without-email

sudo sed -i \
  's|^[[:space:]]*ssl_certificate[[:space:]].*|    ssl_certificate     /etc/letsencrypt/live/api-ai.easynodeone.com/fullchain.pem;|' \
  "$NGINX_SITE"
sudo sed -i \
  's|^[[:space:]]*ssl_certificate_key[[:space:]].*|    ssl_certificate_key /etc/letsencrypt/live/api-ai.easynodeone.com/privkey.pem;|' \
  "$NGINX_SITE"

sudo nginx -t
sudo systemctl reload nginx
echo "OK: https://$DOMAIN usa Let's Encrypt."
