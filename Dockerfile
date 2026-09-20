# syntax=docker/dockerfile:1
#
# Two kinds of image live here.
#
# The development ones (`tailwind`, `dev`) hold a toolchain and no source: the
# working tree arrives as a bind mount, dependencies are installed on start, and
# everything runs as the developer's own uid so files written into the mount
# stay editable on the host.
#
# The production one (`prod`) is the opposite of both: source, dependencies and
# the compiled stylesheet baked in, no toolchain, no lockfiles, no dev
# dependencies, no npm, no uv, and an unprivileged user that owns none of what
# it runs. It is built from `assets` and `builder`, which exist only to be
# copied out of and never ship.
#
#   docker compose build                          the dev stack
#   docker compose -f compose.prod.yaml build     the prod image

ARG PYTHON_VERSION=3.14
ARG NODE_VERSION=25
ARG UV_VERSION=0.12

FROM ghcr.io/astral-sh/uv:${UV_VERSION} AS uv


# ============================================================================
# tailwind: the watcher
# ============================================================================
# Holds npm and nothing else. package.json arrives over the bind mount, and the
# container installs from it on start.

FROM node:${NODE_VERSION}-slim AS tailwind

ARG DOCKER_UID=1000
ARG DOCKER_GID=1000

WORKDIR /app

# The compose file masks /app/node_modules with an anonymous volume so the
# container's modules never touch the host's. Docker seeds that volume from the
# image, ownership included, so the directory has to exist here owned by the
# developer's uid. Without this the volume arrives root-owned and npm cannot
# write to it.
RUN mkdir -p /app/node_modules && chown -R ${DOCKER_UID}:${DOCKER_GID} /app

CMD ["npm", "run", "watch"]


# ============================================================================
# dev: the autoreloading server
# ============================================================================

FROM python:${PYTHON_VERSION}-slim AS dev

COPY --from=uv /uv /uvx /usr/local/bin/

# UV_PROJECT_ENVIRONMENT puts the virtualenv outside /app, because /app is the
# bind-mounted working tree and the host's .venv is built for the host's
# platform. UV_LINK_MODE=copy because the cache volume and the venv are
# different filesystems, where uv's default hardlinking cannot work.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_CACHE_DIR=/cache/uv \
    UV_LINK_MODE=copy \
    PATH="/opt/venv/bin:$PATH"

ARG DOCKER_UID=1000
ARG DOCKER_GID=1000

# Both are written by `uv sync` at start, running as the developer's uid.
RUN mkdir -p /opt/venv /cache/uv \
    && chown -R ${DOCKER_UID}:${DOCKER_GID} /opt/venv /cache/uv

WORKDIR /app

COPY docker/dev-entrypoint.sh /usr/local/bin/dev-entrypoint

ENTRYPOINT ["dev-entrypoint"]
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]


# ============================================================================
# assets: the compiled stylesheet
# ============================================================================
# Build-time only. Node is a build dependency here, not a runtime one: the
# production image gets the file this stage produces and never sees npm.

FROM node:${NODE_VERSION}-slim AS assets

WORKDIR /app

# Ahead of the source so a template edit does not reinstall the toolchain. `ci`
# rather than `install` because this tree is discarded either way and only the
# lockfile's exact versions should ever reach a released image.
COPY package.json package-lock.json ./
RUN --mount=type=cache,target=/root/.npm npm ci --no-audit --no-fund

# Tailwind emits only the utilities it finds referenced, so every directory that
# can name a class has to be present. Missing one costs no error and no warning:
# the build succeeds and those elements render unstyled. Keep this list in step
# with the `@source` lines in assets/css/app.css.
COPY assets/ assets/
COPY templates/ templates/
COPY apps/ apps/
COPY static/fonts/ static/fonts/

RUN npm run build


# ============================================================================
# builder: the virtualenv
# ============================================================================
# Also build-time only. uv, the lockfile and the compilers live here and are
# left behind; the production image copies out /opt/venv and nothing else.

FROM python:${PYTHON_VERSION}-slim AS builder

COPY --from=uv /uv /uvx /usr/local/bin/

# COMPILE_BYTECODE writes the .pyc files now, at build time, instead of leaving
# every worker to write them on first import — which a read-only root filesystem
# would not let it do anyway, making every process pay the compile on each fork.
ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_CACHE_DIR=/cache/uv \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

# Only the two files that decide the dependency set, so the layer below is
# rebuilt when they change and reused when any other file does.
COPY pyproject.toml uv.lock ./

# --frozen resolves nothing: it installs the lockfile exactly or fails, so an
# image can never be built from a lockfile that has drifted from pyproject.toml.
# --no-dev leaves the linters and test runner out of the runtime environment.
RUN --mount=type=cache,target=/cache/uv \
    uv sync --frozen --no-dev --no-install-project


# ============================================================================
# prod: what actually serves
# ============================================================================

FROM python:${PYTHON_VERSION}-slim AS prod

# DONTWRITEBYTECODE because the filesystem is read-only at run time and every
# .pyc that matters was already written into /opt/venv and /app by the two
# stages above. Without it, each worker retries the write on every import and
# takes the compile cost again.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONFAULTHANDLER=1 \
    PATH="/opt/venv/bin:$PATH"

# High and fixed, rather than the developer's uid: this user exists to own
# nothing and to collide with no host account if a volume is ever mounted.
ARG APP_UID=10001
ARG APP_GID=10001

RUN groupadd --system --gid ${APP_GID} app \
    && useradd --system --uid ${APP_UID} --gid app --no-create-home --home-dir /app app

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv

# Everything below stays owned by root and is only readable by the app user, so
# a compromised worker cannot rewrite the code it is running or the stylesheet
# it serves. Nothing in this image is meant to be written at run time.
COPY manage.py ./
COPY config/ config/
COPY apps/ apps/
COPY templates/ templates/
COPY static/ static/
COPY --from=assets /app/static/ static/
COPY docker/gunicorn.conf.py docker/healthcheck.py docker/

# This image holds no state and mounts no volume. The database is a Postgres
# server elsewhere and the uploads are in object storage, so there is nothing
# for the container to write and nothing to persist across a deploy.
#
# collectstatic imports the settings module, which outside DEBUG refuses to
# fall back on defaults for any of these. None of these values reach the image:
# they exist for the length of this one command, and are replaced at run time
# by the real environment. The database URL is parsed and never connected to,
# and the bucket is never reached.
RUN DJANGO_SECRET_KEY=collectstatic \
    DJANGO_DATABASE_URL=postgres://collectstatic:collectstatic@localhost:5432/collectstatic \
    DJANGO_S3_BUCKET=collectstatic \
    DJANGO_S3_ACCESS_KEY_ID=collectstatic \
    DJANGO_S3_SECRET_ACCESS_KEY=collectstatic \
    DJANGO_S3_ENDPOINT_URL=https://collectstatic.invalid \
    python manage.py collectstatic --noinput --clear \
    && python -m compileall -q config manage.py

USER app

EXPOSE 8000

# Config in a file rather than a wall of flags, because every value in it is
# read from the environment and belongs somewhere it can be commented.
CMD ["gunicorn", "--config", "docker/gunicorn.conf.py", "config.wsgi:application"]
