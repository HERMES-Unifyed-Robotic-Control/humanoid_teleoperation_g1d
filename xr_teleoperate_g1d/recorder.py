"""Streaming JSONL recorder used by dry runs and bridge integration tests."""

import json
from pathlib import Path
from typing import Any, Dict, Optional


def _json_default(value: Any) -> Any:
    if hasattr(value, "tolist"):
        return value.tolist()
    raise TypeError("Object of type %s is not JSON serializable" % type(value).__name__)


class Recorder:
    def __init__(self, path: str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._file = self.path.open("a", encoding="utf-8", buffering=1)
        self._sequence = 0

    def write(self, frame: Dict[str, Any], states: Optional[Dict[str, Any]] = None) -> None:
        record = dict(frame)
        record["sequence"] = self._sequence
        if states:
            record.setdefault("states", {}).update(states)
        self._file.write(json.dumps(record, ensure_ascii=False, default=_json_default) + "\n")
        self._sequence += 1

    def close(self) -> None:
        self._file.close()

    def __enter__(self) -> "Recorder":
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()
