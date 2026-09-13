import pytest

from app.metrics.collector import (
    AUTHENTICATION_REQUESTS,
    FAMILIES,
    PROCESS_START_TIME,
    REQUEST_LATENCY,
    REQUESTS_TOTAL,
    RESPONSES_BY_STATUS,
    ROUTE_LATENCY,
    ROUTE_REQUESTS,
    MetricFamily,
    MetricsCollector,
)


@pytest.fixture
def collector():
    """A collector on a frozen clock, so uptime and start time are deterministic."""
    return MetricsCollector(clock=lambda: 1000.0)


def test_unlabelled_families_are_seeded_at_zero(collector):
    """A fresh process must expose its unlabelled series, or rate() reads their first use as a spike."""
    snapshot = collector.snapshot()
    for family in FAMILIES:
        if family.labels or family is PROCESS_START_TIME:
            continue
        if family.metric_type == "summary":
            assert snapshot.value(f"{family.name}_sum") == 0.0
            assert snapshot.value(f"{family.name}_count") == 0.0
        else:
            assert snapshot.value(family.name) == 0.0


def test_process_start_time_is_recorded(collector):
    assert collector.snapshot().value(PROCESS_START_TIME.name) == 1000.0


def test_labelled_families_start_empty(collector):
    """Labelled series cannot be seeded -- their label values are not known until traffic arrives."""
    assert list(collector.snapshot().samples(RESPONSES_BY_STATUS.name)) == []


def test_increment_accumulates(collector):
    collector.increment(REQUESTS_TOTAL)
    collector.increment(REQUESTS_TOTAL)
    assert collector.snapshot().value(REQUESTS_TOTAL.name) == 2.0


def test_increment_accepts_a_custom_value(collector):
    collector.increment(REQUESTS_TOTAL, 5.0)
    assert collector.snapshot().value(REQUESTS_TOTAL.name) == 5.0


def test_labelled_series_are_kept_apart(collector):
    collector.increment(RESPONSES_BY_STATUS, status="200")
    collector.increment(RESPONSES_BY_STATUS, status="401")
    collector.increment(RESPONSES_BY_STATUS, status="401")
    snapshot = collector.snapshot()
    assert snapshot.value(RESPONSES_BY_STATUS.name, status="200") == 1.0
    assert snapshot.value(RESPONSES_BY_STATUS.name, status="401") == 2.0


def test_label_order_does_not_create_a_second_series(collector):
    """Labels are normalised to a sorted tuple, so kwarg order cannot split one series into two."""
    collector.increment(ROUTE_REQUESTS, method="GET", route="/health")
    collector.increment(ROUTE_REQUESTS, route="/health", method="GET")
    assert collector.snapshot().value(ROUTE_REQUESTS.name, method="GET", route="/health") == 2.0


def test_unknown_label_raises(collector):
    with pytest.raises(ValueError, match="expects labels"):
        collector.increment(RESPONSES_BY_STATUS, bogus="x")


def test_missing_label_raises(collector):
    with pytest.raises(ValueError, match="expects labels"):
        collector.increment(ROUTE_REQUESTS, method="GET")


def test_labels_on_an_unlabelled_family_raise(collector):
    with pytest.raises(ValueError, match="expects labels"):
        collector.increment(REQUESTS_TOTAL, status="200")


def test_observe_records_sum_and_count(collector):
    collector.observe(REQUEST_LATENCY, 0.25)
    collector.observe(REQUEST_LATENCY, 0.75)
    snapshot = collector.snapshot()
    assert snapshot.value(f"{REQUEST_LATENCY.name}_sum") == 1.0
    assert snapshot.value(f"{REQUEST_LATENCY.name}_count") == 2.0


def test_observe_keeps_labelled_summaries_apart(collector):
    collector.observe(ROUTE_LATENCY, 1.5, method="GET", route="/health")
    collector.observe(ROUTE_LATENCY, 0.5, method="POST", route="/authenticate")
    snapshot = collector.snapshot()
    assert snapshot.value(f"{ROUTE_LATENCY.name}_sum", method="GET", route="/health") == 1.5
    assert snapshot.value(f"{ROUTE_LATENCY.name}_count", method="POST", route="/authenticate") == 1.0


def test_snapshot_is_isolated_from_later_mutation(collector):
    """A snapshot copies each series, so a renderer iterating it cannot observe a concurrent write."""
    before = collector.snapshot()
    collector.increment(REQUESTS_TOTAL)
    assert before.value(REQUESTS_TOTAL.name) == 0.0
    assert collector.snapshot().value(REQUESTS_TOTAL.name) == 1.0


def test_snapshot_value_defaults_to_zero_for_an_unrecorded_series(collector):
    assert collector.snapshot().value(RESPONSES_BY_STATUS.name, status="418") == 0.0
    assert collector.snapshot().value("pesu_auth_not_a_real_metric") == 0.0


def test_samples_are_label_sorted(collector):
    for status in ("500", "200", "401"):
        collector.increment(RESPONSES_BY_STATUS, status=status)
    statuses = [labels["status"] for labels, _ in collector.snapshot().samples(RESPONSES_BY_STATUS.name)]
    assert statuses == ["200", "401", "500"]


def test_samples_of_an_unrecorded_series_is_empty(collector):
    assert list(collector.snapshot().samples(AUTHENTICATION_REQUESTS.name)) == []


def test_uptime_is_measured_from_the_start_time():
    clock = iter([1000.0, 1042.5])
    collector = MetricsCollector(clock=lambda: next(clock))
    assert collector.snapshot().uptime_seconds == 42.5


def test_uptime_is_never_negative():
    """A clock that steps backwards must not produce a negative uptime."""
    clock = iter([1000.0, 900.0])
    collector = MetricsCollector(clock=lambda: next(clock))
    assert collector.snapshot().uptime_seconds == 0.0


def test_default_clock_is_wall_time():
    """The injected clock is a test seam; the default must still be real time."""
    assert MetricsCollector().snapshot().start_time > 0


def test_metric_family_is_immutable():
    family = MetricFamily("x", "y", "counter")
    with pytest.raises(AttributeError):
        family.name = "z"


def test_a_label_cannot_shadow_the_amount(collector):
    """`value` is positional-only, so a family may declare a label of that name safely."""
    from app.metrics.collector import MetricFamily

    family = MetricFamily("pesu_auth_odd_total", "doc", "counter", ("value",))
    collector.increment(family, 3, value="x")
    assert collector.snapshot().value(family.name, value="x") == 3.0


def test_a_label_cannot_shadow_the_observation(collector):
    from app.metrics.collector import MetricFamily

    family = MetricFamily("pesu_auth_odd_seconds", "doc", "summary", ("seconds",))
    collector.observe(family, 1.5, seconds="x")
    assert collector.snapshot().value(f"{family.name}_sum", seconds="x") == 1.5


def test_every_defined_family_is_registered():
    """`FAMILIES` drives both seeding and rendering.

    A family defined but left out of it would be collected into and then never exposed -- silently,
    since nothing else would notice. This keeps the list from drifting from the module.
    """
    from app.metrics import collector as module

    defined = {
        value.name
        for name, value in vars(module).items()
        if isinstance(value, MetricFamily) and not name.startswith("_")
    }
    assert defined == {family.name for family in FAMILIES}


def test_family_names_are_unique():
    names = [family.name for family in FAMILIES]
    assert len(names) == len(set(names))


def test_no_family_name_collides_with_a_summary_series():
    """A counter named `x_sum` would be indistinguishable from the sum series of a summary `x`."""
    summary_series = {
        f"{family.name}_{suffix}"
        for family in FAMILIES
        if family.metric_type == "summary"
        for suffix in ("sum", "count")
    }
    assert summary_series.isdisjoint({family.name for family in FAMILIES})


def test_every_family_name_is_a_valid_prometheus_identifier():
    import re

    for family in FAMILIES:
        assert re.fullmatch(r"[a-zA-Z_:][a-zA-Z0-9_:]*", family.name), family.name
        for label in family.labels:
            assert re.fullmatch(r"[a-zA-Z_][a-zA-Z0-9_]*", label), (family.name, label)


def test_every_family_documents_itself_within_one_exposition_line():
    """HELP text is rendered into the docs example, which is linted at 120 characters."""
    for family in FAMILIES:
        assert len(f"# HELP {family.name} {family.documentation}") <= 118, family.name
        assert family.documentation.endswith("."), family.name
