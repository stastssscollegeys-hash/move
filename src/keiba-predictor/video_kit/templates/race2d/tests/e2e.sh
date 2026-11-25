#!/bin/bash
# E2E の6本（_spec_race3d/docs/E2E_SCENARIOS.md）。Race3DHQ を実際に書き出して確かめる（2026-11-20 race3d-quality T-005）
# 使い方: bash tests/e2e.sh [出力フォルダ（既定＝一時フォルダ）]
# 書き出しの時間（秒）も出す（NFR-PERF-001：16秒の動画を縦・横それぞれ 180秒以内）
set -u
cd "$(dirname "$0")/.."
OUT="${1:-$(mktemp -d)}"; mkdir -p "$OUT"
FX=tests/fixtures
PASS=0; FAIL=0
ok() { echo "PASS $1"; PASS=$((PASS+1)); }
ng() { echo "FAIL $1: $2"; FAIL=$((FAIL+1)); }
dur() { ffprobe -v error -show_entries format=duration -of csv=p=0 "$1" 2>/dev/null; }
size() { ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=p=0 "$1" 2>/dev/null; }
frames() { node -e "console.log(require('./$1').frame.length)"; }
render() {  # $1=props $2=出力 → かかった秒を出す
  local t0=$(date +%s)
  npx remotion render src/index.ts Race3DHQ "$2" --props="$1" --gl=angle --log=error >"$2.log" 2>&1 || return 1
  echo $(( $(date +%s) - t0 ))
}
check_video() {  # $1=名前 $2=props $3=出力 $4=幅x高さ
  local sec; sec=$(render "$2" "$3") || { ng "$1" "書き出し失敗（$3.log）"; return; }
  local want; want=$(python3 -c "print(round($(frames "$2")/30,2))")
  local got; got=$(dur "$3")
  local wh; wh=$(size "$3")
  python3 -c "import sys; sys.exit(0 if abs($got-$want)<=0.05 else 1)" || { ng "$1" "長さ $got 秒（期待 ${want}）"; return; }
  [ "$wh" = "$4" ] || { ng "$1" "大きさ ${wh}（期待 ${4}）"; return; }
  [ "$sec" -le 180 ] || { ng "$1" "書き出し ${sec}秒（180秒を超えた）"; return; }
  ok "${1}（${got}秒・${wh}・書き出し ${sec}秒）"
}

check_video "E2E-01 縦・終わったレース" "$FX/result_tall.json" "$OUT/e2e01_tall.mp4" "1080,1652"
check_video "E2E-02 縦・展開予想" "$FX/forecast_tall.json" "$OUT/e2e02_forecast.mp4" "1080,1652"
check_video "E2E-03 横・終わったレース" "$FX/result_wide.json" "$OUT/e2e03_wide.mp4" "1620,1080"

# E2E-04/05：読めない素材・コマの無いデータで止まる（tests/render/hq.test.mjs と同じ中身を、ここでも1回）
node -e "const j=require('./$FX/result_tall.json'); j.horseFile='no_such_horse.glb'; require('fs').writeFileSync('$OUT/nohorse.json', JSON.stringify(j))"
if npx remotion still src/index.ts Race3DHQ "$OUT/x.png" --props="$OUT/nohorse.json" --frame=0 --gl=angle --log=error >"$OUT/e04.log" 2>&1; then ng "E2E-04" "止まらなかった"
elif grep -q "馬のモデルが読めません" "$OUT/e04.log"; then ok "E2E-04 素材が読めないと止まる"; else ng "E2E-04" "エラーの文が違う（$OUT/e04.log）"; fi
node -e "const j=require('./$FX/result_tall.json'); j.frame=[]; require('fs').writeFileSync('$OUT/empty.json', JSON.stringify(j))"
if npx remotion still src/index.ts Race3DHQ "$OUT/y.png" --props="$OUT/empty.json" --frame=0 --gl=angle --log=error >"$OUT/e05.log" 2>&1; then ng "E2E-05" "止まらなかった"
elif grep -q "frames.json にコマがありません" "$OUT/e05.log"; then ok "E2E-05 コマの無いデータで止まる"; else ng "E2E-05" "エラーの文が違う（$OUT/e05.log）"; fi

# E2E-06：最初のコマと最後のコマ
n=$(frames "$FX/result_tall.json")
for fr in 0 $((n-2)) $((n-1)); do
  if npx remotion still src/index.ts Race3DHQ "$OUT/e06_$fr.png" --props="$FX/result_tall.json" --frame=$fr --gl=angle --log=error >"$OUT/e06_$fr.log" 2>&1; then :; else ng "E2E-06" "コマ $fr が書き出せない"; fi
done
[ -f "$OUT/e06_0.png" ] && [ -f "$OUT/e06_$((n-1)).png" ] && ok "E2E-06 最初と最後のコマ（脚が止まることは Unit の TC-FR-HORSE-002）"

echo "---"; echo "PASS $PASS / FAIL $FAIL （出力: ${OUT}）"
[ "$FAIL" -eq 0 ]
