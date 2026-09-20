"""Liveness/readiness endpoint for container orchestration."""

from django.db import DatabaseError, connections, transaction
from django.http import HttpRequest, JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET


# Opted out of ATOMIC_REQUESTS: opening a transaction against an unreachable
# database would raise before the view runs, turning a clean 503 into a 500.
@transaction.non_atomic_requests
@never_cache
@require_GET
def healthz(_request: HttpRequest) -> JsonResponse:
    """Report whether the process can still serve traffic.

    The database round-trip is what makes this a readiness check: a process
    that cannot reach SQLite is up but useless, and should be restarted.
    """
    try:
        with connections["default"].cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except DatabaseError:
        return JsonResponse({"status": "error", "database": "down"}, status=503)

    return JsonResponse({"status": "ok", "database": "up"})
