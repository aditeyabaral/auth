"""Custom docs for the /metrics and /metrics.json PESUAuth endpoints."""

from app.docs.base import ApiDocs
from app.models import MetricsModel, ResponseModel

_INTERNAL_SERVER_ERROR = {
    "description": "Internal Server Error.",
    "model": ResponseModel,
    "content": {
        "application/json": {
            "example": {
                "status": False,
                "message": "Internal Server Error. Please try again later.",
                "timestamp": "2024-07-28T22:30:10.103368+05:30",
            }
        }
    },
}

_PROMETHEUS_EXAMPLE = """# HELP pesu_auth_requests_total HTTP requests received.
# TYPE pesu_auth_requests_total counter
pesu_auth_requests_total 1284
# HELP pesu_auth_responses_total HTTP responses, by status code.
# TYPE pesu_auth_responses_total counter
pesu_auth_responses_total{status="200"} 1094
pesu_auth_responses_total{status="401"} 160
# HELP pesu_auth_errors_total Errors rendered by an exception handler, by exception class.
# TYPE pesu_auth_errors_total counter
pesu_auth_errors_total{type="AuthenticationError"} 160
# HELP pesu_auth_request_latency_seconds Seconds from receiving a request to starting its response.
# TYPE pesu_auth_request_latency_seconds summary
pesu_auth_request_latency_seconds_sum 742.1841932
pesu_auth_request_latency_seconds_count 1284
"""

metrics_docs = ApiDocs(
    request_examples={},
    response_examples={
        200: {
            "description": "Metrics in the Prometheus text exposition format.",
            "content": {"text/plain": {"example": _PROMETHEUS_EXAMPLE}},
        },
        500: _INTERNAL_SERVER_ERROR,
    },
)

metrics_json_docs = ApiDocs(
    request_examples={},
    response_examples={
        200: {
            "description": "Metrics as JSON.",
            "model": MetricsModel,
            "content": {
                "application/json": {
                    "example": {
                        "startTimeSeconds": 1757660400.12,
                        "uptimeSeconds": 3612.44,
                        "requests": {"total": 1284, "success": 1102, "failed": 182},
                        "latency": {"sumSeconds": 742.1841932, "count": 1284, "averageSeconds": 0.5779},
                        "authentication": {"total": 774, "withProfile": 134, "withoutProfile": 640},
                        "responsesByStatus": {"200": 1094, "401": 160, "502": 6},
                        "requestsByRoute": {
                            "POST /authenticate": {
                                "requests": 774,
                                "latency": {"sumSeconds": 741.2118, "count": 774, "averageSeconds": 0.9576},
                            }
                        },
                        "errorsByType": {"AuthenticationError": 160, "RequestValidationError": 12},
                    }
                }
            },
        },
        500: _INTERNAL_SERVER_ERROR,
    },
)
