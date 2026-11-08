# -*- coding: utf-8 -*-
"""注目レース5本の画像（1レース1枚・1080x1350・HTML→PNG）。数字は投稿案と同じ（11/8朝10時半のオッズ）。"""
import pathlib
import sys

from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8")
D = pathlib.Path(__file__).parent
MASCOT = (D / "asumeshi_front.png").as_uri()
WCOL = {1: ("#fff", "#222", "#999"), 2: ("#222", "#fff", "#222"), 3: ("#e8242b", "#fff", "#e8242b"), 4: ("#1f5fd0", "#fff", "#1f5fd0"),
        5: ("#ffe000", "#222", "#c9b100"), 6: ("#1fa04a", "#fff", "#1fa04a"), 7: ("#ff8a00", "#fff", "#ff8a00"), 8: ("#ff6fa8", "#fff", "#ff6fa8")}


def waku(u, n):
    if n <= 8:
        return u
    s = 16 - n
    return u if u <= s else s + (u - s + 1) // 2


def chip(u, n, size=60):
    bg, fg, bd = WCOL[waku(u, n)]
    return f'<span class="chip" style="width:{size}px;height:{size}px;background:{bg};color:{fg};border:3px solid {bd};font-size:{int(size*.6)}px">{u}</span>'


RACES = {
    "fukushima7": dict(title="福島7R 3歳上1勝クラス", sub="芝1200m（稍重）／16頭／13:10発走", n=16,
                       th=dict(bg="#0b3450", ray="#124a6e", band="#0f7fb0", glow="255,216,0", acc="#ffd800"),
                       small="割安No.1は6番人気", big="◎①の短縮！", pill="3着内の見込み最上位は1番人気⑨（48%）",
                       rows=[("◎", 1, "カモメガトンダ", "小沢大仁", "6番人気 11.2倍", 28, "未勝利を14番人気で勝った逃げ馬。マイルから400m短縮", "main"),
                             ("○", 10, "ベルセクレト", "田山旺佑", "5番人気 9.9倍", 28, "芝1200mの未勝利を上がり最速で勝利", "row"),
                             ("▲", 4, "モズイージス", "永島まなみ", "8番人気 16.5倍", 18, "ダートから芝に戻る", "row"),
                             ("△", 9, "ベルファスト", "河原田菜々", "1番人気 3.8倍", 48, "芝1200mで6戦3着内5", "tri"),
                             ("△", 8, "ルシェロアズーリ", "小林美駒", "2番人気 6.6倍", 32, "福島芝1200mで3着内3", "tri"),
                             ("△", 12, "エバーラスト", "石神深道", "3番人気 7.1倍", 31, "前走は1番人気で7着", "tri")],
                       buy=[("ワイド", "⑨-⑩", "3,300円"), ("ワイド", "①-⑨", "1,500円"), ("ワイド", "④-⑨", "1,500円"), ("ワイド", "①-⑧", "1,100円"),
                            ("ワイド", "①-⑫", "1,000円"), ("ワイド", "①-⑩", "700円"), ("ワイド", "①-④", "500円"), ("ワイド", "④-⑩", "400円")],
                       total="10,000円", hit="約42%", ret="当たれば約2.1倍以上", bubble="1番人気⑨を<br>相手の中心に！"),
    "fukushima8": dict(title="福島8R 3歳上1勝クラス", sub="ダ1150m（稍重）／16頭／13:40発走", n=16,
                       th=dict(bg="#3a2108", ray="#512e0c", band="#b8570f", glow="255,216,0", acc="#ffd800"),
                       small="前有利のダート短距離", big="◎は②！", pill="逃げの3着内60%のコース・先行馬同士も厚く",
                       rows=[("◎", 2, "ダイイズキャスト", "河原田菜々", "2番人気 8.4倍", 33, "芝からダートへ。このコースは4月に3着", "main"),
                             ("○", 10, "アイスメルティング", "丸山元気", "10番人気 16.5倍", 18, "ダ1200mで2戦1勝。約9か月ぶり", "row"),
                             ("▲", 11, "ライトニングロッド", "横山琉人", "8番人気 15.1倍", 19, "函館ダ1000mを逃げ切り", "row"),
                             ("△", 14, "トゥインクルアップ", "小林美駒", "1番人気 3.6倍", 49, "前走は2番手から3着", "tri"),
                             ("△", 6, "オプティモ", "丹内祐次", "3番人気 8.6倍", 29, "ダ1200mで4・5着", "tri")],
                       buy=[("ワイド", "②-⑭", "2,700円"), ("ワイド", "⑩-⑭", "2,000円"), ("ワイド", "⑪-⑭", "1,800円"), ("ワイド", "②-⑥", "1,300円"),
                            ("ワイド", "⑩-⑪", "1,200円"), ("ワイド", "②-⑩", "500円"), ("ワイド", "②-⑪", "500円")],
                       total="10,000円", hit="約37%", ret="当たれば約2.5倍以上", bubble="前に行く馬の<br>組を厚めに！"),
    "tokyo9": dict(title="東京9R 百日草特別", sub="2歳1勝クラス 芝2000m（良）／9頭／14:20発走", n=9,
                   th=dict(bg="#0a3a2c", ray="#0f4d3b", band="#0d6b4a", glow="255,216,0", acc="#ffd800"),
                   small="9頭立て。割安No.1は", big="5番人気⑨", pill="軸は3着内72%の③・馬連3点",
                   rows=[("◎", 9, "ニシノフランケン", "横山武史", "5番人気 9.5倍", 38, "3戦すべて上がり1〜2位の末脚", "main"),
                         ("○", 3, "テキサス", "T.マーカンド", "1番人気 2.8倍", 72, "未勝利を2番手から上がり最速で勝利", "row"),
                         ("▲", 7, "エスクアドラ", "A.プーシャン", "3番人気 4.9倍", 51, "新馬を後方から上がり最速で勝利", "row"),
                         ("△", 6, "ヴァンドレスト", "ルメール", "2番人気 2.8倍", 63, "新馬勝ち。人気ほどの勝つ確率はない見立て", "tri")],
                   buy=[("馬連", "③-⑥", "6,000円"), ("馬連", "③-⑨", "2,100円"), ("馬連", "③-⑦", "1,900円")], total="10,000円",
                   hit="約40%", ret="当たれば約2.8倍以上", bubble="③軸の馬連<br>3点だよ！"),
    "tokyo12": dict(title="東京12R 3歳上2勝クラス", sub="芝1400m（良）／12頭／16:10発走", n=12,
                    th=dict(bg="#14194a", ray="#1d2468", band="#c41230", glow="255,216,0", acc="#ffd800"),
                    small="1番人気③は単勝2.0倍。割安は", big="2番人気④", pill="3着内の見込み ③74%・④56%",
                    rows=[("◎", 4, "デンプシー", "戸崎圭太", "2番人気 4.4倍", 56, "芝1200mで1・2・5・4着と堅実。200m延長", "main"),
                          ("○", 8, "ラミアメンテ", "岩田望来", "4番人気 9.6倍", 31, "1勝クラスを勝っての昇級。約4か月ぶり", "row"),
                          ("▲", 3, "スペルーチェ", "ルメール", "1番人気 2.0倍", 74, "前走は同じコースのtvk賞で3着", "row"),
                          ("△", 5, "インプロペリア", "A.プーシャン", "3番人気 6.9倍", 34, "東京芝1400mで1戦1勝", "tri")],
                    buy=[("ワイド", "③-④", "5,300円"), ("ワイド", "④-⑤", "3,200円"), ("ワイド", "④-⑧", "1,500円")], total="10,000円",
                    hit="約50%", ret="当たれば約1.7倍以上", bubble="④から<br>ワイド3点！"),
    "fukushima11": dict(title="福島11R みちのくS", sub="OP 芝1200m（稍重）／16頭／15:20発走", n=16,
                        th=dict(bg="#2c1650", ray="#3d2070", band="#7a2bbd", glow="255,200,0", acc="#ffd800"),
                        small="混戦のオープン。割安No.1は", big="6番人気⑭", pill="1〜3番人気も相手に・期待回収率0.93の参考",
                        rows=[("◎", 14, "マーブルパレス", "高杉吏麒", "6番人気 9.8倍", 29, "函館の芝1200mで2連勝。芝1200mは6戦4勝", "main"),
                              ("○", 11, "アスクワンタイム", "丸田恭介", "7番人気 12.5倍", 23, "近2走は上がり最速", "row"),
                              ("▲", 7, "ベイビーキッス", "菊沢一樹", "4番人気 7.7倍", 30, "前走北陸Sを逃げ切り", "row"),
                              ("△", 8, "ギリーズボール", "杉原誠人", "1番人気 5.9倍", 36, "フィリーズレビュー勝ち。約6か月ぶり", "tri"),
                              ("△", 2, "インブロリオ", "吉田隼人", "2番人気 6.1倍", 33, "芝1200mで2連勝中", "tri"),
                              ("△", 5, "アスティスプマンテ", "小沢大仁", "3番人気 7.7倍", 28, "福島芝1200mは3戦すべて3着内", "tri")],
                        buy=[("ワイド", "②-⑭", "1,900円"), ("ワイド", "⑤-⑭", "1,700円"), ("ワイド", "⑦-⑭", "1,400円"), ("ワイド", "⑦-⑧", "1,300円"),
                             ("ワイド", "⑧-⑭", "1,300円"), ("ワイド", "⑧-⑪", "1,100円"), ("ワイド", "⑦-⑪", "700円"), ("ワイド", "⑪-⑭", "600円")],
                        total="10,000円", hit="約39%", ret="当たれば約1.7倍以上", bubble="◎⑭から<br>人気馬へ流す！"),
}

CSS = """
*{box-sizing:border-box;margin:0;padding:0}
body{width:1080px;height:1350px;font-family:'Noto Sans JP','Yu Gothic UI','Meiryo',sans-serif;overflow:hidden;position:relative;font-weight:700;color:#fff}
.chip{display:inline-flex;align-items:center;justify-content:center;border-radius:14px;font-weight:900;flex:none}
.mark{display:inline-flex;align-items:center;justify-content:center;border-radius:50%;font-weight:900;flex:none;color:#fff}
"""


def page(r):
    t, n = r["th"], r["n"]
    many = len(r["rows"]) >= 5
    six = len(r["rows"]) >= 6
    rows_html = ""
    for mk, u, nm, jk, po, t3, cm, kind in r["rows"]:
        mkcol = {"◎": "#e60012", "○": "#1f5fd0", "▲": "#1f5fd0", "△": "#8a8a8a", "×": "#444"}[mk]
        if kind == "main":
            rows_html += f"""<div class="main"><span class="mark" style="width:{88 if many else 104}px;height:{88 if many else 104}px;font-size:{64 if many else 76}px;background:{mkcol}">{mk}</span>{chip(u, n, 80 if many else 96)}
<div class="mb"><div class="nm" style="font-size:{(54 if many else 66) if len(nm)<=7 else (48 if many else 56)}px;white-space:nowrap">{nm}</div><div class="cm" style="font-size:{24 if many else 28}px">{jk}騎手・{po}</div><div class="cm2" style="font-size:{21 if many else 24}px">{cm}</div></div>
<div class="t3"><div class="bar"><i style="width:{t3}%"></i></div><b>{t3}%</b><span>3着内</span></div></div>"""
        elif six and kind == "tri":   # 印が6頭のときは△を1行に詰める（11/8追加）
            rows_html += f"""<div class="row c"><span class="mark" style="width:46px;height:46px;font-size:32px;background:{mkcol}">{mk}</span>{chip(u, n, 46)}
<div class="mb"><div class="nm" style="font-size:{30 if len(nm)<=8 else 27}px;white-space:nowrap">{nm}<small>{jk}・{po}</small></div></div>
<div class="t3 s"><b>{t3}%</b></div></div>"""
        else:
            cls = "row no" if kind == "no" else "row"
            rows_html += f"""<div class="{cls}"><span class="mark" style="width:60px;height:60px;font-size:42px;background:{mkcol}">{mk}</span>{chip(u, n, 60)}
<div class="mb"><div class="nm" style="font-size:{36 if len(nm)<=8 else 32}px;white-space:nowrap">{nm}<small>{jk}・{po}</small></div><div class="cm2">{cm}</div></div>
<div class="t3 s"><div class="bar"><i style="width:{t3}%"></i></div><b>{t3}%</b></div></div>"""
    buy = "".join(f'<div class="tk"><span>{k}</span><b>{c}</b><em>{a}</em></div>' for k, c, a in r["buy"])
    rowmax = (84 if six else 100) if many else 140
    panelh = (540 if len(r['buy']) > 6 and not six else 572) if len(r['buy']) > 4 else 590
    bigfs = 128 if len(r["big"]) <= 5 else (112 if len(r["big"]) <= 7 else 96)
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>{CSS}
body{{background:{t['bg']}}}
.rays{{position:absolute;inset:0;background:repeating-conic-gradient(from 0deg at 50% 26%,{t['ray']} 0deg 7deg,{t['bg']} 7deg 14deg)}}
.glow{{position:absolute;left:-100px;right:-100px;top:120px;height:430px;background:radial-gradient(ellipse at 50% 45%,rgba({t['glow']},.5),rgba({t['glow']},0) 62%)}}
.top{{position:absolute;left:0;right:0;top:0;height:140px;background:{t['band']};border-bottom:8px solid {t['acc']};padding:14px 40px;text-align:center}}
.top .a{{font-size:64px;font-weight:900;letter-spacing:2px;text-shadow:4px 4px 0 rgba(0,0,0,.35);line-height:1.1}}
.top .b{{font-size:27px;font-weight:700;margin-top:4px;color:#fff}}
.date{{position:absolute;left:26px;top:152px;background:{t['acc']};color:#111;font-size:26px;font-weight:900;padding:2px 16px;border-radius:10px}}
.hook{{position:absolute;left:0;right:0;top:154px;text-align:center}}
.hook .s1{{font-size:42px;font-weight:900;text-shadow:3px 3px 0 #000}}
.hook .big{{font-size:{bigfs}px;font-weight:900;line-height:1.05;color:#ffe000;-webkit-text-stroke:12px #111;paint-order:stroke fill;text-shadow:8px 8px 0 #e60012;letter-spacing:-3px}}
.hook .s2{{font-size:32px;font-weight:900;margin-top:2px}} .hook .s2 span{{background:#e60012;padding:3px 16px;border-radius:8px;text-shadow:2px 2px 0 #000}}
.panel{{position:absolute;left:34px;right:34px;top:420px;height:{panelh}px;display:flex;flex-direction:column;gap:{8 if six else 12}px}}
.main{{background:#fff;color:#111;border-radius:26px;border:9px solid {t['acc']};padding:{6 if many else 12}px 24px;display:flex;align-items:center;gap:20px;box-shadow:0 8px 0 #000;flex:none}}
.main .mb{{flex:1;min-width:0}} .main .cm{{font-size:28px;color:#c4000f;font-weight:900;margin-top:2px}} .main .cm2{{font-size:24px;color:#333;margin-top:2px}}
.row{{background:rgba(255,255,255,.96);color:#111;border-radius:18px;padding:8px 18px;display:flex;align-items:center;gap:14px;box-shadow:0 5px 0 rgba(0,0,0,.5);flex:1;max-height:{rowmax}px}}
.row.no{{background:rgba(220,220,220,.93);color:#444}}
.panel.tight .row{{padding:2px 18px}} .panel.tight .main{{padding:2px 24px}} .panel.tight{{gap:8px}}
.row.c{{flex:none;padding:3px 18px;max-height:58px}} .row.c .nm small{{font-size:20px}}
.buy.dense .tk{{font-size:20px;padding:0}} .buy.dense .tk b{{font-size:23px}} .buy.dense .tk span{{font-size:17px}} .buy.dense h3{{font-size:27px;margin-bottom:0}} .buy.dense .stat{{margin-top:2px}} .buy.dense .stat b{{font-size:42px}}
.row .mb{{flex:1;min-width:0}} .row .nm small{{font-size:22px;color:#555;margin-left:12px;font-weight:700}} .row .cm2{{font-size:22px;color:#333;margin-top:1px}}
.t3{{width:170px;text-align:center;flex:none}} .t3.s{{width:130px}}
.t3 .bar{{height:14px;background:#dde3f5;border-radius:7px;overflow:hidden}} .t3 .bar i{{display:block;height:100%;background:#1f5fd0}}
.t3 b{{font-size:34px;display:block;line-height:1.15;color:#111}} .t3.s b{{font-size:28px}} .t3 span{{font-size:18px;color:#555}}
.bottom{{position:absolute;left:0;right:0;bottom:0;height:300px;background:linear-gradient(rgba(0,0,0,0),rgba(0,0,0,.55) 35%)}}
.buy{{position:absolute;left:34px;bottom:56px;width:640px;background:{t['acc']};color:#111;border-radius:22px;border:5px solid #000;box-shadow:0 6px 0 #e60012;padding:12px 20px}}
.buy h3{{font-size:30px;font-weight:900;margin-bottom:4px}}
.tks{{display:grid;grid-template-columns:1fr 1fr;column-gap:22px}}
.tk{{display:flex;align-items:baseline;gap:6px;font-size:23px;border-bottom:2px dashed rgba(0,0,0,.35);padding:2px 0}} .tk span{{font-size:19px;color:#444}} .tk b{{font-size:27px;font-weight:900}} .tk em{{font-style:normal;margin-left:auto;font-weight:900}}
.stat{{display:flex;align-items:baseline;gap:14px;margin-top:6px}} .stat b{{font-size:48px;color:#c4000f;font-weight:900}} .stat span{{font-size:24px;font-weight:900}}
.mascot{{position:absolute;right:30px;bottom:48px;height:236px}}
.bubble{{position:absolute;right:196px;bottom:96px;background:#fff;color:#111;border-radius:22px;padding:10px 14px;font-size:23px;font-weight:900;line-height:1.25;border:5px solid {t['acc']};width:200px}}
.bubble:after{{content:"";position:absolute;right:-28px;bottom:22px;border:14px solid transparent;border-left:28px solid {t['acc']}}}
.foot{{position:absolute;left:0;right:0;bottom:0;height:42px;background:rgba(0,0,0,.6);color:#cfd9ff;font-size:19px;display:flex;align-items:center;justify-content:space-between;padding:0 24px}}
.foot b{{color:{t['acc']};font-size:24px}}
</style></head><body>
<div class="rays"></div><div class="glow"></div>
<div class="top"><div class="a">{r['title']}</div><div class="b">{r['sub']}</div></div>
<div class="date">11/8（日）</div>
<div class="hook"><div class="s1">{r['small']}</div><div class="big">{r['big']}</div><div class="s2"><span>{r['pill']}</span></div></div>
<div class="panel{' tight' if len(r['buy']) > 6 and not six else ''}">{rows_html}</div>
<div class="bottom"></div>
<div class="buy{' dense' if len(r['buy']) > 6 else ''}"><h3>買い目（合計{r['total']}）</h3><div class="tks">{buy}</div><div class="stat"><b>的中 {r['hit']}</b><span>{r['ret']}</span></div></div>
<div class="bubble">{r['bubble']}</div><img class="mascot" src="{MASCOT}">
<div class="foot"><span>※11/8朝10時半のオッズで計算。発走までに変わります</span><b>アスメシ競馬予想</b></div>
</body></html>"""


def main():
    with sync_playwright() as p:
        b = p.chromium.launch(channel="chrome")
        for k, r in RACES.items():
            f = D / f"_{k}.html"
            f.write_text(page(r), encoding="utf-8")
            pg = b.new_page(viewport={"width": 1080, "height": 1350})
            pg.goto(f.as_uri())
            pg.wait_for_timeout(700)
            pg.screenshot(path=str(D / f"race_{k}.png"))
            pg.close()
            f.unlink()
        b.close()
    print("ok")


main()
