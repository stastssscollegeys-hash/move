# -*- coding: utf-8 -*-
"""
ensemble_sprinters_20260926.py — スプリンターズS インフルエンサー合算 v2
=========================================================================
2026-09-26に4並列で収集したシグナルを、SKILL.md「インフルエンサー合算 v2」の
ソース別重みで20因子指数に合算する。

⚠ 独自指数版（score20_20260925.json / kaime_sprinters_v2.json）は上書きしない。
  合算版は別ファイル ensemble_sprinters_20260926.json に出す。

シグナル種別: honmei(+3) / ana(+2) / posi(+1・対抗相当) / nega(-2・消し) / oikiri1(追い切り1位・最低保証の判定のみ)
最低保証: 本命 or 追い切り1位 が2ソース以上重なった馬は最低△。
"""
from __future__ import annotations
import json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8")
from ensemble_v2 import ensemble, print_rows, weight

B = Path.home() / "Desktop" / "競馬予想レポート"
SC = json.loads((B / "20260926" / "research" / "score20_20260925.json").read_text(encoding="utf-8"))["スプリンターズS"]
K = json.loads((B / "20260926" / "research" / "kaime_sprinters.json").read_text(encoding="utf-8"))
NAME = {int(a): b for a, b in K["name"].items()}
N2U = {v: k for k, v in NAME.items()}
SC20 = {h["uma"]: h["final170"] for h in SC["horses"]}
RANK = {h["uma"]: i + 1 for i, h in enumerate(SC["horses"])}

# ── 4並列で収集した生データ（source, published, confidence, 各シグナル）────────
RAW = [
    # A: YouTube 重み高
    ("アジフライ777", "2026-09-26", "ambiguous",
     dict(honmei=["ママコチャ", "ウインカーネリアン", "アイサンサン"], ana=["サウンドモリアーナ"])),
    ("競馬全レース予想TV（絶好の3頭）", "2026-09-24", "clear",
     dict(honmei=["パンジャタワー"], taikou=["ルガル"], ana=["エーティーマクフィ"])),
    ("競馬全レース予想TV（全条件パーフェクト）", "2026-09-22", "clear",
     dict(honmei=["ウインカーネリアン"], taikou=["ママコチャ", "レイピア"])),
    ("情報通のウマ談義", "2026-09-25", "ambiguous", dict()),
    # B: YouTube
    ("しろクロ競馬", "2026-09-24", "clear",
     dict(honmei=["ウインカーネリアン"], taikou=["レイピア", "エーティーマクフィ"],
          ana=["ペアポルックス", "ママコチャ"], keshi=["スターアニス"],
          oikiri=["パンジャタワー", "ウインカーネリアン", "レイピア", "ママコチャ"])),
    ("うまログ", "2026-09-25", "ambiguous",
     dict(honmei=["ルガル", "パンジャタワー", "ウインカーネリアン", "スターアニス"],
          taikou=["フリッカージャブ"], ana=["レイピア", "エーティーマクフィ", "ママコチャ"],
          oikiri=["パンジャタワー", "フリッカージャブ"])),
    ("アギョウの競馬予想TV", "2026-09-24", "ambiguous",
     dict(honmei=["ルガル"], taikou=["フリッカージャブ", "レイピア", "ジューンブレア"],
          ana=["スターアニス", "ペアポルックス"], oikiri=["スターアニス", "ペアポルックス"])),
    ("蓮の競馬予想", "2026-09-26", "clear",
     dict(honmei=["パンジャタワー"], taikou=["ルガル", "エーティーマクフィ"], ana=["ママコチャ"],
          keshi=["スターアニス", "フリッカージャブ", "ウインカーネリアン", "ワールズエンド"])),
    ("ドンズバ競馬", "2026-09-21", "ambiguous",
     dict(ana=["レッドモンレーヴ", "ママコチャ", "ピューロマジック"])),
    # C: メディア・予想サイト
    ("SPAIA（消去法）", "2026-09-23", "ambiguous",
     dict(honmei=["パンジャタワー", "フリッカージャブ"], taikou=["ルガル"],
          ana=["ピューロマジック", "ワールズエンド"],
          keshi=["スターアニス", "ウインカーネリアン", "ママコチャ", "レッドモンレーヴ", "アイサンサン",
                 "ペアポルックス", "エーティーマクフィ", "サウンドモリアーナ", "ジューンブレア", "ブラックチャリス"])),
    ("SPAIA（データ紹介）", "2026-09-24", "ambiguous", dict(ana=["フリッカージャブ"])),
    ("netkeiba AI（前走好走）", "2026-09-23", "ambiguous",
     dict(honmei=["レイピア", "パンジャタワー", "ウインカーネリアン"])),
    ("netkeiba AI（本命）", "2026-09-26", "clear", dict(honmei=["パンジャタワー"])),
    ("うましる", "2026-09-26", "clear",
     dict(honmei=["ジューンブレア", "ウインカーネリアン", "ペアポルックス"],
          ana=["レイピア", "スターアニス"])),
    # D: 追い切り専門
    ("note追い切り診断", "2026-09-25", "clear",
     dict(oikiri=["スターアニス", "ウインカーネリアン", "ルガル", "レッドモンレーヴ"])),
]

KIND = {"honmei": "honmei", "taikou": "posi", "ana": "ana", "keshi": "nega"}


def build(only_clear=False):
    sig = []
    for src, pub, conf, d in RAW:
        if only_clear and conf != "clear":
            continue
        for key, kind in KIND.items():
            for nm in d.get(key, []) or []:
                if nm in N2U:
                    sig.append((src, N2U[nm], kind))
                else:
                    print(f"[WARN] 出走表にない馬名: {src} / {nm}")
        oik = d.get("oikiri") or []
        if oik and oik[0] in N2U:           # 追い切り1位のみ最低保証の判定に使う
            sig.append((src, N2U[oik[0]], "oikiri1"))
    return sig


for label, only in (("全ソース", False), ("confidence=clear のみ", True)):
    sig = build(only)
    rows = ensemble(SC20, sig, NAME)
    print("\n" + "=" * 96)
    print(f"■ インフルエンサー合算 v2 — {label}（シグナル{len(sig)}件）")
    print("=" * 96)
    print(f"{'順':>2} {'馬':>3} {'馬名':<12}{'合算':>7}{'基礎':>7}{'補正':>7}{'指数順':>7}  フラグ")
    for i, r in enumerate(rows, 1):
        flags = []
        if r["min_delta"]:
            flags.append("最低保証△")
        if r["nega"]:
            flags.append(f"消し{len(r['nega'])}")
        if r["honmei"]:
            flags.append(f"本命{len(r['honmei'])}")
        print(f"{i:>2} {r['num']:>3} {r['name']:<12}{r['total']:>7}{r['base']:>7}{r['adj']:>+7.1f}"
              f"{RANK[r['num']]:>6}位  " + " ".join(flags))
    if not only:
        out = B / "20260927" / "research" / "ensemble_sprinters_20260926.json"
        out.write_text(json.dumps(
            {"race": "スプリンターズS", "collected_at": "2026-09-26",
             "note": "インフルエンサー合算v2。独自指数版は score20_20260925.json / kaime_sprinters_v2.json を正とする",
             "sources": [{"source": s, "published": p, "confidence": c, **d} for s, p, c, d in RAW],
             "rows": rows}, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"\n保存: {out}")

print("\n■ 詳細（全ソース版・上位8頭の内訳）")
rows = ensemble(SC20, build(False), NAME)
for r in rows[:8]:
    print(f"  {r['num']:>2} {r['name']}")
    print("      " + " / ".join(r["detail"]))
