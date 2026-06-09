# Deployment Guide

SCD Activity Reporting can run as either a singal Docker container for simple and test installations, or as three Docker containers managed by Docker Compose for more complex installs:

| Service | Image | Role |
|---|---|---|
|`simple` | build from `docker/web/Dockerfile` | Django + Gunicorn + sqlite |
|---|---|---|
| `web` | built from `docker/web/Dockerfile` | Django + Gunicorn |
| `db` | `postgres:16-alpine` | PostgreSQL database |
| `caddy` | `caddy:2-alpine` | HTTPS reverse proxy, static files |

The simple version combines everything that is needed into a single container.  It uses a sqlite (file based) database instead of a separate Postgres database.  The simple version is the same as the main web container, except that it uses a different configuration set to turn on/off features.  

The other point to note is that containers are made as dual architecture so that they can run on both a mac laptop (apple silicon arm64) and on our OKD cluster which is x86.

---

## Prerequisites

- **Docker Engine 24+** or **Docker Desktop** (includes Compose v2)
- A domain name with an A record pointing to your server (for production TLS) [This is setup by our OKD cluster]
- Outbound internet access from the server (Caddy fetches Let's Encrypt certificates) [This is setup by our OKD cluster]

Verify your installation:

```bash
docker --version       # Docker version 24+ or 25+
docker compose version # Docker Compose version v2.x
```

---

## First-time setup

This setup assumes you start with nothing and are going to clone the repo and bootstrap from there.

### 1. Clone the repository

```bash
git clone https://github.com/fermitools/SCD-Reporting.git
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
SCD_HOSTNAME=scd-reporting.fnal.gov
DJANGO_ALLOWED_HOSTS=scd-reporting.fnal.gov

# Database credentials (chosen by you — Compose creates the DB on first run)
POSTGRES_PASSWORD=<strong random password>

# Password for the initial scd-admin account
SCD_INITIAL_ADMIN_PASSWORD=<strong password>
```

> **SQLite note:** For a quick local test you can omit `POSTGRES_*` variables and
> comment out the `db` and `caddy` services. SQLite is the default when
> `DATABASE_URL` is not set.

### 3. (Optional) Configure OIDC or Google SSO

Authentication is handled via a number of different supported methods.  For testing
it is important that you have AT LEAST one version that will get you into the admin 
role in Django.  For the very first time you spin up the application, you will NEED 
this to be password based so that you can login as admin and then promote another 
account to admin level (i.e. an account that is authenticated via a SSO or other 
provider chain)

After that you will want to enable some form of Single signon or identity provider chain.
To do this....

See [HOWTO-SSO.md](HOWTO-SSO.md) for full details. Add the relevant variables to
`.env` — No code changes are needed to enable/disable an identity provider.  You 
just need to set or leave blank the entries that correspond to their secrets and urls

When the application loads, it will look for the `.env` file.  If you want your secrets coming
directly from the `.env` file then it needs to be visible inside the container at runtime.
In this case to access an OIDC client secret stored in a file, you will have to mount the secrets directory into the
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
Which makes it vissible to the container image.  Alternatives are to pass secrets as environment variables
during startup of the application.

### 4. Build and start

There are three ways to run the application:

- **Direct / local webserver** — best for development; runs Django's dev server directly on your machine
- **Local containerised webserver** — runs the full Docker Compose stack (web + postgres + caddy) locally
- **OKD deployment** — production deployment via Helm on the Fermilab OKD cluster

---

#### Option A: Direct / local webserver (development)

`scripts/start-scd-reporting` creates the virtual environment, installs/updates all dependencies, runs migrations, seeds initial data, and starts the Django development server in the background.

**First run (sets the admin password):**

```bash
./scripts/start-scd-reporting --admin-password yourpassword
```

**Subsequent runs (no password needed — account already exists):**

```bash
./scripts/start-scd-reporting
```

If for some reason you can't remember what you set the admin password to you can change
it via the commandline for the locally running server:

```
> python manage.py changepassword scd-admin
Changing password for user 'scd-admin@fnal.gov'
Password: 
Password (again): 
Password changed successfully for user 'scd-admin@fnal.gov'
```

The server starts at <http://127.0.0.1:8000> and logs to `scripts/logs/scd-reporting.log`.  You should be able to login
with the scd-admin account.  From the main page enter the `scd-admin@fnal.gov` email and the password you set.

[Alt]
Altneratively you can use the Django admin url to login directly to the backend.  The endpoint for this (assuming you spun it up on port 8000) is:
```
http://localhost:8000/admin/
```
Here you login as `scd-admin` and use your password that you set.

Congrats you now have a working application!

**Common options:**

When starting up using the scripts you can pass a number of common options.  These will
override anything that is in the config files or passed through the .env file.  (See the manpages for details)

| Option | Description |
|---|---|
| `--admin-password <pass>` | Set/reset the initial admin password (first run) |
| `--anthropic-key <key>` | Enable the AI Summary feature |
| `--oidc-provider-url <url>` | OIDC discovery URL (enables SSO button) |
| `--oidc-client-id <id>` | OIDC client ID |
| `--oidc-secret-file <path>` | Path to a file containing the OIDC client secret |
| `--port <port>` | Port to listen on (default: `8000`) |
| `--prod` | Bind to `0.0.0.0`, use production settings |
| `--no-update` | Skip pip/npm dependency update checks |
| `--with-tailwind` | Also start the Tailwind CSS watcher (hot-reload CSS) |
| `--tail` | Tail the server log after starting |

All options can also be set via environment variables or a `.env` file in the project root — see the script header for the mapping.

**Stop the server:**

To stop the locally running server use:

```bash
./scripts/stop-scd-reporting
```

Pass `--tail` to print the last 20 log lines before stopping:

```bash
./scripts/stop-scd-reporting --tail
```

This is useful to see a "post-mortem" of what might have gone wrong if things get stuck.

NOTE:

When using the local "live" version of the application you can make code changes to the html or underlying
database models and they will be instantantly reflected in the application.  This is useful if you are doing interface
modification or changing parts of the schema since you don't have to rebuild the whole project.  It's MUCH faster than
doing development against the docker-ized version or the deployed OKD version.

---

#### Option B: Local Docker Compose (containerised)

If you want to test in a more "production-like" environment, then you want to build out the 
docker container and run that.  This is important because it builds the image and embeds 
all the files, mounts areas etc... Basically it gets the application ready to run some
place other than your local development environment (i.e. not on Andrew's Laptop)

First you build the image using the `docker compose` syntax:

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

You can also run the `start-docker` and `stop-docker` scripts to fire up
the application from docker.  In this case it will need to bind to some ports
on your local machine so make sure that these are free before firing it up (or map 
the ports to a range that you aren't using). Using scripts will ensure that
options are passed correctly.

*IF* you use Docker-desktop you can also launch from there.

---

#### Option C: OKD / Helm (production)

The final deployment option is to fully deploy to the Fermilab OKD 
cluser.  For this you will need to be added to the project 
on the OKD cluster.  You will also need to login etc....

In general see the [OKD Deployment](#okd--helm-deployment) section below for details on
how this all works and the helper scripts.

---

### 5. Verify

Once you have a running instance of the application you will want to check it.  Open up your
web browser (firefox or chrome work well) and go to the appropriate URL:

Open `http://127.0.0.1:8000` (local) or `https://scd-reporting.fnal.gov` (Docker/OKD) in your browser. Sign in with:

If you don't have any other accounts created you will login as the admin.

- **Username:** `scd-admin`
- **Password:** the value you passed to `--admin-password` or `SCD_INITIAL_ADMIN_PASSWORD`

For Docker Compose, check that all services are healthy:

```bash
docker compose ps
```

All services should show `(healthy)` or `Up`.

---

## Updating

Now for the fun part.  You want to make some changes...how do you do it and push it out?
First off there are a couple of different layers.
* Web application (Django/python logic)
* Webpage Templates (CSS w/ Tailwind)
* Configuration parameters
* Backend database/data store

To update your code base you will do a pull from the repository and then you will
need to rebuild the container image.  This is basically a git command followed by a 
`docker compose`

```bash
git pull
docker compose up -d --build
```

Compose rebuilds only the `web` image, pulls any updated base images, and
restarts the changed services. Migrations run automatically on the next container
start.

To force a full rebuild without the Docker layer cache (after a Python dependency
change, for example) you need to rebuild and then update:

```bash
docker compose build --no-cache web
docker compose up -d
```

This is true if you are working with the web application or the webpage/templates

If you are working with configuration or secrets that is done separately.

---

## Secrets management

There are a lot of *secrets* which are needed for an application like 
this and we don't want to expose them, but we do want to pass them 
to the application and to have them active at run time.  This means that
we have to be careful about how we work with them.

Best practice is to just never have them written down anywhere 
durable and pass them to the program on startup.  That's not practical 
when it comes to API keys and the like this is where we have 
managed secrets and need to be careful about what gets committed to GitHub.

### Avoid putting secrets directly in `.env` when possible

The `.env` file is a really great way to set a whole bunch of 
environment variables that we need at runtime.  The problem is that
if it were to get committed to the GitHub repo, that would be bad 
since people could see the secrets that are in it.

That being said....for local testing the `.env` file is great.
There is a skeleton for this that has all the fields that I typically
use.  Copy the example file to `.env` and fill out the fields 
with the right values.  Then you are off to the races and can
spin up with different services enabled that you wouldn't 
want in production (like for example Google Sign in
so you can test different account setups without relying on the fermi SSO, 
or to get a couple of different accounts setup so you can do cross user
testing)

But there are better ways to do this...

So for the OIDC client secret (the Fermi SSO), the preferred pattern is a secret file:

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

Slick right?  Basically you put the reference in the `.env` file which makes 
startup ease, and the actual value in a different place which can be read
at run time.

### Never commit `.env`

`.env` is listed in `.gitignore`. If you accidentally commit it, rotate all
secrets immediately and rewrite the git history.

This is a pain.  Just don't do commit your `.env`.  Please don't.

The rest of the secrets are handled the same way.  So use this as a pattern and 
the application will start up with the right things active.

---

## Backup and restore

This whole application is designed to be mostly ephemeral.  The only parts that need
to survive restarts are the backend database and the secrets/config.  Everything else 
can be part of the git repo and can be tagged.  In the case of an sqlite deployment the db file
will live in a persisted area on the OKD cluser.  For your local installs it's 
in the top level of the project.  For a postgres deployment, the data lives in
that server.

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

There are a number of "management commands" that you are going to want
to have access to when you are developing or debugging.  The most common
will be reseting the admin password and clearing portions of the database.
There is a helper script `manage.py` which handles this.  Read the 
instructions, but for the most part it is just:

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
