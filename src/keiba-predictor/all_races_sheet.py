# -*- coding: utf-8 -*-
"""all_races_sheet.py — その日の全レースの印と買い目を、根拠の材料つきで1つのファイルにまとめる（内部用・SNSには出さない）。2026-11-15 新設
ユーザー指示（2026-11-15）: 「事前に全レースについて予想の印と買い目を作っておく。SNSで公開する必要はないので1つのファイルにまとめて」
  「SNSに投稿しないけど、全情報・最新情報・データベースを全部含めて綿密に予想して」。
入力（どれも既存の道具の出力。無いものは飛ばす）:
  {OUT}/{日付}_web_probs.json          web_live.py（出走表・単勝・市場確率・計算した勝つ確率）
  --raw                                web_compose.py の標準出力（印・買い目・当たる確率・期待回収率）
  {OUT}/{日付}_{レース}_facts.json     web_facts.py（間隔・距離変化・脚質・コース実績・前走）※ --uma なしで全頭
  {日付}/research/course_cards/*.txt   course_profile.py --course（過去10年のコース傾向）
  {OUT}/{日付}_web_bias.md・{前日}_web_bias.md   web_bias.py（今日ここまで・前日のトラックバイアス）
  {日付}/research/latest_info.txt      取消・馬場・天気など手で集めた最新情報（冒頭に載せる）
手順:
  python web_live.py --date D --seed {Yahoo ID}
  python web_compose.py --date D --race {未発走の全レース} > {日付}/research/web_compose_all_raw.txt
  python web_facts.py --date D --race {未発走の全レース}
  python web_results.py --date D ; python web_bias.py --date D        （発走済みのレースがあるとき）
  python all_races_sheet.py --date D --raw {日付}/research/web_compose_all_raw.txt [--prev 前日]
出力: Desktop/競馬予想レポート/{日付}/{日付}_全レース_印と買い目.md（発走順・BOM付き）"""
import argparse, json, re, sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path("C:/Users/User/Desktop/競馬予想レポート")
OUT = ROOT / "daily_pdca/web_live"
CIRC = "①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱"
c = lambda u: CIRC[int(u) - 1]


def bias_blocks(f):
    """web_bias.md → {'京都ダ': [行…]}"""
    d = {}
    if not f.exists():
        return d
    cur = None
    for ln in f.read_text(encoding="utf-8").splitlines():
        m = re.match(r"■(\S+?)（", ln)
        if m:
            cur = m.group(1); d[cur] = [ln.strip()]
        elif cur and ln.startswith("   "):
            d[cur].append(ln.strip())
        elif ln.startswith("##"):
            cur = None
    return d


def course_card(date, venue, dist):
    f = ROOT / date / "research/course_cards" / f"{venue}{dist}.txt"
    if not f.exists():
        return []
    keep = []
    for ln in f.read_text(encoding="utf-8").splitlines():
        if re.match(r"- \*\*(人気|配当|枠（3着内率）|脚質|ペース別)", ln):
            keep.append(re.sub(r"\*\*", "", ln[2:]).split(" ／ 上がり最速")[0])
    return keep


def fact_line(f):
    if not f or f.get("interval_days") is None:
        return "初出走（成績なし）" if f is not None else ""
    ch = f.get("last_dist_change") or 0
    p = [f"間隔{f['interval_days']}日", "同距離" if ch == 0 else (f"{abs(ch)}m短縮" if ch > 0 else f"{abs(ch)}m延長")]
    if f.get("surface_change"): p.append("芝ダ替わり")
    if f.get("style"): p.append(f["style"])
    p.append(f"同コース{f.get('same_course')}")
    p.append("近走" + "・".join(str(x) for x in (f.get("recent") or [])[:4]))
    return "｜".join(p) + f"\n    前走: {f.get('last')}（上がり{f.get('last_l3_rank')}位）"


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--date", required=True); ap.add_argument("--raw", required=True); ap.add_argument("--prev", default="")
    a = ap.parse_args()
    P = json.load(open(OUT / f"{a.date}_web_probs.json", encoding="utf-8"))
    races = {f"{v['venue']}{int(v['R'])}": (k, v) for k, v in P["races"].items()}
    raw = Path(a.raw).read_text(encoding="utf-8")
    asof = (re.search(r"オッズ取得: (\S+)", raw) or [None, "?"])[1]
    tr = {}
    tf = ROOT / a.date / f"{a.date}_今日の傾向.md"     # web_today_trends.py の一言まとめ（場×芝ダ）
    if tf.exists():
        for ln in tf.read_text(encoding="utf-8-sig").splitlines():
            m = re.match(r"- (\S+?(?:芝|ダ))（[^）]*）: (.*)", ln)
            if m: tr[m.group(1)] = m.group(2).split("／※")[0]
    b_today, b_prev = bias_blocks(OUT / f"{a.date}_web_bias.md"), bias_blocks(OUT / f"{a.prev}_web_bias.md") if a.prev else {}
    out, summ = [], []
    for b in raw.split("■ ")[1:]:
        key = b.split()[0]
        if key not in races: continue
        pk, v = races[key]
        hs = {h["uma"]: h for h in v["horses"]}
        order = sorted(hs.values(), key=lambda h: h["odds"])
        pop = {h["uma"]: i + 1 for i, h in enumerate(order)}
        ff = OUT / f"{a.date}_{pk}_facts.json"
        if not ff.exists(): ff = OUT / f"{a.date}_{key}_facts.json"
        F = {x["uma"]: x for x in json.load(open(ff, encoding="utf-8"))} if ff.exists() else {}
        m = re.search(r"印: (.*)", b)
        marks = re.findall(r"([◎○▲△穴])(\d+)", m.group(1)) if m else []
        mk_of = {int(u): mk for mk, u in marks}
        surf = v["dist"][0]
        L = [f"## {v['start']} {v['venue']}{int(v['R'])}R {v.get('title','')}（{v.get('dist','')}・{v.get('n','')}頭・{v.get('baba','')}）"]
        cc = course_card(a.date, v["venue"], v["dist"])
        if cc: L += ["【コースの傾向（過去10年）】"] + ["・" + x for x in cc]
        if tr.get(v["venue"] + surf): L.append(f"【今日の傾向】{tr[v['venue'] + surf]}（詳細は {a.date}_今日の傾向.md）")
        for lab, B in (("今日ここまで", b_today), ("前日", b_prev)):
            bb = B.get(v["venue"] + surf)
            if bb: L += [f"【{lab}の馬場】{bb[0][1:]}"] + ["・" + x for x in bb[1:]]
        L.append("【印と材料】")
        for mk, u in marks:
            h = hs[int(u)]; r = h["p_model"] / h["p_market"] if h["p_market"] else 0
            L.append(f"{mk} {c(u)}{h['name']}（{h['jockey']}・{pop[int(u)]}番人気 {h['odds']}倍・勝つ確率{h['p_model']*100:.1f}%／市場{h['p_market']*100:.1f}%＝割安さ{r:.2f}）")
            fl = fact_line(F.get(int(u)))
            if fl: L.append("    " + fl)
        # 注意点
        warn = []
        for mk, u in marks:
            f = F.get(int(u)) or {}
            iv = f.get("interval_days")
            if iv and iv >= 150 and pop[int(u)] <= 3:
                warn.append(f"{mk}{c(u)}は{iv}日ぶりの人気馬（150日以上の休み明けの人気馬は3着内が見込みの約0.89倍）" + ("→◎の単独軸は避けたい" if mk == "◎" else ""))
            if hs[int(u)].get("new"): warn.append(f"{mk}{c(u)}は初出走＝計算は市場寄りで根拠が薄い")
            if f.get("surface_change"): warn.append(f"{mk}{c(u)}は芝ダ替わり（消し方向の傾向）")
        for h in order[:3]:
            if h["uma"] not in mk_of:
                warn.append(f"{pop[h['uma']]}番人気{c(h['uma'])}{h['name']}は印なし（割安さ{h['p_model']/h['p_market']:.2f}）＝買い目に入っていない")
        # 2026-11-15 当日の学び（today_lessons）を自動の注意に: 休み明けの◎・前残りの場で差し追込の◎・◎1頭寄せ
        trend = tr.get(v["venue"] + surf, "")
        if marks:
            hm = int(marks[0][1]); fh = F.get(hm) or {}
            sub = next((int(u) for mk, u in marks[1:] if ((F.get(int(u)) or {}).get("interval_days") or 0) < 150), None)
            if (fh.get("interval_days") or 0) >= 150:
                warn.append(f"◎{c(hm)}は{fh['interval_days']}日ぶり＝150日以上の休み明けの◎は単独軸にしない（2026-11-15は2戦2敗）。" + (f"{c(sub)}との2頭軸に" if sub else "2頭軸に"))
            if "前残り" in trend and fh.get("style") == "差し・追込":
                fr = [int(u) for mk, u in marks[1:] if (F.get(int(u)) or {}).get("style") == "逃げ・先行"]
                warn.append(f"◎{c(hm)}は差し・追込型で、今日のこの馬場は前残り＝届かない危険。" + (f"前に行ける{''.join(c(x) for x in fr)}との組を厚く" if fr else "先行馬との組を厚く"))
            others = [int(u) for mk, u in marks[1:4]]
            if len(others) >= 2:
                warn.append(f"保険: ◎が来なかった時のために、◎抜きの印同士（{c(others[0])}-{c(others[1])}の馬連やワイド）を少額入れる")
        nnew = sum(1 for h in hs.values() if h.get("new"))
        if nnew >= max(3, len(hs) // 2): warn.append(f"初出走が{nnew}頭＝計算の根拠が薄いレース（参考）")
        if warn: L += ["【注意点】"] + ["・" + w for w in warn]
        L.append("【買い目】")
        for t, combo, amt, hit, odds in re.findall(r"^\s+(単勝|馬連|ワイド|3連複)\s+([\d-]+)\s+([\d,]+)円\s+当たる\s+([\d.]+)%\s+オッズ\s+([\d.]+)", b, re.M):
            L.append(f"{t} {'-'.join(c(x) for x in combo.split('-'))} {amt}円（当たる{hit}%・{odds}倍）")
        tot = re.search(r"合計 ([\d,]+)円 ／ どれかが当たる ([\d.]+)% ／ 期待回収率 ([\d.]+)", b)
        sc = re.search(r"場面ごと: (.*)", b)
        if tot:
            e = float(tot[3]); L.append(f"合計 {tot[1]}円／どれかが当たる {tot[2]}%／期待回収率 {e:.2f}" + ("（1未満＝参考）" if e < 1 else ""))
        if sc: L.append(sc[1].replace("拾える", "拾える割合"))
        L.append("【全頭】馬番 馬名 人気 単勝 ｜ 勝つ確率／市場 ｜ 割安さ ｜ 間隔・脚質・同コース")
        for h in sorted(hs.values(), key=lambda h: h["uma"]):
            f = F.get(h["uma"]) or {}
            ex = f"{f.get('interval_days')}日・{f.get('style') or '-'}・{f.get('same_course')}" if f.get("interval_days") is not None else "初出走"
            L.append(f"{mk_of.get(h['uma'], '　')} {h['uma']:>2} {h['name']} {pop[h['uma']]}人 {h['odds']} ｜ {h['p_model']*100:.1f}%／{h['p_market']*100:.1f}% ｜ {h['p_model']/h['p_market']:.2f} ｜ {ex}")
        out.append((v["start"].zfill(5), "\n".join(L)))
        if marks and tot:
            u = int(marks[0][1]); h = hs[u]
            summ.append((v["start"].zfill(5), f"{v['start']} {v['venue']}{int(v['R'])}R ｜ ◎{c(u)}{h['name']}（{pop[u]}人 {h['odds']}倍・割安さ{h['p_model']/h['p_market']:.2f}）｜ 当たる{tot[2]}%・期待{float(tot[3]):.2f}" + ("" if not warn else f" ｜ 注意{len(warn)}件")))
    out.sort(); summ.sort()
    info = ROOT / a.date / "research/latest_info.txt"
    txt = (f"# {a.date[:4]}/{a.date[4:6]}/{a.date[6:]} 全レースの印と買い目（内部用・SNSには出さない）\n"
           f"単勝オッズ {asof} 時点。組み合わせの倍率は発売中の途中経過で高めに出やすい＝期待回収率は目安（1.3を超えるものは歪みを疑う）。馬体重は未反映。\n"
           "勝つ確率＝市場オッズ＋蓄積データベース（騎手・厩舎・過去走・傾向）で計算。印＝人気に対する割安さの順。調教は入っていない。\n"
           "買い目は web_compose（単勝◎・馬連◎-○▲穴・ワイド◎-○▲穴・3連複フォーメーション ◎-○▲-印・1万円）。\n\n"
           + (("## 最新情報\n" + info.read_text(encoding="utf-8").strip() + "\n\n") if info.exists() else "")
           + "## 一覧（発走順）\n" + "\n".join(s for _, s in summ) + "\n\n" + "\n\n".join(t for _, t in out) + "\n")
    f = ROOT / a.date / f"{a.date}_全レース_印と買い目.md"; f.write_text(txt, encoding="utf-8-sig"); print(f, len(out), "レース")


if __name__ == "__main__":
    main()
