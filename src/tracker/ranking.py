from __future__ import annotations

from datetime import datetime

from tracker.clock import BEIJING, days_ago, stale_since, today
from tracker.models import STALE_DAYS, Item, Ledger, STATE_ZH


def _touched(item: Item) -> datetime | None:
    return item.last_progress_at or item.confirmed_at or item.created_at


def explodes_today(item: Item, at: datetime | None = None) -> bool:
    if item.state == "ended" or item.explodes_on is None:
        return False
    return item.explodes_on == today(at)


def waiting_stale(item: Item, at: datetime | None = None) -> bool:
    if item.state != "waiting":
        return False
    return stale_since(_touched(item), STALE_DAYS, at)


def untouched_open(item: Item) -> bool:
    return item.state in ("active", "waiting")


def ranked_ids(ledger: Ledger, at: datetime | None = None) -> list[str]:
    """当前主事顺序：每件只出现一次，先匹配的桶优先。"""
    seen: set[str] = set()
    order: list[str] = []

    def take(predicate) -> None:
        for item in ledger.items:
            if item.id in seen or item.state == "ended":
                continue
            if predicate(item):
                seen.add(item.id)
                order.append(item.id)

    take(lambda it: explodes_today(it, at))
    if ledger.weekly_pin_id:
        pin = ledger.item(ledger.weekly_pin_id)
        if pin and pin.state != "ended" and pin.id not in seen:
            seen.add(pin.id)
            order.append(pin.id)
    take(lambda it: it.state == "pending")
    take(lambda it: waiting_stale(it, at))
    take(lambda it: it.from_leader and it.state in ("active", "waiting"))

    rest = [
        it
        for it in ledger.items
        if it.id not in seen and untouched_open(it)
    ]
    rest.sort(key=lambda it: _touched(it) or datetime(1970, 1, 1, tzinfo=BEIJING))
    for item in rest:
        order.append(item.id)
        seen.add(item.id)
    return order


def current_main(ledger: Ledger, at: datetime | None = None) -> Item | None:
    ids = ranked_ids(ledger, at)
    if not ids:
        return None
    return ledger.item(ids[0])


def format_main(item: Item | None) -> str:
    if item is None:
        return "当前主事：无"
    line = f"当前主事：{item.title}"
    if item.next_task:
        line += f"\n下一步：{item.next_task}"
    if item.state == "waiting" and item.waiting_who:
        line += f"\n在等：{item.waiting_who} / {item.waiting_what or ''}".rstrip(" /")
    if item.owner:
        line += f"\n负责人：{item.owner}"
    return line


def stale_open(ledger: Ledger, at: datetime | None = None) -> list[tuple[Item, int]]:
    rows: list[tuple[Item, int]] = []
    for item in ledger.items:
        if item.state not in ("active", "waiting"):
            continue
        ago = days_ago(_touched(item), at)
        if ago is None or ago < STALE_DAYS:
            continue
        rows.append((item, ago))
    rows.sort(key=lambda row: -row[1])
    return rows


def label(item: Item) -> str:
    extra = STATE_ZH[item.state]
    if item.owner:
        extra += f" · {item.owner}"
    return f"{item.title}（{extra}）"
