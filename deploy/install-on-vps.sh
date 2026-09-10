#!/bin/sh
# 在云服务器上、本仓库根目录执行: sh deploy/install-on-vps.sh
set -e
ROOT="$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)"
HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"

python3 -m pip install -e "$ROOT"
mkdir -p "$ROOT/data/inbox/drop" "$ROOT/data/inbox/done"
mkdir -p "$HERMES_HOME/skills"
rm -rf "$HERMES_HOME/skills/shixiang"
cp -R "$ROOT/.hermes/skills/shixiang" "$HERMES_HOME/skills/shixiang"

if [ ! -f "$HERMES_HOME/USER.md" ]; then
  cp "$ROOT/deploy/USER.md" "$HERMES_HOME/USER.md"
else
  echo "已有 $HERMES_HOME/USER.md，未覆盖。"
fi

PROFILE="${SHELL_PROFILE:-$HOME/.bashrc}"
LINE="export TRACKER_HOME=$ROOT/data"
if ! grep -q "TRACKER_HOME" "$PROFILE" 2>/dev/null; then
  echo "$LINE" >> "$PROFILE"
fi
export TRACKER_HOME="$ROOT/data"

echo
echo "TRACKER_HOME=$TRACKER_HOME"
tracker status
echo
echo "接下来在微信那条 Hermes 对话里发："
echo "用 cron 按北京时间 09:30、15:00 跑 tracker beat morning 和 tracker beat afternoon，19:00 跑 tracker beat recap，结果原文投到微信 home，不要改写。"
echo "然后把这条对话置顶。发一句：当前主事"
