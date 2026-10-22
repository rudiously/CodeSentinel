"""Log approved metadata only; no exception messages, credentials or source."""

import json
import logging
from datetime import datetime, timezone


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return json.dumps(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "level": record.levelname,
                "event": record.getMessage(),
                "request_id": getattr(record, "request_id", None),
                "status": getattr(record, "status", None),
                "error_type": getattr(record, "error_type", None),
            }
        )


def configure_logging() -> None:
    logger = logging.getLogger("codesentinel")
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    logger.handlers = [handler]
    logger.setLevel(logging.INFO)
    logger.propagate = False
