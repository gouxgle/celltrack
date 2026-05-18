#!/bin/bash
# ── update.sh — CellTrack VM ──────────────────────────────────────────────────
# Ejecutar EN la VM: ./update.sh
# Hace: fetch GitHub → si hay cambios, pull + restart contenedor
# ─────────────────────────────────────────────────────────────────────────────

APP_PATH="/etc/docker/celulares_flask"
CONTAINER="celltrack_web"

cd "$APP_PATH"

echo ""
echo "▶ Verificando cambios en GitHub..."
git fetch origin main -q

CHANGED=$(git diff --name-only HEAD origin/main)

if [ -z "$CHANGED" ]; then
    echo "   ✓ Sin cambios — ya estás actualizado."
    exit 0
fi

echo "   Cambios detectados:"
echo "$CHANGED" | sed 's/^/     /'

echo ""
echo "▶ Aplicando cambios..."
git pull -q origin main
echo "   ✓ Código actualizado."

echo ""
echo "▶ Reiniciando contenedor..."
docker restart "$CONTAINER"
echo "   ✓ $CONTAINER reiniciado."

echo ""
echo "✅ Update completado → http://192.168.0.42:5010"
