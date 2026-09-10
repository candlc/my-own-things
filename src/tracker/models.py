from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Literal

ItemState = Literal["pending", "active", "waiting", "ended"]

STATE_ZH = {
    "pending": "待确认",
    "active": "进行中",
    "waiting": "等待",
    "ended": "已结束",
}

STALE_DAYS = 7
SELF_RECAP_MAX_SECONDS = 120


def parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value)


def parse_date(value: str | None) -> date | None:
    if not value:
        return None
    return date.fromisoformat(value)


@dataclass
class ProgressNote:
    at: datetime
    text: str

    def to_dict(self) -> dict:
        return {"at": self.at.isoformat(), "text": self.text}

    @classmethod
    def from_dict(cls, raw: dict) -> ProgressNote:
        return cls(at=parse_dt(raw["at"]), text=raw["text"])


@dataclass
class Item:
    id: str
    title: str
    state: ItemState = "pending"
    owner: str | None = None
    waiting_who: str | None = None
    waiting_what: str | None = None
    explodes_on: date | None = None
    from_leader: bool = False
    next_task: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    confirmed_at: datetime | None = None
    ended_at: datetime | None = None
    last_progress_at: datetime | None = None
    progress: list[ProgressNote] = field(default_factory=list)
    recap_id: str | None = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "state": self.state,
            "owner": self.owner,
            "waiting_who": self.waiting_who,
            "waiting_what": self.waiting_what,
            "explodes_on": self.explodes_on.isoformat() if self.explodes_on else None,
            "from_leader": self.from_leader,
            "next_task": self.next_task,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "confirmed_at": self.confirmed_at.isoformat() if self.confirmed_at else None,
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "last_progress_at": self.last_progress_at.isoformat() if self.last_progress_at else None,
            "progress": [p.to_dict() for p in self.progress],
            "recap_id": self.recap_id,
        }

    @classmethod
    def from_dict(cls, raw: dict) -> Item:
        return cls(
            id=raw["id"],
            title=raw["title"],
            state=raw.get("state", "pending"),
            owner=raw.get("owner"),
            waiting_who=raw.get("waiting_who"),
            waiting_what=raw.get("waiting_what"),
            explodes_on=parse_date(raw.get("explodes_on")),
            from_leader=bool(raw.get("from_leader")),
            next_task=raw.get("next_task"),
            created_at=parse_dt(raw.get("created_at")),
            updated_at=parse_dt(raw.get("updated_at")),
            confirmed_at=parse_dt(raw.get("confirmed_at")),
            ended_at=parse_dt(raw.get("ended_at")),
            last_progress_at=parse_dt(raw.get("last_progress_at")),
            progress=[ProgressNote.from_dict(p) for p in raw.get("progress", [])],
            recap_id=raw.get("recap_id"),
        )


@dataclass
class Recap:
    id: str
    text: str
    recorded_at: datetime | None = None
    duration_seconds: int | None = None
    ingested_at: datetime | None = None
    source: str = "drop"
    split: bool = False

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "text": self.text,
            "recorded_at": self.recorded_at.isoformat() if self.recorded_at else None,
            "duration_seconds": self.duration_seconds,
            "ingested_at": self.ingested_at.isoformat() if self.ingested_at else None,
            "source": self.source,
            "split": self.split,
        }

    @classmethod
    def from_dict(cls, raw: dict) -> Recap:
        return cls(
            id=raw["id"],
            text=raw["text"],
            recorded_at=parse_dt(raw.get("recorded_at")),
            duration_seconds=raw.get("duration_seconds"),
            ingested_at=parse_dt(raw.get("ingested_at")),
            source=raw.get("source", "drop"),
            split=bool(raw.get("split")),
        )


@dataclass
class Pipe:
    last_attempt_at: datetime | None = None
    last_ok_at: datetime | None = None
    last_error: str | None = None

    @property
    def failed(self) -> bool:
        return self.last_error is not None

    def to_dict(self) -> dict:
        return {
            "last_attempt_at": self.last_attempt_at.isoformat() if self.last_attempt_at else None,
            "last_ok_at": self.last_ok_at.isoformat() if self.last_ok_at else None,
            "last_error": self.last_error,
        }

    @classmethod
    def from_dict(cls, raw: dict | None) -> Pipe:
        raw = raw or {}
        return cls(
            last_attempt_at=parse_dt(raw.get("last_attempt_at")),
            last_ok_at=parse_dt(raw.get("last_ok_at")),
            last_error=raw.get("last_error"),
        )


@dataclass
class Ledger:
    items: list[Item] = field(default_factory=list)
    recaps: list[Recap] = field(default_factory=list)
    weekly_pin_id: str | None = None
    pipe: Pipe = field(default_factory=Pipe)
    next_item_seq: int = 1
    next_recap_seq: int = 1

    def item(self, item_id: str) -> Item | None:
        for it in self.items:
            if it.id == item_id:
                return it
        return None

    def recap(self, recap_id: str) -> Recap | None:
        for rec in self.recaps:
            if rec.id == recap_id:
                return rec
        return None

    def pending(self) -> list[Item]:
        return [it for it in self.items if it.state == "pending"]

    def to_dict(self) -> dict:
        return {
            "version": 1,
            "weekly_pin_id": self.weekly_pin_id,
            "next_item_seq": self.next_item_seq,
            "next_recap_seq": self.next_recap_seq,
            "pipe": self.pipe.to_dict(),
            "items": [it.to_dict() for it in self.items],
            "recaps": [r.to_dict() for r in self.recaps],
        }

    @classmethod
    def from_dict(cls, raw: dict) -> Ledger:
        return cls(
            items=[Item.from_dict(it) for it in raw.get("items", [])],
            recaps=[Recap.from_dict(r) for r in raw.get("recaps", [])],
            weekly_pin_id=raw.get("weekly_pin_id"),
            pipe=Pipe.from_dict(raw.get("pipe")),
            next_item_seq=int(raw.get("next_item_seq", 1)),
            next_recap_seq=int(raw.get("next_recap_seq", 1)),
        )
