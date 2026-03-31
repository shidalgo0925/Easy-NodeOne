#!/bin/bash

echo "Deteniendo servicios..."

echo "1. Deteniendo membresia-relatic.service..."
sudo systemctl stop membresia-relatic.service

echo "2. Deteniendo nginx..."
sudo systemctl stop nginx

echo "3. Verificando procesos en puerto 9000..."
sudo lsof -i :9000 || echo "Puerto 9000 libre"

echo "4. Verificando procesos en puerto 80..."
sudo lsof -i :80 || echo "Puerto 80 libre"

echo "5. Verificando procesos en puerto 443..."
sudo lsof -i :443 || echo "Puerto 443 libre"

echo ""
echo "✅ Servicios detenidos"

