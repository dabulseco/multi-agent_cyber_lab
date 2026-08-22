from __future__ import annotations
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List
import json

DEFAULT_LOG_DIR_NAME = "logs"
DEFAULT_LOG_FILE_NAME = "interactions.jsonl"

def log_path(project_root: Path) -> Path:
    return project_root / DEFAULT_LOG_DIR_NAME / DEFAULT_LOG_FILE_NAME

def log_event(project_root: Path, event: Dict[str, Any]) -> None:
    path = log_path(project_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {"timestamp": datetime.now().isoformat(timespec="seconds"), **event}
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

def read_events(project_root: Path, limit: int = 200) -> List[Dict[str, Any]]:
    path = log_path(project_root)
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    events = []
    for line in lines[-limit:]:
        try:
            events.append(json.loads(line))
        except Exception:
            continue
    return events
