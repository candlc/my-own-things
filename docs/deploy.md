# 部署到云服务器（第一版）

目标：微信置顶对话能点头，三拍会来，20 秒自述能进待确认。

## 1. 云上装账本

```bash
sudo mkdir -p /opt/shixiang
sudo chown "$USER" /opt/shixiang
git clone <本仓库> /opt/shixiang
cd /opt/shixiang
python3 -m pip install -e .
export TRACKER_HOME=/opt/shixiang/data
echo 'export TRACKER_HOME=/opt/shixiang/data' >> ~/.bashrc
tracker status
```

把本仓库的 `.hermes/skills/shixiang` 拷进 Hermes 技能目录，或把仓库当 Hermes 工作目录并 `hermes skills trust`。

```bash
mkdir -p ~/.hermes/skills
cp -R /opt/shixiang/.hermes/skills/shixiang ~/.hermes/skills/shixiang
cp /opt/shixiang/deploy/USER.md ~/.hermes/USER.md
```

记忆里只留 `USER.md` 那些：名字、三拍、讨厌什么。不要把事项粘进去。

## 2. Hermes + 微信

按官方文档：<https://hermes-agent.nousresearch.com/docs/user-guide/messaging/weixin>

```bash
hermes gateway setup    # 选 Weixin，扫码
# ~/.hermes/.env 里填 WEIXIN_ACCOUNT_ID
# 只让你自己发：
# WEIXIN_DM_POLICY=allowlist
# WEIXIN_ALLOWED_USERS=<你的微信用户 id>
# 三拍要打进同一条对话：
# WEIXIN_HOME_CHANNEL=<这条对话的 chat_id>
hermes gateway          # 长期跑
```

在微信里置顶这个机器人对话。点开只处理盒子。

在该对话里对 Hermes 说（一次即可）：

> 用 cron 按北京时间 09:30、15:00 跑 `tracker beat morning` / `tracker beat afternoon`，19:00 跑 `tracker beat recap`，结果投到微信 home。脚本自己会 pull。不要用模型发挥，原文发出去。

若 Hermes cron 不好使，用 `deploy/crontab.example`，再自己把 stdout 送到微信。

## 3. 听记短自述怎么进账本

没有稳定的听记官方拉取接口。第一版管子是目录：

`/opt/shixiang/data/inbox/drop/`

- 只放**会后自述**（大约两分钟以内）。长会议全文不要丢进来，丢了也会被跳过。
- 纯文本 `.txt`，或 `{"text":"...","duration_seconds":25,"recorded_at":"2026-09-11T12:01:00+08:00"}` 的 `.json`。
- `tracker pull` / `tracker beat` 会收走并归档到 `inbox/done/`。
- drop 目录读失败 → 管子断了，三拍第一句「今天自述没收着。」
- 目录在、里面是空的 → 管子是通的（今天可能没会）。

外网电脑能开听记时：把短转写另存到这台云的 drop（scp、同步盘、或开一个只写这个目录的共享）。不要把公司钉钉账号密码写进仓库。

应急：在微信里把自述原文发给助手，助手跑 `tracker ingest "..."` 再拆待确认。这是补洞，不是散会那 20 秒的主路径。

## 4. 上线前在单位用手机试一次

用流量打开微信这条对话，发「当前主事」。能回才算工位/外勤回看得通。

## 5. 助手日常命令（你不必记，Hermes 会跑）

```text
tracker pending
tracker reply "1"
tracker reply "1丢"
tracker main
tracker beat recap
tracker progress I001 "电话打了，说法务周五回"
```
