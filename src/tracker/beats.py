from __future__ import annotations

from datetime import datetime

from tracker.clock import is_friday, today
from tracker.confirm import pending_numbered
from tracker.models import Ledger, STATE_ZH
from tracker.ranking import current_main, explodes_today, format_main, stale_open


def _pending_block(ledger: Ledger) -> str:
    pending = pending_numbered(ledger)
    if not pending:
        return "待确认 0 件"
    lines = [f"待确认 {len(pending)} 件"]
    for i, item in enumerate(pending, start=1):
        mark = ""
        if explodes_today(item):
            mark = " · 今天会爆"
        if item.from_leader:
            mark += " · 领导"
        lines.append(f"{i}. {item.title}{mark}")
    return "\n".join(lines)


def _explode_block(ledger: Ledger, at: datetime | None = None) -> str:
    items = [
        it
        for it in ledger.items
        if explodes_today(it, at)
    ]
    if not items:
        return "今天可能爆：无"
    names = "、".join(it.title for it in items)
    return f"今天可能爆：{names}"


def _pipe_line(ledger: Ledger) -> str | None:
    if ledger.pipe.failed:
        return "今天自述没收着。"
    return None


def daytime_beat(ledger: Ledger, at: datetime | None = None) -> str:
    parts: list[str] = []
    pipe = _pipe_line(ledger)
    if pipe:
        parts.append(pipe)
    unsplit = [r for r in ledger.recaps if not r.split]
    if unsplit:
        parts.append(f"有 {len(unsplit)} 条自述还没拆成待确认。")
    parts.append(_pending_block(ledger))
    parts.append(_explode_block(ledger, at))
    parts.append(format_main(current_main(ledger, at)))
    return "\n\n".join(parts)


def recap_beat(ledger: Ledger, at: datetime | None = None, friday: bool | None = None) -> str:
    day = today(at)
    confirmed = [
        it
        for it in ledger.items
        if it.confirmed_at and it.confirmed_at.date() == day
    ]
    ended = [
        it
        for it in ledger.items
        if it.state == "ended" and it.ended_at and it.ended_at.date() == day
    ]
    waiting = [it for it in ledger.items if it.state == "waiting"]

    today_bits: list[str] = []
    if confirmed:
        today_bits.append(f"点头 {len(confirmed)} 件")
    if ended:
        names = "、".join(it.title for it in ended)
        today_bits.append(f"{names}已结束")
    today_line = "今天：" + ("，".join(today_bits) if today_bits else "没有点头或结束")

    if waiting:
        wait_bits = []
        for it in waiting:
            bit = it.title
            if it.waiting_who:
                bit += f" / {it.waiting_who}"
            wait_bits.append(bit)
        wait_line = "还在等：" + "、".join(wait_bits)
    else:
        wait_line = "还在等：无"

    main = current_main(ledger, at)
    main_line = "明天当前主事：" + (main.title if main else "无")

    lines = [today_line, wait_line, main_line]
    use_friday = is_friday(at) if friday is None else friday
    if use_friday:
        stale = stale_open(ledger, at)
        if stale:
            extra = ["多久没动："]
            for item, ago in stale:
                extra.append(f"- {item.title}（{STATE_ZH[item.state]} {ago} 天）")
            lines.append("\n".join(extra))
        else:
            lines.append("多久没动：无")
    return "\n".join(lines)
