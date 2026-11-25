# -*- coding: utf-8 -*-
"""全コース対応（2026-11-20）のテスト。使い方: python3 -m unittest discover -s scripts/race2d/tests -v
データ＝JV-Link から作った race2d の JSON（東京 フェブラリーS 2026・札幌 丹頂S 2025・福島 奥羽S 2025）
"""
import json, math, subprocess, sys, tempfile, unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
R2 = HERE.parent
sys.path.insert(0, str(R2))
from course_key import course_key          # noqa: E402
import build_frames as BF                  # noqa: E402

CS = json.loads((R2 / "courses.json").read_text(encoding="utf-8"))
VENUES = ["札幌", "函館", "福島", "新潟", "東京", "中山", "中京", "京都", "阪神", "小倉"]


def frames(src, *extra):
    with tempfile.TemporaryDirectory() as d:
        out = Path(d) / "f.json"
        subprocess.run([sys.executable, str(R2 / "build_frames.py"), str(HERE / src), str(out), *extra], check=True, capture_output=True)
        return json.loads(out.read_text(encoding="utf-8"))


def signed_area(P):
    return sum(P[i][0] * P[i + 1][1] - P[i + 1][0] * P[i][1] for i in range(len(P) - 1))


class TestCourses(unittest.TestCase):
    def test_course_key(self):
        self.assertEqual(course_key("京都", "18"), "京都_芝外")      # 菊花賞・天皇賞（春）の 3000m・3200m（JV-Link で確認）
        self.assertEqual(course_key("京都", "17"), "京都_芝")
        self.assertEqual(course_key("新潟", "12"), "新潟_芝外")
        self.assertEqual(course_key("新潟", "10"), "新潟_直線")
        self.assertEqual(course_key("東京", "23"), "東京_ダート")
        self.assertEqual(course_key("阪神", 24), "阪神_ダート")

    def test_all_venues_in_courses_json(self):
        for v in VENUES:
            self.assertIn(f"{v}_芝", CS); self.assertIn(f"{v}_ダート", CS)
            for k in (f"{v}_芝", f"{v}_ダート"):
                self.assertIn(CS[k]["turn"], ("left", "right"))
        for v in ("新潟", "中山", "京都", "阪神"):
            self.assertIn(f"{v}_芝外", CS)
        self.assertIn("新潟_直線", CS)
        left = {k.split("_")[0] for k, c in CS.items() if not k.startswith("_") and c["turn"] == "left"}
        self.assertEqual(left, {"東京", "新潟", "中京"})              # JRA：左回りは東京・新潟・中京だけ

    def test_every_course_has_a_shape(self):
        """全部のコースで形が作れる（地図に線が無い場は公式の1周から）。輪の長さは公式の1周にそろう"""
        for k, c in CS.items():
            if k.startswith("_"): continue
            g = BF.load_shape(c, CS)
            self.assertIn(c["loop"], g["loops"], k)
            sc = BF.ShapeCourse(c, 1600, True, g)
            L = sum(math.dist(sc.P[i], sc.P[(i + 1) % sc.N]) for i in range(sc.N))
            self.assertAlmostEqual(L, c["lap"], delta=c["lap"] * 0.01, msg=k)

    def test_synth_nested(self):
        g = BF.synth_shape("函館", CS)
        r = {k: max(abs(p[1]) for p in v) for k, v in g["loops"].items()}
        self.assertLess(r["ダート"], r["芝"])                     # ダートが芝の内側

    def test_right_handed_runs_clockwise(self):
        for src, want in (("sapporo_tancho.json", "right"), ("fukushima_ou.json", "right"), ("tokyo_feb.json", "left")):
            d = frames(src)
            self.assertEqual(d["track"]["turn"], want, src)
            a = signed_area([fr["lead"] for fr in d["frame"]])
            self.assertTrue(a < 0 if want == "right" else a > 0, f"{src} の向きが {want} と合わない")

    def test_tokyo_unchanged_shape(self):
        """東京は地図の実物の形のまま（作った形に落ちない）"""
        g = BF.load_shape(CS["東京_ダート"], CS)
        self.assertFalse(g.get("synthetic", False))


if __name__ == "__main__":
    unittest.main()
