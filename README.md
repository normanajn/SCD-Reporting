# SCD Effort Reporting

A Django web application for Fermilab Scientific Computing Division employees to log and review weekly effort reports. Staff submit entries describing work performed against projects and categories; administrators and auditors can filter, preview, and export the full dataset; every data change is recorded in a tamper-evident audit log.

---

## Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Local Development](#local-development)
- [Running Tests](#running-tests)
- [Docker Deployment](#docker-deployment)
- [User Roles](#user-roles)
- [URL Reference](#url-reference)
- [Environment Variables](#environment-variables)
- [Management Commands](#management-commands)

---

## Features

- **Effort entries** — submit and manage weekly/biweekly/monthly work entries with Markdown descriptions, tags, period dates, and a privacy flag
- **HTMX interactions** — period chip selector pre-fills date fields; tag autocomplete with chip UI; live Markdown preview; all without full page reloads
- **Role-based access** — three roles (User, Administrator, Auditor) with enforced permission checks throughout
- **Reports** — admins and auditors filter entries by author, project, category, and date range, then download as plain text, CSV, JSON, XLSX, or PDF
- **Audit log** — every WorkItem create/update/delete, all login/logout events, and every report export are recorded with actor, IP address, user-agent, and field-level diffs
- **SSO-ready** — local email/password auth now via django-allauth; a seam exists for CILogon integration when required

---

## Architecture

```
apps/
├── core/        Dashboard, base templates, shared components
├── accounts/    Custom User model (role + employee_id), profile, admin user management
├── taxonomy/    Project and Category models, Tag autocomplete
├── entries/     WorkItem CRUD (the effort entries themselves)
├── reports/     Filter form, five exporters, HTMX preview
└── audit/       AuditLogEntry model, log_event service, signals, middleware, viewer
```

Each app is independently namespaced and has its own URLs, templates, and tests.

---

## Tech Stack

| Layer | Choice |
|---|---|
| Framework | Django 5 |
| Auth | django-allauth ≥ 65 (local; CILogon seam ready) |
| Frontend | Tailwind CSS 3 via django-tailwind, HTMX 2 |
| Database | PostgreSQL 16 (production), SQLite (local dev fallback) |
| PDF export | WeasyPrint |
| XLSX export | openpyxl |
| Filtering | django-filter |
| Container | Docker + Caddy (reverse proxy + automatic TLS) |
| Tests | pytest-django |

---

## Local Development

### Prerequisites

- Python 3.12+
- Node.js 20+ (for Tailwind CSS compilation)
- Git

### Setup

```bash
git clone https://github.com/your-org/SCD-Reporting.git
cd SCD-Reporting

# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install Python dependencies
pip install -r requirements-dev.txt

# Install Node dependencies for Tailwind
cd theme/static_src && npm install && cd ../..
```

### Database

The default development configuration uses SQLite — no database server required.

```bash
# Apply all migrations
python manage.py migrate

# Seed the default projects and categories
python manage.py seed_taxonomy

# Create an admin account (uses SCD_INITIAL_ADMIN_* env vars; see below)
SCD_INITIAL_ADMIN_PASSWORD=devpassword python manage.py seed_admin
```

### Run the development server

In one terminal, start the Tailwind CSS watcher:

```bash
cd theme/static_src && npm start
```

In another terminal, start Django:

```bash
python manage.py runserver
```

The app will be available at <http://localhost:8000>.

> **Note:** The development settings module is `scd_reporting.settings.dev`, which enables `DEBUG=True`, uses the Tailwind Play CDN (so the npm watcher is optional for casual development), and logs emails to the console.

---

## Running Tests

```bash
# Run the full test suite
.venv/bin/pytest tests/

# Run with coverage
.venv/bin/pytest tests/ --cov=apps --cov-report=term-missing

# Run a single test module
.venv/bin/pytest tests/test_entries.py -v
```

Tests use `scd_reporting.settings.dev` and SQLite in-memory (via `pytest-django`). No external services are required.

Current baseline: **70 tests, all passing.**

---

## Docker Deployment

See [docs/deploy-docker.md](docs/deploy-docker.md) for the full guide.

Quick start:

```bash
cp .env.example .env
# Edit .env — set POSTGRES_PASSWORD, DJANGO_SECRET_KEY, SCD_INITIAL_ADMIN_PASSWORD, SCD_HOSTNAME
docker compose up -d
```

---

## User Roles

| Role | Description | Permissions |
|---|---|---|
| **User** | Regular SCD staff | Submit and manage their own entries; view their own dashboard |
| **Administrator** | SCD managers | All User permissions + manage taxonomy, view all entries, run reports, view audit log, manage user roles |
| **Auditor** | Read-only oversight | View all entries, run reports, view audit log — no write access |

Role assignment is done via the Admin Users page (`/admin-users/`) by an Administrator.

---

## URL Reference

| Path | View | Access |
|---|---|---|
| `/` | Dashboard | Authenticated |
| `/accounts/login/` | Login | Public |
| `/accounts/signup/` | Sign up | Public (can be disabled) |
| `/profile/` | Edit profile | Authenticated |
| `/admin-users/` | User management | Admin |
| `/taxonomy/projects/` | Manage projects | Admin |
| `/taxonomy/categories/` | Manage categories | Admin |
| `/entries/` | My entries list | Authenticated |
| `/entries/new/` | Create entry | Authenticated |
| `/entries/<pk>/` | Entry detail | Entry owner |
| `/entries/<pk>/edit/` | Edit entry | Entry owner |
| `/entries/<pk>/delete/` | Delete entry | Entry owner |
| `/reports/` | Report filter + export | Admin / Auditor |
| `/audit/` | Audit log viewer | Admin / Auditor |
| `/admin/` | Django admin | Superuser |

---

## Environment Variables

All variables are loaded via `.env` in Docker Compose. For local development, export them in your shell or prefix the management command.

### Required in production

| Variable | Description |
|---|---|
| `DJANGO_SECRET_KEY` | Django cryptographic key — generate with `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"` |
| `POSTGRES_PASSWORD` | PostgreSQL password |
| `SCD_INITIAL_ADMIN_PASSWORD` | Password for the initial admin account created by `seed_admin` |

### Optional / have defaults

| Variable | Default | Description |
|---|---|---|
| `DJANGO_ALLOWED_HOSTS` | `localhost` | Comma-separated list of valid `Host` header values |
| `DATABASE_URL` | `sqlite:///db.sqlite3` | Full database connection URL (dj-database-url format) |
| `POSTGRES_DB` | `scd` | PostgreSQL database name |
| `POSTGRES_USER` | `scd` | PostgreSQL user |
| `DJANGO_SETTINGS_MODULE` | *(set explicitly)* | Use `scd_reporting.settings.prod` in production |
| `GUNICORN_WORKERS` | `3` | Number of Gunicorn worker processes |
| `SCD_HOSTNAME` | `localhost` | Hostname Caddy listens on (enables automatic HTTPS for real domains) |
| `SCD_INITIAL_ADMIN_USERNAME` | `scd-admin` | Username of the bootstrapped admin |
| `SCD_INITIAL_ADMIN_EMAIL` | `scd-admin@fnal.gov` | Email of the bootstrapped admin |
| `SCD_DISABLE_LOCAL_SIGNUP` | `0` | Set to `1` to block new local accounts (for SSO-only deployments) |
| `ACCOUNT_EMAIL_VERIFICATION` | `optional` | allauth email verification mode: `none`, `optional`, or `mandatory` |

---

## Management Commands

### `seed_admin`

Creates the initial administrator account. Idempotent — safe to run on every deployment.

```bash
python manage.py seed_admin
```

Reads `SCD_INITIAL_ADMIN_USERNAME`, `SCD_INITIAL_ADMIN_EMAIL`, and `SCD_INITIAL_ADMIN_PASSWORD` from the environment. If `SCD_INITIAL_ADMIN_PASSWORD` is unset, the command exits with a warning and creates nothing.

See [docs/man/scd-seed-admin.1](docs/man/scd-seed-admin.1) for the full man page.

### `seed_taxonomy`

Seeds the default set of projects and categories. Idempotent — safe to run repeatedly.

```bash
python manage.py seed_taxonomy
```

Creates the following if they do not already exist:

**Projects:** DUNE, NOvA, MicroBooNE, CMS, LSST

**Categories:** Scientific, Operations, Outreach, Training

Additional projects and categories can be created through the web interface at `/taxonomy/projects/` and `/taxonomy/categories/` (Admin role required).

See [docs/man/scd-seed-taxonomy.1](docs/man/scd-seed-taxonomy.1) for the full man page.
