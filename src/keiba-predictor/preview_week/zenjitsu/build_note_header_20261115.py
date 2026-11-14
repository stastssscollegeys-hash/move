# -*- coding: utf-8 -*-
"""エリザベス女王杯 前日予想のnoteヘッダー（1280x670・HTML→PNG）。数字は投稿案と同じ。"""
import pathlib, sys
from playwright.sync_api import sync_playwright
sys.stdout.reconfigure(encoding="utf-8")
D = pathlib.Path(__file__).parent
MASCOT = (D / "asumeshi_front.png").as_uri()
HTML = f"""<!doctype html><html><head><meta charset="utf-8"><style>
*{{margin:0;padding:0;box-sizing:border-box}} body{{width:1280px;height:670px;overflow:hidden;font-family:"Noto Sans JP","Yu Gothic","Meiryo",sans-serif;color:#fff;background:#2a1146;position:relative}}
.rays{{position:absolute;inset:0;background:repeating-conic-gradient(from 0deg at 42% 55%,#3b1a63 0deg 7deg,#2a1146 7deg 14deg)}}
.glow{{position:absolute;left:0;right:200px;top:120px;height:420px;background:radial-gradient(ellipse at 45% 50%,rgba(255,205,90,.45),rgba(255,205,90,0) 62%)}}
.top{{position:absolute;left:0;right:0;top:0;height:92px;background:#6a2fa0;border-bottom:7px solid #ffd34d;display:flex;align-items:center;justify-content:center;font-size:44px;font-weight:900;letter-spacing:3px;text-shadow:3px 3px 0 rgba(0,0,0,.4)}}
.tag{{position:absolute;left:40px;top:116px;background:#ffd34d;color:#111;font-size:30px;font-weight:900;padding:4px 20px;border-radius:10px}}
.s1{{position:absolute;left:250px;top:118px;font-size:36px;font-weight:900;text-shadow:3px 3px 0 #000}}
.big{{position:absolute;left:36px;top:168px;font-size:150px;font-weight:900;line-height:1.05;color:#ffe000;-webkit-text-stroke:14px #111;paint-order:stroke fill;text-shadow:9px 9px 0 #e60012;letter-spacing:-4px;white-space:nowrap}}
.nm{{position:absolute;left:44px;top:352px;font-size:76px;font-weight:900;text-shadow:5px 5px 0 #000;white-space:nowrap}}
.pill{{position:absolute;left:44px;top:462px;background:#e60012;font-size:36px;font-weight:900;padding:6px 22px;border-radius:10px;text-shadow:2px 2px 0 #000}}
.sub{{position:absolute;left:44px;top:536px;font-size:30px;font-weight:900;text-shadow:2px 2px 0 #000}}
.mascot{{position:absolute;right:36px;bottom:60px;height:400px}}
.foot{{position:absolute;left:0;right:0;bottom:0;height:52px;background:rgba(0,0,0,.7);display:flex;align-items:center;justify-content:space-between;padding:0 30px;font-size:22px;color:#cfd9ff}} .foot b{{color:#ffd34d;font-size:30px}}
</style></head><body><div class="rays"></div><div class="glow"></div>
<div class="top">エリザベス女王杯（G1）11/15（日）京都 芝2200m</div>
<div class="tag">前日予想</div><div class="s1">5頭が10倍以下の混戦・日曜は雨予報</div>
<div class="big">◎は4番人気⑨</div>
<div class="nm">クイーンズウォーク</div>
<div class="pill">ワイド5点・◎から流し＋保険の⑦-⑪</div>
<div class="sub">金曜の軸候補⑯を△に下げた理由も解説</div>
<img class="mascot" src="{MASCOT}">
<div class="foot"><span>※前日（11/14夕方）のオッズで計算した暫定版。当日朝に作り直します</span><b>アスメシ競馬予想</b></div>
</body></html>"""
with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome"); f = D / "_hdr.html"; f.write_text(HTML, encoding="utf-8")
    pg = b.new_page(viewport={"width": 1280, "height": 670}); pg.goto(f.as_uri()); pg.wait_for_timeout(700)
    pg.screenshot(path=str(D / "note_header_eri_zenjitsu.png")); b.close(); f.unlink()
print("ok")
