#!/bin/bash
# Script para probar la verificación de un pago de Yappy usando el endpoint de la API

RECEIPT_CODE="${1:-EBOWR-38807178}"
BASE_URL="${2:-http://localhost:8080}"

echo "🔍 Verificando pago de Yappy con código: $RECEIPT_CODE"
echo "📡 Usando endpoint: $BASE_URL/api/payments/yappy/verify"
echo ""

# Hacer petición POST al endpoint de verificación (NO requiere login)
curl -X POST "$BASE_URL/api/payments/yappy/verify" \
  -H "Content-Type: application/json" \
  -d "{\"reference\": \"$RECEIPT_CODE\"}" \
  -w "\n\nHTTP Status: %{http_code}\n" \
  -s | jq '.' 2>/dev/null || cat

echo ""
echo "✅ Verificación completada"
