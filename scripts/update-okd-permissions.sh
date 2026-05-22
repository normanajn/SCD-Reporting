#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DOCKERFILE="${1:-$REPO_ROOT/docker/web/Dockerfile}"

if [[ ! -f "$DOCKERFILE" ]]; then
  echo "Dockerfile not found: $DOCKERFILE" >&2
  exit 1
fi

if grep -q 'chgrp -R 0 /app' "$DOCKERFILE" && grep -q 'chmod -R g=u /app' "$DOCKERFILE"; then
  echo "OKD-compatible permission pattern already present in $DOCKERFILE"
  exit 0
fi

backup="${TMPDIR:-/tmp}/$(basename "$DOCKERFILE").bak.$(date +%Y%m%d%H%M%S)"
cp "$DOCKERFILE" "$backup"

perl -0pi -e '
  s/useradd --uid 1001 --no-create-home --shell \/bin\/false appuser/useradd --uid 1001 --gid 0 --no-create-home --shell \/bin\/false appuser/g;
  s/&& chown -R appuser:appuser \/app \\\n\s*&& chmod \+x \/app\/docker\/web\/entrypoint\.sh/&& chgrp -R 0 \/app \\\n    && chmod -R g=u \/app \\\n    && chmod +x \/app\/docker\/web\/entrypoint.sh/g;
' "$DOCKERFILE"

if ! grep -q 'useradd --uid 1001 --gid 0' "$DOCKERFILE"; then
  echo "Failed to update appuser group in $DOCKERFILE" >&2
  echo "Backup retained at $backup" >&2
  exit 1
fi

if ! grep -q 'chgrp -R 0 /app' "$DOCKERFILE" || ! grep -q 'chmod -R g=u /app' "$DOCKERFILE"; then
  echo "Failed to update permission pattern in $DOCKERFILE" >&2
  echo "Backup retained at $backup" >&2
  exit 1
fi

echo "Updated OKD-compatible permissions in $DOCKERFILE"
echo "Backup retained at $backup"
