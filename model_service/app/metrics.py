from prometheus_client import CollectorRegistry, Counter, Histogram


class Metrics:
    def __init__(self) -> None:
        self.registry = CollectorRegistry()
        self.requests = Counter(
            "codesentinel_model_requests_total",
            "Model HTTP requests",
            ["method", "route", "status"],
            registry=self.registry,
        )
        self.latency = Histogram(
            "codesentinel_model_request_seconds", "HTTP latency", registry=self.registry
        )
        self.inference = Histogram(
            "codesentinel_model_inference_seconds",
            "Prediction time",
            registry=self.registry,
        )
        self.errors = Counter(
            "codesentinel_model_errors_total",
            "Failed model HTTP requests",
            registry=self.registry,
        )
