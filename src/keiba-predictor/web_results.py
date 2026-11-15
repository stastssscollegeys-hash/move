# -*- coding: utf-8 -*-
"""web_results.py — Yahoo!スポーツナビ競馬の結果ページから、着順・払戻・ラップを取る（2026-11-07 新設・JV 0B12 の代わり）
  python web_results.py --date 20261107   → {OUT}/{日付}_web_results.json
人気は月曜まで '-'（オッズ(単勝確定)から順位を付け直す）。払戻は100円あたり。"""
import argparse, json, re, sys
sys.stdout.reconfigure(encoding="utf-8")
import web_live as W

def yen(s): return int(re.sub(r"[^\d]", "", s))

def corner_pos(s):
    """'(*1,9)(2,8,10)6-4,7,5-3' → {馬番: 順位}（かたまり内は同順位・先頭は1）"""
    pos, n, i, grp = {}, 0, 0, False
    cur = []
    for tok in re.findall(r"\(|\)|\d+|[,\-]", s.replace("*", "")):
        if tok == "(":
            grp, cur = True, []
        elif tok == ")":
            for u in cur: pos[u] = n + 1
            n += len(cur); grp = False
        elif tok.isdigit():
            if grp: cur.append(int(tok))
            else:
                n += 1; pos[int(tok)] = n
    return pos


def parse(rid):
    soup = W.get(W.BASE + "result/" + rid)
    main = soup.find("main") or soup
    lines = main.get_text("\n", strip=True).split("\n")
    pay = {}
    i = lines.index("払戻金") if "払戻金" in lines else 0
    kinds = ["単勝", "複勝", "枠連", "馬連", "ワイド", "馬単", "3連複", "3連単"]
    cur = None
    j = i
    end = lines.index("競走成績") if "競走成績" in lines else len(lines)
    seg = lines[j:end]
    k = 0
    while k < len(seg):
        if seg[k] in kinds:
            cur = seg[k]; pay.setdefault(cur, []); k += 1; continue
        if cur and k + 2 < len(seg) and re.fullmatch(r"[\d\-]+", seg[k]) and seg[k + 1].endswith("円"):
            pay[cur].append(dict(comb=seg[k], yen=yen(seg[k + 1]), pop=int(seg[k + 2]) if seg[k + 2].isdigit() else None)); k += 3; continue
        k += 1
    rows = []
    for tr in main.select("table tbody tr"):
        c = [re.sub(r"\s+", " ", td.get_text(" ", strip=True)) for td in tr.find_all("td")]
        if len(c) == 9 and c[0].isdigit() and c[2].isdigit():
            nm = c[3].rsplit(" ", 1)
            tm = c[4].split(" ", 1)
            od = re.search(r"\(([\d.]+)\)", c[7])
            jk = c[6].rsplit(" ", 1)
            rows.append(dict(rank=int(c[0]), waku=int(c[1]), uma=int(c[2]), name=nm[0].replace(" ", ""), body=nm[1] if len(nm) > 1 else "", time=tm[0], margin=tm[1] if len(tm) > 1 else "",
                             l3=c[5], jockey=jk[0], kin=jk[1] if len(jk) > 1 else "", odds=float(od.group(1)) if od else None, trainer=c[8]))
    txt = "\n".join(lines)
    lap = re.findall(r"(\d+:\d+\.\d|\d+\.\d)\(([\d.]+)\)", txt)
    corners = {}
    for tr in main.select("table tr"):
        c = [td.get_text("", strip=True) for td in tr.find_all(["td", "th"])]
        if len(c) == 2 and re.fullmatch(r"\d+コーナー", c[0]):
            corners[c[0]] = corner_pos(c[1])
    cp = {}
    for cn in sorted(corners):
        for u, pos in corners[cn].items():
            cp.setdefault(u, []).append(pos)
    return dict(pay=pay, rows=rows, lap=[float(b) for a, b in lap], corners={u: "-".join(map(str, v)) for u, v in cp.items()}, text_ok=bool(rows))


def corner_pos(s):
    """'(*1,9)(2,8,10)6-4,7,5-3' → {馬番: 順位}（かたまり内は同順位・先頭は1）"""
    pos, n, grp, cur = {}, 0, False, []
    for tok in re.findall(r"\(|\)|\d+|[,\-]", s.replace("*", "")):
        if tok == "(":
            grp, cur = True, []
        elif tok == ")":
            for u in cur:
                pos[u] = n + 1
            n += len(cur)
            grp = False
        elif tok.isdigit():
            if grp:
                cur.append(int(tok))
            else:
                n += 1
                pos[int(tok)] = n
    return pos

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--date", required=True); a = ap.parse_args()
    d = json.load(open(W.OUT / f"{a.date}_web_probs.json", encoding="utf-8"))["races"]
    out = {}
    for k, v in d.items():
        try:
            r = parse(v["rid"])
        except Exception as e:
            print("ERR", k, e); continue
        r.update(title=v["title"], dist=v["dist"], baba=v["baba"], n=v["n"], venue=v["venue"], R=v["R"])
        for i, h in enumerate(sorted([x for x in r["rows"] if x["odds"]], key=lambda x: x["odds"])): h["pop"] = i + 1
        out[k] = r
        t = [h["uma"] for h in sorted(r["rows"], key=lambda x: x["rank"])[:3]]
        print(k, v["title"], t, len(r["rows"]), "頭", "3連単", r["pay"].get("3連単"))
    (W.OUT / f"{a.date}_web_results.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
if __name__ == "__main__":
    main()
