import hashlib
import hmac
from threading import Lock
from time import monotonic

from shared.http import ServiceError


def verify_webhook(body: bytes, signature: str | None, secret: str) -> None:
    if not secret:
        raise ServiceError("WEBHOOK_NOT_CONFIGURED", "Webhook secret is not configured")
    expected = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    if not signature or not hmac.compare_digest(
        signature.encode("utf-8"), expected.encode("ascii")
    ):
        raise ServiceError("INVALID_SIGNATURE", "Webhook signature is invalid", 401)


class DeliveryCache:
    """Bounded single-process deduplication. Durable multi-worker delivery queue is pending."""

    def __init__(self, ttl: int = 3600, capacity: int = 10000) -> None:
        self.ttl, self.capacity = ttl, capacity
        self.items: dict[str, float] = {}
        self.lock = Lock()

    def begin(self, delivery: str) -> bool:
        now = monotonic()
        with self.lock:
            self.items = {k: v for k, v in self.items.items() if now - v < self.ttl}
            if delivery in self.items:
                return False
            if len(self.items) >= self.capacity:
                raise ServiceError("WEBHOOK_BUSY", "Delivery cache capacity reached")
            self.items[delivery] = now
            return True

    def forget(self, delivery: str) -> None:
        with self.lock:
            self.items.pop(delivery, None)
