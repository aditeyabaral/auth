"""Models representing the metrics collected by the API."""

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from app.metrics.collector import (
    AUTHENTICATION_REQUESTS,
    ERRORS_BY_TYPE,
    PROCESS_START_TIME,
    REQUEST_LATENCY,
    REQUESTS_FAILED,
    REQUESTS_SUCCESS,
    REQUESTS_TOTAL,
    RESPONSES_BY_STATUS,
    ROUTE_LATENCY,
    ROUTE_REQUESTS,
    MetricsSnapshot,
)


class LatencyModel(BaseModel):
    """Model representing aggregate request latency."""

    model_config = ConfigDict(strict=True, alias_generator=to_camel, populate_by_name=True)

    sum_seconds: float = Field(
        ...,
        title="Total Latency",
        description="Cumulative seconds spent answering requests.",
        json_schema_extra={"example": 742.1841932},
    )

    count: int = Field(
        ...,
        title="Observation Count",
        description="Number of requests whose latency was recorded.",
        json_schema_extra={"example": 1284},
    )

    average_seconds: float | None = Field(
        None,
        title="Mean Latency",
        description="Mean seconds per request, or null when nothing has been recorded yet.",
        json_schema_extra={"example": 0.5779},
    )

    @classmethod
    def from_snapshot(cls, snapshot: MetricsSnapshot, name: str, **labels: str) -> LatencyModel:
        """Build a latency view from a snapshot's sum and count series.

        Args:
            snapshot (MetricsSnapshot): The snapshot to read.
            name (str): The summary family name, without a suffix.
            **labels (str): The label set identifying the series.

        Returns:
            LatencyModel: The aggregated latency for that label set.
        """
        total = snapshot.value(f"{name}_sum", **labels)
        count = snapshot.value(f"{name}_count", **labels)
        return cls(
            sum_seconds=float(total),
            count=int(count),
            average_seconds=float(total / count) if count else None,
        )


class RequestCountsModel(BaseModel):
    """Model representing request outcome counts."""

    model_config = ConfigDict(strict=True, alias_generator=to_camel, populate_by_name=True)

    total: int = Field(
        ...,
        title="Total Requests",
        description="Requests received.",
        json_schema_extra={"example": 1284},
    )

    success: int = Field(
        ...,
        title="Successful Requests",
        description="Requests answered with a status below 400.",
        json_schema_extra={"example": 1102},
    )

    failed: int = Field(
        ...,
        title="Failed Requests",
        description="Requests answered with a status of 400 or above.",
        json_schema_extra={"example": 182},
    )


class AuthenticationCountsModel(BaseModel):
    """Model representing authentication request counts, split by whether profile data was requested."""

    model_config = ConfigDict(strict=True, alias_generator=to_camel, populate_by_name=True)

    total: int = Field(
        ...,
        title="Authentication Requests",
        description="Authentication requests received.",
        json_schema_extra={"example": 774},
    )

    with_profile: int = Field(
        ...,
        title="With Profile Data",
        description="Authentication requests that asked for profile data.",
        json_schema_extra={"example": 134},
    )

    without_profile: int = Field(
        ...,
        title="Without Profile Data",
        description="Authentication requests that did not ask for profile data.",
        json_schema_extra={"example": 640},
    )


class RouteMetricsModel(BaseModel):
    """Model representing the traffic served by a single route."""

    model_config = ConfigDict(strict=True, alias_generator=to_camel, populate_by_name=True)

    requests: int = Field(
        ...,
        title="Route Requests",
        description="Requests matched to this route.",
        json_schema_extra={"example": 774},
    )

    latency: LatencyModel = Field(
        ...,
        title="Route Latency",
        description="Aggregate latency for this route.",
    )


class MetricsModel(BaseModel):
    """Model representing a point-in-time view of the API's collected metrics."""

    model_config = ConfigDict(strict=True, alias_generator=to_camel, populate_by_name=True)

    start_time_seconds: float = Field(
        ...,
        title="Process Start Time",
        description="Start time of this process since the Unix epoch, in seconds. Counters reset on restart.",
        json_schema_extra={"example": 1757660400.12},
    )

    uptime_seconds: float = Field(
        ...,
        title="Uptime",
        description="Seconds since this process started collecting.",
        json_schema_extra={"example": 3612.44},
    )

    requests: RequestCountsModel = Field(
        ...,
        title="Request Counts",
        description="Request outcome counts.",
    )

    latency: LatencyModel = Field(
        ...,
        title="Request Latency",
        description="Aggregate latency across all routes.",
    )

    authentication: AuthenticationCountsModel = Field(
        ...,
        title="Authentication Counts",
        description="Authentication requests received, split by whether profile data was requested.",
    )

    responses_by_status: dict[str, int] = Field(
        ...,
        title="Responses by Status",
        description="Response counts keyed by HTTP status code.",
        json_schema_extra={"example": {"200": 1094, "401": 160, "502": 6}},
    )

    requests_by_route: dict[str, RouteMetricsModel] = Field(
        ...,
        title="Requests by Route",
        description='Per-route traffic, keyed by "METHOD route-template". Unmatched paths collapse into "<unmatched>".',
        json_schema_extra={
            "example": {
                "POST /authenticate": {
                    "requests": 774,
                    "latency": {"sumSeconds": 741.2118, "count": 774, "averageSeconds": 0.9576},
                }
            }
        },
    )

    errors_by_type: dict[str, int] = Field(
        ...,
        title="Errors by Type",
        description="Counts of errors rendered by an exception handler, keyed by exception class name.",
        json_schema_extra={"example": {"AuthenticationError": 160, "RequestValidationError": 12}},
    )

    @classmethod
    def from_snapshot(cls, snapshot: MetricsSnapshot) -> MetricsModel:
        """Build the JSON metrics view from a collector snapshot.

        Every value is cast explicitly: the collector stores floats, and `strict=True` rejects a
        float for an int field, so an un-cast value would be a 500 rather than a payload.

        Args:
            snapshot (MetricsSnapshot): The snapshot to render.

        Returns:
            MetricsModel: The validated metrics payload.
        """
        with_profile = int(snapshot.value(AUTHENTICATION_REQUESTS.name, profile="true"))
        without_profile = int(snapshot.value(AUTHENTICATION_REQUESTS.name, profile="false"))
        return cls(
            start_time_seconds=float(snapshot.value(PROCESS_START_TIME.name)),
            uptime_seconds=float(snapshot.uptime_seconds),
            requests=RequestCountsModel(
                total=int(snapshot.value(REQUESTS_TOTAL.name)),
                success=int(snapshot.value(REQUESTS_SUCCESS.name)),
                failed=int(snapshot.value(REQUESTS_FAILED.name)),
            ),
            latency=LatencyModel.from_snapshot(snapshot, REQUEST_LATENCY.name),
            authentication=AuthenticationCountsModel(
                total=with_profile + without_profile,
                with_profile=with_profile,
                without_profile=without_profile,
            ),
            responses_by_status={
                labels["status"]: int(value) for labels, value in snapshot.samples(RESPONSES_BY_STATUS.name)
            },
            requests_by_route={
                f"{labels['method']} {labels['route']}": RouteMetricsModel(
                    requests=int(value),
                    latency=LatencyModel.from_snapshot(snapshot, ROUTE_LATENCY.name, **labels),
                )
                for labels, value in snapshot.samples(ROUTE_REQUESTS.name)
            },
            errors_by_type={labels["type"]: int(value) for labels, value in snapshot.samples(ERRORS_BY_TYPE.name)},
        )
