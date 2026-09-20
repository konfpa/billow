"""Gunicorn configuration for the production image.

Every value is read from the environment so that tuning a deployment never means
rebuilding the image. The defaults are deliberately modest: they are sized for
the smallest machine this is likely to run on, and raising them is a decision
made per deployment.

Reference: https://docs.gunicorn.org/en/latest/settings.html
"""

import os


def _int(name: str, default: int) -> int:
    return int(os.environ.get(name, default))


# The proxy is the only thing that reaches this, and it does so over the
# loopback address the container publishes to. Binding the container's own
# 0.0.0.0 is what makes that published port reachable at all.
bind = "0.0.0.0:8000"

# Threads, not processes, for the concurrency: a request here spends nearly all
# of its time waiting on Postgres or on object storage, and a thread waiting
# costs a stack where a process waiting costs a copy of the interpreter.
worker_class = "gthread"

# No formula involving os.cpu_count() here on purpose. Inside a container that
# call reports the host's cores and not the share this container was granted,
# so `2 * cpu_count() + 1` on a big host silently asks a 512M container for
# thirty-three workers. A number that has to be chosen is better than one that
# is confidently wrong.
workers = _int("GUNICORN_WORKERS", 2)
threads = _int("GUNICORN_THREADS", 4)

# Every thread holds its own database connection for CONN_MAX_AGE seconds, so
# this product, times the number of replicas, is what Postgres sees. The
# defaults above are 8 connections per replica, which against the stock
# max_connections of 100 leaves room for twelve replicas and nothing else.

# The recycling below is what bounds memory. A worker retires after this many
# requests and is replaced by a fresh fork, so anything the process has
# accumulated and not released — a leak in a C extension, a cache that only ever
# grows, a fragmented heap — is returned to the operating system on a schedule
# rather than never. The jitter spreads those retirements out; without it every
# worker reaches the limit within a few requests of the others and they all
# restart at once, which is a small outage under load.
max_requests = _int("GUNICORN_MAX_REQUESTS", 1000)
max_requests_jitter = _int("GUNICORN_MAX_REQUESTS_JITTER", 100)

# Load the application once in the master and fork workers from it. The pages
# holding Django, the settings and every import are then shared copy-on-write
# instead of being paid for per worker, which is most of what a worker costs.
# Django opens its database connections lazily, per thread, so no socket is
# inherited across the fork — which would be the one thing preloading breaks.
preload_app = os.environ.get("GUNICORN_PRELOAD", "true").lower() == "true"

# A request still running after this is a worker that is not coming back, and it
# is killed. It has to stay above the slowest thing a request legitimately does.
timeout = _int("GUNICORN_TIMEOUT", 60)

# On SIGTERM, workers stop accepting and finish what they are holding. Whatever
# is still running when this expires is killed. `stop_grace_period` in the
# compose file has to exceed it, or Docker kills the container mid-drain and the
# graceful shutdown never happens.
graceful_timeout = _int("GUNICORN_GRACEFUL_TIMEOUT", 30)

# Slightly above the proxy's own keepalive so that the connection is reused
# rather than reopened per request, and closed from this end rather than found
# closed from the other.
keepalive = _int("GUNICORN_KEEPALIVE", 5)

# Bounds the header a request can send. The defaults are already conservative;
# they are stated so that raising one is a visible edit rather than a discovery.
limit_request_line = 8190
limit_request_fields = 100
limit_request_field_size = 8190

# Gunicorn 26 opens a unix socket for runtime control, and defaults it to
# `.gunicorn/` under the working directory — which here is /app, which is
# read-only. Left on, it fails and logs an error every time a worker is spawned,
# which under the recycling above means continuously, and that noise is what a
# real error would be lost in. Nothing here drives gunicorn over a socket: a
# deployment restarts the container instead.
control_socket_disable = True

# Gunicorn heartbeats each worker by touching a file. On the default temporary
# directory that write can land on disk, and a worker whose heartbeat is late
# because the disk is busy is killed as though it had hung. /dev/shm is memory,
# and Docker mounts it read-write even under `read_only: true`.
worker_tmp_dir = "/dev/shm"  # noqa: S108

# Both to the container's streams, where the log driver collects and rotates
# them. Nothing in this image writes a log file.
accesslog = "-"
errorlog = "-"
loglevel = os.environ.get("GUNICORN_LOG_LEVEL", "info")

# The default omits the forwarded address, which is the only one worth having
# when every request arrives from the proxy.
access_log_format = '%({x-forwarded-for}i)s %(t)s "%(r)s" %(s)s %(b)s %(M)sms "%(a)s"'

# Which peers may set X-Forwarded-*. The container is reached through Docker's
# bridge, so the proxy arrives as the gateway address rather than as 127.0.0.1
# and the default would reject it. This is safe only because the published port
# is bound to the loopback interface: nothing but that proxy can connect.
forwarded_allow_ips = os.environ.get("GUNICORN_FORWARDED_ALLOW_IPS", "*")
