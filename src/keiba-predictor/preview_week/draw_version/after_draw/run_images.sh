#!/bin/bash
# 1枚ずつ順に生成（2026-11-13）。キャラシートが誤って保存されたら（2048x1143）1回だけ作り直す。使い方: run_images.sh <promptsフォルダ> ID ID ...
export PYTHONIOENCODING=utf-8 PYTHONUTF8=1
P="$1"; shift
cd /c/Users/User/dev/move
for id in "$@"; do
  out=$(python -c "import json,sys;print(json.load(open(sys.argv[1],encoding='utf-8'))[0]['out'])" "$P/batch_$id.json")
  if [ -s "$out" ] && [ "$out" -nt "$P/batch_$id.json" ]; then echo "$id skip"; continue; fi
  for t in 1 2; do
    timeout 600 node .claude/skills/chatgpt-image-devtools-ss/scripts/cdp_chatgpt.mjs batch "$P/batch_$id.json" > /dev/null 2>&1
    out=$(python -c "import json,sys;print(json.load(open(sys.argv[1],encoding='utf-8'))[0]['out'])" "$P/batch_$id.json")
    sz=$(python -c "from PIL import Image;import sys;print('%dx%d'%Image.open(sys.argv[1]).size)" "$out" 2>/dev/null)
    echo "$(date +%H:%M) $id try$t $sz"
    if [ -n "$sz" ] && [ "$sz" != "2048x1143" ]; then break; fi
  done
done
echo DONE
