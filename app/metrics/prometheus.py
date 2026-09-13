"""Exposition of a metrics snapshot: the formats on offer, and the Prometheus renderer."""

from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING

from app.metrics.collector import FAMILIES

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping

    from app.metrics.collector import MetricsSnapshot

# Prometheus requires this exact media type for the 0.0.4 text format. The version parameter is not
# optional: a scraper handed a bare "text/plain" falls back to guessing the format.
PROMETHEUS_CONTENT_TYPE = "text/plain; version=0.0.4; charset=utf-8"


class MetricsFormat(StrEnum):
    """The representations the metrics endpoint can serve."""

    PROMETHEUS = "prometheus"
    JSON = "json"


# Label values are double-quoted, so a backslash, a quote or a newline inside one has to be escaped
# or the sample line stops parsing. Everything else, including UTF-8, passes through.
_LABEL_VALUE_ESCAPES = str.maketrans({"\\": "\\\\", '"': '\\"', "\n": "\\n"})
# HELP text is not quoted, so a quote is fine there; only the escape character and the line
# terminator have to go.
_DOCUMENTATION_ESCAPES = str.maketrans({"\\": "\\\\", "\n": "\\n"})


def _render_value(value: float) -> str:
    """Render a sample value, preferring integer form for whole numbers.

    Args:
        value (float): The value to render.

    Returns:
        str: The rendered value.
    """
    return str(int(value)) if value.is_integer() else repr(value)


def _render_labels(labels: Mapping[str, str]) -> str:
    """Render a label set as a Prometheus label matcher, or an empty string when unlabelled.

    Args:
        labels (Mapping[str, str]): The label set.

    Returns:
        str: The rendered matcher, including braces, or an empty string.
    """
    if not labels:
        return ""
    pairs = ",".join(f'{name}="{labels[name].translate(_LABEL_VALUE_ESCAPES)}"' for name in sorted(labels))
    return f"{{{pairs}}}"


def _render_series(snapshot: MetricsSnapshot, name: str) -> Iterator[str]:
    """Yield one sample line per label set recorded against a stored series.

    Args:
        snapshot (MetricsSnapshot): The snapshot to read.
        name (str): The stored series name, including any _sum or _count suffix.

    Yields:
        str: A rendered sample line.
    """
    for labels, value in snapshot.samples(name):
        yield f"{name}{_render_labels(labels)} {_render_value(value)}"


def render_prometheus(snapshot: MetricsSnapshot) -> str:
    """Render a snapshot as a Prometheus 0.0.4 text exposition payload.

    Args:
        snapshot (MetricsSnapshot): The point-in-time collector snapshot to render.

    Returns:
        str: The exposition payload, newline terminated.
    """
    lines: list[str] = []
    for family in FAMILIES:
        lines.append(f"# HELP {family.name} {family.documentation.translate(_DOCUMENTATION_ESCAPES)}")
        lines.append(f"# TYPE {family.name} {family.metric_type}")
        # A summary is stored as two series; a counter or a gauge as one.
        names = (f"{family.name}_sum", f"{family.name}_count") if family.metric_type == "summary" else (family.name,)
        for name in names:
            lines.extend(_render_series(snapshot, name))
    return "\n".join(lines) + "\n"
