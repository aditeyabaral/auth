import pytest

from app.metrics.collector import (
    AUTHENTICATION_REQUESTS,
    ERRORS_BY_TYPE,
    REQUEST_LATENCY,
    REQUESTS_FAILED,
    REQUESTS_SUCCESS,
    REQUESTS_TOTAL,
    RESPONSES_BY_STATUS,
    ROUTE_LATENCY,
    ROUTE_REQUESTS,
    MetricsCollector,
)
from app.models import MetricsModel


@pytest.fixture
def collector():
    return MetricsCollector(clock=lambda: 1757660400.0)


def test_from_snapshot_on_a_fresh_collector(collector):
    """The collector stores floats and the model is strict, so an un-cast value would raise here."""
    model = MetricsModel.from_snapshot(collector.snapshot())
    assert model.requests.total == 0
    assert model.latency.count == 0
    assert model.latency.average_seconds is None
    assert model.responses_by_status == {}
    assert model.requests_by_route == {}
    assert model.errors_by_type == {}
    assert model.start_time_seconds == 1757660400.0


def test_counts_are_integers_not_floats(collector):
    """A float where an int is declared is exactly what strict=True rejects."""
    collector.increment(REQUESTS_TOTAL, 3)
    model = MetricsModel.from_snapshot(collector.snapshot())
    assert isinstance(model.requests.total, int)
    assert model.requests.total == 3


def test_request_counts_are_carried_through(collector):
    collector.increment(REQUESTS_TOTAL, 10)
    collector.increment(REQUESTS_SUCCESS, 7)
    collector.increment(REQUESTS_FAILED, 3)
    model = MetricsModel.from_snapshot(collector.snapshot())
    assert (model.requests.total, model.requests.success, model.requests.failed) == (10, 7, 3)


def test_average_latency_is_the_mean(collector):
    collector.observe(REQUEST_LATENCY, 1.0)
    collector.observe(REQUEST_LATENCY, 2.0)
    model = MetricsModel.from_snapshot(collector.snapshot())
    assert model.latency.sum_seconds == 3.0
    assert model.latency.count == 2
    assert model.latency.average_seconds == 1.5


def test_authentication_total_is_the_sum_of_both_splits(collector):
    collector.increment(AUTHENTICATION_REQUESTS, profile="true", value=2)
    collector.increment(AUTHENTICATION_REQUESTS, profile="false", value=5)
    model = MetricsModel.from_snapshot(collector.snapshot())
    assert model.authentication.with_profile == 2
    assert model.authentication.without_profile == 5
    assert model.authentication.total == 7


def test_responses_are_keyed_by_status(collector):
    collector.increment(RESPONSES_BY_STATUS, status="200")
    collector.increment(RESPONSES_BY_STATUS, status="401")
    collector.increment(RESPONSES_BY_STATUS, status="401")
    assert MetricsModel.from_snapshot(collector.snapshot()).responses_by_status == {"200": 1, "401": 2}


def test_errors_are_keyed_by_exception_class(collector):
    collector.increment(ERRORS_BY_TYPE, type="AuthenticationError")
    assert MetricsModel.from_snapshot(collector.snapshot()).errors_by_type == {"AuthenticationError": 1}


def test_routes_are_keyed_by_method_and_template(collector):
    collector.increment(ROUTE_REQUESTS, method="POST", route="/authenticate")
    collector.observe(ROUTE_LATENCY, 0.5, method="POST", route="/authenticate")
    model = MetricsModel.from_snapshot(collector.snapshot())
    assert set(model.requests_by_route) == {"POST /authenticate"}
    route = model.requests_by_route["POST /authenticate"]
    assert route.requests == 1
    assert route.latency.count == 1
    assert route.latency.average_seconds == 0.5


def test_a_route_with_no_latency_recorded_reports_none(collector):
    """Route counts and route latency are separate series, so one can exist without the other."""
    collector.increment(ROUTE_REQUESTS, method="GET", route="/health")
    route = MetricsModel.from_snapshot(collector.snapshot()).requests_by_route["GET /health"]
    assert route.requests == 1
    assert route.latency.count == 0
    assert route.latency.average_seconds is None


def test_model_dump_uses_camel_case_aliases(collector):
    dumped = MetricsModel.from_snapshot(collector.snapshot()).model_dump(by_alias=True)
    assert "responsesByStatus" in dumped
    assert "requestsByRoute" in dumped
    assert "startTimeSeconds" in dumped
    assert dumped["authentication"].keys() == {"total", "withProfile", "withoutProfile"}
    assert dumped["latency"].keys() == {"sumSeconds", "count", "averageSeconds"}


def test_average_seconds_is_present_and_null_rather_than_omitted(collector):
    """Consumers get a stable shape: the key exists on a fresh process rather than appearing later."""
    dumped = MetricsModel.from_snapshot(collector.snapshot()).model_dump(by_alias=True)
    assert dumped["latency"]["averageSeconds"] is None
