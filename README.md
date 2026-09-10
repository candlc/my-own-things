# 事项跟踪

一个人用的事项账本：散会后对着 A1 说 20 秒，进待确认；微信置顶对话里点头；北京时间 09:30 / 15:00 / 19:00 三拍；每次只点名一件当前主事。

领域词见 [CONTEXT.md](CONTEXT.md)。决定见 [docs/adr](docs/adr)。上云步骤见 [docs/deploy.md](docs/deploy.md)。

```bash
python -m pip install -e ".[dev]"
python -m pytest tests -q
tracker status
```

短自述放到 `data/inbox/drop/`（或 `TRACKER_HOME/inbox/drop/`）。长会议转写不要放。
