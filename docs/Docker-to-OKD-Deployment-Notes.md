# SCD Reporting — Docker-to-OKD Deployment Notes

This document describes the end-to-end process for building, updating, and deploying the
SCD Reporting application to the Fermilab OKD cluster.

---

## Table of Contents

1. [Overview](#overview)
2. [A — Building and Pushing the Docker Image](#a--building-and-pushing-the-docker-image)
3. [B — Secrets Propagation](#b--secrets-propagation)
4. [C — OKD Deployment via Helm](#c--okd-deployment-via-helm)
5. [D — Items of Note](#d--items-of-note)

---

## Overview

```
Code change → git commit/push → build-docker.sh (multi-arch) → Docker Hub
                                                                    ↓
                                              helm upgrade (with secrets) → OKD
                                                                    ↓
                                              oc rollout restart → new pod running
```

The application runs as a single `web` pod in the `scd-reporting` namespace on OKD.
Data is persisted in two Ceph-backed PVCs (`scd-reporting-sqlite-data` and
`scd-reporting-media`) that survive pod restarts and upgrades.

---

## A — Building and Pushing the Docker Image

### Prerequisites

- Docker Desktop running with the `multiarch` buildx builder active
- Logged in to Docker Hub: `docker login`

### Standard build and push

```bash
./scripts/build-docker.sh --push
```

This builds for **both** `linux/amd64` and `linux/arm64` and pushes a multi-arch manifest
to `docker.io/normanajn/scd-reporting-web:latest`. OKD automatically pulls the `amd64`
variant.

### Build options

| Option | Description |
|---|---|
| `--push` | Push to Docker Hub after building |
| `--load` | Load into local Docker daemon (single platform only) |
| `--platforms linux/amd64` | Build for a single architecture |
| `-t v1.2.0` | Tag with a specific version (also tags `:latest`) |
| `--no-cache` | Force a clean rebuild of all layers |

### Versioned release build

When cutting a release, tag the git commit first — the script picks up the tag automatically:

```bash
git tag v1.2.0
git push origin v1.2.0
./scripts/build-docker.sh --push          # builds :v1.2.0 and :latest
```

### Local dev/testing (no OKD)

```bash
docker-compose -f compose-simple.yaml up --build
```

This uses SQLite and dev settings on `http://localhost:8000`. Comment out
`OIDC_CLIENT_SECRET_FILE` in `.env` if running without the OIDC credential file.

---

## B — Secrets Propagation

### What is a secret in this project

The following values are sensitive and must **never** be committed to git:

| Secret | Helm key | Description |
|---|---|---|
| Django secret key | `django.secretKey` | 50+ char random string |
| Admin password | `django.initialAdminPassword` | Initial `scd-admin` password |
| OIDC client secret | `oidc.clientSecret` | Keycloak client secret |
| Anthropic API key | `anthropic.apiKey` | For AI report summaries |
| Email password | `email.password` | SMTP credential |
| Google client secret | `google.clientSecret` | OAuth credential |

### How secrets reach the pod

Secrets are stored in a Kubernetes `Secret` object (`scd-reporting-secret`) created and
managed by Helm. They are injected into the pod as environment variables via `envFrom`.

Helm receives the values at upgrade time via `--set` flags or a local override file
(see below). They are **never** stored in `helm/simple/values.yaml` or committed to git.

### Recommended approach — local override file

Create a file called `my-values.yaml` **outside the repository** (or inside but git-ignored):

```yaml
django:
  secretKey: "V2CSywJLIpeukkIm0FqoUzNal8RA3EM0Q1sVyzbefQGdAOjmAiz13myVIMfWgIjBhIw"
  initialAdminPassword: "neutrino"

oidc:
  providerUrl: "https://kc.apps.okddev.fnal.gov/realms/myrealm/.well-known/openid-configuration"
  clientId: "scd-report-summarizer"
  clientSecret: "S6fs4BWwUplSrzbceLlXwdG3FCnNl1HR"

anthropic:
  apiKey: ""

email:
  password: ""

google:
  clientSecret: ""

route:
  hostname: scd-reporting.fnal.gov

certManager:
  enabled: true
```

Then pass it to every `helm upgrade`:

```bash
helm upgrade scd-reporting ./helm/simple -n scd-reporting -f /path/to/my-values.yaml
```

### OIDC client secret location

The raw secret is stored locally at:

```
~/Credentials/OIDC-Secrets/scd-reporting-oidc-secret.txt
```

It is passed directly as `oidc.clientSecret` — no file mount is needed in the container.

---

## C — OKD Deployment via Helm

### Prerequisites

- `helm` CLI installed
- `oc` CLI installed and logged in to the OKD cluster
- Docker image already pushed to Docker Hub (see Section A)

### Full upgrade command

```bash
helm upgrade scd-reporting ./helm/simple \
  -n scd-reporting \
  -f /path/to/my-values.yaml
```

Or with individual `--set` flags:

```bash
helm upgrade scd-reporting ./helm/simple \
  -n scd-reporting \
  --set django.secretKey="..." \
  --set django.initialAdminPassword="..." \
  --set oidc.clientSecret="..." \
  --set route.hostname=scd-reporting.fnal.gov \
  --set certManager.enabled=true
```

### Forcing a pod restart to pull the new image

Because `imagePullPolicy: Always` is set, a rollout restart will pull the latest image
from Docker Hub:

```bash
oc rollout restart deployment/web -n scd-reporting
```

Wait for the new pod to be ready:

```bash
oc get pods -n scd-reporting -w
```

### First-time install

If the namespace does not yet exist:

```bash
oc new-project scd-reporting
helm install scd-reporting ./helm/simple \
  -n scd-reporting \
  -f /path/to/my-values.yaml
```

### Checking release history

```bash
helm history scd-reporting -n scd-reporting
```

### Rolling back a bad release

```bash
helm rollback scd-reporting -n scd-reporting          # rolls back one revision
helm rollback scd-reporting 5 -n scd-reporting        # rolls back to revision 5
```

### Verifying the deployment

```bash
oc get pods -n scd-reporting          # should show 1/1 Running
oc get route -n scd-reporting         # should show scd-reporting.fnal.gov
oc logs deployment/web -n scd-reporting --tail=50
```

### cert-manager TLS certificate

The Helm chart manages a `cert-manager.io/v1 Certificate` resource that requests a
signed certificate from the `incommon-acme` `ClusterIssuer` and stores it in the
`scd-reporting-tls` secret. The OKD Route references this secret via
`spec.tls.externalCertificate`, and a `Role`/`RoleBinding` grants the OKD router
serviceaccount permission to read it.

#### Prerequisites

A cluster admin must configure the OPA admission policy to permit the `scd-reporting`
namespace to request certificates for `scd-reporting.fnal.gov` before this will work.
Without that permission the `Certificate` resource will be rejected at apply time.

#### First-time certificate setup (two-step process)

Because the Route cannot reference a secret that does not yet exist, the certificate
must be issued before wiring it into the Route.

**Step 1** — create the `Certificate` resource and wait for it to be issued:

```bash
helm upgrade scd-reporting ./helm/simple -n scd-reporting \
  -f /path/to/my-values.yaml \
  --set certManager.enabled=true \
  --set certManager.externalCertificate=false
```

Watch cert-manager issue the certificate (takes ~30–60 seconds):

```bash
oc get certificate -n scd-reporting -w
# Wait until READY = True
```

**Step 2** — wire the issued secret into the Route and grant the router RBAC:

```bash
helm upgrade scd-reporting ./helm/simple -n scd-reporting \
  -f /path/to/my-values.yaml \
  --set certManager.enabled=true \
  --set certManager.externalCertificate=true
```

Verify the Route is using the certificate:

```bash
oc get route web -n scd-reporting -o jsonpath='{.spec.tls}' | python3 -m json.tool
# Should show: "externalCertificate": {"name": "scd-reporting-tls"}
```

#### Subsequent upgrades

Once the certificate and RBAC are in place, pass both flags on every future upgrade:

```bash
--set certManager.enabled=true --set certManager.externalCertificate=true
```

Or add both to `my-values.yaml`:

```yaml
certManager:
  enabled: true
  externalCertificate: true
```

cert-manager automatically renews the certificate before expiry — no manual
intervention required.

#### Helm values reference

| Value | Default | Description |
|---|---|---|
| `certManager.enabled` | `false` | Create the `Certificate` resource |
| `certManager.clusterIssuer` | `incommon-acme` | Name of the `ClusterIssuer` |
| `certManager.secretName` | `scd-reporting-tls` | Secret cert-manager writes the cert into |
| `certManager.externalCertificate` | `false` | Wire the secret into the Route and create router RBAC |

---

## D — Items of Note

### Data persistence

| Volume | Mount | Content | Survives restarts? |
|---|---|---|---|
| `scd-reporting-sqlite-data` | `/app/data` | SQLite database | Yes (Ceph PVC) |
| `scd-reporting-media` | `/app/media` | User uploads | Yes (Ceph PVC) |
| *(image layer)* | `/app/staticfiles` | Compiled CSS/JS | Repopulated on every startup |

Static files are re-collected from the image on every container start (`collectstatic
--clear`). This is intentional — static files are part of the image, not persistent state.

### Automatic startup tasks

The entrypoint (`docker/web/entrypoint.sh`) runs these on every pod start:

1. `manage.py migrate` — applies any pending database migrations
2. `manage.py collectstatic` — copies static files into `/app/staticfiles`
3. `manage.py seed_taxonomy` — idempotent; creates projects, categories, and lab priorities if missing
4. `manage.py seed_admin` — idempotent; creates the `scd-admin` superuser if missing, and ensures the allauth `EmailAddress` record exists

### Django settings in OKD

The simple chart runs with `DJANGO_SETTINGS_MODULE=scd_reporting.settings.dev`
(DEBUG=True, relaxed ALLOWED_HOSTS). This is intentional for the simple/SQLite
deployment. For a production PostgreSQL deployment use `helm/compose` and
`scd_reporting.settings.prod`.

### HTTPS and the OKD router

TLS is terminated at the OKD HAProxy router (edge termination). The app itself speaks
plain HTTP internally. `SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')`
is set in `base.py` so Django correctly identifies requests as HTTPS — this is required
for OIDC callback URLs and CSRF to work correctly.

### OIDC / Fermilab SSO

- Provider: `https://kc.apps.okddev.fnal.gov/realms/myrealm`
- Client ID: `scd-report-summarizer`
- Redirect URI registered in Keycloak:
  `https://scd-reporting.fnal.gov/accounts/oidc/keycloak/login/callback/`
- OIDC is optional — if `oidc.clientSecret` is empty, the SSO button is hidden and
  local email/password login still works.

### Adding users

Users created through the Django admin panel bypass django-allauth's normal signup
flow and will not have an `EmailAddress` record, causing silent login failures.
After creating a user via the admin, run:

```bash
oc exec deployment/web -n scd-reporting -- python manage.py shell -c "
from django.contrib.auth import get_user_model
from allauth.account.models import EmailAddress
User = get_user_model()
user = User.objects.get(email='user@example.com')
EmailAddress.objects.get_or_create(user=user, email=user.email,
    defaults={'primary': True, 'verified': True})
"
```

Or create users through the sign-up form at `/accounts/signup/` — allauth handles
`EmailAddress` creation automatically that way.

### Multi-architecture builds

The build script always targets `linux/amd64,linux/arm64`. OKD nodes are `amd64`;
the `arm64` variant supports local Mac testing with `docker-compose`. Both are pushed
as a single multi-arch manifest — no separate tags needed.

### SSH host key warning during git push

```
Warning: the ED25519 host key for 'github.com' differs from the key for the IP address ...
```

This warning is benign. GitHub uses multiple IP addresses and the host key itself
matches — the warning is about the IP-to-key mapping in `known_hosts`, not a
security issue.
