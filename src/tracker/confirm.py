from __future__ import annotations

import re
from dataclasses import dataclass

from tracker.clock import now
from tracker.models import Item, Ledger

# 1 / 1丢 / 1 丢掉 / 1 负责人小王 / 1负责人：小王
REPLY = re.compile(
    r"^\s*(\d+)\s*(丢掉|丢|不要|删除|删掉|删)?\s*(?:负责人[:：]?\s*(.+?))?\s*$"
)


@dataclass
class Reply:
    index: int
    discard: bool = False
    owner: str | None = None


def parse_reply(text: str) -> Reply | None:
    match = REPLY.match(text.strip())
    if not match:
        return None
    index = int(match.group(1))
    if index < 1:
        return None
    discard = match.group(2) is not None
    owner = match.group(3).strip() if match.group(3) else None
    if discard and owner:
        return None
    return Reply(index=index, discard=discard, owner=owner)


def parse_replies(text: str) -> list[Reply] | None:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return None
    parsed: list[Reply] = []
    for line in lines:
        one = parse_reply(line)
        if one is None:
            return None
        parsed.append(one)
    return parsed


def pending_numbered(ledger: Ledger) -> list[Item]:
    return sorted(ledger.pending(), key=lambda it: it.created_at or now())


def apply_item(item: Item, reply: Reply, at=None) -> str:
    stamp = now(at)
    if reply.discard:
        item.state = "ended"
        item.ended_at = stamp
        item.updated_at = stamp
        return f"已丢掉：{item.title}"
    item.state = "active"
    item.confirmed_at = stamp
    item.updated_at = stamp
    item.last_progress_at = stamp
    if reply.owner:
        item.owner = reply.owner
    who = f"，负责人 {item.owner}" if item.owner else ""
    return f"已记下：{item.title}{who}"


def apply_reply(ledger: Ledger, reply: Reply, at=None) -> str:
    pending = pending_numbered(ledger)
    if reply.index > len(pending):
        return f"没有第 {reply.index} 件待确认。"
    return apply_item(pending[reply.index - 1], reply, at)


def apply_replies(ledger: Ledger, replies: list[Reply], at=None) -> list[str]:
    pending = pending_numbered(ledger)
    seen: set[int] = set()
    lines: list[str] = []
    for reply in replies:
        if reply.index in seen or reply.index > len(pending):
            lines.append(f"没有第 {reply.index} 件待确认。")
            continue
        seen.add(reply.index)
        lines.append(apply_item(pending[reply.index - 1], reply, at))
    return lines
