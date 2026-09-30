#!/bin/zsh
# launchd から呼ばれる。Macが起きている間、2時間ごとに新着を確認して公開する。
cd "$(dirname "$0")"
export PATH="/usr/local/bin:/usr/bin:/bin"
mkdir -p logs
{
  echo "=== $(date '+%F %T')"
  /usr/bin/python3 podcast.py update --limit 10 --keep 30
} >> logs/update.log 2>&1
tail -n 2000 logs/update.log > logs/update.tmp && mv logs/update.tmp logs/update.log
