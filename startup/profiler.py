from __future__ import annotations

import json
from pathlib import Path
import time
from typing import Any


class StartupProfiler:
    def __init__(self, *, enabled: bool, output_path: Path | None = None):
        self.enabled = bool(enabled)
        self.output_path = output_path or (Path("logs") / "startup_timing.log")
        self._t0 = time.perf_counter()
        self._last = self._t0
        self._events: list[dict[str, Any]] = []

    def mark(self, stage: str, **extra: Any) -> None:
        if not self.enabled:
            return

        now = time.perf_counter()
        event = {
            "stage": str(stage),
            "since_start_ms": round((now - self._t0) * 1000.0, 3),
            "since_prev_ms": round((now - self._last) * 1000.0, 3),
        }
        if extra:
            event.update(extra)

        self._events.append(event)
        self._last = now

    def finish(self, *, exit_code: int, **extra: Any) -> None:
        if not self.enabled:
            return

        payload: dict[str, Any] = {
            "timestamp_unix": time.time(),
            "exit_code": int(exit_code),
            "total_ms": round((time.perf_counter() - self._t0) * 1000.0, 3),
            "events": self._events,
        }
        if extra:
            payload.update(extra)

        try:
            self.output_path.parent.mkdir(parents=True, exist_ok=True)
            with self.output_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(payload, ensure_ascii=True) + "\n")
        except Exception:
            pass
