#!/bin/sh
# Development entrypoint: reconcile the virtualenv with the lockfile and bring
# the schema up to date, then run whatever the compose file asked for.
#
# Both run on every start rather than at build time because the lockfile and the
# migrations live in the bind-mounted working tree: pulling a branch that adds a
# dependency or a migration should not require rebuilding the image.
set -eu

echo "dev-entrypoint: syncing dependencies"
uv sync --frozen

echo "dev-entrypoint: applying migrations"
python manage.py migrate --noinput

exec "$@"
