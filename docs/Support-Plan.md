# SCD Effort Reporting — Long-Term Support Plan

## Overview

This document describes a minimal-staffing support model for the SCD Effort Reporting application running on a well-supported OKD cluster at Fermilab. It covers:
* General code maintenance
* Deployment operations
* Backup strategy 
* Resource estimates, 
* Secrets management

There are also some recommendations for improving the codebase over time and how we would do that in the context of our Github model at FNAL.

# Assumptions

In the design of the application, there was an instrinsic assumption that it would be a "business hours best-effort" type of support model (rather than a 24x7 w/ on-call model), since nothing is critical to operations.

The design also assumes:

* User base of ~200 people
* Reporting schedule of ~ 1/week for most users
* Small number of manager type roles that need to run reporting (i.e. ~10)
* Security consistent w/ FNAL policy (i.e. single sign on)
* Minimal admin overhead (i.e. auto account creation, simple self-serve operations for most user maintence tasks)
* Web based interface w/ simple backend persistence
* Ability to migrate to a true Postgres backend if needed

# Code Base
The application is a Django 5 / Python web app backed by PostgreSQL (right now using SQLite for the test deployment, and this should actually be fine in the near term or pseduo long term).

The application is fully containerized.  The helper scripts that do the containerization assume Docker as basis for this, but then translate it to other container infrastructures (i.e. podman) and deploy it to our OKD cluster via Helm (which is standard).

Because this is a low-traffic, internal-facing only tool, the design is simple.  However even with this in mind its availability requirements are "business hours best-effort" rather than 24×7 on-call.

--> Should put an architectural diagram here.

---

## 1. Code Maintenance

The majority of the code is vanilla python + Django.  The formal depedancies are listed in the requirements.txt file for the project and can be installed/updated via Pip.  

The methodology that is used is that a python virtual environment is used for all dependancies, so things can be automatically upgraded (or migrated) easily.  There are bootstrap scripts that handle updates in an automated fashion, and a test suite that is run.  This handles the majority of simple maintenance and takes a couple of minutes to run (and can be run and tested on a laptop)

The code base itself is stored in GitHub, so bug can be tracked and pull requests handled easily.  The only pieces that aren't included in the GitHub repo are the various secrets that are needed for deployment (so a developer needs a copy of these to do certain types of testing.)

### Update Cadence

| Activity | Frequency | Effort | Automated | Notes |
|---|---|---|
| Dependency updates (`pip`, `npm`) | Monthly | 5-10 min | Yes | |
| Django major upgrades (e.g., 5 → 6) | Optional | 1 day | No | Freeze Version |
| Python major runtime upgrade | Every 18–24 months | 4–8 hrs | No | Freeze Version|
| Anthropic SDK / model version review | Quarterly | 5 min | Yes | Config change only |
| Bug fixes and feature requests | Ad hoc | Varies | No | Github managed |
| Security patches (CVEs) | As disclosed | Same-day to same-week | No | |

### Dependency Update Process

These steps run automatically through the boostrap script, but can also be run interactively.  The deploy script in particular is nice because it handles building the docker image and doing the configuration changes needed for OKD.

In general the major operations are:

1. Run `pip list --outdated` and review changelogs for breaking changes.
2. Update `requirements.txt`, rebuild the Docker image locally, run the test suite (`pytest`).
3. Commit, tag, and deploy following the standard process (`./scripts/deploy.sh`).

For the CSS components (which aren't actually critical since it's just display styles) you *can* update via npm.

For npm (Tailwind CSS build): `npm --prefix theme/static_src outdated` and update `package.json` as needed.

### AI Model Pin

The Anthropic model is configured via a Helm values key (`anthropic.model`). Review Anthropic's model deprecation notices quarterly and update the values file when a model is end-of-lifed. No code changes are required — only a values file update and Helm upgrade.

The important piece is that this is setup to look at our own LiteLLM frontend, so we are insulated from any changes that Anthropic might make, and it's only a configuration change, not a code change.

### Test Coverage

The existing `pytest-django` suite covers accounts, entries, reports, taxonomy, and audit. 

It can be run before any deployment:

```bash
pytest --tb=short -q
```

There are over 120 tests that it covers, so its pretty easy to find any true breaks in the code.

Integration testing is also covered by the deployment scripts (they check mainly the passing of config values but give info on the startup sequence and what is passing/failing)


---

## 2. Application Deployment and Updates

There are three separate way to test/deploy the application.

1. The application can be run "local" using a localhost setup (there is a start script for this) which allows for code development and testing of new features.
2. In a local container (i.e. local docker container) which allows for testing of the actual run time environment prior to deployment.  The scripts for this build a multi-architecture image so what you run on your laptop is the OSX arm build, but the exact same contain, when it's pushed to DockerHub, has the x86 build too.
3. Deployed on our OKD cluster (this is the "live" version, but we can also deploy a test version because it's OKD!)

### Standard Deployment

All deployments are handled by a single script:

```bash
./scripts/deploy.sh -t <tag> -f <values-file>
```

This script:
1. Pushes the current branch to GitHub (`fnal` remote).
2. Builds and pushes a multi-arch Docker image (`linux/amd64` + `linux/arm64`) to Docker Hub.
3. Runs `helm upgrade` against the OKD cluster.
4. Restarts the pod and waits for rollout to complete.

For configuration-only changes (no code changes), use `--skip-build --skip-push` to skip the Docker build and go straight to Helm upgrade and pod restart. This takes under 60 seconds.

### Tagging Convention

Tags use the format `vMM.mm.pp[-qualifier]`, e.g. `v00.05.01-pre`. Increment:
- **patch** for bug fixes and minor changes.
- **minor** for new features.
- **major** for breaking changes or major framework upgrades.

And a separate suffix is used for any descriptor that I want to attach (for example I might tag something as a "preview" with the "pre" descriptor or as a "release candidate" with the "rc" suffix.)

Tagging is standard GitHub tagging, so it's easy to change or move a tag as needed.

### Rollback

OKD keeps the previous Deployment revision. To roll back:

```bash
oc rollout undo deployment/web -n scd-reporting
```

To roll back to a specific Helm revision:

```bash
helm rollback scd-reporting <revision> -n scd-reporting
```

Revision history is visible via `helm history scd-reporting -n scd-reporting`.

### Zero-Downtime Consideration

Okay we don't need zero-downtime but....if....we....did....we can do it easily.

The current deployment uses `replicaCount: 1` with a `RollingUpdate` strategy. For true zero-downtime updates, increase to `replicaCount: 2` in the values file. The application is stateless (session data in the database, static files served by Gunicorn/Caddy) and supports multiple replicas without modification.  Slick right!

---

## 3. Backup Strategy

The way the application is designed and containerized, there is minimal critical data that needs to be backed up.  Essentially it's *ONLY* the persistent store that needs to be saved.  In the running application this is only the sqlite database.  The way the container works, it has been built with some extra utilities so that we can snap shot the DB and copy it out.  

Alternatively if we want to move to a Postgress host, the hooks are already there for that (and then we would just use the managed host model for our other Postgres instances as our strategy)

### What Needs Backing Up

| Asset | Where | Backup priority |
|---|---|---|
| PostgreSQL database | OKD PVC or external DB | **Critical** |
| SQLite database (if used) | `/app/data/db.sqlite3` on PVC | **Critical** |
| Helm values file (with secrets) | Outside the repo — see §5 | **Critical** |
| Django `SECRET_KEY` | In the values file | Critical (covered above) |

Secrets and deployment files are special.  These aren't really "backed up" so much as securely stored and managed.  See later on how this is done.

### Database Backup

**PostgreSQL (recommended for production):**  
Use the OKD cluster's built-in backup infrastructure or a CronJob that runs `pg_dump` nightly and ships the compressed dump to an S3-compatible endpoint (Rucio, CERN EOS, AWS S3, or any object store available at Fermilab):

```yaml
# Example OKD CronJob — adapt as needed
schedule: "0 2 * * *"   # 02:00 UTC daily
command:
  - pg_dump $DATABASE_URL | gzip > /backup/scd-$(date +%F).sql.gz
```

Retain 30 daily + 12 monthly snapshots. Test restore quarterly.

**SQLite (smaller/dev deployments):**  
Copy the PVC-mounted `/app/data/db.sqlite3` to object storage daily. The simplest approach is a CronJob using `rclone` or `oc rsync`. Keep at least 7 daily copies.

### Recovery Time

With a current backup, recovery from a total pod/PVC loss involves:
1. Restore database from latest dump (~5 min for typical SCD dataset size).
2. Re-run `helm upgrade` with the saved values file (~2 min).

Estimated Recovery Time: **< 30 minutes**.

---

## 4. Resource Estimates

These are based off of the current deployment and assumptions (see above).  The storage estimate is a project of what we would need if 200 people were making really verbose reports every week

### Compute (OKD)

| Resource | Recommended | Notes |
|---|---|---|
| CPU request | 100m | Gunicorn is CPU-light at SCD scale |
| CPU limit | 500m | Burst for AI summary generation |
| Memory request | 256 Mi | Django + Gunicorn steady state |
| Memory limit | 512 Mi | Headroom for PDF/XLSX export |
| Replicas | 1 (min), 2 (HA) | Single replica is fine for business-hours tool |
| PVC — database | 1 Gi | Ample for years of entry data |
| Docker Hub pulls | Low | `pullPolicy: Always` — consider `IfNotPresent` in steady state |

The AI summary feature makes outbound HTTPS calls to our LiteLLM instance.  Our OKD egress policy already handles these calls correctly.

### Manpower

| Role | Time per month | Responsibility |
|---|---|---|
| Primary maintainer | 12-16 hrs/yr | Dependency updates, bug fixes, deployments |
| Backup / reviewer | 1–2 hrs/yr | Code review, deployment approvals |

A single developer can maintain this application with roughly ** 2 hours per month** during steady state. Periods of active feature development would require more effort but given the general scope of what we want it seems reasonable.

No dedicated ops staff are required beyond what the OKD cluster already provides.

---

## 5. Secrets Management

### What Counts as a Secret

| Secret | Where it's used |
|---|---|
| `DJANGO_SECRET_KEY` | Session signing, CSRF tokens |
| `DATABASE_URL` | PostgreSQL connection string (user, password, host) |
| `ANTHROPIC_API_KEY` | AI summary calls |
| `OIDC_*` (client ID + secret) | Fermilab / CILogon SSO |
| Initial admin password | Seeded on first deploy only |
| Docker Hub credentials | Image push during build |

### Current Approach

Secrets are passed to the application via a Helm values file (`my-values.yaml`) that is **never committed to the repository**. The `values.yaml` checked into the repo contains only blank placeholders and comments marking required fields.

The actual secrets values are stored by the developers in a "vault" (and no this is not Andrew's laptop) and can be checked out or passed to people.

This is the minimum viable approach (and we can do better). 

---

### Scenario A: Private GitHub Repository

So what can we do for secrets management at FNAL?

A private repository is one option.  It reduces the blast radius of an accidental secret commit, but it is **not a substitute for proper secrets management** — secrets should never be committed to git regardless of repository visibility.

But since people do make mistakes, we can reduce our exposure by making the repo on FermiTools private (so that when someone invariably commits the my-values.yaml file, we just roll the commits back, rotate the secrets and are back up and running)

**Recommended approach:**

- Store the production values file in a **separate private repository** (e.g., `SCD-Reporting-deploy`) or a dedicated secrets store.
- Use **GitHub Actions secrets** (or Fermilab's equivalent CI/CD secrets store) to inject values at deploy time.
- Rotate the `DJANGO_SECRET_KEY` and database password annually or after any suspected compromise.
- Use `git-secrets` or a pre-commit hook to scan for accidental secret commits:
  ```bash
  pip install detect-secrets
  detect-secrets scan > .secrets.baseline
  ```

**Access control:**
- Limit repository write access to the primary maintainer and their backup.
- Require pull request reviews before merging to `main`.
- Protect the `main` branch; deploy only from tagged commits.

---

### Scenario B: Public GitHub Repository

However, what if we want to make this public so that more people can work with it and put in code changes?  

We can make the Fermitools repo  public.  But then any accidental commit of a secret is immediately exposed (and this will happen because people will do something by accident and commit a .env file or have a bad gitignore list).

What we would do in this case is separate the runtime secrets from "develop" so that we NEVER run with any secret that is in the primary repo tree.  This means separating out some of the deployment files, but is a trival modification to the rest of the scripts.

**Recommended approach:**

In this approach we would:

- Never store secrets in the repository, even in encrypted form
- Use **OKD Secrets** to inject secrets directly into the pod environment, bypassing the values file for sensitive keys:

  ```bash
  oc create secret generic scd-secrets \
    --from-literal=DJANGO_SECRET_KEY="..." \
    --from-literal=DATABASE_URL="..." \
    --from-literal=ANTHROPIC_API_KEY="..." \
    -n scd-reporting
  ```

  Reference the secret in the Helm chart via `envFrom`:
  ```yaml
  envFrom:
    - secretRef:
        name: scd-secrets
  ```

- Keep only non-sensitive configuration (hostnames, replica counts, feature flags) in the public values file.
- Separately maintain the sensitive values file in a **private repository** or a secrets manager (HashiCorp Vault, AWS Secrets Manager, etc.).
- Enable **GitHub secret scanning** on the public repo — GitHub will alert if it detects known secret patterns in any commit.
- Add a `.gitignore` entry for all `*-values.yaml`, `my-values.yaml`, and `.env` files.
- Add a `SECURITY.md` with a responsible disclosure contact so external contributors know how to report leaked credentials.

---

### Secrets Rotation

| Secret | Rotation trigger | Process |
|---|---|---|
| `DJANGO_SECRET_KEY` | Annual / compromise | Update values file, redeploy; all existing sessions invalidated |
| Database password | Annual / compromise | Update DB + values file, redeploy |
| `ANTHROPIC_API_KEY` | Annual / compromise | Rotate in Anthropic console, update values file, redeploy |
| OIDC client secret | Per IdP policy | Coordinate with Fermilab IAM team |
| Admin seed password | After first login | Delete the `initialAdminPassword` key from values file after first deploy |

---

## 6. Codebase Improvement Recommendations

The following improvements are suggested in roughly priority order. None are urgent; the application is functionally complete and stable.

### High Priority

**1. Migrate from SQLite to PostgreSQL for production**  
The Helm chart already supports PostgreSQL via `database.url`. SQLite on a PVC is fragile under OKD pod rescheduling and does not support concurrent writes. Migrate by dumping with `python manage.py dumpdata` and loading into PostgreSQL with `loaddata`, or use `pgloader`.

**2. Add a database migration CI check**  
The test suite currently does not verify that all migrations are applied. Add a CI step:
```bash
python manage.py migrate --check
```
This catches unapplied migrations before they reach production.

**3. Move from Docker Hub to a private registry**  
Docker Hub rate-limits unauthenticated pulls and is a public surface. Fermilab's Harbor registry (or GitHub Container Registry `ghcr.io`) is a better long-term home for production images, especially for a private repository scenario.

### Medium Priority

**4. Add a health check endpoint**  
OKD's liveness and readiness probes currently hit `/` (an authenticated page), which means the probe may report healthy when the database is down. Add a lightweight `/health/` view that checks the database connection and returns `200 OK` or `503`:

```python
# Minimal health check
def health(request):
    from django.db import connection
    connection.ensure_connection()
    return JsonResponse({"status": "ok"})
```

**5. Structured logging**  
Replace plain Gunicorn text logs with JSON-structured logs (using `python-json-logger`). This makes log aggregation with OKD's built-in EFK/Loki stack straightforward and enables alerting on error rates.

**6. Rate-limit the API endpoint**  
`POST /api/entries/` is currently unauthenticated beyond a valid Bearer token. Add Django's `django-ratelimit` or OKD's built-in route-level rate limiting to prevent bulk submission abuse.

**7. Pin the Anthropic model explicitly in code**  
The default model is currently a fallback constant in the source. Surfacing it in the Helm values file (already partially done) means model upgrades are configuration changes, not code changes, which simplifies the maintenance cycle.

### Lower Priority

**8. Extract the AI summary prompt to the database**  
The system prompt is already editable through the UI. Consider storing the user template in the database as well (it currently lives in the code), so prompt iteration does not require a deployment.

**9. Add export to more formats**  
Several stakeholders have requested Excel exports with formatting. The `openpyxl` dependency is already present; a formatted workbook exporter (column widths, frozen headers, table styles) would be a low-effort addition.

**10. Automate dependency updates with Dependabot**  
For a public repository, enable GitHub Dependabot for both `requirements.txt` and `theme/static_src/package.json`. For a private repository, configure Dependabot with a `dependabot.yml` file — it works on private repos with the appropriate GitHub plan.

**11. Add a staging environment**  
A second Helm release (`scd-reporting-staging`) pointing to a `:latest` or `:main` image tag, deployed to the same OKD namespace or a separate one, provides a safe place to validate changes before tagging a production release. The existing `deploy.sh` script supports this via the `-n` namespace flag.

---

## 7. Summary Checklist for the Supporting Developer

### Day-to-day (reactive)
- [ ] Monitor OKD pod events and logs (`oc logs deployment/web -n scd-reporting`)
- [ ] Respond to bug reports; patch and deploy using `deploy.sh`

### Monthly
- [ ] Run `pip list --outdated`; update and test dependencies
- [ ] Verify backup jobs completed successfully

### Quarterly
- [ ] Review Anthropic model deprecation notices
- [ ] Rotate credentials if approaching annual rotation schedule
- [ ] Run `pytest` against the main branch
- [ ] Test a backup restore to confirm recovery procedure works

### Annually
- [ ] Rotate `DJANGO_SECRET_KEY` and database password
- [ ] Evaluate Django LTS upgrade path
- [ ] Review OKD resource utilization; adjust CPU/memory limits if needed
- [ ] Review and update this document
