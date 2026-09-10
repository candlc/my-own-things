from __future__ import annotations

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

BEIJING = ZoneInfo("Asia/Shanghai")


def now(at: datetime | None = None) -> datetime:
    if at is None:
        return datetime.now(BEIJING)
    if at.tzinfo is None:
        return at.replace(tzinfo=BEIJING)
    return at.astimezone(BEIJING)


def today(at: datetime | None = None) -> date:
    return now(at).date()


def is_friday(at: datetime | None = None) -> bool:
    return now(at).weekday() == 4


def days_ago(when: datetime | None, at: datetime | None = None) -> int | None:
    if when is None:
        return None
    delta = now(at).date() - now(when).date()
    return delta.days


def stale_since(when: datetime | None, days: int, at: datetime | None = None) -> bool:
    ago = days_ago(when, at)
    if ago is None:
        return False
    return ago >= days


def start_of_day(at: datetime | None = None) -> datetime:
    n = now(at)
    return n.replace(hour=0, minute=0, second=0, microsecond=0)


def since(hours: int, at: datetime | None = None) -> datetime:
    return now(at) - timedelta(hours=hours)
