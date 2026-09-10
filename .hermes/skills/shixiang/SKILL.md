---
name: shixiang
description: 会后自述进账本、微信点头、只点名一件当前主事。
metadata:
  hermes:
    tags: [tracking, wechat, ledger]
    category: productivity
    requires_toolsets: [terminal]
---

# 事项跟踪

账本在 `tracker` 命令里，不在聊天记忆里。合同细节用 `tracker progress` 写进事项。

工作目录：事项跟踪仓库。环境变量 `TRACKER_HOME` 指向账本目录（默认仓库 `data/`）。

## When to Use

用户在谈事项、待确认、点头、丢掉、负责人、当前主事、下一步、复盘、进度、这周主事、管子、自述。

## Procedure

1. 先跑 `tracker status`。管子断了，回复第一句必须是「今天自述没收着。」
2. 用户消息像 `1`、`1丢`、`1 负责人小王`：跑 `tracker reply "<原文>"`。输出 `UNCLEAR` 就问一句，不准猜。
3. 人话点头（「合同记下，bug 给小王」）：`tracker pending` 对号。对得上就 `tracker reply` 或 `tracker add-pending` 后记下；对不上只问一句。
4. 有未拆自述：`tracker unsplit`，拆成待确认 `tracker add-pending "<标题>" --recap R00x`，可选 `--explodes YYYY-MM-DD`、`--leader`、`--owner`、`--next-task`。拆完 `tracker mark-split R00x`。不准把闲话写成事项。
5. 「现在最该干什么 / 当前主事」：只跑 `tracker main`，只点名那一件。
6. 「这周主事是 X」：找到事项 id，`tracker pin I00x`。
7. 进度补一句：写到对应事项 `tracker progress I00x "<原话>"`，不要写进记忆。
8. 等待：`tracker wait I00x --who 谁 --what 什么`。任务做完事项没完：`tracker task-done I00x`。只有用户明确说结束：`tracker end I00x`。
9. 起草给手下的话可以写出来，由用户自己发。不要替用户发消息给任何人。

白天两拍和 19:00 复盘由 cron 跑 `tracker beat`，不要另外写小作文。

## 点头格式

- `1` 记下第 1 件
- `1丢` 丢掉
- `1 负责人小王` 记下并写负责人
- 人话可以，对不上就问

## 当前主事顺序（已写死，不准改）

今天会爆 → 这周置顶 → 待确认 → 等待过久该催 → 已点头的领导交办 → 最久没动。

## 记忆里只许有

手下名字、09:30 / 15:00 / 19:00 这三拍、用户讨厌怎么被唠叨。事项内容不进记忆。

## Pitfalls

- 用聊天记忆当列表，账本会和你说的不一致。
- 小王口头说完就 `end`。只有用户能结束事项。
- 回复里贴纪要、分析、鼓励。白天只处理待确认、今天会爆、管子。
- 管子失败却装作没会。

## Verification

`tracker status` 与回复一致；点头后 `tracker pending` 少了那一件；问当前主事时回复里只有一件。
