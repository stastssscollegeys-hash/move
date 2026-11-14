# -*- coding: utf-8 -*-
"""11/15（日）エリザベス女王杯の前日予想の投稿（20261114版 build_picks2 と同じ型）: 上に「印・買い目」、その下に「印の根拠／レースの注目点／注目の馬／短評」。
X=長文1本、Threads=4本（結論と買い目／◎○の根拠／残りの印の根拠／注目点・注目の馬・短評）。
前日夜版（11/14 17:35 の前日売最終オッズ・取得19:12）。印は web_picks.py（◎8%以上で最も割安／○▲5%以上で割安順／1〜3番人気は△）＋金曜に名指しした穴候補⑥は割安度1.0以上なので△で残す。
買い目は 11/14 夜の券種の検証（bet_type_by_race_test.py）で作り直した: 18頭・混戦（1番人気19.4%）・◎4番人気 → 本線＝単勝◎・馬単◎→○▲・3連単◎1着固定、押さえ＝ワイド◎-○・◎-▲。旧版（ワイド5点）は build_picks2_20261115_wide1930.py。
前売りのワイドは倍率が歪む＝期待回収率は書かない。当日朝に web_live → web_picks で作り直して差し替える。
数字の出どころ: モデル確率=web_live.py、間隔・コース実績=web_facts.py、近走=web_recent.py、過去10年=race_profile.py、追い切り・天気・取消=research/eri_info_20261114.md。"""
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
D = Path(__file__).resolve().parent.parent
TAG = "\n\n#エリザベス女王杯 #競馬予想 #AI予想"
FOOT = "※前日（11/14夕方）のオッズで計算した暫定版です。印と買い目は当日朝のオッズ・馬体重・馬場で作り直します"
NOTE1 = "※前日のオッズで計算した暫定版。当日朝に作り直します"

R = {}
R["eri"] = dict(
    head="🏇【エリザベス女王杯 G1】11月15日（日）\n━━ 京都 芝2200m／18頭／15:40発走 ━━",
    lead="前日予想です。◎は4番人気の⑨クイーンズウォーク。上位5頭が10倍以下の混戦なので、ワイドで広く買うのをやめ、⑨が勝つ形を本線にしました。雨予報なので、朝に作り直します。",
    marks="◎ ⑨クイーンズウォーク（4番人気 8.7倍）\n○ ⑦カムニャック（2番人気 4.3倍）\n▲ ⑪ジュウリョクピエロ（1番人気 4.1倍）\n△ ⑯アクアヴァーナル（3番人気 8.2倍）\n△ ⑥ヴーレヴー（8番人気 16.9倍）",
    buy="単勝 ⑨ 2,000円\n馬単 ⑨→⑦ 1,500円／⑨→⑪ 1,500円\n3連単 ⑨→⑦⑪→⑦⑪⑯⑥ 6点 1,800円\nワイド ⑦-⑨ 1,600円／⑨-⑪ 1,600円（計10,000円）\n・本線は⑨が勝つ形（単勝・馬単・3連単）。ワイドは押さえ\n・どれかが当たる確率は約25%",
    why=[
        "◎⑨クイーンズウォーク（C.デムーロ／中内田充正厩舎）\n▶ ヴィクトリアマイル2着・3着、金鯱賞3着の実績馬\n近走: 前走アイルランドトロフィー 3番人気8着\n根拠: 勝つ確率11.0%（市場9.2%）で割安さ最上位。最終追い切りは終い11秒前半で高評価\n懸念: 2200mと京都は初めて。3着内の見込みは31%",
        "○⑦カムニャック（川田将雅／友道康夫厩舎）\n▶ 前走アイルランドトロフィーを1番人気・上がり最速で勝利\n根拠: 勝つ確率19.5%（市場18.5%）。3着内の見込み46%\n懸念: 京都は2戦とも着外。2200mと道悪は初めて。最終追い切りは軽め",
        "▲⑪ジュウリョクピエロ（今村聖奈）\n▶ オークスを上がり最速で勝った3歳馬\n根拠: 勝つ確率20.0%で最上位。3着内の見込み47%\n懸念: 175日ぶり。併せ馬で遅れ、騎手も「少し物足りなさ」",
        "△⑯アクアヴァーナル（松山弘平）\n▶ 前走京都大賞典3着。金曜の軸候補\n懸念: 勝つ確率の見込み（8.0%）が市場（9.7%）より低い。京都大賞典組は過去10年3着内なし",
        "△⑥ヴーレヴー（吉田隼人）\n▶ 重のオールカマー3着。追い切りは今週一番の評価\n懸念: 想定44.8倍から16.9倍まで売れて、割安さはほぼなし",
    ],
    point="・過去10年: 1〜3番人気が7勝。3番人気は4勝・3着内70%、2番人気は0勝。3連単の中央値は約9.2万円で荒れる年が多い\n・日曜の京都は雨予報（15時の降水確率90%）。稍重〜重の見込み\n・金曜の見立てとの違い: 軸候補⑯は実際のオッズで計算し直すと割安でなく△。想定6番人気だった⑨が割安さ最上位で◎。穴候補⑥は売れたが△で残します\n・取消・騎手変更なし（11/14夜）",
    star="・⑨クイーンズウォーク: 単勝・馬単・3連単の1着に置く本線\n・⑥ヴーレヴー: 3連単の3着候補。雨が強まれば浮上",
    brief="混戦で割安なのは◎⑨。過去約25,000レースを調べ直すと、ワイドの総流しは当たりやすい代わりに回収率が低く、頭数の多い混戦では単勝・馬単・3連単のほうが良い結果でした。当たる頻度は下がります。期待回収率は朝のオッズで出します。",
)


def x_text(r):
    why = "\n\n".join(r["why"])
    return (f"{r['head']}\n\n{r['lead']}\n\n【印】\n{r['marks']}\n\n【買い目（暫定）】\n{r['buy']}\n\n─────\n\n【この印の根拠】\n{why}\n\n"
            f"【このレースの注目点】\n{r['point']}\n\n【注目の馬】\n{r['star']}\n\n【短評】\n{r['brief']}\n\n{FOOT}{TAG}")


def th_texts(r):
    t1 = f"{r['head']}\n\n{r['lead']}\n\n【印】\n{r['marks']}\n\n【買い目（暫定）】\n{r['buy']}\n\n{NOTE1}{TAG}"

    def mk(w):
        return "".join(re.match(r"[◎○▲△☆]*", x.lstrip()).group(0) for x in w)
    H = r["head"]
    t2 = f"{H}\n\n{mk(r['why'][:2]) or '印'}の根拠（近走・理由・懸念）\n\n" + "\n\n".join(r["why"][:2])
    t3 = f"{H}\n\n{mk(r['why'][2:]) or '残りの印'}の根拠（近走・理由・懸念）\n\n" + "\n\n".join(r["why"][2:])
    t4 = f"{H}\n\nこのレースの注目点・注目の馬・短評\n\n【このレースの注目点】\n{r['point']}\n\n【注目の馬】\n{r['star']}\n\n【短評】\n{r['brief']}"
    return [t1, t2, t3, t4]


out = {}
over = []
for k, r in R.items():
    x = x_text(r)
    th = th_texts(r)
    out[k] = dict(x=x, threads=th)
    for i, t in enumerate(th, 1):
        if len(t) > 500:
            over.append((k, f"T{i}", len(t)))
    assert all(t.startswith("🏇") for t in [x] + th)
    for bad in ("PDCA", "EV", "netkeiba", "sc[", "指数", "モデル", "蹄"):
        assert bad not in x, (k, bad)
    mk = set(re.findall(r"[①-⑱]", r["marks"])); by = set(re.findall(r"[①-⑱]", r["buy"].split("（計")[0]))
    assert mk == by, (k, mk ^ by)
print("X字数:", {k: len(v["x"]) for k, v in out.items()})
print("Threads字数:", {k: [len(t) for t in v["threads"]] for k, v in out.items()})
print("500字超:", over)
for k, r in R.items():
    pts = [int(a.replace(",", "")) for a in re.findall(r"([\d,]+)円", r["buy"].split("（計")[0])]
    tot = int(re.search(r"計([\d,]+)円", r["buy"]).group(1).replace(",", ""))
    print(k, "合計", sum(pts), "表記", tot, "OK" if sum(pts) == tot and all(p % 100 == 0 for p in pts) else "★不一致")
json.dump(out, open(D / "research" / "picks2_20261115.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
txt = "2026年11月15日（日）エリザベス女王杯 前日予想 SNS投稿案（X長文1本＋Threads4本）\n※前日売最終オッズ（11/14 17:35）での暫定版。当日朝に作り直して差し替える\n" + "=" * 40 + "\n"
for k, v in out.items():
    txt += f"\n\n######## {R[k]['head'].splitlines()[0]} ########\n\n【X】（{len(v['x'])}字）\n{v['x']}\n"
    for i, t in enumerate(v["threads"], 1):
        txt += f"\n【Threads {i}/4】（{len(t)}字）\n{t}\n"
(D / "20261115_エリザベス女王杯_前日予想_SNS投稿案.txt").write_text(txt, encoding="utf-8-sig")
print("保存:", D / "20261115_エリザベス女王杯_前日予想_SNS投稿案.txt")
