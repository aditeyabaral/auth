"""Metrics collection for the PESUAuth API.

This package deliberately exports no collector instance. The singleton is created in `app/app.py`
alongside the PESUAcademy client, so that importing the package has no side effects and tests can
swap the collector out by patching one module attribute.
"""

from .collector import AUTHENTICATION_REQUESTS as AUTHENTICATION_REQUESTS
from .collector import AUTHENTICATION_RESULTS as AUTHENTICATION_RESULTS
from .collector import CSRF_CACHE as CSRF_CACHE
from .collector import CSRF_REFRESHES as CSRF_REFRESHES
from .collector import ERRORS_BY_TYPE as ERRORS_BY_TYPE
from .collector import FAILURES_BY_FAULT as FAILURES_BY_FAULT
from .collector import FAMILIES as FAMILIES
from .collector import HTTP_CLIENTS as HTTP_CLIENTS
from .collector import LIFESPAN_EVENTS as LIFESPAN_EVENTS
from .collector import PREFETCH_TASKS as PREFETCH_TASKS
from .collector import PROCESS_START_TIME as PROCESS_START_TIME
from .collector import PROFILE_PARSE_ERRORS as PROFILE_PARSE_ERRORS
from .collector import REQUEST_LATENCY as REQUEST_LATENCY
from .collector import REQUESTS_FAILED as REQUESTS_FAILED
from .collector import REQUESTS_IN_FLIGHT as REQUESTS_IN_FLIGHT
from .collector import REQUESTS_SUCCESS as REQUESTS_SUCCESS
from .collector import REQUESTS_TOTAL as REQUESTS_TOTAL
from .collector import RESPONSES_BY_STATUS as RESPONSES_BY_STATUS
from .collector import ROUTE_LATENCY as ROUTE_LATENCY
from .collector import ROUTE_REQUESTS as ROUTE_REQUESTS
from .collector import UPSTREAM_LATENCY as UPSTREAM_LATENCY
from .collector import UPSTREAM_REQUESTS as UPSTREAM_REQUESTS
from .collector import UPSTREAM_RESPONSES as UPSTREAM_RESPONSES
from .collector import VALIDATION_ERRORS as VALIDATION_ERRORS
from .collector import MetricFamily as MetricFamily
from .collector import MetricsCollector as MetricsCollector
from .collector import MetricsSnapshot as MetricsSnapshot
from .prometheus import PROMETHEUS_CONTENT_TYPE as PROMETHEUS_CONTENT_TYPE
from .prometheus import MetricsFormat as MetricsFormat
from .prometheus import render_prometheus as render_prometheus
