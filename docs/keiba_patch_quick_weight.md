# 本体（v5.1）の `ev_live.py --quick` に当日の馬体重を入れる修正（2026-10-14）

## 何が起きていたか

`--quick` は朝に作った特徴量（`db/ev_cache/{日付}.pkl`）にオッズだけ入れ替えて計算する。
馬体重は発走の約1時間前に発表されるので、**朝の特徴量では馬体重の列が全部0のまま、発走前の本番の計算に使われていた**。
学習では確定の馬体重で「馬体重 増減」「10kg以上減」「10kg以上増」が効いているのに、本番では効いていなかった。
2026-10-14 に採用した「馬体重（470kgとの差）」「馬体重 439kg以下」も同じ扱いになる。

もう1つ: `load_wh()` は増減が出ない馬（初出走・前走計不能＝増減999）を**体重ごと捨てていた**。学習データ（TARGET）では
初出走の馬は `"506"` の形で体重が入っているので、本番も同じ形で残す。

このブランチ（worktree-keiba-word-order）の `ev_live.py` は `--quick` が無く、レースごとに全部計算するので、
当日の馬体重は入っている。`load_wh()` の修正はこのブランチで済んでいる。

## 修正（本体の `src/keiba-predictor/ev_live.py`）

1) `load_wh()` の中（増減999の馬も体重を残す）:

```python
            if uma.strip().isdigit() and wt.strip().isdigit() and int(wt) > 0:
                if df.strip().isdigit() and df.strip() != "999":
                    out[(venue, R, int(uma))] = f"{int(wt)}({'-' if sg == '-' else '+'}{int(df)})"
                else:                                      # 初出走・前走計不能は増減なし。学習データと同じ "506" の形
                    out[(venue, R, int(uma))] = f"{int(wt)}"
```

2) `run()` の `quick` の枝（`liv.append(...)` の所）:

```python
        import weight_refresh as WR
        wh = load_wh(date)                                  # 当日発表の馬体重（JV速報 0B11）
        for c in cache["races"]:
            ...
            uma = [c["uma"][i] for i in keep]
            X = WR.refresh(c["X"][keep], c["key"], uma, wh, E.F)     # 馬体重の列だけ当日の値で上書き
            inv = np.array([1 / tan[u] for u in uma])
            liv.append(dict(key=c["key"], uma=uma, X=X, q=inv / inv.sum(), odds=np.array([tan[u] for u in uma]), part="live"))
        k, n = WR.coverage(liv, wh)
        print(f"  当日の馬体重 {k}/{n}頭を反映")
```

`weight_refresh.py` はこのブランチにある（`ev_engine` と同じ式。`python -c` の単体確認済み: 484(+12)→増減1.2・10kg以上増1・470との差0.35／430→−1.0・439kg以下1）。

## 確かめ方

レース当日、発走35分前の `--quick` のログに「当日の馬体重 ○/○頭を反映」が出て、○がほぼ全頭であること。
朝の重い計算（全部計算）では体重は0頭で正常（未発表）。
