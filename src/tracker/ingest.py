from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path

from tracker.clock import now
from tracker.models import SELF_RECAP_MAX_SECONDS, Ledger
from tracker.service import add_recap
from tracker.store import data_dir

# clock.parse_maybe doesn't exist - I'll parse in this file


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value)


def drop_dir() -> Path:
    return data_dir() / "inbox" / "drop"


def done_dir() -> Path:
    return data_dir() / "inbox" / "done"


def pull_drop(ledger: Ledger, at: datetime | None = None) -> tuple[int, str | None]:
    """读 drop 目录里的短自述。目录不可读 = 管子失败。空目录 = 成功但今天可能没会。"""
    folder = drop_dir()
    stamp = now(at)
    ledger.pipe.last_attempt_at = stamp
    try:
        folder.mkdir(parents=True, exist_ok=True)
        files = sorted(
            p
            for p in folder.iterdir()
            if p.is_file() and p.suffix.lower() in {".txt", ".json", ".md"}
        )
    except OSError as exc:
        ledger.pipe.last_error = f"听记管子读不了 drop 目录：{exc}"
        return 0, ledger.pipe.last_error

    added = 0
    try:
        for path in files:
            recap_text, duration, recorded = _read_drop_file(path)
            if duration is not None and duration > SELF_RECAP_MAX_SECONDS:
                _archive(path, skipped=True)
                continue
            if not recap_text.strip():
                _archive(path, skipped=True)
                continue
            add_recap(
                ledger,
                recap_text,
                duration_seconds=duration,
                recorded_at=recorded,
                source="drop",
                at=stamp,
            )
            added += 1
            _archive(path, skipped=False)
    except OSError as exc:
        ledger.pipe.last_error = f"听记管子处理 drop 失败：{exc}"
        return added, ledger.pipe.last_error

    ledger.pipe.last_ok_at = stamp
    ledger.pipe.last_error = None
    return added, None


def _read_drop_file(path: Path) -> tuple[str, int | None, datetime | None]:
    if path.suffix.lower() == ".json":
        raw = json.loads(path.read_text(encoding="utf-8"))
        text = str(raw.get("text") or raw.get("transcript") or "")
        duration = raw.get("duration_seconds") or raw.get("duration")
        recorded = _parse_dt(raw.get("recorded_at"))
        return text, int(duration) if duration is not None else None, recorded
    return path.read_text(encoding="utf-8"), None, None


def _archive(path: Path, skipped: bool) -> None:
    dest_root = done_dir()
    dest_root.mkdir(parents=True, exist_ok=True)
    suffix = ".skipped" if skipped else ""
    dest = dest_root / f"{path.name}{suffix}"
    n = 1
    while dest.exists():
        dest = dest_root / f"{path.stem}-{n}{path.suffix}{suffix}"
        n += 1
    shutil.move(str(path), str(dest))
