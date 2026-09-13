import pytest

from app.metrics.collector import (
    ERRORS_BY_TYPE,
    FAMILIES,
    PROCESS_START_TIME,
    REQUEST_LATENCY,
    REQUESTS_TOTAL,
    RESPONSES_BY_STATUS,
    ROUTE_LATENCY,
    ROUTE_REQUESTS,
    MetricsCollector,
)
from app.metrics.prometheus import (
    PROMETHEUS_CONTENT_TYPE,
    _render_labels,
    _render_value,
    render_prometheus,
)


@pytest.fixture
def collector():
    return MetricsCollector(clock=lambda: 1757660400.0)


def test_content_type_is_the_0_0_4_text_format():
    """The version parameter is not optional: without it a scraper guesses the format."""
    assert PROMETHEUS_CONTENT_TYPE == "text/plain; version=0.0.4; charset=utf-8"


def test_every_family_is_declared_exactly_once(collector):
    payload = render_prometheus(collector.snapshot())
    for family in FAMILIES:
        assert payload.count(f"# HELP {family.name} ") == 1
        assert payload.count(f"# TYPE {family.name} {family.metric_type}\n") == 1


def test_payload_is_newline_terminated(collector):
    assert render_prometheus(collector.snapshot()).endswith("\n")


def test_unlabelled_counter_sample_line(collector):
    collector.increment(REQUESTS_TOTAL, 3)
    assert "\npesu_auth_requests_total 3\n" in render_prometheus(collector.snapshot())


def test_labelled_counter_sample_line(collector):
    collector.increment(RESPONSES_BY_STATUS, status="401")
    assert '\npesu_auth_responses_total{status="401"} 1\n' in render_prometheus(collector.snapshot())


def test_labels_are_rendered_in_sorted_order(collector):
    """Sorted labels keep the payload deterministic, so tests and diffs are stable."""
    collector.increment(ROUTE_REQUESTS, route="/health", method="GET")
    payload = render_prometheus(collector.snapshot())
    assert '\npesu_auth_route_requests_total{method="GET",route="/health"} 1\n' in payload


def test_summary_renders_sum_and_count_under_one_type_line(collector):
    collector.observe(REQUEST_LATENCY, 0.5)
    collector.observe(REQUEST_LATENCY, 0.25)
    payload = render_prometheus(collector.snapshot())
    assert "# TYPE pesu_auth_request_latency_seconds summary\n" in payload
    assert "\npesu_auth_request_latency_seconds_sum 0.75\n" in payload
    assert "\npesu_auth_request_latency_seconds_count 2\n" in payload


def test_labelled_summary_renders_both_series_with_labels(collector):
    collector.observe(ROUTE_LATENCY, 1.5, method="POST", route="/authenticate")
    payload = render_prometheus(collector.snapshot())
    assert '\npesu_auth_route_latency_seconds_sum{method="POST",route="/authenticate"} 1.5\n' in payload
    assert '\npesu_auth_route_latency_seconds_count{method="POST",route="/authenticate"} 1\n' in payload


def test_gauge_renders_the_start_time(collector):
    payload = render_prometheus(collector.snapshot())
    assert "# TYPE pesu_auth_process_start_time_seconds gauge\n" in payload
    assert f"\n{PROCESS_START_TIME.name} 1757660400\n" in payload


def test_whole_numbers_render_without_a_decimal_point():
    assert _render_value(3.0) == "3"
    assert _render_value(0.0) == "0"


def test_fractional_values_round_trip():
    assert float(_render_value(0.1 + 0.2)) == 0.1 + 0.2
    assert _render_value(1.5) == "1.5"


def test_label_values_are_escaped(collector):
    """A quote, a backslash or a newline in a label value would otherwise break the sample line."""
    collector.increment(ERRORS_BY_TYPE, type='we"ird\\type\nhere')
    payload = render_prometheus(collector.snapshot())
    assert '\npesu_auth_errors_total{type="we\\"ird\\\\type\\nhere"} 1\n' in payload


def test_documentation_is_escaped(monkeypatch):
    """A newline in HELP text would split it across two lines and corrupt the payload."""
    from app.metrics import collector as collector_module
    from app.metrics import prometheus as prometheus_module

    family = collector_module.MetricFamily("pesu_auth_odd", "line one\nline two\\end", "counter")
    monkeypatch.setattr(prometheus_module, "FAMILIES", (family,))
    payload = render_prometheus(MetricsCollector().snapshot())
    assert payload.splitlines()[0] == "# HELP pesu_auth_odd line one\\nline two\\\\end"


def test_unlabelled_render_produces_no_braces():
    assert _render_labels({}) == ""


def test_a_family_with_no_observations_still_declares_itself(collector):
    """A labelled family with no samples yet must still emit HELP and TYPE, which is valid."""
    payload = render_prometheus(collector.snapshot())
    assert "# TYPE pesu_auth_errors_total counter\n" in payload
    assert "pesu_auth_errors_total{" not in payload


def test_render_is_stable_across_calls(collector):
    collector.increment(RESPONSES_BY_STATUS, status="500")
    collector.increment(RESPONSES_BY_STATUS, status="200")
    snapshot = collector.snapshot()
    assert render_prometheus(snapshot) == render_prometheus(snapshot)
