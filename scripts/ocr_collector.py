#!/usr/bin/env python3
"""
OCR Collector - 画像・動画・PDFからテキストを抽出
=====================================================
ローカルOllama上のQwenビジョンモデルを使用してOCRを実行する。
物語YOUTUBE/generate_script.py のOllamaストリーミングパターンを踏襲。

Usage:
    python scripts/ocr_collector.py scan.png
    python scripts/ocr_collector.py doc.pdf slide.png lecture.mp4
    python scripts/ocr_collector.py --fps 2.0 lecture.mp4
    python scripts/ocr_collector.py -o /tmp/ocr doc.pdf
    python scripts/ocr_collector.py -m qwen2.5vl:72b image.jpg
"""

import argparse
import base64
import json
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from difflib import SequenceMatcher

import requests

# ===== 定数 =====
OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "qwen3.5-397b-a17b"
OUTPUT_DIR = Path(__file__).parent / "ocr_output"

GENERATION_OPTIONS = {
    "temperature": 0.1,
    "top_p": 0.9,
    "num_ctx": 8192,
    "num_predict": 4096,
}

# 対応拡張子
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tiff", ".tif"}
VIDEO_EXTS = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v", ".flv"}
PDF_EXTS = {".pdf"}

# 重複排除の閾値
DUPLICATE_THRESHOLD = 0.9

# OCRプロンプト
OCR_PROMPT = (
    "この画像に含まれるすべてのテキストを正確に抽出してください。"
    "テキスト以外の説明は不要です。画像内のテキストのみをそのまま出力してください。"
    "テキストが存在しない場合は「（テキストなし）」と出力してください。"
)


# ===== データモデル =====
class MediaType(str, Enum):
    IMAGE = "image"
    VIDEO = "video"
    PDF = "pdf"


@dataclass
class PageResult:
    page: int
    text: str
    source_frame: str = ""  # 動画の場合はフレームファイル名


@dataclass
class OcrResult:
    source: str
    media_type: str
    model: str
    timestamp: str
    pages: list = field(default_factory=list)
    full_text: str = ""

    def to_dict(self):
        return {
            "source": self.source,
            "media_type": self.media_type,
            "model": self.model,
            "timestamp": self.timestamp,
            "pages": [asdict(p) if isinstance(p, PageResult) else p for p in self.pages],
            "full_text": self.full_text,
        }


# ===== Ollama Vision API =====
def call_ollama_vision(image_b64: str, prompt: str, model: str = MODEL) -> str:
    """OllamaビジョンAPIを呼び出し、ストリーミングでテキストを返す"""
    messages = [
        {
            "role": "user",
            "content": prompt,
            "images": [image_b64],
        }
    ]
    payload = {
        "model": model,
        "messages": messages,
        "stream": True,
        "options": GENERATION_OPTIONS,
    }
    try:
        full_text = ""
        with requests.post(OLLAMA_URL, json=payload, stream=True, timeout=300) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines():
                if not line:
                    continue
                try:
                    chunk = json.loads(line)
                except json.JSONDecodeError as e:
                    print(f"  [警告] JSONパース失敗: {e}", file=sys.stderr)
                    continue
                if chunk.get("done"):
                    break
                content = chunk.get("message", {}).get("content", "")
                full_text += content
                print(content, end="", flush=True)
        print()
        return full_text.strip()
    except requests.exceptions.ConnectionError:
        print(f"  [エラー] Ollama未起動 ({OLLAMA_URL})", file=sys.stderr)
        raise
    except requests.exceptions.RequestException as e:
        print(f"  [エラー] Ollama API呼び出し失敗: {e}", file=sys.stderr)
        raise


# ===== メディアタイプ判定 =====
def detect_media_type(path: Path) -> MediaType:
    """拡張子からメディアタイプを判定する"""
    ext = path.suffix.lower()
    if ext in IMAGE_EXTS:
        return MediaType.IMAGE
    if ext in VIDEO_EXTS:
        return MediaType.VIDEO
    if ext in PDF_EXTS:
        return MediaType.PDF
    raise ValueError(f"未対応の拡張子: {ext} ({path.name})")


# ===== 画像をBase64エンコード =====
def image_to_b64(image_path: Path) -> str:
    """画像ファイルをBase64文字列に変換する"""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


# ===== 重複排除 =====
def is_duplicate_text(a: str, b: str, threshold: float = DUPLICATE_THRESHOLD) -> bool:
    """2つのテキストが重複しているか判定する（difflib使用）"""
    if not a or not b:
        return False
    ratio = SequenceMatcher(None, a, b).ratio()
    return ratio >= threshold


# ===== 画像OCR =====
def process_image(path: Path, model: str = MODEL) -> OcrResult:
    """画像ファイルのOCRを実行する"""
    print(f"[画像OCR] {path.name}")
    image_b64 = image_to_b64(path)
    text = call_ollama_vision(image_b64, OCR_PROMPT, model)

    page = PageResult(page=1, text=text, source_frame=path.name)
    return OcrResult(
        source=str(path),
        media_type=MediaType.IMAGE,
        model=model,
        timestamp=datetime.now().isoformat(),
        pages=[page],
        full_text=text,
    )


# ===== 動画OCR =====
def process_video(path: Path, fps: float = 1.0, model: str = MODEL) -> OcrResult:
    """動画ファイルからフレームを抽出してOCRを実行する"""
    print(f"[動画OCR] {path.name} (fps={fps})")

    with tempfile.TemporaryDirectory() as tmpdir:
        frame_pattern = str(Path(tmpdir) / "frame_%06d.jpg")

        # ffmpegでフレーム抽出（配列引数でインジェクション防止）
        cmd = [
            "ffmpeg",
            "-i", str(path),
            "-vf", f"fps={fps}",
            "-q:v", "2",
            frame_pattern,
            "-y",
        ]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"ffmpeg失敗 (code={result.returncode}): {result.stderr[:500]}"
            )

        # フレームを時系列順に処理
        frames = sorted(Path(tmpdir).glob("frame_*.jpg"))
        if not frames:
            raise RuntimeError(f"フレーム抽出失敗: {path.name}")

        print(f"  {len(frames)} フレームを抽出しました")

        pages = []
        prev_text = ""

        for i, frame_path in enumerate(frames, 1):
            print(f"  フレーム {i}/{len(frames)}: {frame_path.name}")
            image_b64 = image_to_b64(frame_path)
            text = call_ollama_vision(image_b64, OCR_PROMPT, model)

            # 連続重複テキストを除去
            if is_duplicate_text(text, prev_text):
                print(f"  [スキップ] 前フレームと重複")
                continue

            pages.append(PageResult(
                page=i,
                text=text,
                source_frame=frame_path.name,
            ))
            prev_text = text

    full_text = "\n\n".join(p.text for p in pages if p.text and p.text != "（テキストなし）")
    return OcrResult(
        source=str(path),
        media_type=MediaType.VIDEO,
        model=model,
        timestamp=datetime.now().isoformat(),
        pages=pages,
        full_text=full_text,
    )


# ===== PDF OCR =====
def process_pdf(path: Path, model: str = MODEL) -> OcrResult:
    """PDFファイルのOCRを実行する。

    Strategy 1: pdfplumber でテキスト直接抽出（高速）
    Strategy 2: pdf2image でページ画像化 → ビジョンOCR（スキャンPDF用）
    """
    print(f"[PDF OCR] {path.name}")

    # Strategy 1: pdfplumber による直接テキスト抽出
    try:
        import pdfplumber  # type: ignore
        pages = []
        with pdfplumber.open(str(path)) as pdf:
            print(f"  pdfplumber: {len(pdf.pages)} ページを検出")
            for i, page in enumerate(pdf.pages, 1):
                text = page.extract_text() or ""
                text = text.strip()
                if text:
                    print(f"  ページ {i}: {len(text)}文字 (直接抽出)")
                    pages.append(PageResult(page=i, text=text, source_frame=""))
                else:
                    print(f"  ページ {i}: テキストなし -> ビジョンOCRへフォールバック")
                    pages.append(None)  # 後で差し替え

        # テキスト抽出できたページと空ページを確認
        empty_pages = [i for i, p in enumerate(pages) if p is None]
        if not empty_pages:
            full_text = "\n\n".join(p.text for p in pages)
            return OcrResult(
                source=str(path),
                media_type=MediaType.PDF,
                model=model,
                timestamp=datetime.now().isoformat(),
                pages=pages,
                full_text=full_text,
            )

        # 空ページのみビジョンOCRでフォールバック
        print(f"  {len(empty_pages)} ページをビジョンOCRで処理します")
        pages = _fill_empty_pages_with_vision(path, pages, model)
        full_text = "\n\n".join(
            p.text for p in pages
            if p and p.text and p.text != "（テキストなし）"
        )
        return OcrResult(
            source=str(path),
            media_type=MediaType.PDF,
            model=model,
            timestamp=datetime.now().isoformat(),
            pages=[p for p in pages if p],
            full_text=full_text,
        )

    except ImportError:
        print("  [情報] pdfplumber未インストール -> ビジョンOCRのみで処理")

    # Strategy 2: pdf2image -> ビジョンOCR（全ページ）
    return _process_pdf_vision_only(path, model)


def _fill_empty_pages_with_vision(path: Path, pages: list, model: str) -> list:
    """pdfplumberで抽出できなかったページをビジョンOCRで補完する"""
    try:
        from pdf2image import convert_from_path  # type: ignore
    except ImportError:
        print("  [警告] pdf2image未インストール -> 空ページはスキップ")
        return [p if p else PageResult(page=i + 1, text="（テキスト抽出不可）", source_frame="")
                for i, p in enumerate(pages)]

    images = convert_from_path(str(path))
    for i, p in enumerate(pages):
        if p is None:
            img = images[i]
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
                tmp_path = Path(tmp.name)
            try:
                img.save(str(tmp_path), "JPEG")
                image_b64 = image_to_b64(tmp_path)
                text = call_ollama_vision(image_b64, OCR_PROMPT, model)
                pages[i] = PageResult(page=i + 1, text=text, source_frame="")
                print(f"  ページ {i + 1}: ビジョンOCR完了 ({len(text)}文字)")
            finally:
                tmp_path.unlink(missing_ok=True)
    return pages


def _process_pdf_vision_only(path: Path, model: str) -> OcrResult:
    """pdf2image でPDF全ページをビジョンOCR処理する"""
    try:
        from pdf2image import convert_from_path  # type: ignore
    except ImportError:
        raise RuntimeError(
            "PDF処理には pdfplumber または pdf2image が必要です。\n"
            "インストール: pip install pdfplumber pdf2image"
        )

    images = convert_from_path(str(path))
    print(f"  pdf2image: {len(images)} ページを変換")

    pages = []
    for i, img in enumerate(images, 1):
        print(f"  ページ {i}/{len(images)}")
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            tmp_path = Path(tmp.name)
        try:
            img.save(str(tmp_path), "JPEG")
            image_b64 = image_to_b64(tmp_path)
            text = call_ollama_vision(image_b64, OCR_PROMPT, model)
            pages.append(PageResult(page=i, text=text, source_frame=""))
        finally:
            tmp_path.unlink(missing_ok=True)

    full_text = "\n\n".join(
        p.text for p in pages if p.text and p.text != "（テキストなし）"
    )
    return OcrResult(
        source=str(path),
        media_type=MediaType.PDF,
        model=model,
        timestamp=datetime.now().isoformat(),
        pages=pages,
        full_text=full_text,
    )


# ===== 出力保存 =====
def save_json(result: OcrResult, out_dir: Path) -> Path:
    """OcrResultをJSONファイルとして保存する"""
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = Path(result.source).stem
    out_path = out_dir / f"{stem}_ocr.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result.to_dict(), f, ensure_ascii=False, indent=2)
    return out_path


def save_markdown(result: OcrResult, out_dir: Path) -> Path:
    """OcrResultをMarkdownファイルとして保存する"""
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = Path(result.source).stem
    out_path = out_dir / f"{stem}_ocr.md"

    lines = [
        f"# OCR結果: {Path(result.source).name}",
        "",
        f"- **メディアタイプ**: {result.media_type}",
        f"- **モデル**: {result.model}",
        f"- **抽出日時**: {result.timestamp}",
        f"- **ページ数**: {len(result.pages)}",
        "",
        "---",
        "",
        "## 全文テキスト",
        "",
        result.full_text or "（テキストなし）",
        "",
    ]

    if len(result.pages) > 1:
        lines += ["---", "", "## ページ別テキスト", ""]
        for page in result.pages:
            if isinstance(page, PageResult):
                lines += [
                    f"### ページ {page.page}",
                    f"{page.source_frame}" if page.source_frame else "",
                    "",
                    page.text or "（テキストなし）",
                    "",
                ]

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return out_path


# ===== バッチ処理 =====
def process_batch(
    inputs: list[str],
    out_dir: Path = OUTPUT_DIR,
    fps: float = 1.0,
    model: str = MODEL,
) -> list[OcrResult]:
    """複数ファイルを一括OCR処理する"""
    results = []
    total = len(inputs)

    for i, input_path_str in enumerate(inputs, 1):
        path = Path(input_path_str)
        print(f"\n[{i}/{total}] {path.name}")

        if not path.exists():
            print(f"  [エラー] ファイルが見つかりません: {path}", file=sys.stderr)
            continue

        try:
            media_type = detect_media_type(path)
        except ValueError as e:
            print(f"  [エラー] {e}", file=sys.stderr)
            continue

        start = time.time()
        try:
            if media_type == MediaType.IMAGE:
                result = process_image(path, model)
            elif media_type == MediaType.VIDEO:
                result = process_video(path, fps, model)
            elif media_type == MediaType.PDF:
                result = process_pdf(path, model)
            else:
                print(f"  [エラー] 未対応メディアタイプ: {media_type}", file=sys.stderr)
                continue
        except Exception as e:
            print(f"  [エラー] OCR処理失敗: {e}", file=sys.stderr)
            continue

        elapsed = time.time() - start
        print(f"  完了: {elapsed:.1f}s | {len(result.full_text)}文字 抽出")

        # 結果保存
        json_path = save_json(result, out_dir)
        md_path = save_markdown(result, out_dir)
        print(f"  JSON: {json_path}")
        print(f"  MD:   {md_path}")

        results.append(result)

    return results


# ===== CLI =====
def main():
    parser = argparse.ArgumentParser(
        description="OCR Collector - 画像・動画・PDFからテキストを抽出（Ollama Vision）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  python scripts/ocr_collector.py scan.png
  python scripts/ocr_collector.py doc.pdf slide.png lecture.mp4
  python scripts/ocr_collector.py --fps 2.0 lecture.mp4
  python scripts/ocr_collector.py -o /tmp/ocr doc.pdf
  python scripts/ocr_collector.py -m qwen2.5vl:72b image.jpg

対応形式:
  画像: .png .jpg .jpeg .webp .gif .bmp .tiff
  動画: .mp4 .mov .avi .mkv .webm .m4v .flv
  PDF:  .pdf  (pdfplumber / pdf2image が必要)
        """,
    )
    parser.add_argument(
        "inputs",
        nargs="+",
        help="OCR対象ファイル（複数指定可）",
    )
    parser.add_argument(
        "--fps",
        type=float,
        default=1.0,
        help="動画フレーム抽出レート (default: 1.0 fps)",
    )
    parser.add_argument(
        "--output", "-o",
        default=str(OUTPUT_DIR),
        help=f"出力ディレクトリ (default: {OUTPUT_DIR})",
    )
    parser.add_argument(
        "--model", "-m",
        default=MODEL,
        help=f"Ollamaモデル名 (default: {MODEL})",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Ollama接続確認のみ実行",
    )

    args = parser.parse_args()

    if args.check:
        _check_ollama(args.model)
        return

    print("=" * 60)
    print("OCR Collector")
    print(f"モデル : {args.model}")
    print(f"出力先 : {args.output}")
    print(f"対象数 : {len(args.inputs)} ファイル")
    print("=" * 60)

    results = process_batch(
        inputs=args.inputs,
        out_dir=Path(args.output),
        fps=args.fps,
        model=args.model,
    )

    print("\n" + "=" * 60)
    print(f"完了: {len(results)}/{len(args.inputs)} ファイルを処理しました")
    total_chars = sum(len(r.full_text) for r in results)
    print(f"合計抽出文字数: {total_chars}")
    print("=" * 60)


def _check_ollama(model: str = MODEL):
    """Ollama接続とモデルの存在を確認する"""
    tags_url = "http://localhost:11434/api/tags"
    try:
        resp = requests.get(tags_url, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        models = [m.get("name", "") for m in data.get("models", [])]
        print(f"[OK] Ollama起動中 ({len(models)} モデル登録済み)")
        if model in models:
            print(f"[OK] モデル '{model}' 利用可能")
        else:
            print(f"[警告] モデル '{model}' が見つかりません")
            print(f"  登録済みモデル: {', '.join(models[:10])}")
            print(f"  インストール: ollama pull {model}")
    except requests.exceptions.ConnectionError:
        print(f"[NG] Ollama未起動 ({tags_url})")
        print("  起動コマンド: ollama serve")
    except requests.exceptions.RequestException as e:
        print(f"[NG] 接続エラー: {e}")


if __name__ == "__main__":
    main()
