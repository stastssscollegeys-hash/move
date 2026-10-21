# -*- coding: utf-8 -*-
"""
gen_cards_sns.py — 新エンジン（predict_day.py の予想カード）から重賞のSNS投稿案を作る（2026-10-03／10-04 充実版）
=====================================================================================
入力: {日付}/research/cards_{日付}.json（predict_day.py） ＋ draw_content.json（人が調べた事実: 追い切り・陣営談話・過去10回・コース）
方針: 印・確率・買い目は新エンジンの値。draw_content は「事実の文章」だけを使い、旧印に依存する文（指数・印の付け外し）は除く。
X の書き方（2026-10-04 ユーザー指示）: Xは「さらに表示」を押さないと全部見えない（約140字・8行で折りたたみ）。
  → 各投稿の 2行ヘッダーの直後の数行に「結論」を集め、根拠の詳細は「─── 詳細 ───」の下に置く。
出力: {日付}_重賞_SNS投稿案_エンジン版.docx ／ 各レースの note 用 .txt（X7・Threads6・note12セクション）
使い方: python gen_cards_sns.py --dir 20261004
"""
from __future__ import annotations
import argparse, json, re, sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8")
import bet_engine as B
from kaime_format import circ

BASE = Path.home() / "Desktop" / "競馬予想レポート"
import os as _os
if _os.environ.get("REPLAY"):                      # 再生テストは _replay/ の中で作る
    BASE = BASE / "_replay"
SEP = "─────"
DETAIL = "─── 詳細 ───"
FOLD = 140                                   # X の折りたたみ（字数）
BAN = ["netkeiba", "SPAIA", "うましる", "競馬ラボ", "重賞ナビ", "ウマニティ", "東スポ", "サンスポ", "スポニチ", "日刊スポーツ", "デイリー",
       "PDCA", "EV", "sc[", "インフルエンサー", "両関門", "z=", "在サンプル", "Harville", "lift", "合算", "仮版", "指数"]
SKIP = ("指数", "印は付けていません", "印を外しました", "枠順前", "先週", "下げた理由", "に下げ", "評価を上げ", "netkeiba", "競馬ラボ", "うましる", "東スポ", "サンスポ", "スポニチ", "日刊スポーツ", "デイリー", "ウマニティ")
ap = argparse.ArgumentParser()
ap.add_argument("--dir", required=True)
a = ap.parse_args()
D = BASE / a.dir
CARDS = json.loads((D / "research" / f"cards_{a.dir}.json").read_text(encoding="utf-8"))["cards"]
CONT = json.loads((D / "research" / "draw_content.json").read_text(encoding="utf-8"))
DATE, TAGS = CONT["post_date_label"], CONT["hashtags"]
CR = {r["name"]: r for r in CONT["races"]}
ORDER = {"◎": 0, "○": 1, "▲": 2, "△": 3, "🔥": 4}
_WF = D / "research" / "next_week_watch.json"     # 1週間前プレビューの注目馬（2026-10-21: 印から外れた馬は理由を書く）
WATCH = {r["name"]: r for r in json.loads(_WF.read_text(encoding="utf-8"))["races"]} if _WF.exists() else {}
ODDS_NOTE = "オッズは発走前に動きます。発走前に実際のオッズで計算し直します。"


def first_clause(x, n=40):
    """箇条書きの頭の1文（かぎかっこの外の「。」まで）。長ければ「、」で切る"""
    depth, out = 0, ""
    for ch in x:
        depth += ch == "「"
        depth -= ch == "」"
        if ch == "。" and depth <= 0:
            break
        out += ch
    if len(out) <= n:
        return out
    cut = out[:n].rfind("、")
    return out[:cut] if cut >= 12 else out[:n - 1] + "…"


class Race:
    def __init__(self, c):
        self.c = c
        self.t = CR[c["name"]]
        self.h = {h["uma"]: h for h in c["horses"]}
        self.marked = sorted(((c["marks"][str(u)], u) for u in self.h if str(u) in c["marks"]), key=lambda x: (ORDER[x[0]], x[1]))
        self.caution = [u for u in c["caution"] if str(u) not in c["marks"]]
        self.ref = self.make_bets()
        tr = " ".join(c["trends"])
        self.bias = next((t for t in c["trends"] if t.startswith("今日ここまで")), None) or next((t for t in c["trends"] if t.startswith("前日")), None)
        self.front_ok = "前の馬が残りやすい" in (self.bias or "")
        self.back_ok = "差し・追い込みが届きやすい" in (self.bias or "")

    def nm(self, u):
        return f"{circ(u)}{self.h[u]['name']}"

    def head(self):
        return f"🏇【{self.c['name']} {self.t['grade']}】{DATE}\n━━ {self.c['venue']} {self.t['course']} / {self.c['n']}頭 ━━"

    def tag(self):
        return f"{TAGS} {self.t['tag']}"

    def mk(self, lab):
        return [u for l, u in self.marked if l == lab]

    def pct(self, u):
        h = self.h[u]
        return f"{h['p_model']*100:.0f}%（人気が示す確率{h['p_market']*100:.0f}%）"

    def facts(self, u):
        t = self.t["horses"].get(str(u))
        src = (t or {}).get("detail") or self.t.get("caution", {}).get(str(u)) or []
        out = [x for x in src if not any(s in x for s in SKIP)]
        if not out and self.t.get("others", {}).get(str(u)):
            out = [re.sub(r"枠順前の指数\d+位から\d+位へ。", "", self.t["others"][str(u)])]
        return out or self.h[u].get("reasons_all") or self.h[u]["reasons"]

    def bias_fit(self, u):
        st = self.h[u].get("style")
        if not st or not self.bias:
            return None
        where = "今日の" if self.bias.startswith("今日") else "昨日の"
        surf = "芝" if self.c["dist"][:1] == "芝" else "ダート"
        if self.front_ok:
            return {"前で運ぶ": (f"{where}{self.c['venue']}{surf}は前が残る流れ。前で運ぶこの馬に合う", True),
                    "後ろから": (f"{where}{self.c['venue']}{surf}は前が残る流れ。後ろから行くこの馬には向かい風", False)}.get(st)
        if self.back_ok:
            return {"後ろから": (f"{where}{self.c['venue']}{surf}は差しが届く流れ。後ろから行くこの馬に合う", True),
                    "前で運ぶ": (f"{where}{self.c['venue']}{surf}は差しが届く流れ。前で運ぶこの馬には向かい風", False)}.get(st)
        return None

    def points(self, u, k=3):
        """結論の ✅ 行（短く）"""
        out = []
        dc = (self.t["horses"].get(str(u)) or {}).get("decide")
        if dc and not any(s in dc for s in SKIP):
            out.append(dc)
        bf = self.bias_fit(u)
        if bf and bf[1]:
            out.append(bf[0])
        for x in list(self.facts(u)) + list(self.h[u].get("reasons_all") or []):
            if len(out) >= k:
                break
            fc = first_clause(x)
            if len(fc) < 8 or re.search(r"\d枠\d+番$", fc) or fc.startswith(("過去10回", "前走", "最終追い切りは")) or any(w in x for w in ("加点していません", "頭に入れて", "割れて", "控えめ", "下げ")):          # 短すぎる・レース全体の話・ローテの説明は結論に出さない
                continue
            if any(fc[i:i + 6] in o for o in out for i in range(len(fc) - 5)):   # 同じことの言い換えは除く
                continue
            out.append(fc)
        return out[:k]

    def detail(self, u):
        h = self.h[u]
        L = [f"{h['sexage']}・{h['kin']:g}kg・{h['jockey']}騎手・{h['trainer']}厩舎" + (f"・父{h['sire']}" if h.get("sire") else ""),
             f"通算 {h['career']}" + (f"／脚質: {h['style']}" if h.get("style") else "")]
        bf = self.bias_fit(u)
        if bf and not bf[1]:
            L.append(f"⚠{bf[0]}")
        L += [f"・{x}" for x in self.facts(u)]
        for x in (h.get("reasons_all") or [])[:4]:
            if not any(x[:12] in y for y in L):
                L.append(f"・{x}")
        if h.get("jockey_course"):
            L.append(f"・{h['jockey_course']}")
        if h.get("last5"):
            L += ["直近の成績"] + [f"　{x}" for x in h["last5"][:5]]
        return L

    def make_bets(self):
        if self.c["ref_bets"]:                          # 2026-10-07: 公開は標準形V1
            return [dict(b, kind="標準") for b in self.c["ref_bets"]]
        if self.c["bets"]:
            return [dict(b, kind="E2") for b in self.c["bets"]]
        uma = sorted(self.h)
        p = np.array([self.h[u]["p_model"] for u in uma]); q = np.array([self.h[u]["p_market"] for u in uma])
        p, q = p / p.sum(), q / q.sum()
        tm, tq = B.tables(p, uma), B.tables(q, uma)
        top = [u for _, u in self.marked[:3]]
        want = [("馬連", tuple(sorted(x))) for x in ((top[0], top[1]), (top[0], top[2]), (top[1], top[2]))] + [("ワイド", tuple(sorted((top[0], top[1])))), ("ワイド", tuple(sorted((top[0], top[2]))))]
        rows = []
        for t, k in want:
            keys, pm = tm[t]; _, pq = tq[t]
            i = keys.index(k)
            rows.append((t, k, float(pm[i]), B.TAKE[t] / float(pq[i])))
        w = np.array([1.0 / o for *_, o in rows])
        amt = np.floor(10000 * w / w.sum() / 100.0) * 100.0
        return [dict(type=t, combo=list(k), stake=int(s), odds_est=round(o, 1), p_model=round(pm, 4), kind="提示用") for (t, k, pm, o), s in zip(rows, amt) if s >= 100]

    def od(self, b):
        return b.get("odds_now") or b.get("odds_est")

    def ev_total(self):
        s = sum(b["stake"] for b in self.ref)
        return sum(b["stake"] * b["p_model"] * self.od(b) for b in self.ref) / s

    def kaime_short(self):
        if self.ref[0]["kind"] == "標準":
            return f"{len(self.ref)}点・{sum(b['stake'] for b in self.ref):,}円"
        if self.ev_total() < 1.0 and self.ref[0]["kind"] != "E2":
            return f"見送り（期待値{self.ev_total()*100:.0f}%）"
        return " ".join(f"{b['type']}{'-'.join(circ(x) for x in b['combo'])}" for b in self.ref[:3]) + (f"ほか{len(self.ref)-3}点" if len(self.ref) > 3 else "")

    def kaime_lines(self):
        L = [f"💰 買い目 {len(self.ref)}点・{sum(b['stake'] for b in self.ref):,}円"]
        for b in self.ref:
            L.append(f"{'🎯' if b.get('value') else ''}【{b['type']}】{'-'.join(circ(x) for x in b['combo'])} {b['stake']:,}円／的中{b['p_model']*100:.1f}%×{self.od(b):.1f}倍＝期待値{b['p_model']*self.od(b):.2f}")
        L.append(f"全体の期待回収率 {self.ev_total()*100:.0f}%")
        return L

    def verdict(self):
        ev = self.ev_total()
        if self.ref[0]["kind"] == "標準":
            v = [b for b in self.ref if b.get("value")]
            base = "印は人気ではなく「人気に対する割安さ」の順。相手は◎からのワイドで広く押さえています。"
            return base + ("🎯人気より割安な馬連が出たので、勝負レースとして別枠で足しています。" if v else "")
        if self.ref[0]["kind"] == "E2":
            return "モデルが市場より1.3倍以上高く見ている組み合わせがあり、買う根拠のある買い目です。"
        return (f"期待値は{ev*100:.0f}%で、100%を超える組み合わせはありません。印の馬を買う場合の参考です。" if ev < 1.0 else "期待値は100%を超えていますが、検証済みの条件（市場との比1.3倍以上）には届きません。")

    def runners(self):
        """前に行きたい馬・後ろから行く馬（直近5走の位置取りから）"""
        g = {"前で運ぶ": [], "中団": [], "後ろから": []}
        for u, h in sorted(self.h.items()):
            if h.get("style") in g:
                g[h["style"]].append(u)
        return g


def lead(r):
    h = r.mk("◎")[0]
    rel = "人気より高く見ています" if r.h[h]["ratio"] >= 1.05 else "人気とほぼ同じ評価です"
    return f"本命{r.nm(h)}の勝つ確率は{r.h[h]['p_model']*100:.0f}%で、{rel}。"


def recent(r, u, n=3):
    """直近n走を1行に（例: 共同通信杯1着→皐月賞2着→東京優駿7着）"""
    xs = []
    for s in (r.h[u].get("last5") or [])[:n][::-1]:
        m_ = re.match(r"\S+ \S+ (.+?) (\d+)着/", s)
        if m_ and "農林水産省賞典" in m_.group(1):
            xs.append(f"{m_.group(1).replace('農林水産省賞典', '').strip()}記念{m_.group(2)}着")
        elif m_:
            xs.append(f"{re.sub(r'(農林水産省賞典|ステークス)', lambda k: 'S' if k.group(1) == 'ステークス' else '', m_.group(1)).strip()}{m_.group(2)}着")
    return "→".join(xs)


def brief(r, u):
    """詳細の3行（騎手・斤量・脚質／直近3走／追い切りか陣営）"""
    h = r.h[u]
    L = [f"・{h['jockey']}騎手・{h['kin']:g}kg" + (f"・馬体重{h['weight'].replace('(', 'kg(')}" if h.get("weight") else "") + (f"・{h['style']}" if h.get("style") else "")]
    rc = recent(r, u)
    if rc:
        L.append(f"・近走: {rc}")
    ok = next((first_clause(x, 46) for x in r.facts(u) if x.startswith(("最終追い切り", "木曜", "陣営"))), None)
    if ok:
        L.append(f"・{ok}")
    elif h.get("chokyo"):
        L.append(f"・調教: {h['chokyo']}")                # JRA-VAN の調教タイム（全馬・自動）
    used = " ".join(r.points(u)) + " ".join(L)
    for x in r.facts(u):
        fc = first_clause(x, 60)
        if (len(L) >= 6 or fc[:10] in used or len(fc) < 10 or re.search(r"\d枠\d+番$", fc) or x.startswith(("最終追い切り", "木曜", "陣営"))
                or any(w in x for w in ("加点していません", "頭に入れて", "下げ"))):
            continue
        L.append(f"・{fc}")
        used += fc
    if r.h[u].get("jockey_course"):
        L.append("・" + r.h[u]["jockey_course"].replace("人気から期待される数の", "期待の"))
    bf = r.bias_fit(u)
    if bf and not bf[1]:
        L.append(f"⚠{bf[0]}")
    return L


RANK_EXP = {"◎": 1, "○": 2, "▲": 3}


def pop_view(r):
    """上位人気（1〜3番人気）なのに印が無い・△以下の馬（2026-10-10 ユーザー指示: なぜ評価を下げたかはリスナーが気になる）"""
    out = []
    for u, h in sorted(r.h.items(), key=lambda x: x[1]["pop"]):
        if h["pop"] > 3:
            continue
        lab = r.c["marks"].get(str(u))
        if lab in ("◎", "○", "▲"):
            continue
        out.append((u, lab))
    return out


def gap_marks(r):
    """印の重さに比べて人気が大きく低い馬（◎○▲で期待順位より3つ以上下の人気・🔥は全部）"""
    return [(lab, u) for lab, u in r.marked if (lab in RANK_EXP and r.h[u]["pop"] - RANK_EXP[lab] >= 3) or lab == "🔥"]


def why_low(r, u):
    """人気馬の評価を下げた理由（確率の比較＋手書きの説明 pop_view）"""
    h = r.h[u]
    rt = h["p_model"] / h["p_market"] if h["p_market"] else 1
    rel = ("人気が示す確率より低く、買われすぎと見ています" if rt < 0.9 else
           "人気が示す確率とほぼ同じで、割安さがありません")
    L = [f"勝つ確率{h['p_model']*100:.0f}%／人気が示す確率{h['p_market']*100:.0f}% → {rel}"]
    pv = (r.t.get("pop_view") or {}).get(str(u))
    if pv:
        L += [f"・{x}" for x in (pv if isinstance(pv, list) else [pv])]
    return L


def watch_dropped(r):
    """1週間前の注目馬で、最終版で印が付かなかった馬（2026-10-21 ユーザー指示: 秋華賞で注目馬ギャラボーグが印なし→2着。
    注目していた馬が黙って消えないよう、外した理由を1頭1投稿で書く）。人気馬の投稿（pop_view）と重なる馬は除く"""
    w = WATCH.get(r.c["name"])
    if not w:
        return []
    byname = {h["name"]: u for u, h in r.h.items()}
    popv = {u for u, _ in pop_view(r)}
    out = []
    for x in w.get("watch", []):
        u = byname.get(x["horse"])
        if u is not None and str(u) not in r.c["marks"] and u not in popv:
            out.append((u, x))
    return out


def why_dropped(r, u, x):
    """注目馬を印から外した理由（確率の比較＋割安さの順位＋手書きの説明 watch_view）"""
    h = r.h[u]
    rk = sorted(r.h, key=lambda k: -r.h[k]["ratio"]).index(u) + 1
    L = [f"勝つ確率{h['p_model']*100:.1f}%／人気が示す確率{h['p_market']*100:.1f}%（割安さは{len(r.h)}頭中{rk}番目）"]
    wv = (r.t.get("watch_view") or {}).get(str(u))
    if wv:
        L += [f"・{y}" for y in (wv if isinstance(wv, list) else [wv])]
    else:
        PROBLEMS.append(f"{r.c['name']}: 注目馬 {r.nm(u)} を印から外した理由（draw_content の watch_view）が未記入")
    return L


def why_high(r, u):
    h = r.h[u]
    return [f"勝つ確率{h['p_model']*100:.1f}%／人気が示す確率{h['p_market']*100:.1f}%（{h['p_model']/h['p_market']:.2f}倍）"] + [f"・{x}" for x in r.points(u, 2)]


def x_posts(r):
    c = r.c
    m = {lab: r.mk(lab) for lab in ORDER}
    hon = m["◎"][0]
    g = r.runners()
    P = []
    L = [r.head(), "",
         ] + [f"{lab}{r.nm(u)}" for lab, u in r.marked] + [
         "",
         f"買い目：{r.kaime_short()}",
         "",
         SEP,
         f"決め手：{r.points(hon, 1)[0]}"]
    if r.bias:
        L.append(f"馬場：{r.bias.split(': ')[-1]}")
    L += ["", lead(r)] + [f"・{x}" for x in r.t["profile"][:2]]
    if r.caution:
        L.append("人気でも軸にしない：" + "・".join(r.nm(u) for u in r.caution))
    L += ["", "根拠はスレッドで👇", r.tag()]
    P.append(("X① 予想印", L))
    for no, lab in (("②", "◎"), ("③", "○"), ("④", "▲")):
        u = m[lab][0]
        L = [r.head(), "", f"{lab}{r.nm(u)}", f"勝つ確率{r.pct(u)}", ""] + [f"✅{x}" for x in r.points(u)] + ["", SEP] + brief(r, u) + ["", r.tag()]
        P.append((f"X{no} {lab}", L))
    L = [r.head(), "", "相手と穴", ""]
    for u in m["△"] + m["🔥"]:
        L += [f"{c['marks'][str(u)]}{r.nm(u)}（勝つ確率{r.h[u]['p_model']*100:.0f}%）"] + [f"　{x}" for x in r.points(u, 2)] + [""]
    for u in r.caution:
        L += [f"軸にしない {r.nm(u)}（{r.h[u]['pop']}番人気）", f"　勝つ確率{r.pct(u)}", ""]
    P.append(("X⑤ 相手と穴", L + [r.tag()]))
    for u, lab in pop_view(r):                       # 1頭1投稿（2頭まとめると500字を超えて理由が削られた）
        w = why_low(r, u)
        L = [r.head(), "", f"人気馬をどう見たか（{r.h[u]['pop']}番人気）", "",
             f"{lab or '印なし'}{r.nm(u)}　単勝{r.h[u]['odds']}倍", w[0], "",
             "印は強さの順ではなく「勝つ確率が人気より高いか（割安さ）」の順です。", "", SEP] + w[1:] + ["",
             "評価を下げた＝負けると見ている、ではありません。人気どおりの確率なら、買っても得にならないという意味です。", r.tag()]
        P.append((f"X 人気馬をどう見たか {r.nm(u)}", L))
    for u, x in watch_dropped(r):                    # 1週間前の注目馬で印が付かなかった馬（1頭1投稿）
        w = why_dropped(r, u, x)
        L = [r.head(), "", f"1週間前の注目馬をどう見たか（{r.h[u]['pop']}番人気）", "",
             f"印なし{r.nm(u)}　単勝{r.h[u]['odds']}倍", w[0], "",
             f"1週間前に注目した理由：{x['lead']}", "", SEP] + w[1:] + ["",
             "印は強さの順ではなく「勝つ確率が人気より高いか（割安さ）」の順です。印を外した＝負けると見ている、ではありません。", r.tag()]
        P.append((f"X 注目馬をどう見たか {r.nm(u)}", L))
    gm = gap_marks(r)
    if gm:
        L = [r.head(), "", "人気より印が重い馬", ""] + [f"{lab}{r.nm(u)}（{r.h[u]['pop']}番人気）" for lab, u in gm] + ["",
             "人気に対して勝つ確率が高く出た馬に、重い印を付けています。", "", SEP]
        for lab, u in gm:
            L += [f"{lab}{r.nm(u)}　{r.h[u]['pop']}番人気・{r.h[u]['odds']}倍"] + why_high(r, u) + [""]
        L += ["人気薄の印は当たる回数は少なくても、来たときの配当で取り返す考え方です。", r.tag()]
        P.append(("X 人気と印のずれ", L))
    L = [r.head(), "", "展開と馬場", ""]
    if r.bias:
        L += [r.bias, ""]
    L += [f"前に行きたい馬：{'・'.join(circ(u) for u in g['前で運ぶ']) or 'なし'}（{len(g['前で運ぶ'])}頭）",
          f"後ろから行く馬：{'・'.join(circ(u) for u in g['後ろから']) or 'なし'}",
          f"◎{r.nm(hon)}は「{r.h[hon].get('style') or '位置取り不明'}」", "", SEP] + [f"・{x}" for x in r.t["course_note"][:2]] + [f"・{x}" for x in r.t["profile"][1:3]] + ["", r.tag()]
    P.append(("X⑥ 展開と馬場", L))
    L = [r.head(), ""] + [f"{lab}{r.nm(u)}" for lab, u in r.marked] + ["", f"買い目：{r.kaime_short()}", ""] + [f"{b['type']} {'-'.join(circ(x) for x in b['combo'])}　{b['stake']:,}円（的中{b['p_model']*100:.0f}%×{r.od(b):.1f}倍＝{b['p_model']*r.od(b):.2f}）" for b in r.ref] + \
        ["", f"期待回収率 {r.ev_total()*100:.0f}%", r.verdict(), "", "買い目は「的中率×オッズ＝期待値」で決めています。100%を超えない組み合わせは買う根拠がありません。", f"※{ODDS_NOTE}", r.tag()]
    P.append(("X⑦ 買い目", L))
    NUM = "①②③④⑤⑥⑦⑧⑨⑩⑪⑫"
    P = [(f"X{NUM[i]} {t.split(' ', 1)[1]}", x) for i, (t, x) in enumerate(P)]   # 追加の投稿があっても通し番号にする
    out = []
    for t, x in P:                                   # 520字を超えたら「・」の行を後ろから削る
        x = list(x)
        while len("\n".join(x)) > 520 and any(l.startswith("・") for l in x):
            x.pop(max(i for i, l in enumerate(x) if l.startswith("・")))
        out.append((t, "\n".join(x)))
    return out


def fit(head, bullets, tail, limit=500):
    b = list(bullets)
    while True:
        body = "\n".join(head + b + tail)
        if len(body) <= limit or len(b) <= 1:
            return body
        b.pop()


def threads_posts(r):
    xs = {t.split(" ", 1)[1]: x for t, x in x_posts(r)}
    T = []
    want = [("予想印", "予想印"), ("◎", "◎本命"), ("○", "○対抗"), ("▲", "▲単穴"), ("相手と穴", "相手と穴"), ("人気馬をどう見たか", "人気馬をどう見たか"),
            ("注目馬をどう見たか", "注目馬をどう見たか"), ("人気と印のずれ", "人気と印のずれ"), ("買い目", "買い目")]
    want = [(k2, lab if k2 == k else k2) for k, lab in want for k2 in xs if k2 == k or k2.startswith(k + " ")]
    order = [(k, f"{i}/{len(want)} {lab}") for i, (k, lab) in enumerate(want, 1)]
    for k, lab in order:
        lines = xs[k].split("\n")
        lines.insert(2, f"（{lab}）")
        body = "\n".join(lines)
        while len(body) > 500 and any(l.startswith("・") for l in lines):
            i = max(i for i, l in enumerate(lines) if l.startswith("・"))
            lines.pop(i)
            body = "\n".join(lines)
        for drop in ("※", "買い目は「的中率"):          # 買い目の点数が多いとき（ワイド流し）は説明の行から削る
            if len(body) > 500:
                lines = [l for l in lines if not l.startswith(drop)]
                body = "\n".join(lines)
        T.append((f"Threads {lab}", body))
    return T


def note_article(r):
    c, t = r.c, r.t
    m = {lab: r.mk(lab) for lab in ORDER}
    hon = m["◎"][0]
    g = r.runners()
    N = [f"【{c['name']}2026 予想】本命は{r.nm(hon)}｜過去10年のデータ・今日の馬場・買い目の期待値", "",
         "1. はじめに", "こんにちは、アスメシ競馬予想です🍱", "「明日の飯代」を懸けて、AIとデータで競馬に挑む予想アカウントです。",
         "結論を先に言います。", f"本命は{r.nm(hon)}、対抗は{r.nm(m['○'][0])}、単穴は{r.nm(m['▲'][0])}。", lead(r), f"買い目は「{r.kaime_short()}」です。{r.verdict()}", "",
         "2. レース基本情報", f"{c['name']}（{t['grade']}）", f"{DATE} {t['start']}", f"{c['venue']} {t['course']} ／ {c['n']}頭立て", t["cond"], "",
         "3. コース特性と今回の狙い"] + t["course_note"] + ["", "このレースの過去10回"] + [f"・{x}" for x in t["profile"]] + \
        ["", "競馬場・距離ごとの傾向（過去10年・人気をそろえた比較）"] + [f"・{x}" for x in c["trends"] if not x.startswith(("今日", "前日"))] + ["",
         "4. 今日の馬場と展開"] + [f"・{x}" for x in c["trends"] if x.startswith(("今日", "前日"))] + \
        [f"・前に行きたい馬（直近5走で前にいることが多い馬）: {'・'.join(r.nm(u) for u in g['前で運ぶ']) or 'なし'}",
         f"・後ろから行く馬: {'・'.join(r.nm(u) for u in g['後ろから']) or 'なし'}",
         "レース前にペースを当てるのは難しいため、展開は「前に行きたい馬の数」までにとどめています。", "",
         "5. オッズ一覧（全頭）"]
    for h in sorted(c["horses"], key=lambda x: x["pop"]):
        N.append(f"{h['pop']}番人気 {circ(h['uma'])}{h['name']} {h['odds']}倍")
    N += ["", "6. 追い切りと陣営の話", CONT["oikiri_note"], "印を付けた馬の追い切り・陣営の話は、7の各馬の分析に入れています。", "",
          "7. 有力馬 詳細分析"]
    for lab, u in r.marked:
        N += [f"{lab}{r.nm(u)}　勝つ確率{r.pct(u)}"] + [f"✅{x}" for x in r.points(u)] + brief(r, u) + [""]
    for u in r.caution:
        N += [f"軸にしない馬 {r.nm(u)}（{r.h[u]['pop']}番人気）　勝つ確率{r.pct(u)}"] + [f"・{x}" for x in r.facts(u)[:2]] + [""]
    if pop_view(r) or gap_marks(r):
        N += ["人気と印がずれた馬", "印は強さの順ではなく「勝つ確率が人気より高いか（割安さ）」の順です。"]
        for u, lab in pop_view(r):
            N += [f"{lab or '印なし'}{r.nm(u)}（{r.h[u]['pop']}番人気）を下げた理由"] + why_low(r, u)
        for lab, u in gap_marks(r):
            N += [f"{lab}{r.nm(u)}（{r.h[u]['pop']}番人気）を上げた理由"] + why_high(r, u)
        N += ["評価を下げた＝負けると見ている、ではありません。人気どおりの確率なら、買っても得にならないという意味です。", ""]
    if watch_dropped(r):
        N += ["1週間前の注目馬で印を外した馬"]
        for u, x in watch_dropped(r):
            N += [f"{r.nm(u)}（{r.h[u]['pop']}番人気）　1週間前に注目した理由：{x['lead']}"] + why_dropped(r, u, x)
        N += ["印を外した＝負けると見ている、ではありません。", ""]
    N += ["8. 全頭短評"]
    for h in c["horses"]:
        u = h["uma"]
        mk = c["marks"].get(str(u), "")
        N.append(f"{h['waku']}枠{circ(u)}{h['name']}（{h['sexage']}・{h['jockey']}）{mk} 勝つ確率{h['p_model']*100:.1f}%・{h['pop']}番人気。{first_clause(r.facts(u)[0], 60) if r.facts(u) else ''}")
    N += ["", "9. 勝つ確率のランキング TOP5"]
    for i, h in enumerate(c["horses"][:5], 1):
        N.append(f"{i}位 {circ(h['uma'])}{h['name']} {h['p_model']*100:.1f}%（人気が示す確率{h['p_market']*100:.1f}%）")
    N += ["確率は、人気（オッズ）を土台に、馬の過去10年の成績・コースの傾向・同じレースの過去10回を加えた統計モデルで出しています。追い切りや陣営の話はこの確率には入っていません。", "",
          "10. 最終予想印まとめ"] + [f"{lab}{r.nm(u)}　{r.points(u, 1)[0]}" for lab, u in r.marked] + ["",
          "11. 買い目設計", "買い目は、的中する確率とオッズを掛けた「期待値」で決めます。100%を超えない組み合わせは買う根拠がありません。", "", "予想印"] + [f"{lab}{r.nm(u)}" for lab, u in r.marked] + [""] + r.kaime_lines() + ["", r.verdict(), ODDS_NOTE, "",
          "12. まとめ",
          f"・本命は{r.nm(hon)}。{r.points(hon, 1)[0]}",
          f"・相手は{r.nm(m['○'][0])}と{r.nm(m['▲'][0])}。△は{'・'.join(r.nm(u) for u in m['△'])}",
          f"・買い目は「{r.kaime_short()}」",
          "", "結果もそのまま報告します。フォローしてお待ちいただけると嬉しいです🐴", "", f"{TAGS} {t['tag']} #競馬 #重賞予想"]
    return N


PROBLEMS = []


def check(label, text, limit=None, fold=False):
    body = "\n".join(l for l in text.split("\n") if not re.match(r"^\s*\d\d/\d\d ", l))   # 成績行のレース名（例: 日刊スポーツ賞）は除く
    hits = [b for b in BAN if b in body]
    if hits:
        PROBLEMS.append(f"{label}: 禁止語 {hits}")
    if limit and len(text) > limit:
        PROBLEMS.append(f"{label}: {len(text)}字（上限{limit}）")
    if fold:
        above = text.split(DETAIL)[0].rstrip()
        if len(above) > FOLD + 20 or above.count("\n") > 8:
            PROBLEMS.append(f"{label}: 結論部分が{len(above)}字・{above.count(chr(10)) + 1}行（折りたたみ前に収まらない可能性）")
    for ln in text.split("\n"):
        if "3連単" in ln or "中央値" in ln:
            continue
        for amt in re.findall(r"([\d,]+)円", ln):
            v = int(amt.replace(",", ""))
            if 0 < v < 100000 and v % 100:
                PROBLEMS.append(f"{label}: 100円単位でない金額 {amt}円")


from docx import Document
from docx.shared import Pt

doc = Document()
doc.styles["Normal"].font.size = Pt(10)


def box(title, text, limit=None, fold=False):
    above = len(text.split(DETAIL)[0].rstrip()) if fold else None
    doc.add_heading(f"{title}　{len(text)}字" + (f"（折りたたみ前 {above}字）" if fold else "") + (f"/{limit}字 {'OK' if len(text) <= limit else '⚠超過'}" if limit else ""), 3)
    tb = doc.add_table(rows=1, cols=1); tb.style = "Table Grid"; tb.cell(0, 0).text = text
    doc.add_paragraph()
    check(title, text, limit, fold)


doc.add_heading(f"重賞 SNS投稿案（新エンジン版・充実版）— {DATE}", 0)
doc.add_paragraph("印・確率・買い目は、過去10年のデータ＋コース傾向＋同じレースの過去10回＋今日の馬場を使った新しい予想エンジンの値です。"
                  "X は約140字・8行で折りたたまれるため、各投稿の冒頭に結論を集め、根拠は「─── 詳細 ───」の下に置いています。各レース X7＋Threads6＋note。")
for c in CARDS:
    if not c["graded"] or c["name"] not in CR:
        continue
    r = Race(c)
    doc.add_page_break()
    doc.add_heading(f"■ {c['name']}（{r.t['grade']}）{DATE} {r.t['start']}　{c['venue']} {r.t['course']}　{c['n']}頭", 1)
    doc.add_heading("予想印と確率", 2)
    tb = doc.add_table(rows=0, cols=7); tb.style = "Table Grid"
    for row in [["印", "馬", "馬名", "性齢・斤量・騎手", "脚質", "勝つ確率", "人気が示す確率"]] + \
               [[lab, f"{r.h[u]['waku']}枠{circ(u)}", r.h[u]["name"], f"{r.h[u]['sexage']} {r.h[u]['kin']:g}kg {r.h[u]['jockey']}", r.h[u].get("style", ""),
                 f"{r.h[u]['p_model']*100:.1f}%", f"{r.h[u]['p_market']*100:.1f}%（{r.h[u]['pop']}人気）"] for lab, u in r.marked]:
        cs = tb.add_row().cells
        for j, v in enumerate(row):
            cs[j].text = str(v)
    doc.add_heading("買い目と期待値", 2)
    for x in r.kaime_lines():
        doc.add_paragraph(x)
    doc.add_paragraph(r.verdict() + ODDS_NOTE)
    doc.add_heading("X（7本）", 2)
    xs = x_posts(r)
    for t, p in xs:
        box(f"{c['name']} {t}", p)
    doc.add_heading("Threads（6本・各500字以内）", 2)
    ts = threads_posts(r)
    for t, p in ts:
        box(f"{c['name']} {t}", p, 500)
    doc.add_heading("note記事（12セクション）", 2)
    note = "\n".join(note_article(r))
    check(f"{c['name']} note", note)
    doc.add_paragraph(note)
    (D / f"{a.dir}_{c['name']}_note記事_エンジン版.txt").write_text(note, encoding="utf-8")
    print(f"■ {c['name']}: X {[len(p) for _, p in xs]}字（冒頭 {[len(p.split(DETAIL)[0].rstrip()) for _, p in xs]}） ／ Threads {[len(p) for _, p in ts]}字 ／ note {len(note):,}字")

out = D / f"{a.dir}_重賞_SNS投稿案_エンジン版.docx"
try:
    doc.save(out)
except PermissionError:
    out = D / f"{a.dir}_重賞_SNS投稿案_エンジン版_new.docx"; doc.save(out)
PROBLEMS = list(dict.fromkeys(PROBLEMS))            # X・Threads・note で同じ指摘が重なるのをまとめる
print("検査: " + ("問題なし" if not PROBLEMS else f"{len(PROBLEMS)}件"))
for x in PROBLEMS:
    print("  ⚠", x)
print("保存:", out)
