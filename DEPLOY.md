# Deployment Guide

SCD Activity Reporting runs as three Docker containers managed by Docker Compose:

| Service | Image | Role |
|---|---|---|
| `web` | built from `docker/web/Dockerfile` | Django + Gunicorn |
| `db` | `postgres:16-alpine` | PostgreSQL database |
| `caddy` | `caddy:2-alpine` | HTTPS reverse proxy, static files |

---

## Prerequisites

- **Docker Engine 24+** or **Docker Desktop** (includes Compose v2)
- A domain name with an A record pointing to your server (for production TLS)
- Outbound internet access from the server (Caddy fetches Let's Encrypt certificates)

Verify your installation:

```bash
docker --version       # Docker version 24+ or 25+
docker compose version # Docker Compose version v2.x
```

---

## First-time setup

### 1. Clone the repository

```bash
git clone https://github.com/normanajn/SCD-Reporting.git
cd SCD-Reporting
```

### 2. Create the environment file

```bash
cp .env.example .env
```

Edit `.env` and fill in **at minimum** these values:

```dotenv
# A long random string — generate with: python -c "import secrets; print(secrets.token_hex(32))"
DJANGO_SECRET_KEY=<50+ random characters>

# Your server's public hostname (no https://)
SCD_HOSTNAME=scd-reporting.example.org
DJANGO_ALLOWED_HOSTS=scd-reporting.example.org

# Database credentials (chosen by you — Compose creates the DB on first run)
POSTGRES_PASSWORD=<strong random password>

# Password for the initial scd-admin account
SCD_INITIAL_ADMIN_PASSWORD=<strong password>
```

> **SQLite note:** For a quick local test you can omit `POSTGRES_*` variables and
> comment out the `db` and `caddy` services. SQLite is the default when
> `DATABASE_URL` is not set.

### 3. (Optional) Configure OIDC or Google SSO

See [HOWTO-SSO.md](HOWTO-SSO.md) for full details. Add the relevant variables to
`.env` — no code changes are needed.

For an OIDC client secret stored in a file, mount the secrets directory into the
`web` container and point `OIDC_CLIENT_SECRET_FILE` at it:

```yaml
# compose.override.yaml — do not edit compose.yaml
services:
  web:
    volumes:
      - /etc/scd/secrets:/run/secrets:ro
```

```dotenv
# .env
OIDC_CLIENT_SECRET_FILE=/run/secrets/oidc_secret
```

### 4. Build and start

```bash
docker compose up -d --build
```

On the very first run this will:
1. Pull `postgres:16-alpine` and `caddy:2-alpine`
2. Build the `web` image (compiles Tailwind CSS, installs Python dependencies)
3. Start the database, run Django migrations, seed the initial admin account
4. Obtain a TLS certificate from Let's Encrypt (production only)

Watch the startup logs:

```bash
docker compose logs -f web
```

You should see:

```
[entrypoint] Running database migrations...
[entrypoint] Collecting static files...
[entrypoint] Seeding initial admin account...
[entrypoint] Starting gunicorn...
```

### 5. Verify

Open `https://<SCD_HOSTNAME>` in your browser. Sign in with:

- **Username:** `scd-admin`
- **Password:** the value of `SCD_INITIAL_ADMIN_PASSWORD` from your `.env`

Check that all three containers are healthy:

```bash
docker compose ps
```

All three services should show `(healthy)` or `Up`.

---

## Updating

```bash
git pull
docker compose up -d --build
```

Compose rebuilds only the `web` image, pulls any updated base images, and
restarts the changed services. Migrations run automatically on the next container
start.

To force a full rebuild without the Docker layer cache (after a Python dependency
change, for example):

```bash
docker compose build --no-cache web
docker compose up -d
```

---

## Secrets management

### Avoid putting secrets directly in `.env` when possible

For the OIDC client secret, the preferred pattern is a secret file:

```bash
sudo mkdir -p /etc/scd/secrets
echo "your-client-secret" | sudo tee /etc/scd/secrets/oidc_secret
sudo chmod 600 /etc/scd/secrets/oidc_secret
```

Then in `compose.override.yaml`:

```yaml
services:
  web:
    volumes:
      - /etc/scd/secrets:/run/secrets:ro
```

And in `.env`:

```dotenv
OIDC_CLIENT_SECRET_FILE=/run/secrets/oidc_secret
```

### Never commit `.env`

`.env` is listed in `.gitignore`. If you accidentally commit it, rotate all
secrets immediately and rewrite the git history.

---

## Backup and restore

### Backup the database

```bash
docker compose exec db pg_dump -U scd scd | gzip > scd-$(date +%Y%m%d).sql.gz
```

### Restore from a backup

```bash
# Stop the web container first to avoid writes during restore
docker compose stop web
gunzip -c scd-20260101.sql.gz | docker compose exec -T db psql -U scd scd
docker compose start web
```

### Backup uploaded media files

```bash
docker run --rm \
    -v scd-reporting_media:/data \
    -v $(pwd):/backup \
    alpine tar czf /backup/media-$(date +%Y%m%d).tar.gz -C /data .
```

---

## Routine operations

### View logs

```bash
docker compose logs -f            # all services
docker compose logs -f web        # web only
```

### Run a management command

```bash
docker compose exec web python manage.py <command>
```

For example, to open a Django shell:

```bash
docker compose exec web python manage.py shell
```

### Stop the stack

```bash
docker compose down          # stops containers, keeps volumes
docker compose down -v       # stops containers AND deletes all data volumes
```

---

## Architecture notes

### Static files

`collectstatic` runs automatically on every container start and writes to the
`staticfiles` Docker volume. Caddy serves `/static/*` and `/media/*` directly
from that volume without proxying to Django, so static assets are fast even under
load.

### TLS / HTTPS

Caddy automatically provisions and renews Let's Encrypt TLS certificates for
`SCD_HOSTNAME`. The `caddy_data` volume persists the certificate across restarts.

For local development or an intranet deployment where Let's Encrypt cannot reach
the server, Caddy falls back to a self-signed certificate. You may see a browser
warning — this is expected.

### Health checks

The `web` container exposes a health check that polls `/accounts/login/` every
30 seconds. Caddy will not receive traffic until the `web` container is healthy,
preventing 502 errors during startup or after a restart.

### Non-root container user

The `web` container runs as `appuser` (UID 1001). The `staticfiles` and `media`
volumes are owned by this UID. If you mount host directories in their place,
ensure they are readable and writable by UID 1001.

---

## Environment variable reference

| Variable | Required | Default | Description |
|---|---|---|---|
| `DJANGO_SECRET_KEY` | **Yes** | insecure dev key | Django secret key — must be unique and secret in production |
| `SCD_HOSTNAME` | **Yes** (prod) | `localhost` | Public hostname — used by Caddy and for CSRF trusted origins |
| `DJANGO_ALLOWED_HOSTS` | **Yes** (prod) | `localhost` | Comma-separated hostnames Django will serve |
| `POSTGRES_PASSWORD` | **Yes** (if using Postgres) | — | Postgres password |
| `POSTGRES_USER` | No | `scd` | Postgres username |
| `POSTGRES_DB` | No | `scd` | Postgres database name |
| `SCD_INITIAL_ADMIN_PASSWORD` | **Yes** (first run) | — | Password for the `scd-admin` account created on first start |
| `SCD_INITIAL_ADMIN_USERNAME` | No | `scd-admin` | Username for the initial admin account |
| `SCD_INITIAL_ADMIN_EMAIL` | No | `scd-admin@fnal.gov` | Email for the initial admin account |
| `GUNICORN_WORKERS` | No | `3` | Number of Gunicorn worker processes |
| `GUNICORN_LOG_LEVEL` | No | `info` | Gunicorn log verbosity (`debug`, `info`, `warning`, `error`) |
| `ACCOUNT_EMAIL_VERIFICATION` | No | `optional` | `none` \| `optional` \| `mandatory` |
| `SCD_DISABLE_LOCAL_SIGNUP` | No | `0` | Set to `1` to block new local account creation |
| `ANTHROPIC_API_KEY` | No | — | Enables AI-generated report summaries |
| `OIDC_PROVIDER_URL` | No | — | OIDC discovery URL — see [HOWTO-SSO.md](HOWTO-SSO.md) |
| `OIDC_CLIENT_ID` | No | — | OIDC client ID |
| `OIDC_CLIENT_SECRET_FILE` | No | — | Path to file containing the OIDC client secret |
| `OIDC_CLIENT_SECRET` | No | — | OIDC client secret as env var (file takes precedence) |
| `GOOGLE_CLIENT_ID` | No | — | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | No | — | Google OAuth client secret |
| `CSRF_TRUSTED_ORIGINS` | No | derived from `SCD_HOSTNAME` | Comma-separated trusted origins for CSRF (e.g. `https://scd.example.org`) |

---

## Troubleshooting

### Container exits immediately after starting

```bash
docker compose logs web
```

Common causes:
- `POSTGRES_PASSWORD` not set — Postgres refuses connections
- `DJANGO_SECRET_KEY` is the insecure default in `DEBUG=False` mode (prod settings enforce this)
- A migration failed — check for schema conflicts

### `502 Bad Gateway` from Caddy

The `web` container is not yet healthy. Check its status:

```bash
docker compose ps web
docker compose logs web
```

### Database connection refused

Ensure the `db` container is running and healthy before `web` starts. Compose
enforces this via `depends_on: condition: service_healthy`.

If you upgraded Postgres and the data volume has an older major version:

```bash
docker compose down
docker volume rm scd-reporting_pgdata   # destroys data — restore from backup first!
docker compose up -d
```

### "CSRF verification failed"

Ensure `SCD_HOSTNAME` in `.env` matches the hostname in the browser URL exactly.
The `CSRF_TRUSTED_ORIGINS` setting is derived from `SCD_HOSTNAME` automatically.
