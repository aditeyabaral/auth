"""HTTP middleware that records request, response and latency metrics."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from app.metrics.collector import (
    FAILURES_BY_FAULT,
    REQUEST_LATENCY,
    REQUESTS_FAILED,
    REQUESTS_IN_FLIGHT,
    REQUESTS_SUCCESS,
    REQUESTS_TOTAL,
    RESPONSES_BY_STATUS,
    ROUTE_LATENCY,
    ROUTE_REQUESTS,
)

if TYPE_CHECKING:
    from collections.abc import Mapping

    from starlette.middleware.base import RequestResponseEndpoint
    from starlette.requests import Request
    from starlette.responses import Response

    from app.metrics.collector import MetricsCollector

# A response at or above this status is counted as a failure. Not `>= 300`: /readme answers with a
# 308 redirect, which is the endpoint working correctly.
FAILURE_STATUS = 400
# What an exception that reached us is recorded as. ServerErrorMiddleware renders the actual 500
# above us, so we never see that response and have to record the status ourselves.
EXCEPTION_STATUS = 500
# At or above this status the fault is ours (or the upstream's) rather than the caller's
SERVER_FAULT_STATUS = 500

KNOWN_METHODS = frozenset({"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"})
UNMATCHED_ROUTE = "<unmatched>"
OTHER_METHOD = "<other>"


def method_label(scope: Mapping[str, Any]) -> str:
    """Return the request method, clamped to a known verb.

    The method is caller-supplied, so an unrecognised verb collapses into one bucket rather than
    minting a new series per value.

    Args:
        scope (Mapping[str, Any]): The ASGI scope of the request.

    Returns:
        str: The method, or a sentinel for anything unrecognised.
    """
    method = scope.get("method", OTHER_METHOD)
    return method if method in KNOWN_METHODS else OTHER_METHOD


def route_label(scope: Mapping[str, Any]) -> str:
    """Return the matched route template, or a single bucket for unmatched paths.

    Never the raw path: a scanner walking /wp-login.php, /.env and friends would otherwise create a
    new series per probe and the key space would grow without bound.

    Args:
        scope (Mapping[str, Any]): The ASGI scope of the request, after routing.

    Returns:
        str: The route template, the path for a non-API route, or a sentinel.
    """
    if (path := getattr(scope.get("route"), "path", None)) and isinstance(path, str):
        return path
    # FastAPI sets scope["route"] only on its own APIRoutes. The Swagger UI and /openapi.json are
    # plain Starlette routes, which set scope["endpoint"] instead; their paths are static, so the
    # raw path is safe there and keeps them out of the unmatched bucket, which should mean probes.
    if scope.get("endpoint") is not None:
        return str(scope.get("path", UNMATCHED_ROUTE))
    return UNMATCHED_ROUTE


def _record_outcome(collector: MetricsCollector, scope: Mapping[str, Any], status: int, latency: float) -> None:
    """Record the status, route and latency of a completed request.

    Args:
        collector (MetricsCollector): The collector to record into.
        scope (Mapping[str, Any]): The ASGI scope, read after routing has run.
        status (int): The status code the caller will see.
        latency (float): Seconds until the response started.
    """
    # scope["route"] is populated by the router, which runs inside call_next -- so this must be
    # called after that await, never before it.
    method = method_label(scope)
    route = route_label(scope)
    if status < FAILURE_STATUS:
        collector.increment(REQUESTS_SUCCESS)
    else:
        collector.increment(REQUESTS_FAILED)
    collector.increment(RESPONSES_BY_STATUS, status=str(status))
    if status >= FAILURE_STATUS:
        # Who should act on this: a 4xx means the caller sent something wrong, a 5xx means we or
        # PESU Academy did. Derivable from the status codes, but stated outright so an alert can
        # fire on "our fault" without enumerating every status.
        fault = "server" if status >= SERVER_FAULT_STATUS else "client"
        collector.increment(FAILURES_BY_FAULT, fault=fault)
    collector.increment(ROUTE_REQUESTS, method=method, route=route)
    collector.observe(REQUEST_LATENCY, latency)
    collector.observe(ROUTE_LATENCY, latency, method=method, route=route)


async def record_request_metrics(
    collector: MetricsCollector,
    request: Request,
    call_next: RequestResponseEndpoint,
) -> Response:
    """Record request, response and latency metrics around a request.

    Args:
        collector (MetricsCollector): The collector to record into.
        request (Request): The incoming request.
        call_next (RequestResponseEndpoint): The rest of the application.

    Returns:
        Response: The response produced downstream.

    Raises:
        Exception: Re-raised unchanged, so error handling above is unaffected.
    """
    collector.increment(REQUESTS_TOTAL)
    collector.increment(REQUESTS_IN_FLIGHT)
    # perf_counter, not time(): a wall clock is not monotonic, and one NTP step backwards would
    # poison a cumulative latency sum permanently.
    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        # Only genuinely unhandled exceptions arrive here. A handled PESUAcademyError or
        # RequestValidationError has already become a response in ExceptionMiddleware, which
        # Starlette installs *below* user middleware, so call_next returns an ordinary 4xx and this
        # branch never sees it. ServerErrorMiddleware, which renders the 500 for what does reach
        # here, sits *above* us -- so that response is never observed either, and the status has to
        # be recorded now or requests_total stops matching the sum of responses_total.
        #
        # The exception *type* is recorded by the exception handlers, not here. The two layers write
        # to different families on purpose: one failed request produces exactly one status sample
        # and exactly one error sample, never two of either.
        _record_outcome(collector, request.scope, EXCEPTION_STATUS, time.perf_counter() - started)
        raise
    finally:
        # In a finally, not in each branch: a client disconnect surfaces as CancelledError, which
        # is a BaseException and so slips past `except Exception`. Decrementing only in the two
        # branches above would leave the gauge permanently high after every abandoned request.
        collector.increment(REQUESTS_IN_FLIGHT, -1.0)
    _record_outcome(collector, request.scope, response.status_code, time.perf_counter() - started)
    return response
