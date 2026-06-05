#!/usr/bin/env bash
# scd-post-entry-json.sh — post a work entry to SCD Activity Reporting from a JSON file.
#
# Reads entry JSON from FILE (or stdin when FILE is omitted or "-").
# Requires curl.  Uses jq for pretty output when available.
#
# Config file: ~/.config/scd-reporting/config.yaml
#   url:   https://scd-reporting.fnal.gov
#   token: <your API token from Profile > API Token>
#
# Environment variables (override config file): SCD_URL, SCD_TOKEN

set -euo pipefail

# ── Defaults ──────────────────────────────────────────────────────────────────

CONFIG_FILE="${HOME}/.config/scd-reporting/config.yaml"
URL=""
TOKEN=""
FILE="-"
DRY_RUN=0

# ── Usage ─────────────────────────────────────────────────────────────────────

usage() {
  cat <<EOF
Usage: $(basename "$0") [OPTIONS] [FILE]

Post a work entry to SCD Activity Reporting from a JSON file (or stdin).

Arguments:
  FILE          JSON file containing the entry object (default: stdin / -)

Options:
  -u, --url URL     Base URL of the SCD Reporting instance
  -t, --token TOK   API Bearer token (from Profile > API Token)
  -c, --config FILE Config file path (default: ${HOME}/.config/scd-reporting/config.yaml)
  --dry-run         Print the resolved URL and JSON without posting
  -h, --help        Show this help and exit

Required JSON fields: title, description, project, category, period_start, period_end

Example:
  echo '{"title":"My entry","description":"...","project":"mu2e-daq",
         "category":"software-development","period_kind":"week",
         "period_start":"2026-05-26","period_end":"2026-06-01"}' \\
    | $(basename "$0") -t "\$SCD_TOKEN"
EOF
}

# ── Argument parsing ───────────────────────────────────────────────────────────

while [[ $# -gt 0 ]]; do
  case $1 in
    -u|--url)    URL="$2";         shift 2 ;;
    -t|--token)  TOKEN="$2";       shift 2 ;;
    -c|--config) CONFIG_FILE="$2"; shift 2 ;;
    --dry-run)   DRY_RUN=1;        shift   ;;
    -h|--help)   usage; exit 0              ;;
    -*)          echo "Unknown option: $1" >&2; usage >&2; exit 1 ;;
    *)           FILE="$1"; shift           ;;
  esac
done

# ── Load config file (minimal YAML: key: value lines only) ────────────────────

if [[ -f "$CONFIG_FILE" ]]; then
  if [[ -z "$URL" ]]; then
    URL=$(grep -E '^url:[[:space:]]*' "$CONFIG_FILE" 2>/dev/null \
          | sed 's/^url:[[:space:]]*//' | head -n1 || true)
  fi
  if [[ -z "$TOKEN" ]]; then
    TOKEN=$(grep -E '^token:[[:space:]]*' "$CONFIG_FILE" 2>/dev/null \
            | sed 's/^token:[[:space:]]*//' | head -n1 || true)
  fi
fi

# ── Environment variable overrides ────────────────────────────────────────────

URL="${SCD_URL:-$URL}"
TOKEN="${SCD_TOKEN:-$TOKEN}"

# ── Validate ──────────────────────────────────────────────────────────────────

if [[ -z "$URL" ]]; then
  echo "ERROR: No URL specified. Use -u/--url, SCD_URL env var, or config file." >&2
  exit 1
fi

if [[ -z "$TOKEN" ]]; then
  echo "ERROR: No API token. Use -t/--token, SCD_TOKEN env var, or config file." >&2
  echo "  Generate a token at: ${URL%/}/profile/" >&2
  exit 1
fi

URL="${URL%/}"

# ── Read JSON ─────────────────────────────────────────────────────────────────

if [[ "$FILE" == "-" ]]; then
  DATA=$(cat)
else
  if [[ ! -f "$FILE" ]]; then
    echo "ERROR: File not found: $FILE" >&2
    exit 1
  fi
  DATA=$(cat "$FILE")
fi

if [[ -z "$DATA" ]]; then
  echo "ERROR: Empty input." >&2
  exit 1
fi

# ── Dry run ───────────────────────────────────────────────────────────────────

if [[ "$DRY_RUN" -eq 1 ]]; then
  echo "Dry run — would POST to: ${URL}/api/entries/"
  if command -v jq &>/dev/null; then
    echo "$DATA" | jq .
  else
    echo "$DATA"
  fi
  exit 0
fi

# ── POST ──────────────────────────────────────────────────────────────────────

RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${URL}/api/entries/" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${TOKEN}" \
  --data-raw "$DATA")

HTTP_CODE=$(printf '%s' "$RESPONSE" | tail -n1)
BODY=$(printf '%s' "$RESPONSE" | head -n -1)

case $HTTP_CODE in
  201)
    if command -v jq &>/dev/null; then
      echo "$BODY" | jq -r '"Entry #\(.id) created: \(.title)\n  \(.url)"'
    else
      echo "Entry created."
      echo "$BODY"
    fi
    ;;
  400)
    echo "ERROR: The server rejected the entry:" >&2
    if command -v jq &>/dev/null; then
      echo "$BODY" | jq -r '(.errors // .) | to_entries[] | "  \(.key): \(.value)"' >&2
    else
      echo "$BODY" >&2
    fi
    exit 1
    ;;
  401)
    echo "ERROR: Invalid or missing API token." >&2
    echo "  Generate one at: ${URL}/profile/" >&2
    exit 1
    ;;
  "")
    echo "ERROR: curl produced no response (connection failed?)." >&2
    exit 1
    ;;
  *)
    echo "ERROR: Unexpected response ${HTTP_CODE}: ${BODY:0:300}" >&2
    exit 1
    ;;
esac
