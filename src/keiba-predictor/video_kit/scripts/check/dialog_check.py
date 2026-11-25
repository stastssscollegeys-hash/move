# -*- coding: utf-8 -*-
"""dialog_check.py — 対話モードの台本を、音声を作る前に検品する（2026-11-19）

対話の型（解説役が中身を話し、聞き役が【見ている人が頭の中で思うこと】を口に出す。誰が聞き役かは templates/voices.json の role＝kikite）が守れているかを見る。
  NG ① 数字・％・専門用語の場面のあと、聞き役のセリフが無いまま 3場面以上続く（--gap で変えられる）
  注意 ② 聞き役のセリフが、直前の解説の1.5倍より長い（聞き役が話しすぎ）
  注意 ③ 聞き役のセリフが、受け答えの形（？・！・だね・ってこと）になっていない
  注意 ④ 台本の最後のまとめの場面が聞き役（結論は解説役が言う）
  NG ⑤ 聞き役のセリフに です・ます がある（聞き役はタメ口・2026-11-20 ユーザー「男性タメ口にしたい」）
使い方: python scripts/check/dialog_check.py <script.json> [--gap 3]
終了コード: NG があれば 1
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
TERMS = ["上がり", "脚質", "差し", "先行", "逃げ", "追込", "追い込み", "内枠", "外枠", "連対", "3着内", "3着以内", "中央値", "期待値", "指数",
         "斤量", "馬場", "重賞", "新馬", "未勝利", "追い切り", "併入", "回避", "登録", "単勝", "複勝", "3連単", "ワイド", "人気"]


def heavy(text):
    """数字・％・専門用語を含むか（見ている人が受け止める必要がある場面）"""
    return bool(re.search(r"[0-9０-９]|％|%|割", text)) or any(t in text for t in TERMS)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("script"); ap.add_argument("--gap", type=int, default=3)
    a = ap.parse_args()
    S = json.load(open(a.script, encoding="utf-8"))
    sc = S["scenes"]
    # 聞き役＝voices.json（＋台本の "speakers"）で role が kikite の話し手（2026-11-19：解説＝アスメシ・聞き役＝競馬ファンに入れ替え）
    vj = Path(__file__).resolve().parents[2] / "templates" / "voices.json"
    spk = json.load(open(vj, encoding="utf-8"))["speakers"] if vj.exists() else {}
    spk.update(S.get("speakers", {}))
    ASKER = {k for k, v in spk.items() if v.get("role") == "kikite"} or {"fan"}
    NAME = "・".join(spk.get(k, {}).get("name", k) for k in sorted(ASKER))
    who = lambda s: s.get("speaker") or "narrator"
    if not any(who(s) in ASKER for s in sc):
        print(f"聞き役（{NAME}）のセリフが1つもありません（1人の語りの台本なら、この検品は要りません）"); return 0
    ng, warn, run = [], [], []
    for i, s in enumerate(sc):
        if who(s) in ASKER:
            run = []
            prev = next((p for p in reversed(sc[:i]) if who(p) not in ASKER), None)
            if prev and len(s["narration"]) > len(prev["narration"]) * 1.5:   # 見本（聞き役32字・解説25字）は通す
                warn.append(f"場面{s['id']}: 聞き役（{len(s['narration'])}字）が直前の解説（場面{prev['id']}・{len(prev['narration'])}字）の1.5倍より長い＝聞き役が話しすぎ")
            if re.search(r"です|ます|でしょう|ません|ください", s["narration"]):
                ng.append(f"場面{s['id']}: 聞き役のセリフが です・ます になっている（タメ口にする）「{s['narration'][:30]}」")
            if not re.search(r"[？?！!]|だね|ってこと|なんだ|かな|よね", s["narration"]):
                warn.append(f"場面{s['id']}: 聞き役のセリフが受け答えの形になっていない「{s['narration'][:30]}」")
        elif heavy(s["narration"]):
            run.append(s["id"])
            if len(run) == a.gap:
                ng.append(f"場面{run[0]}〜{run[-1]}: 数字・用語の場面が{a.gap}つ続くのに、聞き役の代弁（言い換え・次へのつなぎ・用語の質問）が無い")
        # 数字・用語の無い場面は数えない（つなぎ・場面転換）
    if who(sc[-1]) in ASKER:
        warn.append(f"場面{sc[-1]['id']}: 最後の場面が聞き役（結論・まとめは解説役が言う）")
    n_a = sum(1 for s in sc if who(s) in ASKER)
    print(f"■ {S.get('race', '')}  {len(sc)}場面・聞き役（{NAME}） {n_a}回")
    for x in ng: print("  NG  ", x)
    for x in warn: print("  注意", x)
    if not ng and not warn: print("  OK")
    return 1 if ng else 0


if __name__ == "__main__":
    sys.exit(main())
