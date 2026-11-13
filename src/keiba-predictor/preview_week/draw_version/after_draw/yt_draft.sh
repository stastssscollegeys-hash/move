#!/bin/bash
# YouTube に1本下書き保存（playbook ⑤d の手順・2026-11-13）。公開はしない。使い方: yt_draft.sh <mp4> <文面の接頭辞(フルパス)> [サムネ]
set -e
export PYTHONIOENCODING=utf-8
cd /c/Users/User/dev/move/src/keiba-predictor/preview_week
U="${YT_TAB:-https://studio.youtube.com/channel/UCgNvrQOqNGFh50To1mPTU4w/videos/upload}"; MP4="$1"; P="$2"; TH="$3"
w(){ node -e "setTimeout(()=>{},$1)"; }
ev(){ timeout 60 node yt_studio_cdp.mjs eval $U "$1" | tail -1; }
ev "(function(){const d=document.querySelector('ytcp-uploads-dialog #title-textarea'); return d&&d.offsetParent!==null?'DIALOG_OPEN':'ok'})()"
ev "(function(){document.querySelector('button[aria-label=作成]').click(); return 1})()" >/dev/null; w 1500
ev "(function(){const it=[...document.querySelectorAll('*')].filter(e=>e.children.length<3 && /^動画をアップロード$/.test((e.innerText||'').trim())); it[it.length-1].click(); return 1})()" >/dev/null; w 2500
st=$(ev "[!!document.querySelector('ytcp-uploads-file-picker input[type=file]'), (()=>{const d=document.querySelector('ytcp-uploads-dialog #title-textarea'); return !!(d&&d.offsetParent)})()].join(',')")
echo "ファイル選択画面: $st"; [ "$st" = '"true,false"' ] || { echo "ファイル選択画面ではない→中止"; exit 1; }
timeout 120 node yt_studio_cdp.mjs files $U "ytcp-uploads-file-picker input[type=file]" "$MP4" >/dev/null; w 7000
ev "(document.querySelector('#title-textarea #textbox')||{}).innerText"
timeout 60 node yt_studio_cdp.mjs type $U "#title-textarea #textbox" "${P}_title.txt" | tail -c 120; echo
timeout 60 node yt_studio_cdp.mjs type $U "#description-textarea #textbox" "${P}_desc.txt" | tail -c 60; echo
[ -n "$TH" ] && timeout 120 node yt_studio_cdp.mjs files $U "input#file-loader" "$TH" >/dev/null
ev "(function(){document.querySelector('[name=VIDEO_MADE_FOR_KIDS_NOT_MFK]').click(); return 'kids-no'})()"
if [ -f "${P}_tags.txt" ]; then ev "(async()=>{document.querySelector('#toggle-button')?.click(); await new Promise(r=>setTimeout(r,1500)); return 1})()" >/dev/null; timeout 120 node yt_studio_cdp.mjs tags $U "${P}_tags.txt" | tail -1; fi
for i in $(seq 1 30); do s=$(ev "(document.querySelector('ytcp-uploads-dialog')?.innerText||'').match(/非公開として保存済み|アップロード中[^\n]*/)?.[0]||''"); echo "$s"; case "$s" in *保存済み*) break;; esac; w 10000; done
ev "(function(){const b=document.querySelector('#ytcp-uploads-dialog-close-button'); (b.querySelector('button')||b).click(); return 'closed'})()"; w 2500
