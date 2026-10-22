from prometheus_client import CollectorRegistry, Counter, Histogram


class Metrics:
    def __init__(self) -> None:
        self.registry = CollectorRegistry()
        self.requests = Counter(
            "codesentinel_api_requests_total",
            "API requests",
            ["method", "route", "status"],
            registry=self.registry,
        )
        self.latency = Histogram(
            "codesentinel_api_request_seconds", "API latency", registry=self.registry
        )
        self.errors = Counter(
            "codesentinel_api_errors_total", "API errors", registry=self.registry
        )
        self.scans = Counter(
            "codesentinel_scans_total",
            "Completed scan attempts",
            ["decision"],
            registry=self.registry,
        )
        self.scan_seconds = Histogram(
            "codesentinel_scan_seconds",
            "Scan pipeline duration",
            registry=self.registry,
        )
