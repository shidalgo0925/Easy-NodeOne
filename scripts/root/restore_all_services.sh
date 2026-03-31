#!/bin/bash

echo "=========================================="
echo "RESTAURANDO CONFIGURACIÓN ORIGINAL"
echo "=========================================="
echo ""

echo "1. Recargando configuración de systemd..."
sudo systemctl daemon-reload
echo ""

echo "2. Verificando configuración de nginx..."
sudo nginx -t
if [ $? -ne 0 ]; then
    echo "❌ Error en configuración de nginx"
    exit 1
fi
echo ""

echo "3. Iniciando relatic-frontend (puerto 5173)..."
sudo systemctl start relatic-frontend.service
sleep 2
sudo systemctl status relatic-frontend.service --no-pager -l | head -10
echo ""

echo "4. Iniciando membresia-relatic (puerto 9000)..."
sudo systemctl start membresia-relatic.service
sleep 2
sudo systemctl status membresia-relatic.service --no-pager -l | head -10
echo ""

echo "5. Recargando nginx..."
sudo systemctl reload nginx
echo ""

echo "6. Verificando puertos..."
echo "Puerto 5173 (relatic-frontend):"
sudo ss -tlnp | grep :5173 || echo "❌ No está en uso"
echo ""
echo "Puerto 9000 (membresia-relatic):"
sudo ss -tlnp | grep :9000 || echo "❌ No está en uso"
echo ""

echo "=========================================="
echo "RESUMEN DE CONFIGURACIÓN:"
echo "=========================================="
echo "✅ dev.relatic.org → relatic-frontend (puerto 5173)"
echo "✅ miembros.relatic.org → membresia-relatic (puerto 9000)"
echo ""
echo "Verificar servicios:"
echo "  sudo systemctl status relatic-frontend.service"
echo "  sudo systemctl status membresia-relatic.service"
echo ""

