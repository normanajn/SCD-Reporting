#!/usr/bin/env bash
# bootstrap.sh — first-time setup and development server launcher for SCD Effort Reporting
#
# Usage:
#   ./bootstrap.sh [options]
#
# Options:
#   --admin-password <pass>   Password for the initial admin account
#                             (or set SCD_INITIAL_ADMIN_PASSWORD env var)
#   --anthropic-key <key>     Anthropic API key for AI Summary feature
#                             (or set ANTHROPIC_API_KEY env var)
#   --no-server               Set up the database but do not start the server
#   --skip-npm                Skip Node/Tailwind dependency install
#
# Examples:
#   ./bootstrap.sh --admin-password secret
#   ./bootstrap.sh --admin-password secret --anthropic-key sk-ant-...
#   ANTHROPIC_API_KEY=sk-ant-... ./bootstrap.sh --admin-password secret

set -euo pipefail

# ── Colours ───────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RED='\033[0;31m'
BOLD='\033[1m'
RESET='\033[0m'

info()    { printf "${CYAN}==> %s${RESET}\n" "$*"; }
success() { printf "${GREEN}✓  %s${RESET}\n" "$*"; }
warn()    { printf "${YELLOW}!  %s${RESET}\n" "$*"; }
error()   { printf "${RED}✗  %s${RESET}\n" "$*" >&2; }
header()  { printf "\n${BOLD}%s${RESET}\n%s\n" "$*" "$(printf '─%.0s' {1..60})"; }

# ── Argument parsing ──────────────────────────────────────────────────────────
ADMIN_PASSWORD="${SCD_INITIAL_ADMIN_PASSWORD:-}"
ANTHROPIC_KEY="${ANTHROPIC_API_KEY:-}"
START_SERVER=true
SKIP_NPM=false

while [[ $# -gt 0 ]]; do
  case $1 in
    --admin-password) ADMIN_PASSWORD="$2"; shift 2 ;;
    --anthropic-key)  ANTHROPIC_KEY="$2";  shift 2 ;;
    --no-server)      START_SERVER=false;  shift ;;
    --skip-npm)       SKIP_NPM=true;       shift ;;
    -h|--help)
      sed -n '/^# Usage:/,/^[^#]/{ /^#/{ s/^# \{0,2\}//; p } }' "$0"
      exit 0 ;;
    *) error "Unknown option: $1"; exit 1 ;;
  esac
done

header "SCD Effort Reporting — Bootstrap"

# ── Python 3.12+ ──────────────────────────────────────────────────────────────
info "Locating Python 3.12+..."
PYTHON=""
for cmd in python3.12 python3.13 python3 python; do
  if command -v "$cmd" &>/dev/null; then
    if "$cmd" -c 'import sys; sys.exit(0 if sys.version_info >= (3,12) else 1)' 2>/dev/null; then
      PYTHON="$cmd"
      break
    fi
  fi
done

if [[ -z "$PYTHON" ]]; then
  error "Python 3.12 or newer is required but was not found."
  echo "  macOS:  brew install python@3.12"
  echo "  Ubuntu: sudo apt install python3.12 python3.12-venv"
  echo "  RHEL:   sudo dnf install python3.12"
  echo "  See docs/quickstart.md for full instructions."
  exit 1
fi
success "Found $("$PYTHON" --version)"

# ── Virtual environment ───────────────────────────────────────────────────────
if [[ ! -d .venv ]]; then
  info "Creating virtual environment (.venv)..."
  "$PYTHON" -m venv .venv
  success "Virtual environment created"
else
  success "Virtual environment already exists"
fi

# shellcheck source=/dev/null
source .venv/bin/activate
success "Virtual environment activated"

# ── Python dependencies ───────────────────────────────────────────────────────
info "Installing Python dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements-dev.txt
success "Python dependencies installed"

# ── Node / Tailwind ───────────────────────────────────────────────────────────
if [[ "$SKIP_NPM" == false ]]; then
  if command -v npm &>/dev/null; then
    info "Installing Node dependencies (Tailwind CSS)..."
    (cd theme/static_src && npm install --silent)
    success "Node dependencies installed"
  else
    warn "npm not found — skipping. Tailwind will load from the Play CDN in dev mode."
    warn "Install Node.js 20+ from https://nodejs.org if you need CSS hot-reload."
  fi
else
  info "Skipping npm install (--skip-npm)"
fi

# ── Database setup ────────────────────────────────────────────────────────────
header "Database"

info "Applying migrations..."
python manage.py migrate -v 0
success "Migrations applied"

info "Seeding taxonomy (default projects and categories)..."
python manage.py seed_taxonomy
success "Taxonomy seeded"

if [[ -z "$ADMIN_PASSWORD" ]]; then
  warn "No admin password provided — skipping seed_admin."
  warn "Re-run with:  ./bootstrap.sh --admin-password <yourpassword>"
  warn "  or set:     SCD_INITIAL_ADMIN_PASSWORD=<yourpassword> ./bootstrap.sh"
else
  info "Creating/verifying admin account..."
  SCD_INITIAL_ADMIN_PASSWORD="$ADMIN_PASSWORD" python manage.py seed_admin
  success "Admin account ready"
  success "  Email:    scd-admin@fnal.gov"
  success "  Password: $ADMIN_PASSWORD"
fi

# ── Summary ───────────────────────────────────────────────────────────────────
header "Ready"

if [[ -n "$ANTHROPIC_KEY" ]]; then
  success "Anthropic API key set — AI Summary feature will be available"
else
  warn "ANTHROPIC_API_KEY not set — AI Summary will be disabled"
  warn "To enable it, re-run with:  ./bootstrap.sh --anthropic-key sk-ant-..."
  warn "  or export it and re-run:  export ANTHROPIC_API_KEY=sk-ant-..."
fi

echo ""

if [[ "$START_SERVER" == false ]]; then
  success "Bootstrap complete. Start the server any time with:"
  if [[ -n "$ANTHROPIC_KEY" ]]; then
    echo "  ANTHROPIC_API_KEY=<key> .venv/bin/python manage.py runserver"
  else
    echo "  .venv/bin/python manage.py runserver"
  fi
  exit 0
fi

info "Starting development server at http://localhost:8000 ..."
echo ""

export ANTHROPIC_API_KEY="$ANTHROPIC_KEY"
python manage.py runserver
