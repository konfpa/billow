"""Container healthcheck: ask the app to answer and to reach its database.

Both compose stacks run this. It hits /healthz rather than the port because
a bound port proves only that something is listening: under the autoreloader
an import error leaves the parent alive and watching files while the child
never serves, and a worker that cannot reach Postgres is up but useless.

Python rather than curl because the slim base has no curl.
"""

import sys
import urllib.request
from http import HTTPStatus

URL = "http://127.0.0.1:8000/healthz"

timeout = float(sys.argv[1]) if len(sys.argv) > 1 else 5.0

try:
    with urllib.request.urlopen(URL, timeout=timeout) as response:
        sys.exit(0 if response.status == HTTPStatus.OK else 1)
except OSError:
    sys.exit(1)
