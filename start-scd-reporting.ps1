# start-scd-reporting.ps1 — install/update dependencies, migrate, and start the server
#
# Usage:
#   .\start-scd-reporting.ps1 [options]
#
# Options:
#   -AdminPassword    <pass>   Password for the initial admin account on first run
#                              (or set $env:SCD_INITIAL_ADMIN_PASSWORD)
#   -AnthropicKey     <key>    Anthropic API key for the AI Summary feature
#                              (or set $env:ANTHROPIC_API_KEY)
#   -OidcSecretFile     <path>   Path to a file containing the OIDC client secret
#                                (or set $env:OIDC_CLIENT_SECRET_FILE)
#   -OidcProviderUrl    <url>    OIDC discovery URL or base realm URL
#                                (or set $env:OIDC_PROVIDER_URL)
#   -OidcClientId       <id>     OIDC client ID
#                                (or set $env:OIDC_CLIENT_ID)
#   -GoogleClientId     <id>     Google OAuth2 client ID
#                                (or set $env:GOOGLE_CLIENT_ID)
#   -GoogleClientSecret <sec>    Google OAuth2 client secret
#                                (or set $env:GOOGLE_CLIENT_SECRET)
#   -Port <port>               Port to listen on (default: 8000)
#   -NoUpdate                  Skip pip/npm update checks
#   -WithTailwind              Also start the Tailwind CSS watcher
#   -Tail                      Open the server log in a new window after starting
#
# The script is safe to run repeatedly. It updates packages, applies any pending
# migrations, and restarts the server if one is already running.

param(
    [string]$AdminPassword      = $env:SCD_INITIAL_ADMIN_PASSWORD,
    [string]$AnthropicKey       = $env:ANTHROPIC_API_KEY,
    [string]$OidcSecretFile     = $env:OIDC_CLIENT_SECRET_FILE,
    [string]$OidcProviderUrl    = $env:OIDC_PROVIDER_URL,
    [string]$OidcClientId       = $env:OIDC_CLIENT_ID,
    [string]$GoogleClientId     = $env:GOOGLE_CLIENT_ID,
    [string]$GoogleClientSecret = $env:GOOGLE_CLIENT_SECRET,
    [int]   $Port               = 8000,
    [switch]$NoUpdate,
    [switch]$WithTailwind,
    [switch]$Tail
)

$ErrorActionPreference = 'Stop'
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

$PidFile        = Join-Path $ScriptDir '.scd-reporting.pid'
$TailwindPidFile= Join-Path $ScriptDir '.scd-tailwind.pid'
$LogDir         = Join-Path $ScriptDir 'logs'
$LogFile        = Join-Path $LogDir 'scd-reporting.log'

function Write-Header($t) { Write-Host ""; Write-Host $t -ForegroundColor White; Write-Host ("-"*60) -ForegroundColor DarkGray }
function Write-Info($t)   { Write-Host "==> $t" -ForegroundColor Cyan }
function Write-Ok($t)     { Write-Host "✓  $t"  -ForegroundColor Green }
function Write-Warn($t)   { Write-Host "!  $t"  -ForegroundColor Yellow }
function Write-Err($t)    { Write-Host "✗  $t"  -ForegroundColor Red }

Write-Header "SCD Effort Reporting — Start"

# ── Stop any running instance ─────────────────────────────────────────────────
if (Test-Path $PidFile) {
    $oldPid = [int](Get-Content $PidFile)
    try {
        $proc = Get-Process -Id $oldPid -ErrorAction Stop
        Write-Warn "Server already running (PID $oldPid) — restarting..."
        Stop-Process -Id $oldPid -Force
        Start-Sleep -Seconds 1
    } catch { }
    Remove-Item $PidFile -Force
}

# ── Python 3.12+ ──────────────────────────────────────────────────────────────
Write-Info "Locating Python 3.12+..."
$Python = $null
foreach ($cmd in @("python3.12","python3","python")) {
    try {
        $v = & $cmd -c "import sys; print(sys.version_info >= (3,12))" 2>$null
        if ($v -eq "True") { $Python = $cmd; break }
    } catch { }
}
if (-not $Python) {
    Write-Err "Python 3.12 or newer is required. See docs/quickstart.md."
    exit 1
}
Write-Ok "Found $(& $Python --version)"

# ── Virtual environment ───────────────────────────────────────────────────────
if (-not (Test-Path ".venv")) {
    Write-Info "Creating virtual environment (.venv)..."
    & $Python -m venv .venv
    Write-Ok "Virtual environment created"
}
& .\.venv\Scripts\Activate.ps1
Write-Ok "Virtual environment active"

# ── Python packages ───────────────────────────────────────────────────────────
if (-not $NoUpdate) {
    Write-Info "Updating Python dependencies..."
    pip install -q --upgrade pip
    pip install -q -r requirements-dev.txt
    Write-Ok "Python dependencies up to date"
} else {
    Write-Info "Skipping package update (-NoUpdate)"
}

# ── Node / Tailwind ───────────────────────────────────────────────────────────
if (-not $NoUpdate) {
    $npmCmd = Get-Command npm -ErrorAction SilentlyContinue
    if ($npmCmd) {
        Write-Info "Updating Node dependencies..."
        Push-Location theme/static_src
        npm install --silent
        Pop-Location
        Write-Ok "Node dependencies up to date"
    }
}

# ── Database ──────────────────────────────────────────────────────────────────
Write-Header "Database"

Write-Info "Applying migrations..."
python manage.py migrate -v 0
Write-Ok "Migrations applied"

Write-Info "Seeding taxonomy..."
python manage.py seed_taxonomy
Write-Ok "Taxonomy up to date"

if (-not [string]::IsNullOrEmpty($AdminPassword)) {
    Write-Info "Seeding admin account..."
    $env:SCD_INITIAL_ADMIN_PASSWORD = $AdminPassword
    python manage.py seed_admin
    Write-Ok "Admin account: scd-admin@fnal.gov"
}

# ── Tailwind watcher (optional) ───────────────────────────────────────────────
if ($WithTailwind) {
    $npmCmd = Get-Command npm -ErrorAction SilentlyContinue
    if ($npmCmd) {
        if (Test-Path $TailwindPidFile) {
            $twPid = [int](Get-Content $TailwindPidFile)
            try { Stop-Process -Id $twPid -Force } catch { }
            Remove-Item $TailwindPidFile -Force
        }
        Write-Info "Starting Tailwind CSS watcher..."
        if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir | Out-Null }
        $twJob = Start-Process -FilePath "npm" -ArgumentList "start" `
            -WorkingDirectory (Join-Path $ScriptDir "theme\static_src") `
            -RedirectStandardOutput (Join-Path $LogDir "scd-tailwind.log") `
            -RedirectStandardError  (Join-Path $LogDir "scd-tailwind-err.log") `
            -PassThru -WindowStyle Hidden
        $twJob.Id | Set-Content $TailwindPidFile
        Write-Ok "Tailwind watcher started (PID $($twJob.Id))"
    } else {
        Write-Warn "npm not found — skipping Tailwind watcher (CDN will be used)"
    }
}

# ── Start server ──────────────────────────────────────────────────────────────
Write-Header "Server"

if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir | Out-Null }

Write-Info "Starting server on port $Port..."

if (-not [string]::IsNullOrEmpty($AnthropicKey)) {
    $env:ANTHROPIC_API_KEY = $AnthropicKey
    Write-Ok "AI Summary enabled (Anthropic API key set)"
}

if (-not [string]::IsNullOrEmpty($OidcSecretFile) -or -not [string]::IsNullOrEmpty($OidcProviderUrl)) {
    $env:OIDC_CLIENT_SECRET_FILE = $OidcSecretFile
    $env:OIDC_PROVIDER_URL       = $OidcProviderUrl
    $env:OIDC_CLIENT_ID          = $OidcClientId
    Write-Ok "OIDC SSO enabled"
    if (-not [string]::IsNullOrEmpty($OidcSecretFile)) { Write-Ok "  Secret file: $OidcSecretFile" }
}

if (-not [string]::IsNullOrEmpty($GoogleClientId) -and -not [string]::IsNullOrEmpty($GoogleClientSecret)) {
    $env:GOOGLE_CLIENT_ID     = $GoogleClientId
    $env:GOOGLE_CLIENT_SECRET = $GoogleClientSecret
    Write-Ok "Google OAuth enabled"
}

$serverProc = Start-Process -FilePath (Join-Path $ScriptDir ".venv\Scripts\python.exe") `
    -ArgumentList "manage.py runserver $Port" `
    -WorkingDirectory $ScriptDir `
    -RedirectStandardOutput $LogFile `
    -RedirectStandardError  $LogFile `
    -PassThru -WindowStyle Hidden

Start-Sleep -Seconds 1

if ($serverProc.HasExited) {
    Write-Err "Server failed to start. Check the log: $LogFile"
    Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
    exit 1
}

$serverProc.Id | Set-Content $PidFile

Write-Ok "Server started   (PID $($serverProc.Id))"
Write-Ok "URL:             http://localhost:$Port"
Write-Ok "Log:             $LogFile"
if (-not [string]::IsNullOrEmpty($AdminPassword)) {
    Write-Ok "Login:           scd-admin@fnal.gov / $AdminPassword"
}
Write-Host ""
Write-Host "To stop: .\stop-scd-reporting.ps1" -ForegroundColor Cyan

if ($Tail) {
    Write-Host ""
    Write-Info "Tailing server log (Ctrl-C stops tailing — server keeps running)..."
    Write-Host ""
    Get-Content $LogFile -Wait
}
