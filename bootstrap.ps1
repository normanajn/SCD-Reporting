# bootstrap.ps1 — first-time setup and development server launcher for SCD Effort Reporting
#
# Usage:
#   .\bootstrap.ps1 [options]
#
# Options:
#   -AdminPassword <pass>    Password for the initial admin account
#                            (or set $env:SCD_INITIAL_ADMIN_PASSWORD before running)
#   -AnthropicKey  <key>     Anthropic API key for the AI Summary feature
#                            (or set $env:ANTHROPIC_API_KEY before running)
#   -NoServer                Set up the database but do not start the server
#   -SkipNpm                 Skip Node/Tailwind dependency install
#
# Examples:
#   .\bootstrap.ps1 -AdminPassword secret
#   .\bootstrap.ps1 -AdminPassword secret -AnthropicKey sk-ant-...
#   $env:ANTHROPIC_API_KEY="sk-ant-..."; .\bootstrap.ps1 -AdminPassword secret

param(
    [string]$AdminPassword = $env:SCD_INITIAL_ADMIN_PASSWORD,
    [string]$AnthropicKey  = $env:ANTHROPIC_API_KEY,
    [switch]$NoServer,
    [switch]$SkipNpm
)

$ErrorActionPreference = 'Stop'

function Write-Header($text) {
    Write-Host ""
    Write-Host $text -ForegroundColor White
    Write-Host ("-" * 60) -ForegroundColor DarkGray
}
function Write-Info($text)    { Write-Host "==> $text" -ForegroundColor Cyan }
function Write-Success($text) { Write-Host "✓  $text"  -ForegroundColor Green }
function Write-Warn($text)    { Write-Host "!  $text"  -ForegroundColor Yellow }
function Write-Err($text)     { Write-Host "✗  $text"  -ForegroundColor Red }

Write-Header "SCD Effort Reporting — Bootstrap"

# ── Python 3.12+ ──────────────────────────────────────────────────────────────
Write-Info "Locating Python 3.12+..."
$Python = $null
foreach ($cmd in @("python3.12", "python3", "python")) {
    try {
        $ver = & $cmd -c "import sys; print(sys.version_info >= (3,12))" 2>$null
        if ($ver -eq "True") { $Python = $cmd; break }
    } catch {}
}

if (-not $Python) {
    Write-Err "Python 3.12 or newer is required but was not found."
    Write-Host "  Download from: https://www.python.org/downloads/"
    Write-Host "  During install, check 'Add python.exe to PATH'."
    Write-Host "  See docs/quickstart.md for full instructions."
    exit 1
}
$pyVersion = & $Python --version
Write-Success "Found $pyVersion"

# ── Virtual environment ───────────────────────────────────────────────────────
if (-not (Test-Path ".venv")) {
    Write-Info "Creating virtual environment (.venv)..."
    & $Python -m venv .venv
    Write-Success "Virtual environment created"
} else {
    Write-Success "Virtual environment already exists"
}

& .\.venv\Scripts\Activate.ps1
Write-Success "Virtual environment activated"

# ── Python dependencies ───────────────────────────────────────────────────────
Write-Info "Installing Python dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements-dev.txt
Write-Success "Python dependencies installed"

# ── Node / Tailwind ───────────────────────────────────────────────────────────
if (-not $SkipNpm) {
    $npmExists = $null
    try { $npmExists = Get-Command npm -ErrorAction Stop } catch {}

    if ($npmExists) {
        Write-Info "Installing Node dependencies (Tailwind CSS)..."
        Push-Location theme/static_src
        npm install --silent
        Pop-Location
        Write-Success "Node dependencies installed"
    } else {
        Write-Warn "npm not found — skipping. Tailwind will load from the Play CDN in dev mode."
        Write-Warn "Install Node.js 20+ from https://nodejs.org if you need CSS hot-reload."
    }
} else {
    Write-Info "Skipping npm install (-SkipNpm)"
}

# ── Database setup ────────────────────────────────────────────────────────────
Write-Header "Database"

Write-Info "Applying migrations..."
python manage.py migrate -v 0
Write-Success "Migrations applied"

Write-Info "Seeding taxonomy (default projects and categories)..."
python manage.py seed_taxonomy
Write-Success "Taxonomy seeded"

if ([string]::IsNullOrEmpty($AdminPassword)) {
    Write-Warn "No admin password provided — skipping seed_admin."
    Write-Warn "Re-run with:  .\bootstrap.ps1 -AdminPassword <yourpassword>"
} else {
    Write-Info "Creating/verifying admin account..."
    $env:SCD_INITIAL_ADMIN_PASSWORD = $AdminPassword
    python manage.py seed_admin
    Write-Success "Admin account ready"
    Write-Success "  Email:    scd-admin@fnal.gov"
    Write-Success "  Password: $AdminPassword"
}

# ── Summary ───────────────────────────────────────────────────────────────────
Write-Header "Ready"

if (-not [string]::IsNullOrEmpty($AnthropicKey)) {
    Write-Success "Anthropic API key set — AI Summary feature will be available"
    $env:ANTHROPIC_API_KEY = $AnthropicKey
} else {
    Write-Warn "ANTHROPIC_API_KEY not set — AI Summary will be disabled"
    Write-Warn "Re-run with:  .\bootstrap.ps1 -AnthropicKey sk-ant-..."
    Write-Warn "  or set:     `$env:ANTHROPIC_API_KEY='sk-ant-...'"
}

Write-Host ""

if ($NoServer) {
    Write-Success "Bootstrap complete. Start the server any time with:"
    Write-Host "  python manage.py runserver"
    exit 0
}

Write-Info "Starting development server at http://localhost:8000 ..."
Write-Host ""
python manage.py runserver
