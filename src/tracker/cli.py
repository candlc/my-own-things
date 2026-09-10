from __future__ import annotations

import argparse
import json
import sys
from datetime import date

from tracker import beats, confirm, ranking, service, store
from tracker.clock import now
from tracker.ingest import pull_drop


def _out(text: str) -> None:
    sys.stdout.write(text)
    if not text.endswith("\n"):
        sys.stdout.write("\n")


def _load():
    return store.load()


def _save(ledger) -> None:
    store.save(ledger)


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(prog="tracker", description="事项账本")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("pending", help="列出待确认（编号给点头用）")
    sub.add_parser("main", help="只点名当前主事")
    sub.add_parser("status", help="账本摘要")
    p_beat = sub.add_parser("beat", help="打一拍微信文案")
    p_beat.add_argument("which", choices=["morning", "afternoon", "recap"])

    p_pull = sub.add_parser("pull", help="从 drop 目录收短自述")
    p_pull.add_argument("--quiet", action="store_true")

    p_ingest = sub.add_parser("ingest", help="手动写入一条自述")
    p_ingest.add_argument("text")
    p_ingest.add_argument("--duration", type=int, default=None)

    p_split = sub.add_parser("add-pending", help="从自述拆出待确认")
    p_split.add_argument("title")
    p_split.add_argument("--recap", dest="recap_id")
    p_split.add_argument("--owner")
    p_split.add_argument("--explodes", dest="explodes_on")
    p_split.add_argument("--leader", action="store_true")
    p_split.add_argument("--next-task")

    p_reply = sub.add_parser("reply", help="处理点头：1 / 1丢 / 1 负责人小王")
    p_reply.add_argument("text")

    p_wait = sub.add_parser("wait", help="事项进入等待")
    p_wait.add_argument("item_id")
    p_wait.add_argument("--who", required=True)
    p_wait.add_argument("--what", required=True)

    p_resume = sub.add_parser("resume", help="等待回到进行中")
    p_resume.add_argument("item_id")

    p_end = sub.add_parser("end", help="你把事项标已结束")
    p_end.add_argument("item_id")

    p_task = sub.add_parser("next-task", help="写下一步任务")
    p_task.add_argument("item_id")
    p_task.add_argument("text")

    p_done_task = sub.add_parser("task-done", help="任务完成，事项不结束")
    p_done_task.add_argument("item_id")

    p_prog = sub.add_parser("progress", help="进度写进事项")
    p_prog.add_argument("item_id")
    p_prog.add_argument("text")

    p_pin = sub.add_parser("pin", help="这周主事")
    p_pin.add_argument("item_id")
    sub.add_parser("unpin", help="取消这周主事")

    p_exp = sub.add_parser("explode", help="标今天/某天会爆")
    p_exp.add_argument("item_id")
    p_exp.add_argument("--on", dest="on_date", default="today")

    p_show = sub.add_parser("show", help="看一件事项")
    p_show.add_argument("item_id")

    sub.add_parser("unsplit", help="还没拆的自述")
    p_mark = sub.add_parser("mark-split", help="自述已拆完")
    p_mark.add_argument("recap_id")

    args = parser.parse_args(argv)
    ledger = _load()

    if args.cmd == "pending":
        items = confirm.pending_numbered(ledger)
        if not items:
            _out("待确认 0 件")
            return 0
        lines = [f"待确认 {len(items)} 件"]
        for i, item in enumerate(items, start=1):
            lines.append(f"{i}. {item.id} {item.title}")
        _out("\n".join(lines))
        return 0

    if args.cmd == "main":
        _out(ranking.format_main(ranking.current_main(ledger)))
        return 0

    if args.cmd == "status":
        pending = len(ledger.pending())
        active = sum(1 for it in ledger.items if it.state == "active")
        waiting = sum(1 for it in ledger.items if it.state == "waiting")
        pipe = "断" if ledger.pipe.failed else "通"
        _out(
            f"待确认 {pending} · 进行中 {active} · 等待 {waiting} · 管子{pipe}"
        )
        return 0

    if args.cmd == "beat":
        added, err = pull_drop(ledger)
        _save(ledger)
        if args.which in ("morning", "afternoon"):
            _out(beats.daytime_beat(ledger))
        else:
            _out(beats.recap_beat(ledger))
        return 0 if not err else 2

    if args.cmd == "pull":
        added, err = pull_drop(ledger)
        _save(ledger)
        if err:
            _out(err)
            return 2
        if not args.quiet:
            _out(f"收入 {added} 条自述")
        return 0

    if args.cmd == "ingest":
        recap = service.add_recap(ledger, args.text, duration_seconds=args.duration)
        ledger.pipe.last_attempt_at = now()
        ledger.pipe.last_ok_at = now()
        ledger.pipe.last_error = None
        _save(ledger)
        _out(recap.id)
        return 0

    if args.cmd == "add-pending":
        explodes = None
        if args.explodes_on:
            explodes = date.fromisoformat(args.explodes_on)
        item = service.add_pending(
            ledger,
            args.title,
            recap_id=args.recap_id,
            owner=args.owner,
            explodes_on=explodes,
            from_leader=args.leader,
            next_task=args.next_task,
        )
        _save(ledger)
        _out(item.id)
        return 0

    if args.cmd == "reply":
        replies = confirm.parse_replies(args.text)
        if replies is None:
            _out("UNCLEAR")
            return 3
        lines = confirm.apply_replies(ledger, replies)
        _save(ledger)
        _out("\n".join(lines))
        return 0

    if args.cmd == "wait":
        item = ledger.item(args.item_id)
        if not item:
            _out("没有这件事项")
            return 1
        try:
            service.wait(item, args.who, args.what)
        except ValueError as exc:
            _out(str(exc))
            return 1
        _save(ledger)
        _out(f"{item.id} 等待 {item.waiting_who} / {item.waiting_what}")
        return 0

    if args.cmd == "resume":
        item = ledger.item(args.item_id)
        if not item:
            _out("没有这件事项")
            return 1
        try:
            service.resume(item)
        except ValueError as exc:
            _out(str(exc))
            return 1
        _save(ledger)
        _out(f"{item.id} 进行中")
        return 0

    if args.cmd == "end":
        item = ledger.item(args.item_id)
        if not item:
            _out("没有这件事项")
            return 1
        try:
            service.end_item(item)
        except ValueError as exc:
            _out(str(exc))
            return 1
        _save(ledger)
        _out(f"{item.id} 已结束")
        return 0

    if args.cmd == "next-task":
        item = ledger.item(args.item_id)
        if not item:
            _out("没有这件事项")
            return 1
        service.set_next_task(item, args.text)
        _save(ledger)
        _out(f"{item.id} 下一步：{item.next_task}")
        return 0

    if args.cmd == "task-done":
        item = ledger.item(args.item_id)
        if not item:
            _out("没有这件事项")
            return 1
        try:
            service.complete_task(item)
        except ValueError as exc:
            _out(str(exc))
            return 1
        _save(ledger)
        _out(f"{item.id} 任务完成，事项未结束")
        return 0

    if args.cmd == "progress":
        item = ledger.item(args.item_id)
        if not item:
            _out("没有这件事项")
            return 1
        try:
            service.add_progress(item, args.text)
        except ValueError as exc:
            _out(str(exc))
            return 1
        _save(ledger)
        _out(f"{item.id} 已记进度")
        return 0

    if args.cmd == "pin":
        try:
            service.pin_week(ledger, args.item_id)
        except ValueError as exc:
            _out(str(exc))
            return 1
        _save(ledger)
        _out(f"这周主事：{args.item_id}")
        return 0

    if args.cmd == "unpin":
        service.pin_week(ledger, None)
        _save(ledger)
        _out("已取消这周主事")
        return 0

    if args.cmd == "explode":
        item = ledger.item(args.item_id)
        if not item:
            _out("没有这件事项")
            return 1
        if args.on_date == "today":
            item.explodes_on = now().date()
        else:
            item.explodes_on = date.fromisoformat(args.on_date)
        item.updated_at = now()
        _save(ledger)
        _out(f"{item.id} 会爆 {item.explodes_on.isoformat()}")
        return 0

    if args.cmd == "show":
        item = ledger.item(args.item_id)
        if not item:
            _out("没有这件事项")
            return 1
        _out(json.dumps(item.to_dict(), ensure_ascii=False, indent=2))
        return 0

    if args.cmd == "unsplit":
        recaps = [r for r in ledger.recaps if not r.split]
        if not recaps:
            _out("没有未拆自述")
            return 0
        for rec in recaps:
            _out(f"{rec.id}\n{rec.text}\n")
        return 0

    if args.cmd == "mark-split":
        recap = ledger.recap(args.recap_id)
        if not recap:
            _out("没有这条自述")
            return 1
        recap.split = True
        _save(ledger)
        _out(f"{recap.id} 已拆")
        return 0

    parser.error(f"unknown command {args.cmd}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
