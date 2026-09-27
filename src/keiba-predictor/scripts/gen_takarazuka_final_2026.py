"""
宝塚記念2026 SNS投稿案 当日最終版 生成スクリプト
前回のSNS投稿案をベースに、当日朝の最新情報を反映
"""
import shutil
from docx import Document
from docx.shared import Pt, RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

src = r"C:\Users\User\Desktop\競馬予想レポート\20260614\20260614_宝塚記念_SNS投稿案.docx"
dst = r"C:\Users\User\Desktop\競馬予想レポート\20260614\20260614_宝塚記念_SNS投稿案_当日最終版.docx"

shutil.copy2(src, dst)
print(f"[OK] コピー完了: {dst}")

doc = Document(dst)
body = doc.element.body

def make_para(text, bold=False, color_hex=None, size_pt=None):
    p = OxmlElement('w:p')
    r = OxmlElement('w:r')
    rPr = OxmlElement('w:rPr')
    if bold:
        b = OxmlElement('w:b')
        rPr.append(b)
    if color_hex:
        c = OxmlElement('w:color')
        c.set(qn('w:val'), color_hex)
        rPr.append(c)
    if size_pt:
        sz = OxmlElement('w:sz')
        sz.set(qn('w:val'), str(size_pt * 2))
        rPr.append(sz)
    r.append(rPr)
    t = OxmlElement('w:t')
    t.set(qn('xml:space'), 'preserve')
    t.text = text
    r.append(t)
    p.append(r)
    return p

# 先頭に挿入する当日更新情報（逆順で挿入 → 最終的に正順になる）
update_lines = [
    # (text, bold, color_hex, size_pt)
    ("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", False, None, None),
    ("", False, None, None),
    ("以下、前回のSNS投稿案（変更部分はそのまま使用）", False, "888888", 9),
    ("", False, None, None),
    ("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", False, None, None),
    ("", False, None, None),
    ("6. 買い目：変更なし（12点・10,000円・3ブロック設計を維持）", False, None, None),
    ("   △ 15番 マイユニバース（横山典弘）AI指数128点", False, None, None),
    ("   △  1番 ダノンデサイル（戸崎圭太）AI指数132点 ★最終追い切りメンバートップ確認", False, "006400", None),
    ("   ▲  2番 ミュージアムマイル（D.レーン）AI指数133点", False, None, None),
    ("   ○  5番 クロワデュノール（北村友一）AI指数129点（EV更にマイナス −0.78）", False, None, None),
    ("   ◎ 16番 メイショウタバル（武豊）AI指数136点", False, None, None),
    ("5. 最終予想印：変更なし", True, None, None),
    ("", False, None, None),
    ("   → ただし◎メイショウタバルは昨年この舞台の実際の優勝馬。単純比較不可。", False, None, None),
    ("   → カルプスペルシュは「前走圧勝の逃げ馬」だったが5着。逃げ馬過信に警戒を。", False, None, None),
    ("   昨日（6/13）函館スプリントS：ピューロマジック1着 / カルプスペルシュ5着", False, None, None),
    ("4. 函館SS（6/13）の教訓", True, None, None),
    ("", False, None, None),
    ("   → 馬連・3連複に組み込まない完全消し。", False, "FF0000", None),
    ("   外枠17番（過去10年外枠勝率12%）× 差し脚質 × コース適性不足 = 3重の不利", False, None, None),
    ("3. レガレイラ：17番 大外枠確定 → 完全消し", True, "FF0000", None),
    ("", False, None, None),
    ("   → 馬連・3連複の相手として最優先。状態面の評価が更に上昇。", False, None, None),
    ("   最終追い切りでメンバートップ評価を獲得。", False, None, None),
    ("2. ダノンデサイル：最終追い切りメンバートップ評価確認", True, "006400", None),
    ("", False, None, None),
    ("   → 本命から外す根拠がさらに強化。単勝は絶対に買わない。", False, None, None),
    ("   当日EV = 推定勝率25% × 1.1倍 × 0.80 − 1 = −0.78（前回−0.46からさらにマイナス）", False, "FF0000", None),
    ("   ★クロワデュノールのオッズが前回想定2.7倍 → 当日1.1倍に大幅下落", False, "FF0000", None),
    ("1. クロワデュノール：オッズ更新（2.7倍 → 1.1倍）", True, "FF0000", None),
    ("", False, None, None),
    ("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", False, None, None),
    ("【当日更新情報 2026/06/14 朝（発走15:40まで有効・最終確定版）】", True, "0000CC", 12),
    ("", False, None, None),
    ("★★★  宝塚記念 G1 2026  SNS投稿案 — 当日最終確定版  ★★★", True, "CC0000", 14),
]

for text, bold, color, size in reversed(update_lines):
    p = make_para(text, bold, color, size)
    body.insert(0, p)

doc.save(dst)
print(f"[OK] 当日最終版を保存しました: {dst}")
print()
print("当日変更サマリー:")
print("  ◎ メイショウタバル → 変更なし（前回の立場を維持）")
print("  ○ クロワデュノール → EV更にマイナス（1.1倍）。対抗維持・単勝禁止")
print("  ▲ ミュージアムマイル → 変更なし")
print("  △ ダノンデサイル → 追い切りトップ評価確認。相手として最優先")
print("  × レガレイラ → 17番大外確定・完全消し（新規追加）")
print("  買い目 → 変更なし（12点・10,000円）")
