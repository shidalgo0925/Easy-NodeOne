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

echo "3. Iniciando example-frontend (puerto 5173)..."
sudo systemctl start example-frontend.service
sleep 2
sudo systemctl status example-frontend.service --no-pager -l | head -10
echo ""

echo "4. Iniciando nodeone (puerto 9000)..."
sudo systemctl start nodeone.service
sleep 2
sudo systemctl status nodeone.service --no-pager -l | head -10
echo ""

echo "5. Recargando nginx..."
sudo systemctl reload nginx
echo ""

echo "6. Verificando puertos..."
echo "Puerto 5173 (example-frontend):"
sudo ss -tlnp | grep :5173 || echo "❌ No está en uso"
echo ""
echo "Puerto 9000 (nodeone):"
sudo ss -tlnp | grep :9000 || echo "❌ No está en uso"
echo ""

echo "=========================================="
echo "RESUMEN DE CONFIGURACIÓN:"
echo "=========================================="
echo "✅ dev.app.example.com → example-frontend (puerto 5173)"
echo "✅ app.example.com → nodeone (puerto 9000)"
echo ""
echo "Verificar servicios:"
echo "  sudo systemctl status example-frontend.service"
echo "  sudo systemctl status nodeone.service"
echo ""

