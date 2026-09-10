from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from tracker.models import Ledger

DEFAULT_NAME = "ledger.json"


def repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pyproject.toml").exists():
            return parent
    return Path.cwd()


def data_dir() -> Path:
    env = os.environ.get("TRACKER_HOME")
    if env:
        path = Path(env)
    else:
        path = repo_root() / "data"
    path.mkdir(parents=True, exist_ok=True)
    (path / "inbox" / "drop").mkdir(parents=True, exist_ok=True)
    (path / "inbox" / "done").mkdir(parents=True, exist_ok=True)
    return path


def ledger_path() -> Path:
    return data_dir() / DEFAULT_NAME


def load() -> Ledger:
    path = ledger_path()
    if not path.exists():
        return Ledger()
    raw = json.loads(path.read_text(encoding="utf-8"))
    return Ledger.from_dict(raw)


def save(ledger: Ledger) -> None:
    path = ledger_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(ledger.to_dict(), ensure_ascii=False, indent=2)
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    except Exception:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise
