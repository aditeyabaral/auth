"""Custom documentation module for PESUAuth API."""

from .authenticate import authenticate_docs
from .health import health_docs
from .metrics import metrics_docs, metrics_json_docs
from .readme import readme_docs

__all__ = [
    "authenticate_docs",
    "health_docs",
    "metrics_docs",
    "metrics_json_docs",
    "readme_docs",
]
