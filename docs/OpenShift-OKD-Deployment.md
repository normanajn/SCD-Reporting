# OpenShift OKD Deployment Checklist

Use this checklist to adapt SCD Reporting for deployment on an OpenShift OKD cluster.

## 1. Container Readiness

- [ ] Use the Django/Gunicorn web container as the app workload.
- [ ] Do not deploy the Compose Caddy container unless you intentionally choose a sidecar/static-server design.
- [ ] Confirm the app listens on port `8000`.
- [ ] Update any stale port references in deployment manifests or scripts.
- [ ] Make the Docker image compatible with OKD arbitrary UIDs.

Recommended Dockerfile permission pattern:
∏
```dockerfile
RUN mkdir -p staticfiles media \
    && chgrp -R 0 /app \
    && chmod -R g=u /app \
    && chmod +x /app/docker/web/entrypoint.sh
```

OKD runs containers as non-root unique users by default, so writable paths must not depend on a fixed UID such as `appuser`.

## 2. Static And Media Files

- [ ] Decide how `/static/` will be served.
- [ ] Decide how `/media/` user uploads will be persisted.
- [ ] Do not rely on ephemeral pod storage for uploaded media in production.

Recommended options:

- [ ] Add WhiteNoise for Django static files, or run a dedicated static server.
- [ ] Use S3/object storage or a PVC-backed media volume for uploaded media.
- [ ] If using a PVC for media, mount it at `/app/media`.
- [ ] If using static collection at runtime, mount or prepare `/app/staticfiles`.

## 3. Startup Tasks

- [ ] Remove production-only setup work from the long-running web container startup path where practical.
- [ ] Run database migrations as an OKD `Job`.
- [ ] Run initial admin seeding as an OKD `Job` or one-time administrative command.
- [ ] Avoid running migrations from every web pod during scale-up or restart.

Current entrypoint tasks to split or explicitly accept:

```bash
python manage.py migrate --noinput
python manage.py collectstatic --noinput --clear
python manage.py seed_admin
gunicorn scd_reporting.wsgi:application --bind 0.0.0.0:8000
```

## 4. Database

- [ ] Use PostgreSQL for OKD.
- [ ] Do not use SQLite in production.
- [ ] Choose a database provider:
  - [ ] External managed PostgreSQL
  - [ ] PostgreSQL Operator, such as CrunchyData
  - [ ] Cluster-provided PostgreSQL template/operator
- [ ] Create the database.
- [ ] Create the database user.
- [ ] Store the connection string in an OKD `Secret`.

Required format:

```dotenv
DATABASE_URL=postgres://user:password@postgres-host:5432/scd
```

## 5. Configuration

- [ ] Create an OKD `ConfigMap` for non-secret settings.
- [ ] Create an OKD `Secret` for sensitive settings.
- [ ] Set production settings.
- [ ] Set the public hostname.
- [ ] Set CSRF trusted origins.

Minimum required environment:

```dotenv
DJANGO_SETTINGS_MODULE=scd_reporting.settings.prod
DJANGO_ALLOWED_HOSTS=scd-reporting.apps.<cluster-domain>
CSRF_TRUSTED_ORIGINS=https://scd-reporting.apps.<cluster-domain>
DATABASE_URL=postgres://...
MFA_WEBAUTHN_ALLOW_INSECURE_ORIGIN=false
```

Minimum required secrets:

```dotenv
DJANGO_SECRET_KEY=<strong-secret>
SCD_INITIAL_ADMIN_EMAIL=scd-admin@fnal.gov
SCD_INITIAL_ADMIN_PASSWORD=<initial-password>
POSTGRES_PASSWORD=<database-password>
```

Optional secrets/config:

```dotenv
ANTHROPIC_API_KEY=<api-key>
OIDC_PROVIDER_URL=<provider-url>
OIDC_CLIENT_ID=<client-id>
OIDC_CLIENT_SECRET=<client-secret>
GOOGLE_CLIENT_ID=<client-id>
GOOGLE_CLIENT_SECRET=<client-secret>
EMAIL_HOST=<smtp-host>
EMAIL_PORT=587
EMAIL_HOST_USER=<smtp-user>
EMAIL_HOST_PASSWORD=<smtp-password>
DEFAULT_FROM_EMAIL=<sender-address>
```

## 6. OKD Resources

- [ ] Create an OKD project/namespace.
- [ ] Create app `Secret`.
- [ ] Create app `ConfigMap`.
- [ ] Create PostgreSQL resources or external database secret.
- [ ] Create migration `Job`.
- [ ] Create optional seed-admin `Job`.
- [ ] Create web `Deployment`.
- [ ] Create web `Service`.
- [ ] Create external `Route`.
- [ ] Create optional media `PersistentVolumeClaim`.
- [ ] Create optional image `ImageStream`.
- [ ] Create optional `BuildConfig`, if building inside OKD.

Expected service port:

```yaml
ports:
  - name: http
    port: 8000
    targetPort: 8000
```

Expected route shape:

```yaml
tls:
  termination: edge
  insecureEdgeTerminationPolicy: Redirect
```

Expected deployment container shape:

```yaml
ports:
  - containerPort: 8000
envFrom:
  - secretRef:
      name: scd-reporting-secrets
  - configMapRef:
      name: scd-reporting-config
```

## 7. Build And Image Publishing

- [ ] Choose an image build path:
  - [ ] Build externally and push to a registry OKD can pull from.
  - [ ] Build inside OKD with `BuildConfig`.
- [ ] Tag the image with a version, commit SHA, or release tag.
- [ ] Configure OKD image pull credentials if needed.
- [ ] Confirm the image can be pulled by the target namespace.

Example external build:

```bash
docker build -f docker/web/Dockerfile -t registry.example.org/scd-reporting:<tag> .
docker push registry.example.org/scd-reporting:<tag>
```

## 8. Health Checks

- [ ] Configure readiness probe.
- [ ] Configure liveness probe.
- [ ] Point probes at a stable, unauthenticated or redirect-tolerant path.
- [ ] Confirm probes use port `8000`.

Current container health check target:

```text
http://localhost:8000/accounts/login/
```

## 9. First Deployment

- [ ] Apply ConfigMap and Secret.
- [ ] Deploy or connect PostgreSQL.
- [ ] Run migration Job.
- [ ] Run seed-admin Job.
- [ ] Deploy web Deployment.
- [ ] Create Service.
- [ ] Create Route.
- [ ] Open the public route URL.
- [ ] Confirm the login page is styled.
- [ ] Log in as the initial admin email.
- [ ] Run `seed_taxonomy` if it is not part of the initial Job flow.

Useful commands:

```bash
oc project <namespace>
oc apply -f deploy/okd/
oc get pods
oc get route
oc logs deploy/scd-reporting-web
```

## 10. Post-Deployment Validation

- [ ] Confirm `/accounts/login/` loads.
- [ ] Confirm static CSS loads.
- [ ] Confirm admin login works.
- [ ] Confirm database migrations are applied.
- [ ] Confirm taxonomy records exist.
- [ ] Create a test entry.
- [ ] Confirm media upload behavior, if media uploads are used.
- [ ] Confirm reports work for admin/auditor roles.
- [ ] Confirm SSO callback URLs match the OKD route hostname, if SSO is enabled.
- [ ] Confirm email sending works, if SMTP is enabled.
- [ ] Confirm logs do not expose secrets.

Static CSS smoke test:

```bash
curl -I https://scd-reporting.apps.<cluster-domain>/static/css/dist/styles.css
```

Expected result:

```text
HTTP/2 200
```

## 11. Known Project-Specific Items To Resolve

- [ ] Confirm `compose.yaml` port mapping matches the image port (`8000`).
- [ ] Decide whether `collectstatic` should run at image build time, migration Job time, or web startup time.
- [ ] Decide how uploaded media should be stored before running more than one replica.
- [ ] Keep Docker Compose deployment docs separate from OKD deployment docs.
- [ ] Document the canonical admin login as the email address, not the username.

## 12. Reference Links

- OKD overview and container security model: https://okd.io/docs/project/about/
- OKD secured routes: https://docs.okd.io/4.19/networking/ingress_load_balancing/routes/secured-routes.html
