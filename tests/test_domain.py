from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from tracker.beats import daytime_beat, recap_beat
from tracker.clock import BEIJING
from tracker.confirm import apply_replies, apply_reply, parse_reply, parse_replies, pending_numbered
from tracker.ingest import pull_drop
from tracker.models import Item, Ledger, Recap
from tracker.ranking import current_main, ranked_ids
from tracker.service import (
    add_pending,
    add_progress,
    add_recap,
    complete_task,
    end_item,
    pin_week,
    wait,
)

NOW = datetime(2026, 9, 11, 10, 0, tzinfo=BEIJING)  # Friday
TODAY = NOW.date()


def stamp(hours: int = 0) -> datetime:
    return NOW - timedelta(hours=hours)


def item(**kwargs) -> Item:
    defaults = dict(
        id="I001",
        title="x",
        state="active",
        created_at=stamp(48),
        updated_at=stamp(48),
        confirmed_at=stamp(48),
        last_progress_at=stamp(48),
    )
    defaults.update(kwargs)
    return Item(**defaults)


def test_parse_numbered_replies():
    assert parse_reply("1").index == 1
    assert parse_reply("1丢").discard is True
    assert parse_reply("2 丢掉").discard is True
    assert parse_reply("1 负责人小王").owner == "小王"
    assert parse_reply("1负责人：小王").owner == "小王"
    assert parse_reply("合同记下") is None
    assert parse_replies("1\n2丢")[1].discard is True
    assert parse_replies("合同记下") is None


def test_confirm_and_discard():
    ledger = Ledger()
    a = add_pending(ledger, "合同", at=stamp(2))
    b = add_pending(ledger, "周报", at=stamp(1))
    assert [it.title for it in pending_numbered(ledger)] == ["合同", "周报"]
    msg = apply_reply(ledger, parse_reply("2丢"), at=NOW)
    assert "周报" in msg
    assert b.state == "ended"
    apply_reply(ledger, parse_reply("1 负责人小王"), at=NOW)
    assert a.state == "active"
    assert a.owner == "小王"
    assert ledger.pending() == []


def test_batch_reply_uses_original_numbers():
    ledger = Ledger()
    add_pending(ledger, "合同", at=stamp(2))
    add_pending(ledger, "bug", at=stamp(1))
    add_pending(ledger, "周报", at=NOW)
    lines = apply_replies(ledger, parse_replies("1\n3丢"), NOW)
    assert "合同" in lines[0]
    assert "周报" in lines[1]
    left = [it.title for it in ledger.pending()]
    assert left == ["bug"]


def test_current_main_order():
    explode = item(id="A", title="周报", state="pending", explodes_on=TODAY)
    pin = item(id="B", title="合同", state="active")
    pending = item(id="C", title="新口头", state="pending", explodes_on=None)
    waiting = item(
        id="D",
        title="老合同",
        state="waiting",
        waiting_who="法务",
        waiting_what="红章",
        last_progress_at=stamp(24 * 10),
    )
    leader = item(id="E", title="领导交办", state="active", from_leader=True)
    old = item(id="F", title="旧bug", state="active", last_progress_at=stamp(24 * 20))
    ledger = Ledger(
        items=[old, leader, waiting, pending, pin, explode],
        weekly_pin_id="B",
    )
    assert ranked_ids(ledger, NOW) == ["A", "B", "C", "D", "E", "F"]
    assert current_main(ledger, NOW).id == "A"


def test_task_done_does_not_end_item():
    it = item(title="合同", next_task="催邮件")
    complete_task(it, at=NOW)
    assert it.next_task is None
    assert it.state == "active"


def test_wait_needs_who_and_what():
    it = item()
    try:
        wait(it, "", "红章")
        assert False, "should fail"
    except ValueError:
        pass
    wait(it, "法务", "红章", at=NOW)
    assert it.state == "waiting"
    assert it.waiting_who == "法务"


def test_only_user_ends_item():
    it = item()
    end_item(it, at=NOW)
    assert it.state == "ended"


def test_daytime_beat_pipe_and_numbers(tmp_path, monkeypatch):
    monkeypatch.setenv("TRACKER_HOME", str(tmp_path))
    ledger = Ledger()
    add_pending(ledger, "合同", at=stamp(1))
    add_pending(ledger, "周报", explodes_on=TODAY, at=NOW)
    ledger.pipe.last_error = "auth"
    text = daytime_beat(ledger, NOW)
    assert text.startswith("今天自述没收着。")
    assert "1. 合同" in text
    assert "2. 周报" in text
    assert "今天可能爆：周报" in text
    assert "当前主事：周报" in text


def test_recap_three_lines_friday_stale():
    ledger = Ledger()
    weekly = add_pending(ledger, "周报", at=stamp(3))
    apply_reply(ledger, parse_reply("1"), at=NOW)
    end_item(weekly, at=NOW)
    waiting = item(
        id="I009",
        title="合同",
        state="waiting",
        waiting_who="法务",
        waiting_what="红章",
        last_progress_at=stamp(24 * 8),
        created_at=stamp(24 * 20),
        confirmed_at=stamp(24 * 20),
    )
    ledger.items.append(waiting)
    text = recap_beat(ledger, NOW, friday=True)
    lines = text.splitlines()
    assert lines[0].startswith("今天：")
    assert "周报已结束" in lines[0]
    assert "还在等：合同 / 法务" in text
    assert "明天当前主事：合同" in text
    assert "多久没动：" in text
    assert "合同（等待" in text


def test_pull_short_not_long(tmp_path, monkeypatch):
    monkeypatch.setenv("TRACKER_HOME", str(tmp_path))
    drop = Path(tmp_path) / "inbox" / "drop"
    drop.mkdir(parents=True)
    (drop / "short.txt").write_text("跟一下合同，bug给小王", encoding="utf-8")
    (drop / "long.json").write_text(
        '{"text": "两小时会议全文", "duration_seconds": 3600}',
        encoding="utf-8",
    )
    ledger = Ledger()
    added, err = pull_drop(ledger, NOW)
    assert err is None
    assert added == 1
    assert ledger.recaps[0].text.startswith("跟一下合同")
    assert ledger.pipe.failed is False


def test_progress_stays_on_item():
    it = item(title="合同")
    add_progress(it, "电话打了，说法务周五回", at=NOW)
    assert it.progress[-1].text.startswith("电话打了")
    assert it.last_progress_at == NOW


def test_weekly_pin_after_explode():
    explode = item(id="A", title="周报", explodes_on=TODAY, state="pending")
    contract = item(id="B", title="合同", state="active")
    ledger = Ledger(items=[contract, explode])
    pin_week(ledger, "B")
    assert ranked_ids(ledger, NOW)[:2] == ["A", "B"]
