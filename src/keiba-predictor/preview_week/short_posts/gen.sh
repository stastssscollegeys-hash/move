#!/bin/bash
# 15枚を1枚ずつ生成。正方形でない（添付がそのまま保存された）ときは作り直す
H="C:/Users/User/Desktop/競馬予想レポート/20261122/short_posts"; cd /c/Users/User/dev/move
for k in fk_h1 fk_h2 fk_h3 fk_d1 fk_d2 mc_h1 mc_h2 mc_h3 mc_d1 mc_d2 ts_h1 ts_h2 ts_h3 ts_d1 ts_d2; do
  for try in 1 2 3; do rm -f "$H/images/$k.png"; timeout 420 node .claude/skills/chatgpt-image-devtools-ss/scripts/cdp_chatgpt.mjs batch "$H/prompts/batch_$k.json" > /dev/null 2>&1
    w=$(ffprobe -v error -show_entries stream=width -of csv=p=0 "$H/images/$k.png" 2>/dev/null); h=$(ffprobe -v error -show_entries stream=height -of csv=p=0 "$H/images/$k.png" 2>/dev/null)
    [ -n "$w" ] && [ "$w" = "$h" ] && break; done
  echo "$(date +%H:%M) $k ${w}x${h}" >> "$H/img_log.txt"; done
echo done >> "$H/img_log.txt"
