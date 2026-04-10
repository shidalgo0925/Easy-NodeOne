#!/bin/bash

echo "=========================================="
echo "REVIRTIENDO CAMBIOS Y RESTAURANDO"
echo "=========================================="
echo ""

echo "1. Verificando configuración de nginx..."
sudo nginx -t
if [ $? -ne 0 ]; then
    echo "❌ Error en configuración de nginx - REVISAR"
    exit 1
fi
echo "✅ Configuración de nginx OK"
echo ""

echo "2. Recargando configuración de systemd..."
sudo systemctl daemon-reload
echo ""

echo "3. Recargando nginx..."
sudo systemctl reload nginx
echo "✅ Nginx recargado"
echo ""

echo "4. Verificando servicios..."
echo ""
echo "nodeone:"
sudo systemctl status nodeone.service --no-pager | head -5
echo ""
echo "example-frontend:"
sudo systemctl status example-frontend.service --no-pager | head -5
echo ""

echo "=========================================="
echo "CAMBIOS REVERTIDOS"
echo "=========================================="
echo "✅ dev.app.example.com → nodeone (puerto 9000)"
echo "✅ example-frontend.service → WorkingDirectory original restaurado"
echo ""

