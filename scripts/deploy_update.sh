#!/usr/bin/env bash
set -euo pipefail

ROOT=${THEOSIS_ROOT:-/opt/theosis-mcp}
SERVICE=theosis-mcp.service
BACKUP_DIR=/root/theosis-backups
mkdir -p "$BACKUP_DIR"

if [[ -n "$(git -C "$ROOT" status --porcelain)" ]]; then
  echo "Refusing deployment: $ROOT has local changes." >&2
  exit 1
fi

old_commit=$(git -C "$ROOT" rev-parse HEAD)
stamp=$(date -u +%Y%m%dT%H%M%SZ)
cp -a "/etc/systemd/system/$SERVICE" "$BACKUP_DIR/$SERVICE.$stamp"

git -C "$ROOT" fetch origin main
git -C "$ROOT" reset --hard origin/main

if command -v uv >/dev/null 2>&1; then
  uv sync --frozen --project "$ROOT"
else
  "$ROOT/.venv/bin/python" -m pip install --disable-pip-version-check --quiet --upgrade -e "$ROOT"
fi

chown -R theosis:theosis "$ROOT"
systemctl daemon-reload
systemctl restart "$SERVICE"

if systemctl is-active --quiet "$SERVICE" && "$ROOT/.venv/bin/python" "$ROOT/scripts/health_check.py"; then
  echo "THEOSIS_DEPLOY_OK commit=$(git -C "$ROOT" rev-parse HEAD)"
  exit 0
fi

echo "Deployment health check failed; rolling back to $old_commit" >&2
git -C "$ROOT" reset --hard "$old_commit"
systemctl restart "$SERVICE" || true
exit 1
