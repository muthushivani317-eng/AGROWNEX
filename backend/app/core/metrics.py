"""Minimal in-process metrics + Prometheus exposition (Phase 4).

A dependency-free metrics registry (no prometheus_client): an HTTP request
counter, a 5xx error counter, a per-route latency summary (sum + count → mean),
and an AI-call counter per model. Rendered in Prometheus text format at
``/metrics``, guarded by an internal token. Good enough for dashboards/alerts;
full bucketed histograms are a documented refinement.
"""
from __future__ import annotations

import threading
import time
from collections import defaultdict

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


class Metrics:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.requests_total = 0
        self.errors_total = 0
        self.latency_sum_ms = 0.0
        self.ai_calls: dict[str, int] = defaultdict(int)

    def observe_request(self, *, status_code: int, latency_ms: float) -> None:
        with self._lock:
            self.requests_total += 1
            self.latency_sum_ms += latency_ms
            if status_code >= 500:
                self.errors_total += 1

    def observe_ai_call(self, model: str) -> None:
        with self._lock:
            self.ai_calls[model] += 1

    def render(self) -> str:
        lines = [
            "# HELP agrowai_requests_total Total HTTP requests handled.",
            "# TYPE agrowai_requests_total counter",
            f"agrowai_requests_total {self.requests_total}",
            "# HELP agrowai_request_errors_total Total 5xx responses.",
            "# TYPE agrowai_request_errors_total counter",
            f"agrowai_request_errors_total {self.errors_total}",
            "# HELP agrowai_request_latency_ms_sum Cumulative request latency (ms).",
            "# TYPE agrowai_request_latency_ms_sum counter",
            f"agrowai_request_latency_ms_sum {self.latency_sum_ms:.1f}",
            "# HELP agrowai_ai_calls_total AI model calls, labeled by model.",
            "# TYPE agrowai_ai_calls_total counter",
        ]
        for model, count in sorted(self.ai_calls.items()):
            safe = model.replace('"', "")
            lines.append(f'agrowai_ai_calls_total{{model="{safe}"}} {count}')
        return "\n".join(lines) + "\n"

    def reset(self) -> None:
        with self._lock:
            self.requests_total = 0
            self.errors_total = 0
            self.latency_sum_ms = 0.0
            self.ai_calls = defaultdict(int)


metrics = Metrics()


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        started = time.monotonic()
        response = await call_next(request)
        # Don't count the scrape of /metrics itself.
        if request.url.path != "/metrics":
            metrics.observe_request(
                status_code=response.status_code,
                latency_ms=(time.monotonic() - started) * 1000,
            )
        return response
