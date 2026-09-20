# billow

Billing software built with Django.

> **Work in progress.** Proper documentation will be written once the core is in place.

## Setup

```bash
cp .env.example .env   # then fill in DJANGO_SECRET_KEY and DJANGO_DATABASE_URL
docker compose up
```

Neither stack runs a database: point `DJANGO_DATABASE_URL` at a Postgres you
already have. Inside a container `localhost` means the container, so one
running on your own machine is reached as `host.docker.internal`. Uploads stay
on local disk while `DJANGO_DEBUG` is on, so no bucket is needed to develop.

Two containers come up: `django`, running the
autoreloading server against a bind mount of this directory, and `tailwind`,
watching `assets/css/app.css` and recompiling `static/css/app.css` on every
change. Dependencies and migrations are applied on each start, so pulling a
branch that adds either needs no rebuild. The app is on
<http://localhost:8000>.

They run as your own uid, so the database, new migrations and the compiled
stylesheet stay editable on the host. Set `DOCKER_UID`/`DOCKER_GID` in `.env`
and rebuild if your account is not the usual 1000.

```bash
docker compose exec django python manage.py createsuperuser
docker compose exec django python manage.py makemigrations
docker compose logs -f tailwind
```

Running on the host instead works the same way:

```bash
uv sync
npm install
uv run manage.py migrate   # needs DJANGO_DATABASE_URL reachable
uv run manage.py createsuperuser
npm run watch &          # or `npm run build` once
uv run manage.py runserver
```

Set `DJANGO_DEBUG=True` in `.env` for local development. Every configurable
setting is listed in [`.env.example`](.env.example).

## Tests and linting

```bash
uv run pytest
uv run ruff check .
uv run ruff format .
```

## Running in production

```bash
cp .env.example .env   # DJANGO_SECRET_KEY and DOCKER_IMAGE are required
docker compose -f compose.prod.yaml up -d
```

The production image carries the source, the virtualenv and the compiled
stylesheet, and nothing else: no npm, no uv, no lockfiles, no dev dependencies.
It runs as an unprivileged user on a read-only filesystem with every capability
dropped. `migrate` runs to completion first; gunicorn only starts once it has.

Static files are served by WhiteNoise from the app process, so no separate
static file server is needed. The container terminates no TLS and answers no
hostname — it publishes to `127.0.0.1` for a reverse proxy on the same host to
forward to, and that proxy must set `X-Forwarded-Proto` and strip any copy of
it a client sent, since `settings.py` trusts it.

The stack is stateless and mounts no volumes. The database is a Postgres server
named by `DJANGO_DATABASE_URL`, and uploads go to the S3-compatible bucket
configured in `.env` — Backblaze B2 or Cloudflare R2, with a Cloudflare domain
in front of it via `DJANGO_S3_CUSTOM_DOMAIN`. Both containers can be destroyed
and recreated with nothing to migrate out of them; what needs backing up is the
Postgres server and the bucket, neither of which these files manage.

`GET /healthz` returns `200` with `{"status": "ok", "database": "up"}` when the
process can reach the database, and `503` with `{"status": "error", "database":
"down"}` otherwise; it is what both compose files use as the container
healthcheck.

### Publishing an image

Pushing a `v*` tag runs the test suite and then builds and pushes the
production image to this repository's GHCR package, as
`ghcr.io/<owner>/<repo>`. A `v1.2.3` tag publishes `1.2.3`, `1.2`, the full
commit sha, and moves `latest` — which is what `compose.prod.yaml` runs when
`DOCKER_IMAGE_TAG` is unset. Pin the sha for a deployment that must not change
under itself.

```bash
git tag v1.2.3 && git push origin v1.2.3
```

The package inherits the repository's visibility, so a private repository
publishes a private package and pulling it on a server needs credentials.

Building the image by hand, without publishing:

```bash
docker compose -f compose.prod.yaml build
```

## License

[MIT](LICENSE)
