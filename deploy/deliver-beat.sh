#!/bin/sh
# 由 Hermes cron 投递更好：在微信里对助手说
# 「用 cron 在北京时间 09:30/15:00/19:00 跑 tracker beat，投到微信 home」。
# 若 cron 直接跑本脚本，把 stdout 交给 hermes 的投递命令。
set -e
WHICH="${1:?morning|afternoon|recap}"
ROOT="${TRACKER_HOME:-/opt/shixiang/data}"
export TRACKER_HOME="$ROOT"
tracker beat "$WHICH"
