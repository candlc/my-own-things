from __future__ import annotations

from datetime import date, datetime

from tracker.clock import now
from tracker.models import Item, Ledger, ProgressNote, Recap


def new_item_id(ledger: Ledger) -> str:
    seq = ledger.next_item_seq
    ledger.next_item_seq += 1
    return f"I{seq:03d}"


def new_recap_id(ledger: Ledger) -> str:
    seq = ledger.next_recap_seq
    ledger.next_recap_seq += 1
    return f"R{seq:03d}"


def add_recap(
    ledger: Ledger,
    text: str,
    *,
    duration_seconds: int | None = None,
    recorded_at: datetime | None = None,
    source: str = "drop",
    at: datetime | None = None,
) -> Recap:
    stamp = now(at)
    recap = Recap(
        id=new_recap_id(ledger),
        text=text.strip(),
        recorded_at=recorded_at or stamp,
        duration_seconds=duration_seconds,
        ingested_at=stamp,
        source=source,
        split=False,
    )
    ledger.recaps.append(recap)
    return recap


def add_pending(
    ledger: Ledger,
    title: str,
    *,
    recap_id: str | None = None,
    owner: str | None = None,
    explodes_on: date | None = None,
    from_leader: bool = False,
    next_task: str | None = None,
    at: datetime | None = None,
) -> Item:
    stamp = now(at)
    item = Item(
        id=new_item_id(ledger),
        title=title.strip(),
        state="pending",
        owner=owner,
        explodes_on=explodes_on,
        from_leader=from_leader,
        next_task=next_task,
        created_at=stamp,
        updated_at=stamp,
        recap_id=recap_id,
    )
    ledger.items.append(item)
    if recap_id:
        recap = ledger.recap(recap_id)
        if recap:
            recap.split = True
    return item


def wait(item: Item, who: str, what: str, at: datetime | None = None) -> None:
    if item.state == "pending":
        raise ValueError("待确认不能进入等待，先点头。")
    if item.state == "ended":
        raise ValueError("已结束的事项不能进入等待。")
    if not who.strip() or not what.strip():
        raise ValueError("等待必须写清等谁、等什么。")
    stamp = now(at)
    item.state = "waiting"
    item.waiting_who = who.strip()
    item.waiting_what = what.strip()
    item.updated_at = stamp
    item.last_progress_at = stamp


def resume(item: Item, at: datetime | None = None) -> None:
    if item.state != "waiting":
        raise ValueError("只有等待中的事项能回到进行中。")
    stamp = now(at)
    item.state = "active"
    item.waiting_who = None
    item.waiting_what = None
    item.updated_at = stamp
    item.last_progress_at = stamp


def end_item(item: Item, at: datetime | None = None) -> None:
    if item.state == "pending":
        raise ValueError("待确认请丢掉，不要直接结束。")
    stamp = now(at)
    item.state = "ended"
    item.ended_at = stamp
    item.updated_at = stamp


def complete_task(item: Item, at: datetime | None = None) -> None:
    if item.state in ("pending", "ended"):
        raise ValueError("没有进行中的任务可完成。")
    stamp = now(at)
    item.next_task = None
    item.updated_at = stamp
    item.last_progress_at = stamp
    item.progress.append(ProgressNote(at=stamp, text="任务完成（事项未结束）"))


def set_next_task(item: Item, text: str, at: datetime | None = None) -> None:
    stamp = now(at)
    item.next_task = text.strip() or None
    item.updated_at = stamp


def add_progress(item: Item, text: str, at: datetime | None = None) -> None:
    stamp = now(at)
    note = text.strip()
    if not note:
        raise ValueError("进度不能空。")
    item.progress.append(ProgressNote(at=stamp, text=note))
    item.last_progress_at = stamp
    item.updated_at = stamp
    if item.state == "pending":
        return


def pin_week(ledger: Ledger, item_id: str | None) -> None:
    if item_id is None:
        ledger.weekly_pin_id = None
        return
    item = ledger.item(item_id)
    if item is None or item.state == "ended":
        raise ValueError("置顶的事项不存在或已结束。")
    ledger.weekly_pin_id = item_id
