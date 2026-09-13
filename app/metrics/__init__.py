"""Metrics collection for the PESUAuth API.

This package deliberately exports no collector instance. The singleton is created in `app/app.py`
alongside the PESUAcademy client, so that importing the package has no side effects and tests can
swap the collector out by patching one module attribute.
"""

from .collector import (
    AUTHENTICATION_REQUESTS as AUTHENTICATION_REQUESTS,
)
from .collector import (
    ERRORS_BY_TYPE as ERRORS_BY_TYPE,
)
from .collector import (
    FAMILIES as FAMILIES,
)
from .collector import (
    PROCESS_START_TIME as PROCESS_START_TIME,
)
from .collector import (
    REQUEST_LATENCY as REQUEST_LATENCY,
)
from .collector import (
    REQUESTS_FAILED as REQUESTS_FAILED,
)
from .collector import (
    REQUESTS_SUCCESS as REQUESTS_SUCCESS,
)
from .collector import (
    REQUESTS_TOTAL as REQUESTS_TOTAL,
)
from .collector import (
    RESPONSES_BY_STATUS as RESPONSES_BY_STATUS,
)
from .collector import (
    ROUTE_LATENCY as ROUTE_LATENCY,
)
from .collector import (
    ROUTE_REQUESTS as ROUTE_REQUESTS,
)
from .collector import (
    MetricFamily as MetricFamily,
)
from .collector import (
    MetricsCollector as MetricsCollector,
)
from .collector import (
    MetricsSnapshot as MetricsSnapshot,
)
