# billow

Billing software built with Django.

> **Work in progress.** Proper documentation will be written once the core is in place.

## Setup

```bash
uv sync
cp .env.example .env   # then fill in DJANGO_SECRET_KEY
uv run manage.py migrate
uv run manage.py createsuperuser
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
uv run manage.py check --deploy   # must be clean before deploying
uv run manage.py migrate
uv run manage.py collectstatic --noinput
uv run gunicorn config.wsgi:application --bind 0.0.0.0:8000
```

Static files are served by WhiteNoise from the app process, so no separate
static file server is needed. TLS is expected to be terminated by a reverse
proxy that sets `X-Forwarded-Proto`.

SQLite lives at `DJANGO_DB_PATH` and uploads at `DJANGO_MEDIA_ROOT`; both must
point at persistent storage (a mounted volume in Docker).

`GET /healthz` returns `200` with `{"status": "ok"}` when the process can reach
the database and `503` otherwise — use it as the container healthcheck.

## License

[MIT](LICENSE)
