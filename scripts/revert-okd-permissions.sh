#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DOCKERFILE="${1:-$REPO_ROOT/docker/web/Dockerfile}"

if [[ ! -f "$DOCKERFILE" ]]; then
  echo "Dockerfile not found: $DOCKERFILE" >&2
  exit 1
fi

if grep -q 'chown -R appuser:appuser /app' "$DOCKERFILE" && ! grep -q 'chgrp -R 0 /app' "$DOCKERFILE"; then
  echo "Fixed appuser ownership pattern already present in $DOCKERFILE"
  exit 0
fi

backup="${TMPDIR:-/tmp}/$(basename "$DOCKERFILE").bak.$(date +%Y%m%d%H%M%S)"
cp "$DOCKERFILE" "$backup"

perl -0pi -e '
  s/useradd --uid 1001 --gid 0 --no-create-home --shell \/bin\/false appuser/useradd --uid 1001 --no-create-home --shell \/bin\/false appuser/g;
  s/&& chgrp -R 0 \/app \\\n\s*&& chmod -R g=u \/app \\\n\s*&& chmod \+x \/app\/docker\/web\/entrypoint\.sh/&& chown -R appuser:appuser \/app \\\n    && chmod +x \/app\/docker\/web\/entrypoint.sh/g;
' "$DOCKERFILE"

if ! grep -q 'useradd --uid 1001 --no-create-home' "$DOCKERFILE"; then
  echo "Failed to restore appuser creation in $DOCKERFILE" >&2
  echo "Backup retained at $backup" >&2
  exit 1
fi

if ! grep -q 'chown -R appuser:appuser /app' "$DOCKERFILE"; then
  echo "Failed to restore fixed ownership pattern in $DOCKERFILE" >&2
  echo "Backup retained at $backup" >&2
  exit 1
fi

echo "Restored fixed appuser ownership pattern in $DOCKERFILE"
echo "Backup retained at $backup"
