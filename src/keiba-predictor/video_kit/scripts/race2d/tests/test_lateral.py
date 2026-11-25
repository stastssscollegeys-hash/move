"""2026-11-20 ユーザー「急に移動したり最後の方バグってるところない?」→ 馬が1コマに最大1.8m 横に滑っていた。
横の速さの上限（build_frames.py の LAT_V）が効いているかを、福島記念 2026 の予想の着順（fukushima_pred.json）で見る。"""
import json, math, subprocess, sys, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _frames(tmp):
    out = Path(tmp) / "f.json"
    subprocess.run([sys.executable, str(HERE.parent / "build_frames.py"), str(HERE / "fukushima_pred.json"), str(out),
                    "--w", "1620", "--h", "1080", "--fast", "5.6", "--slow", "4.0"], check=True, capture_output=True)
    return json.loads(out.read_text(encoding="utf-8"))


def _lateral(F, f, i):
    n = len(F)
    a, b = F[f - 1]["p"][i], F[f]["p"][i]
    a5, b5 = F[max(0, f - 6)]["p"][i], F[min(n - 1, f + 5)]["p"][i]
    hx, hy = b5[0] - a5[0], b5[1] - a5[1]
    l = math.hypot(hx, hy)
    if l < 0.5:
        return 0.0
    return abs(-(b[0] - a[0]) * hy / l + (b[1] - a[1]) * hx / l)


def test_no_sideways_jump():
    with tempfile.TemporaryDirectory() as tmp:
        p = _frames(tmp)
    F = p["frame"]
    worst = max(_lateral(F, f, i) for f in range(31, len(F) - 1) for i in range(len(F[f]["p"])))
    late = max(_lateral(F, f, i) for f in range(31, len(F) - 1) if F[f]["rem"] <= p["final_m"] for i in range(len(F[f]["p"])))
    assert worst < 0.9, f"1コマに {worst:.2f}m 横に動いた（前は 1.8m）"
    assert late < 0.35, f"最後の直線（ゆっくりの区間）で1コマに {late:.2f}m 横に動いた（前は 1.33m）"
