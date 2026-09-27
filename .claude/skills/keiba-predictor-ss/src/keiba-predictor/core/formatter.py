"""出力フォーマッター - CLI表示用"""
import json
from typing import Dict, List, Optional

try:
    from tabulate import tabulate
    _TABULATE_AVAILABLE = True
except ImportError:
    _TABULATE_AVAILABLE = False


# 印の順番（上位5頭）
_MARKS = ['◎', '○', '▲', '△', '×']
_LINE_WIDTH = 54


class OutputFormatter:
    """
    予想結果・バックテスト・週次レポートを CLI 向けにフォーマットするクラス。
    要件定義の出力フォーマットに準拠する。
    """

    # ------------------------------------------------------------------
    # メイン出力
    # ------------------------------------------------------------------

    def format_prediction(
        self,
        race_data: Dict,
        eliminated: List[Dict],
        remaining: List[Dict],
        predictions: List[Dict],
        recommendations: List[Dict],
        difficulty: Dict,
        bias: Optional[Dict] = None,
    ) -> str:
        """予想結果を要件定義フォーマットで組み立てる。

        Parameters
        ----------
        race_data:
            レース基本情報（date, venue, race_num, race_name,
            surface, distance, condition, num_runners, cushion_value）。
        eliminated:
            消去馬リスト（elimination_rule / elimination_reason 付き）。
        remaining:
            消去後の残存馬リスト。
        predictions:
            ``[{post, name, win_prob, show_prob}, ...]`` の推定結果（勝率降順）。
        recommendations:
            ``[{type, combination, odds, expected_value}, ...]`` の推奨馬券リスト。
        difficulty:
            ``{score, reasons, should_skip}`` の難易度判定結果。
        bias:
            ``{inner_advantage, front_advantage}`` の馬場バイアス（省略可）。

        Returns
        -------
        str
            CLI に出力する文字列。
        """
        lines: List[str] = []
        sep = "=" * _LINE_WIDTH

        # --- ヘッダー ---
        lines.append(sep)
        lines.append(
            f"{race_data.get('date', '')}  "
            f"{race_data.get('venue', '')}"
            f"{race_data.get('race_num', '')}R  "
            f"{race_data.get('race_name', '')}"
        )
        lines.append(
            f"{race_data.get('surface', '')}"
            f"{race_data.get('distance', '')}m  "
            f"{race_data.get('condition', '')}  "
            f"{race_data.get('num_runners', 0)}頭"
        )
        diff_score = difficulty.get('score', '-')
        cushion = race_data.get('cushion_value', 'N/A')
        upset = difficulty.get('upset_score', 0)
        upset_label = "堅い" if upset <= 2 else ("やや荒れ" if upset <= 5 else "大荒れ警戒")
        lines.append(f"レース難易度: {diff_score}  荒れ度: {upset}({upset_label})  クッション値: {cushion}")

        if bias:
            inner = bias.get('inner_advantage', 0)
            front = bias.get('front_advantage', 0)
            lines.append(
                f"馬場バイアス: 内有利度({inner:+.0f})  先行有利度({front:+.0f})"
            )
        lines.append(sep)

        # --- 消去馬 ---
        if eliminated:
            lines.append(f"\n【消去馬】{len(eliminated)}頭")
            for h in eliminated:
                rule = h.get('elimination_rule', '?')
                reason = h.get('elimination_reason', '')
                lines.append(
                    f"  {h.get('post', 0):2d} {h.get('name', ''):8s}"
                    f" → {rule}: {reason}"
                )

        # --- 推定勝率（上位5頭） ---
        lines.append("\n【推定勝率】")
        for rank, pred in enumerate(predictions[:5]):
            mark = self._get_mark(rank)
            win_pct = pred.get('win_prob', 0.0) * 100
            show_pct = pred.get('show_prob', 0.0) * 100
            lines.append(
                f"  {mark} {pred.get('post', 0):2d} {pred.get('name', ''):8s}"
                f"  推定勝率:{win_pct:5.1f}%"
                f"  推定複勝率:{show_pct:5.1f}%"
            )

        # --- 根拠（上位5頭の詳細） ---
        lines.append("\n【根拠】")
        for rank, pred in enumerate(predictions[:5]):
            mark = self._get_mark(rank)
            post = pred.get('post', 0)
            name = pred.get('name', '')
            lines.append(f"\n  {mark} {post} {name}")

            # 馬情報
            jockey = pred.get('jockey', '')
            sire = pred.get('sire', '')
            bms = pred.get('bms', '')
            sex = pred.get('sex', '')
            age = pred.get('age', '')
            futan = pred.get('weight_carried', '')
            if jockey:
                lines.append(f"    騎手: {jockey}  {sex}{age}歳  斤量{futan}kg")
            if sire:
                lines.append(f"    血統: {sire} × {bms}")

            # エンジンスコア
            scores = pred.get('scores', {})
            if scores:
                bars = []
                for key, label in [
                    ('ability', '能力'),
                    ('jockey', '騎手'),
                    ('course', 'コース'),
                    ('bloodline', '血統'),
                    ('condition', '状態'),
                    ('trainer', '調教師'),
                ]:
                    val = scores.get(key, 0)
                    bar_len = int(val / 10)
                    bar = '█' * bar_len + '░' * (10 - bar_len)
                    bars.append(f"    {label:4s} {bar} {val:4.0f}")
                lines.extend(bars)

            # オッズ・推定人気・CR
            est_pop = pred.get('est_pop')
            cr = pred.get('cr_value')
            odds = pred.get('win_odds')
            info_parts = []
            if est_pop:
                info_parts.append(f"推定人気{est_pop}番")
            if cr:
                info_parts.append(f"CR値{cr}")
            if odds:
                info_parts.append(f"単勝{odds}倍")
            if info_parts:
                lines.append(f"    {' / '.join(info_parts)}")

            # 過去走
            past = pred.get('past_summary', [])
            if past:
                past_strs = []
                for p in past:
                    f = p.get('finish')
                    d = p.get('distance')
                    f3 = p.get('last_3f')
                    pop = p.get('popularity')
                    s = f"{f}着" if f else "?"
                    if d:
                        s += f"/{d}m"
                    if f3:
                        s += f"/上{f3}"
                    if pop:
                        s += f"/{pop}人気"
                    past_strs.append(s)
                lines.append(f"    近走: {' → '.join(past_strs)}")

        # --- 信頼度 ---
        lines.append("\n【信頼度】")
        # データ充実度で信頼度を算出
        top = predictions[0] if predictions else {}
        past_count = len(top.get('past_summary', []))
        has_odds = top.get('win_odds') is not None and top.get('win_odds', 0) > 0
        has_cr = top.get('cr_value') is not None
        score_vals = list((top.get('scores') or {}).values())
        non_default = sum(1 for v in score_vals if v != 50 and v != 0)

        confidence_pts = 0
        confidence_pts += min(past_count, 3) * 15   # 過去走データ（最大45）
        confidence_pts += 20 if has_odds else 0       # オッズあり
        confidence_pts += 10 if has_cr else 0          # CR値あり
        confidence_pts += non_default * 5              # エンジンスコア有効数
        confidence_pts = min(confidence_pts, 100)

        if confidence_pts >= 70:
            conf_label = "高（データ十分）"
        elif confidence_pts >= 40:
            conf_label = "中（一部データ不足）"
        else:
            conf_label = "低（データ不足 — 参考程度）"

        lines.append(f"  データ充実度: {confidence_pts}/100  → {conf_label}")

        if not has_odds:
            lines.append("  ⚠ オッズ未反映（期待値は参考値）")
        if past_count == 0:
            lines.append("  ⚠ 過去走データなし（新馬戦の可能性）")
        lines.append(
            f"  ※ 現在はルールベース予測（LightGBM学習前）。"
            f"データ蓄積後に精度向上します。"
        )

        # --- 期待値判定 ---
        lines.append("\n【期待値判定】")
        if recommendations:
            for rec in recommendations:
                ev = rec.get('expected_value', 0.0)
                odds = rec.get('odds', 0.0)
                combo = rec.get('combination', '')
                ticket_type = rec.get('type', '')
                flag = "  ← 妙味あり★" if ev >= 1.2 else ""
                lines.append(
                    f"  {ticket_type:<4s} {combo:<8s}"
                    f"  オッズ{odds:6.1f}倍"
                    f"  期待値{ev:.2f}{flag}"
                )
        else:
            lines.append("  期待値>1.0の馬券なし → 見送り推奨")

        # --- 三連複推奨（発表の戦略: 人気馬2+穴馬1） ---
        lines.append("\n【三連複推奨】")
        if len(predictions) >= 3:
            # 戦略: 人気上位2頭（軸）+ AI高評価の穴馬1頭（高配当狙い）
            # 10170頭統計: 3着内の平均人気=4.5、人気差が最重要指標
            top2 = predictions[:2]  # 人気上位2頭を軸に

            # 穴馬候補: 予想3-7位で人気5番以降（AIは評価しているが市場は低評価）
            value_candidates = []
            for p in predictions[2:7]:
                pop = int(p.get('est_pop') or 3)
                odds = p.get('win_odds', 0) or 1
                show_prob = p.get('show_prob', 0)
                if pop >= 4:  # 4番人気以降が穴馬候補
                    # 期待値 = 3着内確率 × (配当の高さ)
                    ev_score = show_prob * odds
                    value_candidates.append({
                        'post': p.get('post', 0),
                        'name': p.get('name', ''),
                        'show_prob': show_prob,
                        'pop': pop,
                        'odds': odds,
                        'ev': ev_score,
                    })

            # 穴馬がなければ3番手を使う
            if not value_candidates:
                value_candidates = [{
                    'post': predictions[2].get('post', 0),
                    'name': predictions[2].get('name', ''),
                    'show_prob': predictions[2].get('show_prob', 0),
                    'pop': predictions[2].get('est_pop'),
                    'odds': predictions[2].get('win_odds', 0),
                    'ev': 0,
                }]

            # 期待値が最も高い穴馬を選択
            value_candidates.sort(key=lambda x: x['ev'], reverse=True)
            value_pick = value_candidates[0]

            trio = [
                {'post': top2[0].get('post',0), 'name': top2[0].get('name',''),
                 'pop': top2[0].get('est_pop'), 'odds': top2[0].get('win_odds',0),
                 'show_prob': top2[0].get('show_prob',0), 'role': '軸'},
                {'post': top2[1].get('post',0), 'name': top2[1].get('name',''),
                 'pop': top2[1].get('est_pop'), 'odds': top2[1].get('win_odds',0),
                 'show_prob': top2[1].get('show_prob',0), 'role': '軸'},
                {**value_pick, 'role': '穴'},
            ]

            posts = sorted([h['post'] for h in trio])
            lines.append(f"  ▶ {posts[0]}-{posts[1]}-{posts[2]} （三連複1点 100円）")
            for h in trio:
                pop_str = f"pop{h['pop']}" if h['pop'] else ""
                lines.append(
                    f"    [{h['role']}] {h['post']:2d} {h['name']:10s}"
                    f"  3着内率:{h['show_prob']*100:4.0f}%"
                    f"  {pop_str}"
                    f"  単勝{h['odds']:.1f}倍"
                )
            lines.append("  戦略: 人気上位2頭（軸）+ AI高評価の穴馬1頭")
        else:
            lines.append("  出走馬不足（3頭未満）")

        # --- 推奨アクション ---
        if difficulty.get('should_skip'):
            lines.append(
                f"\n【見送り】難易度{diff_score} "
                f"→ 見送り推奨"
                + (f"（理由: {', '.join(difficulty.get('reasons', []))}）"
                   if difficulty.get('reasons') else "")
            )
        elif recommendations:
            count = len(recommendations)
            lines.append(f"\n【推奨】単複{count}点 + 三連複1点 （{count * 100 + 100}円）")
        else:
            lines.append("\n【見送り】期待値基準を満たす馬券なし")

        lines.append(sep)
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # 週次/月次レポート
    # ------------------------------------------------------------------

    def format_report(self, tracking_data: Dict) -> str:
        """週次/月次サマリーレポートをフォーマットする。

        Parameters
        ----------
        tracking_data:
            ``{period, hit_rates, roi, num_races, num_bets,
               overfitting_alert, skip_accuracy}`` 形式の集計データ。

        Returns
        -------
        str
            サマリーレポート文字列。
        """
        lines: List[str] = []
        sep = "-" * _LINE_WIDTH
        period = tracking_data.get('period', '集計期間不明')

        lines.append("=" * _LINE_WIDTH)
        lines.append(f"  競馬予想ツール サマリーレポート（{period}）")
        lines.append("=" * _LINE_WIDTH)

        # --- 基本統計 ---
        lines.append(f"対象レース数  : {tracking_data.get('num_races', 0)}レース")
        lines.append(f"購入馬券数    : {tracking_data.get('num_bets', 0)}点")
        lines.append(sep)

        # --- 馬券種別の的中率 ---
        hit_rates: Dict = tracking_data.get('hit_rates', {})
        if hit_rates:
            lines.append("【馬券種別 的中率】")
            for ticket_type, rate in hit_rates.items():
                lines.append(f"  {ticket_type:<6s}: {rate * 100:5.1f}%")
            lines.append(sep)

        # --- 回収率 ---
        roi = tracking_data.get('roi', {})
        if roi:
            lines.append("【回収率】")
            lines.append(f"  通常       : {roi.get('normal', 0.0) * 100:.1f}%")
            lines.append(
                f"  外れ値除外 : {roi.get('outlier_excluded', 0.0) * 100:.1f}%"
                "  （100倍超の配当を除外）"
            )
            lines.append(sep)

        # --- 見送り精度 ---
        skip_acc = tracking_data.get('skip_accuracy')
        if skip_acc is not None:
            lines.append(f"見送りレース利益回避率: {skip_acc * 100:.1f}%")

        # --- 消去精度 ---
        elim_acc = tracking_data.get('elimination_accuracy')
        if elim_acc is not None:
            lines.append(f"消去精度（消去馬が来なかった率）: {elim_acc * 100:.1f}%")

        # --- 過学習アラート ---
        if tracking_data.get('overfitting_alert'):
            lines.append("")
            lines.append(
                "[ALERT] 過学習の可能性があります。"
                "バックテストROIと実績ROIの乖離を確認してください。"
            )

        lines.append("=" * _LINE_WIDTH)
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # JSON 出力
    # ------------------------------------------------------------------

    def format_json(self, data: Dict, indent: int = 2) -> str:
        """辞書データを JSON 文字列に変換する。

        Parameters
        ----------
        data:
            出力したい辞書データ。
        indent:
            JSON のインデント幅（デフォルト 2）。

        Returns
        -------
        str
            JSON 文字列。
        """
        return json.dumps(data, ensure_ascii=False, indent=indent, default=str)

    # ------------------------------------------------------------------
    # テーブル出力（tabulate）
    # ------------------------------------------------------------------

    def format_table(
        self,
        rows: List[Dict],
        headers: Optional[List[str]] = None,
        tablefmt: str = 'simple',
    ) -> str:
        """辞書リストをテーブル形式でフォーマットする。

        Parameters
        ----------
        rows:
            各行を辞書で表現したリスト。
        headers:
            表示するキーの順序リスト。None の場合は rows[0] のキー順。
        tablefmt:
            tabulate のテーブルフォーマット。

        Returns
        -------
        str
            テーブル文字列。tabulate が使えない場合は簡易フォーマット。
        """
        if not rows:
            return "（データなし）"

        if headers is None:
            headers = list(rows[0].keys())

        if _TABULATE_AVAILABLE:
            table_data = [[row.get(h, '') for h in headers] for row in rows]
            return tabulate(table_data, headers=headers, tablefmt=tablefmt)

        # tabulate 未インストール時の簡易フォーマット
        lines: List[str] = ["\t".join(headers)]
        for row in rows:
            lines.append("\t".join(str(row.get(h, '')) for h in headers))
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # 内部ユーティリティ
    # ------------------------------------------------------------------

    def _get_mark(self, rank: int) -> str:
        """順位に対応する印を返す（0始まり）。"""
        return _MARKS[rank] if rank < len(_MARKS) else "  "
