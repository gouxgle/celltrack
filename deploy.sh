#!/bin/bash
# ── deploy.sh — CellTrack ─────────────────────────────────────────────────────
# Uso: ./deploy.sh "descripción del cambio"
# Hace: commit local → push GitHub → pull en VM → restart si hay .py modificados
# ─────────────────────────────────────────────────────────────────────────────

VM_HOST="root@192.168.0.42"
VM_PATH="/etc/docker/celulares_flask"
CONTAINER="celltrack_web"

MSG="${1:-actualización}"

set -e

echo ""
echo "▶ 1/3  Commit y push local..."
git add .

if git diff --cached --quiet; then
    echo "   Sin cambios para commitear."
else
    git commit -m "$MSG"
    git push
    echo "   ✓ Subido a GitHub."
fi

echo ""
echo "▶ 2/3  Pull en VM $VM_HOST..."
CHANGED=$(ssh -o StrictHostKeyChecking=no "$VM_HOST" "
    cd $VM_PATH &&
    git fetch origin main -q &&
    git diff --name-only HEAD origin/main
")

ssh -o StrictHostKeyChecking=no "$VM_HOST" "cd $VM_PATH && git pull -q"
echo "   ✓ VM actualizada."

echo ""
echo "▶ 3/3  Reinicio del contenedor..."
if echo "$CHANGED" | grep -q "\.py$"; then
    ssh -o StrictHostKeyChecking=no "$VM_HOST" "docker restart $CONTAINER"
    echo "   ✓ Contenedor reiniciado (cambios en .py detectados)."
else
    echo "   ⚡ Sin cambios en .py — no hace falta reiniciar."
fi

echo ""
echo "✅ Deploy completado → http://192.168.0.42:5010"
