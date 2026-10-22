"""Single-process fixed-window limiter. Production needs a shared edge limiter."""

from threading import Lock
from time import monotonic


class RateLimiter:
    def __init__(self, limit: int, window: int, max_clients: int = 10000) -> None:
        self.limit, self.window, self.max_clients = limit, window, max_clients
        self.clients: dict[str, tuple[float, int]] = {}
        self.lock = Lock()

    def allow(self, key: str) -> bool:
        now = monotonic()
        with self.lock:
            if len(self.clients) >= self.max_clients:
                self.clients = {
                    k: v for k, v in self.clients.items() if now - v[0] < self.window
                }
                if key not in self.clients and len(self.clients) >= self.max_clients:
                    return False
            started, count = self.clients.get(key, (now, 0))
            if now - started >= self.window:
                started, count = now, 0
            if count >= self.limit:
                return False
            self.clients[key] = (started, count + 1)
            return True
