"""Optional JSON-lines observability without leaking secrets or file contents."""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any


class EventLogger:
    def __init__(self, debug: bool = False) -> None:
        self.debug = debug
        self.logger = logging.getLogger("forge")
        if not self.logger.handlers:
            handler = logging.StreamHandler(sys.stderr)
            handler.setFormatter(logging.Formatter("%(message)s"))
            self.logger.addHandler(handler)
        self.logger.setLevel(logging.DEBUG if debug else logging.INFO)

    def emit(self, name: str, **data: Any) -> None:
        if not self.debug and name in {"model.request", "model.response"}:
            return
        payload = {"event": name, "time": datetime.now(timezone.utc).isoformat(), **data}
        self.logger.info(json.dumps(payload, default=str))