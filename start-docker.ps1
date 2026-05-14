# start-docker.ps1 — build and start SCD Reporting in Docker
#
# Usage:
#   .\start-docker.ps1 [options]
#
# Modes:
#   (default)    Full stack — Postgres + Caddy via docker compose (reads .env)
#   -Quick       Smoke test — single container, SQLite, no compose needed
#
# Options:
#   -Build          Force image rebuild before starting
#   -Port <n>       Host port (default: 8000; quick mode only)
#   -Quick          Smoke test: SQLite, no Postgres, no compose required
#   -Tail           Tail logs after starting
#
# Full stack requires the docker compose v2 plugin.
# Quick mode requires only Docker — useful for one-off testing.

param(
    [switch]$Quick,
    [switch]$Build,
    [int]   $Port = 8000,
    [switch]$Tail
)

$ErrorActionPreference = 'Stop'
$ScriptDir  = Split-Path -Parent $MyInvocation.MyCommand.Path
$ImageName  = 'scd-reporting-web'
$QuickName  = 'scd-quick'
$ModeFile   = Join-Path $ScriptDir '.scd-docker.mode'
Set-Location $ScriptDir

# ── Load .env ─────────────────────────────────────────────────────────────────
$envFile = Join-Path $ScriptDir '.env'
if (Test-Path $envFile) {
    foreach ($line in Get-Content $envFile) {
        if ($line -match '^\s*#' -or $line -match '^\s*$') { continue }
        $parts = $line -split '=', 2
        if ($parts.Count -ne 2) { continue }
        $k = $parts[0].Trim()
        $v = $parts[1].Trim().Trim('"').Trim("'")
        if (-not [System.Environment]::GetEnvironmentVariable($k, 'Process')) {
            [System.Environment]::SetEnvironmentVariable($k, $v, 'Process')
        }
    }
}

function Write-Header($t) { Write-Host ""; Write-Host $t -ForegroundColor White; Write-Host ('-'*60) -ForegroundColor DarkGray }
function Write-Info($t)   { Write-Host "==> $t" -ForegroundColor Cyan }
function Write-Ok($t)     { Write-Host "✓  $t"  -ForegroundColor Green }
function Write-Warn($t)   { Write-Host "!  $t"  -ForegroundColor Yellow }
function Write-Err($t)    { Write-Host "✗  $t"  -ForegroundColor Red }

# ── Check Docker ──────────────────────────────────────────────────────────────
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Err 'Docker is not installed or not on PATH.'
    Write-Host '  Install: https://docs.docker.com/get-docker/'
    exit 1
}

# ── Build image ───────────────────────────────────────────────────────────────
$needsBuild = $Build
if (-not $needsBuild) {
    $existing = docker image inspect $ImageName 2>$null
    if (-not $existing) { $needsBuild = $true }
}

if ($needsBuild) {
    Write-Header 'Building image'
    Write-Info "Building $ImageName (this takes ~2 min on first run)..."
    docker build -f docker/web/Dockerfile -t $ImageName .
    Write-Ok "Image built: $ImageName"
} else {
    Write-Info "Image $ImageName already exists — skipping build (use -Build to force)"
}

# ══════════════════════════════════════════════════════════════════════════════
# QUICK MODE
# ══════════════════════════════════════════════════════════════════════════════
if ($Quick) {
    Write-Header 'SCD Reporting — Quick (SQLite)'

    $existing = docker container inspect $QuickName 2>$null
    if ($existing) {
        Write-Info 'Stopping existing quick container...'
        docker rm -f $QuickName | Out-Null
    }

    $adminPass = if ($env:SCD_INITIAL_ADMIN_PASSWORD) { $env:SCD_INITIAL_ADMIN_PASSWORD } else { 'admin' }

    # Mount the local db.sqlite3 if it exists so the container starts with existing data
    $dbPath = Join-Path $ScriptDir 'db.sqlite3'
    $dbMount = @()
    if (Test-Path $dbPath) {
        $dbMount = @('-v', "${dbPath}:/app/db.sqlite3")
        Write-Info 'Mounting existing db.sqlite3'
    }

    docker run -d `
        --name $QuickName `
        @dbMount `
        -e DJANGO_SETTINGS_MODULE=scd_reporting.settings.dev `
        -e SCD_INITIAL_ADMIN_PASSWORD=$adminPass `
        -p "${Port}:8000" `
        $ImageName | Out-Null

    Write-Info 'Waiting for server to be ready...'
    $ready = $false
    for ($i = 0; $i -lt 30; $i++) {
        $check = docker exec $QuickName python -c `
            "import urllib.request; urllib.request.urlopen('http://localhost:8000/accounts/login/')" `
            2>$null
        if ($LASTEXITCODE -eq 0) { $ready = $true; break }
        Start-Sleep -Seconds 2
    }

    $QuickName | Set-Content $ModeFile
    Write-Ok "Container started: $QuickName"
    Write-Ok "URL:              http://localhost:$Port"
    Write-Ok "Login:            scd-admin / $adminPass"
    Write-Host ''
    Write-Host "Logs: docker logs -f $QuickName" -ForegroundColor Cyan
    Write-Host 'Stop: .\stop-docker.ps1'         -ForegroundColor Cyan

    if ($Tail) {
        Write-Host ''
        Write-Info 'Tailing logs (Ctrl-C stops tailing — container keeps running)...'
        docker logs -f $QuickName
    }
    exit 0
}

# ══════════════════════════════════════════════════════════════════════════════
# FULL STACK MODE — docker compose
# ══════════════════════════════════════════════════════════════════════════════
Write-Header 'SCD Reporting — Full Stack (docker compose)'

$composeCheck = docker compose version 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Err 'docker compose (v2 plugin) is not available.'
    Write-Host ''
    Write-Host '  Install on Windows with Docker Desktop (includes Compose):'
    Write-Host '    https://docs.docker.com/desktop/install/windows-install/'
    Write-Host ''
    Write-Host '  To test without Compose, use: .\start-docker.ps1 -Quick'
    exit 1
}

# Validate required vars
$missing = @()
if (-not $env:DJANGO_SECRET_KEY)          { $missing += 'DJANGO_SECRET_KEY' }
if (-not $env:POSTGRES_PASSWORD)          { $missing += 'POSTGRES_PASSWORD' }

if ($missing.Count -gt 0) {
    Write-Err 'Required variables are not set in .env or the environment:'
    foreach ($v in $missing) { Write-Host "  - $v" }
    Write-Host ''
    Write-Host '  Copy .env.example to .env and fill in the values.'
    exit 1
}

$composeArgs = @('up', '-d')
if ($Build) { $composeArgs += '--build' }

Write-Info 'Starting services (db, web, caddy)...'
docker compose @composeArgs

# Wait for web to be healthy
Write-Info 'Waiting for web container to be healthy...'
$deadline = (Get-Date).AddSeconds(120)
$healthy = $false
while ((Get-Date) -lt $deadline) {
    try {
        $json    = docker compose ps --format json web 2>$null
        $status  = ($json | ConvertFrom-Json).Health
        if ($status -eq 'healthy') { $healthy = $true; break }
    } catch { }
    Start-Sleep -Seconds 3
}

'compose' | Set-Content $ModeFile

if ($healthy) {
    Write-Ok 'All services are up and healthy'
} else {
    Write-Warn 'Containers started but health check timed out — check logs:'
    Write-Host '  docker compose logs web'
}

$hostname = if ($env:SCD_HOSTNAME) { $env:SCD_HOSTNAME } else { 'localhost' }
$scheme   = if ($hostname -ne 'localhost') { 'https' } else { 'http' }
Write-Ok "URL:    ${scheme}://${hostname}"
if ($env:SCD_INITIAL_ADMIN_PASSWORD) {
    Write-Ok "Login:  scd-admin / $($env:SCD_INITIAL_ADMIN_PASSWORD)"
}
Write-Host ''
Write-Host 'Logs: docker compose logs -f web' -ForegroundColor Cyan
Write-Host 'Stop: .\stop-docker.ps1'          -ForegroundColor Cyan

if ($Tail) {
    Write-Host ''
    Write-Info 'Tailing web logs (Ctrl-C stops tailing — containers keep running)...'
    docker compose logs -f web
}
