#!/usr/bin/env bash
# ==============================================================================
# Script de Construcción para Render - Software de Inventarios P.M.E.
# ==============================================================================
# Este script se ejecuta en el paso 'Build Command' de Render.
# NOTA IMPORTANTE: Por directiva de arquitectura, NO ejecuta migraciones
# automáticamente. Las migraciones son revisadas y ejecutadas manualmente.
# ==============================================================================

set -o errexit

echo "==> [1/3] Actualizando gestor de paquetes pip..."
pip install --upgrade pip

echo "==> [2/3] Instalando dependencias del proyecto..."
pip install -r requirements.txt

echo "==> [3/3] Compilando archivos estáticos con WhiteNoise..."
python manage.py collectstatic --no-input

echo "==> Construcción finalizada con éxito."
