#!/bin/bash
# 1枚生成→40秒待って最新画像を取り直す（添付画像の取り違え対策）→添付と同一でないか md5 で確認。使い方: gen1.sh <batch.json> <out.png> <添付...>
cd /c/Users/User/dev/move
B="$1"; O="$2"; shift 2
rm -f "$O"
timeout 400 node .claude/skills/chatgpt-image-devtools-ss/scripts/cdp_chatgpt.mjs batch "$B" >/dev/null 2>&1
node -e "setTimeout(()=>{},40000)"
timeout 200 node .claude/skills/chatgpt-image-devtools-ss/scripts/cdp_chatgpt.mjs grab "$O" 2>&1 | tail -1
m=$(md5sum "$O" | cut -c1-32); for a in "$@"; do [ "$(md5sum "$a" | cut -c1-32)" = "$m" ] && echo "★添付と同じ画像: $a"; done; echo done
