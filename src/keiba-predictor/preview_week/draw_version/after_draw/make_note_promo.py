# -*- coding: utf-8 -*-
"""note記事（枠順確定版）の告知投稿案（X 1本・Threads 1本／レース・各500字以内・画像なし）。雛形 20261115/research/build_note_promo_20261115.py。2026-11-14
公開URLは note.com/keiba_asumeshi_t/n/{記事キー}（開いて本文があるのを確認済み）。印・買い目は書かない。"""
import sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path("C:/Users/User/Desktop/競馬予想レポート")
U = "https://note.com/keiba_asumeshi_t/n/"
R = [
 dict(d="20261114", f="武蔵野S", key="nab49dd868383", tag="#武蔵野ステークス",
  head="🏇【武蔵野ステークス G3】11月14日（土）\n━━ 東京 ダ1600m／16頭 ━━",
  lead="note記事を公開しました。枠順確定版を、全16頭の独自指数つきで解説しています",
  concl=["・独自指数1位は、想定6番人気のルヴァレドクール", "・軸候補はヘニーガイスト、相手の筆頭はドンインザムード", "・軸にしないのはドンエレクトスとジェイパームス"],
  body=["・芝スタートは外枠が有利（勝ち馬10頭のうち6頭が外6〜8枠）", "・最終追い切りと100万回シミュレーション（3着内の確率）", "・全16頭の独自指数ランキングとひとこと"],
  note="※印と買い目は、土曜朝の実際のオッズを見てから出します"),
 dict(d="20261114", f="デイリー杯2歳S", key="n2b5b316992ed", tag="#デイリー杯2歳ステークス",
  head="🏇【デイリー杯2歳ステークス G2】11月14日（土）\n━━ 京都 芝1600m／13頭 ━━",
  lead="note記事を公開しました。枠順確定版を、全13頭の独自指数つきで解説しています",
  concl=["・3着内の確率は、キューティボンド63%・ブラッドバローズ60%の2強", "・軸候補はキューティボンド、相手の筆頭はブラッドバローズ", "・穴候補はスーサンコルティナ、軸にしないのはトップチェッカー"],
  body=["・前走で新馬・未勝利を勝った馬が7勝、前走で上がり最速の馬が8勝", "・最終追い切りと100万回シミュレーション", "・全13頭の独自指数ランキングとひとこと"],
  note="※印と買い目は、土曜朝の実際のオッズを見てから出します"),
 dict(d="20261115", f="エリザベス女王杯", key="n86a45a185a60", tag="#エリザベス女王杯",
  head="🏇【エリザベス女王杯 G1】11月15日（日）\n━━ 京都 芝2200m／18頭 ━━",
  lead="note記事を公開しました。枠順確定版を、全18頭の独自指数つきで解説しています",
  concl=["・軸候補は8枠16番のアクアヴァーナル、相手の筆頭はカムニャック", "・独自指数2位は、想定13番人気のヴーレヴー", "・軸にしないのは、175日ぶりの3歳2頭"],
  body=["・3着内30頭のうち9頭が前走アイルランドトロフィー組", "・先週の京都芝は外枠が有利、日曜は雨の予報", "・100万回シミュレーションと全18頭の独自指数ランキング"],
  note="※印と買い目は、実際のオッズを見てから出します"),
]
for r in R:
    url = U + r["key"]; tags = f"#競馬予想 #AI予想 #JRA {r['tag']}"
    t = f"{r['head']}\n{r['lead']}\n\n先に結論\n" + "\n".join(r["concl"]) + "\n\n記事の中身\n" + "\n".join(r["body"]) + f"\n\n▼全文はこちら\n{url}\n\n{r['note']}\n{tags}"
    assert len(t) <= 500, (r["f"], len(t))
    for bad in ("PDCA", "EV", "netkeiba", "◎", "○", "▲", "△", "🔥"): assert bad not in t, (r["f"], bad)
    assert t.count("http") == 1
    out = ROOT / r["d"] / "note" / f"note告知_SNS投稿案_{r['f']}.txt"
    out.write_text(f"{r['f']} note記事の告知 SNS投稿案（X 1本・Threads 1本・同文）2026-11-14\n※画像は添付しない（リンクカードのみ）\n{'='*40}\n\n【X】（{len(t)}字）\n{t}\n\n【Threads】（{len(t)}字）\n{t}\n", encoding="utf-8-sig")
    (out.with_suffix(".json")).write_text(__import__("json").dumps({"x": t, "threads": t}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(out.name, len(t), t.count("\n") + 1, "行", sum(1 for l in t.split("\n") if not l.strip()), "空行")
