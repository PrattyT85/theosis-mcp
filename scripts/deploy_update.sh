#!/usr/bin/env bash
set -euo pipefail

ROOT=${THEOSIS_ROOT:-/opt/theosis-mcp}
SERVICE=theosis-mcp.service
BACKUP_DIR=/root/theosis-backups
mkdir -p "$BACKUP_DIR"

GIT=(git -c "safe.directory=$ROOT" -C "$ROOT")

if [[ -n "$("${GIT[@]}" status --porcelain)" ]]; then
  echo "Refusing deployment: $ROOT has local changes." >&2
  exit 1
fi

old_commit=$("${GIT[@]}" rev-parse HEAD)
stamp=$(date -u +%Y%m%dT%H%M%SZ)
cp -a "/etc/systemd/system/$SERVICE" "$BACKUP_DIR/$SERVICE.$stamp"

"${GIT[@]}" fetch origin main
"${GIT[@]}" reset --hard origin/main

if command -v uv >/dev/null 2>&1; then
  uv sync --frozen --project "$ROOT"
else
  "$ROOT/.venv/bin/python" -m pip install --disable-pip-version-check --quiet --upgrade -e "$ROOT"
fi

chown -R theosis:theosis "$ROOT"
systemctl daemon-reload
systemctl restart "$SERVICE"

if systemctl is-active --quiet "$SERVICE" && "$ROOT/.venv/bin/python" "$ROOT/scripts/health_check.py"; then
  echo "THEOSIS_DEPLOY_OK commit=$("${GIT[@]}" rev-parse HEAD)"
  exit 0
fi

echo "Deployment health check failed; rolling back to $old_commit" >&2
"${GIT[@]}" reset --hard "$old_commit"
systemctl restart "$SERVICE" || true
exit 1
