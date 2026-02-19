#!/usr/bin/env python3
"""
Gemini image generator script.
Generates images using Gemini's image generation capabilities via browser automation.

Usage:
    # Basic usage
    python scripts/run.py image_generator.py --prompt "your prompt here" --output output.png
    python scripts/run.py image_generator.py --prompt "sunset" --output images/sunset.png --show-browser

    # With reference image (style extraction)
    python scripts/run.py image_generator.py --prompt "犬を描いて" --reference-image ref.png --output output.png

    # With attach image (character consistency - uploads image to Gemini chat)
    python scripts/run.py image_generator.py --prompt "draw this character running" --attach-image character_sheet.png --output output.png
"""

import sys
import json
import argparse
import time
from pathlib import Path
from patchright.sync_api import sync_playwright
import base64
import io

# Windows環境でのUTF-8出力設定
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from config import (
    DATA_DIR,
    AUTH_INFO_FILE,
    STATE_FILE,
    OUTPUT_DIR,
    DEFAULT_TIMEOUT,
    GEMINI_URL
)
from browser_utils import BrowserFactory, StealthUtils


def check_thinking_mode(page):
    """
    Check if page is in thinking mode (思考モード).

    Detection strategy:
    1. Look for "思考" / "Think" / "Deep Think" text in mode switcher
    2. Check if NOT in fast mode ("高速" / "Flash" / "Fast")
    """
    try:
        # Positive indicators: Thinking mode is active
        thinking_keywords = ["思考", "Think", "Deep Think", "Thinking"]
        thinking_selectors = [
            'button:has-text("思考")',
            'button:has-text("Think")',
            'button:has-text("Deep Think")',
            'div:has-text("思考モード")',
            '*[aria-label*="思考"]',
            '*[aria-label*="Think"]',
            # Mode switcher button area
            'button[class*="mode"]',
            'div[class*="mode-switch"]',
        ]

        for selector in thinking_selectors:
            try:
                elem = page.locator(selector)
                if elem.count() > 0:
                    for i in range(elem.count()):
                        el = elem.nth(i)
                        if el.is_visible():
                            try:
                                text = el.inner_text()
                                for keyword in thinking_keywords:
                                    if keyword in text:
                                        return True
                            except:
                                continue
            except:
                continue

        # Negative check: If in fast mode, definitely not thinking mode
        fast_keywords = ["高速", "Flash", "Fast", "フラッシュ"]
        fast_selectors = [
            'button:has-text("高速")',
            'button:has-text("Flash")',
            'button:has-text("Fast")',
            '*[aria-label*="高速"]',
            '*[aria-label*="Flash"]',
        ]

        for selector in fast_selectors:
            try:
                elem = page.locator(selector)
                if elem.count() > 0:
                    for i in range(elem.count()):
                        el = elem.nth(i)
                        if el.is_visible():
                            try:
                                text = el.inner_text()
                                for keyword in fast_keywords:
                                    if keyword in text:
                                        # Fast mode is active, not thinking mode
                                        return False
                            except:
                                continue
            except:
                continue

    except:
        pass
    return False


def run_setup_check(page, context, image_gen_selectors, setup_timeout=300):
    """
    Combined setup check: login + thinking mode.

    Strategy:
    1. Wait for login (image generation button to appear) - max setup_timeout
    2. Once logged in, instruct user to switch to thinking mode
    3. Wait 30 seconds for user to switch, then proceed

    Returns:
        tuple: (success, image_gen_button)
    """
    print("")
    print("=" * 70)
    print("🔧 セットアップ確認")
    print("=" * 70)

    # Phase 1: Wait for login (image generation button)
    print("\n[Phase 1] ログイン確認中...")

    start_time = time.time()
    image_gen_button = None

    while time.time() - start_time < setup_timeout:
        elapsed = int(time.time() - start_time)

        # Check for image generation button (= logged in)
        for selector in image_gen_selectors:
            try:
                locator = page.locator(selector)
                if locator.count() > 0:
                    for i in range(locator.count()):
                        btn = locator.nth(i)
                        if btn.is_visible():
                            bbox = btn.bounding_box()
                            if bbox and bbox['width'] > 50:
                                image_gen_button = btn
                                break
                if image_gen_button:
                    break
            except:
                continue

        if image_gen_button:
            print("  [OK] ログイン済み（画像の作成ボタン確認）")
            break

        # Show status every 10 seconds
        if elapsed == 0 or elapsed % 10 == 0:
            remaining = setup_timeout - elapsed
            print(f"  [WAIT] ログインを待っています... （残り {remaining}s）")
            print("    Googleアカウントでログインしてください")

        page.wait_for_timeout(2000)

    if not image_gen_button:
        print("")
        print("=" * 70)
        print("[ERROR] ログインがタイムアウトしました")
        print("   Googleアカウントでログインしてから再実行してください")
        print("=" * 70)
        return False, None

    # Phase 2: Wait for thinking mode (detect automatically)
    print("\n[Phase 2] 思考モード確認")
    print("=" * 70)
    print("[WARN]  重要: 右下のモードを「思考」に切り替えてください！")
    print("")
    print("   ┌─────────────────────────────────────────┐")
    print("   │  高速モードでは日本語テキストの品質が   │")
    print("   │  低下します。必ず「思考」モードを使用   │")
    print("   │  してください。                         │")
    print("   └─────────────────────────────────────────┘")
    print("")
    print("   思考モードが検出されるまで待機します...")
    print("=" * 70)

    # Wait for thinking mode to be detected
    thinking_start = time.time()
    thinking_timeout = 300  # 5 minutes
    is_thinking_mode = False

    while time.time() - thinking_start < thinking_timeout:
        elapsed = int(time.time() - thinking_start)

        is_thinking_mode = check_thinking_mode(page)
        if is_thinking_mode:
            print("")
            print("  [OK] 思考モード検出！")
            break

        if elapsed == 0 or elapsed % 10 == 0:
            remaining = thinking_timeout - elapsed
            print(f"  [WAIT] 思考モードを待っています... （残り {remaining}s）")

        page.wait_for_timeout(2000)

    if not is_thinking_mode:
        print("")
        print("=" * 70)
        print("[ERROR] 思考モードが確認できませんでした")
        print("   思考モードに切り替えてから再実行してください")
        print("=" * 70)
        return False, None

    # Save session
    try:
        state = context.storage_state()
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f)
        print("  [OK] セッション保存完了")
    except:
        pass

    print("")
    print("=" * 70)
    print("[OK] セットアップ完了 - 画像生成を開始します")
    print("=" * 70)

    return True, image_gen_button


def ensure_output_dir():
    """Create output directory if it doesn't exist."""
    OUTPUT_DIR.mkdir(exist_ok=True)

def check_authenticated():
    """
    Check if user is authenticated with Google auth cookies.

    Uses STATE_FILE (state.json) as the primary check since it contains
    actual browser cookies. Verifies Google auth cookies exist, not just
    analytics cookies.

    This matches the NotebookLM skill pattern where state.json is the
    source of truth for authentication status.
    """
    # Primary check: state.json with cookies
    if not STATE_FILE.exists():
        return False

    try:
        with open(STATE_FILE, 'r') as f:
            state = json.load(f)

        # Verify we have cookies
        if 'cookies' not in state or len(state['cookies']) == 0:
            return False

        # Check for Google auth cookies specifically
        google_auth_cookie_names = [
            'SID', 'HSID', 'SSID', 'APISID', 'SAPISID',
            '__Secure-1PSID', '__Secure-3PSID',
            '__Secure-1PAPISID', '__Secure-3PAPISID'
        ]
        google_auth_cookies = [c for c in state['cookies']
                               if c['name'] in google_auth_cookie_names]

        if len(google_auth_cookies) < 3:
            print(f"[WARN]  Missing Google auth cookies (found {len(google_auth_cookies)}, need 3+)")
            return False

        # Check if state file is not too old (7 days)
        import time
        age_days = (time.time() - STATE_FILE.stat().st_mtime) / 86400
        if age_days > 7:
            print(f"[WARN]  Browser state is {age_days:.1f} days old, may need re-authentication")

        return True

    except Exception:
        return False

def upload_attach_images(page, image_paths: list, max_attempts: int = 3) -> bool:
    """
    Upload multiple images to Gemini chat at once via a single file chooser dialog.
    This avoids the overlay/menu issue that occurs with consecutive single uploads.

    Args:
        page: Playwright page object
        image_paths: List of absolute paths to image files
        max_attempts: Max retry attempts (default: 3)

    Returns:
        bool: True if upload successful
    """
    # Validate all files exist
    valid_files = []
    for img_path in image_paths:
        f = Path(img_path)
        if f.exists():
            valid_files.append(str(f.absolute()))
        else:
            print(f"   [WARN] Attach image not found: {img_path}")

    if not valid_files:
        print("   [WARN] No valid image files to attach")
        return False

    file_names = [Path(f).name for f in valid_files]
    print(f"   → Attaching {len(valid_files)} images: {', '.join(file_names)}")

    for attempt in range(1, max_attempts + 1):
        if attempt > 1:
            print(f"   [RETRY] Upload attempt {attempt}/{max_attempts}...")
            page.wait_for_timeout(2000)

        # Step 1: Find and click add/attach button
        add_button_selectors = [
            'button[aria-label*="その他のオプション"]',
            'button[aria-label*="Add"]',
            'button[aria-label*="追加"]',
            'button[aria-label*="添付"]',
            'button[aria-label*="ファイル"]',
            'button[aria-label*="画像を追加"]',
            'button[aria-label*="Insert"]',
            '[class*="add-content"]',
            '[class*="upload"]',
            'button:has(mat-icon:has-text("add"))',
            'button:has(mat-icon:has-text("attach_file"))',
            'button:has(mat-icon:has-text("image"))',
        ]

        button_clicked = False
        for selector in add_button_selectors:
            try:
                btn = page.locator(selector).first
                if btn.is_visible():
                    btn.click()
                    page.wait_for_timeout(2000)
                    button_clicked = True
                    print(f"   [OK] Found add button: {selector}")
                    break
            except:
                continue

        if not button_clicked:
            print("   [WARN] Could not find add button")
            continue

        # Step 2: Click "ファイルをアップロード" and set multiple files at once
        upload_menu_selectors = [
            'text="ファイルをアップロード"',
            'text="画像をアップロード"',
            'text="Upload file"',
            'text="Upload image"',
            '[role="menuitem"]:has-text("アップロード")',
            '[role="menuitem"]:has-text("Upload")',
            '[class*="menu"] *:has-text("アップロード")',
        ]

        uploaded = False
        for selector in upload_menu_selectors:
            try:
                item = page.locator(selector).first
                if item.is_visible():
                    try:
                        with page.expect_file_chooser(timeout=5000) as fc_info:
                            item.click()
                        file_chooser = fc_info.value
                        # Upload ALL files at once via single file chooser
                        file_chooser.set_files(valid_files)
                        print(f"   [OK] Found upload menu: {selector}")
                        print(f"   [OK] {len(valid_files)} images attached via file chooser")
                        # Wait for all uploads to process
                        page.wait_for_timeout(3000 + len(valid_files) * 2000)
                        print("   [OK] All images upload complete")
                        uploaded = True
                        break
                    except Exception as e:
                        print(f"   [WARN] File chooser failed: {e}")
                        # Try to dismiss any leftover menu
                        try:
                            page.keyboard.press("Escape")
                            page.wait_for_timeout(500)
                        except:
                            pass
                        continue
            except:
                continue

        if uploaded:
            return True

        # Fallback: try file input element
        file_input = None
        for selector in ['input[type="file"]', 'input[accept*="image"]', 'input[accept*="*"]']:
            try:
                locator = page.locator(selector)
                if locator.count() > 0:
                    file_input = locator.first
                    break
            except:
                continue

        if file_input:
            try:
                with page.expect_file_chooser(timeout=10000) as fc_info:
                    file_input.dispatch_event('click')
                file_chooser = fc_info.value
                file_chooser.set_files(valid_files)
                print(f"   [OK] {len(valid_files)} images attached via file input fallback")
                page.wait_for_timeout(3000 + len(valid_files) * 2000)
                print("   [OK] All images upload complete")
                return True
            except Exception as e:
                print(f"   [WARN] File input fallback failed: {e}")

        # Dismiss overlays before retry
        try:
            page.keyboard.press("Escape")
            page.wait_for_timeout(500)
        except:
            pass

    print(f"   [WARN] All {max_attempts} upload attempts failed")
    return False


def generate_image(prompt: str, output_path: str, show_browser: bool = False, timeout: int = 180, max_retries: int = 3, attach_image=None):
    """
    Generate image using Gemini with persistent browser context.

    Args:
        prompt: Image generation prompt
        output_path: Path to save generated image
        show_browser: Whether to show browser window
        timeout: Maximum wait time in seconds (default: 180)
        max_retries: Maximum number of retry attempts on timeout (default: 3)
        attach_image: Path(s) to image(s) to attach to Gemini chat before prompt (str, list, or None)

    Returns:
        bool: True if successful
    """
    ensure_output_dir()

    print(f"🎨 Generating image with prompt: '{prompt}'")
    print(f"   Output: {output_path}")
    print(f"   Max wait time: {timeout}s")
    print(f"   Max retries: {max_retries}")

    playwright = None
    context = None

    for attempt in range(1, max_retries + 1):
        if attempt > 1:
            print(f"\n🔄 リトライ {attempt}/{max_retries}...")
            print("   → ページを再読み込みして再試行します")

        try:
            if playwright is None:
                playwright = sync_playwright().start()

            if context is None:
                # Use persistent context (key improvement!)
                context = BrowserFactory.launch_persistent_context(
                    playwright,
                    headless=not show_browser
                )

            # Get or create page
            page = context.pages[0] if context.pages else context.new_page()

            # Navigate to Gemini
            print(f"   → Opening Gemini ({GEMINI_URL})...")
            page.goto(GEMINI_URL, wait_until="domcontentloaded", timeout=30000)

            # Wait for page to be ready
            page.wait_for_timeout(3000)

            # First, ensure we're on a fresh chat page (not a conversation)
            if '/app/c' in page.url or '/app/' not in page.url:
                print("   → Navigating to fresh chat...")
                page.goto("https://gemini.google.com/app", wait_until="domcontentloaded", timeout=30000)
                page.wait_for_timeout(3000)

            # Image generation button selectors
            image_gen_selectors = [
                # New UI (2026): Suggestion chip below input - full aria-label match
                'button:has-text("🍌 画像の作成")',
                'button:has-text("画像の作成、ボタン")',
                # Partial text match
                'button:has-text("画像の作成")',
                # Role-based selector
                'button[role="button"]:has-text("画像")',
                # Generic text match
                '*:has-text("画像の作成"):visible',
            ]

            # Combined setup check: login + thinking mode
            # This will wait for user to complete both before proceeding
            setup_success, image_gen_button = run_setup_check(
                page=page,
                context=context,
                image_gen_selectors=image_gen_selectors,
                setup_timeout=300  # 5 minutes
            )

            if not setup_success or not image_gen_button:
                print("[ERROR] セットアップが完了しませんでした")
                print("   ログインと思考モード切替を完了してから再実行してください")
                context.close()
                playwright.stop()
                return False

            # Click to activate NanoBanana (image generation mode)
            image_gen_button.click()
            page.wait_for_timeout(2000)

            print("   → NanoBanana (画像の作成) activated")

            # Step 2.5: Attach image(s) if provided (for character consistency + template)
            if attach_image:
                images = attach_image if isinstance(attach_image, list) else [attach_image]
                attach_success = upload_attach_images(page, images)
                if not attach_success:
                    print("   [WARN] Attach images failed, continuing without images...")

            # Step 3: Find input field (now in NanoBanana mode)
            print("   → Finding input field...")
            input_selectors = [
                'div[contenteditable="true"]',
                'textarea[placeholder*="プロンプト"]',
                'textarea[placeholder*="画像"]',
                'textarea',
                'rich-textarea textarea',
            ]

            input_element = None
            for selector in input_selectors:
                try:
                    if page.locator(selector).count() > 0:
                        input_element = page.locator(selector).first
                        if input_element.is_visible():
                            print(f"   [OK] Found input: {selector}")
                            break
                except:
                    continue

            if not input_element:
                print("[ERROR] Could not find input field. UI may have changed.")
                print("   Try running with --show-browser to debug")
                context.close()
                playwright.stop()
                return False

            # Type prompt
            print("   → Typing prompt...")
            input_element.click()
            StealthUtils.random_delay(200, 500)
            input_element.fill(prompt)
            page.wait_for_timeout(500)

            # Step 4: Find and click send button
            print("   → Sending request...")
            send_selectors = [
                'button[aria-label*="送信"]',
                'button[aria-label*="Send"]',
                'button:has-text("生成")',
                'button:has-text("Generate")',
                'button[mattooltip*="Send"]',
                'button.send-button',
            ]

            send_button = None
            for selector in send_selectors:
                try:
                    locator = page.locator(selector)
                    if locator.count() > 0:
                        for i in range(locator.count()):
                            btn = locator.nth(i)
                            if btn.is_visible():
                                send_button = btn
                                print(f"   [OK] Found send button: {selector}")
                                break
                    if send_button:
                        break
                except:
                    continue

            if not send_button:
                # Try Enter key as fallback
                print("   → Send button not found, trying Enter key...")
                input_element.press("Enter")
            else:
                send_button.click()

            # Wait for image generation
            print(f"   → Waiting for image generation (max {timeout}s)...")
            print("      This may take 30-180 seconds...")

            # Try to find generated image (improved selectors from sales_letter_generator)
            image_selectors = [
                'img.image.loaded',  # 2026年2月時点の最新セレクタ（class="image loaded"）
                'img[class*="image"][class*="loaded"]',  # 複合classセレクタ
                'img[src*="lh3.googleusercontent"]',
                'img[src*="googleusercontent"]',
                'div[class*="response"] img',
                'model-response img',
            ]

            image_found = False
            image_element = None
            start_time = time.time()

            while time.time() - start_time < timeout:
                elapsed = int(time.time() - start_time)
                if elapsed % 30 == 0 and elapsed > 0:
                    print(f"      ... {elapsed}s elapsed")

                for selector in image_selectors:
                    try:
                        locator = page.locator(selector)
                        count = locator.count()
                        if count > 0:
                            for i in range(count):
                                img = locator.nth(i)
                                if img.is_visible():
                                    src = img.get_attribute('src') or ''
                                    if 'googleusercontent' in src:
                                        # Check image size to ensure it's the generated image
                                        try:
                                            bbox = img.bounding_box()
                                            if bbox and bbox['width'] > 100 and bbox['height'] > 100:
                                                print("   [OK] Image generated!")
                                                image_found = True
                                                image_element = img
                                                break
                                        except:
                                            # If bounding_box fails, accept the image anyway
                                            print("   [OK] Image generated! (size check skipped)")
                                            image_found = True
                                            image_element = img
                                            break
                            if image_found:
                                break
                    except:
                        continue

                if image_found:
                    break

                # Check for error messages (Japanese and English)
                error_texts = [
                    "画像を生成できません",
                    "生成できませんでした",
                    "申し訳",
                    "I cannot help",
                    "Unable to generate",
                    "Sorry"
                ]
                for error_text in error_texts:
                    try:
                        if page.locator(f'text="{error_text}"').count() > 0:
                            print("[ERROR] Gemini declined to generate the image")
                            context.close()
                            playwright.stop()
                            return False
                    except:
                        pass

                page.wait_for_timeout(2000)

            if not image_found:
                print(f"[ERROR] Timeout after {timeout}s - image not generated")
                if attempt < max_retries:
                    print(f"   → ページを再読み込みしてリトライします...")
                    # Reload page for retry
                    try:
                        page.goto("https://gemini.google.com/app", wait_until="domcontentloaded", timeout=30000)
                        page.wait_for_timeout(3000)
                    except:
                        pass
                    continue  # Retry with SAME prompt (not simplified!)
                else:
                    print(f"[ERROR] {max_retries}回リトライしましたが失敗しました")
                    context.close()
                    playwright.stop()
                    return False

            # Download image (inside the try block, after image is found)
            print("   → Downloading image...")

            try:
                # Get image source
                img_src = image_element.get_attribute("src")

                if img_src.startswith("data:"):
                    # Base64 encoded image
                    print("   → Saving base64 image...")
                    img_data = img_src.split(",")[1]
                    img_bytes = base64.b64decode(img_data)

                    output_file = Path(output_path)
                    output_file.parent.mkdir(parents=True, exist_ok=True)
                    output_file.write_bytes(img_bytes)

                elif img_src.startswith("http"):
                    # URL image
                    print("   → Downloading from URL...")
                    response = page.request.get(img_src)
                    img_bytes = response.body()

                    output_file = Path(output_path)
                    output_file.parent.mkdir(parents=True, exist_ok=True)
                    output_file.write_bytes(img_bytes)

                else:
                    # Try screenshot as fallback
                    print("   → Using screenshot fallback...")
                    image_element.screenshot(path=output_path)

                print(f"\n[OK] Image saved to: {output_path}")
                context.close()
                playwright.stop()
                return True

            except Exception as e:
                print(f"[ERROR] Error downloading image: {e}")
                print("   → Trying screenshot fallback...")
                try:
                    image_element.screenshot(path=output_path)
                    print(f"[OK] Image saved via screenshot: {output_path}")
                    context.close()
                    playwright.stop()
                    return True
                except Exception as e2:
                    print(f"[ERROR] Screenshot also failed: {e2}")
                    context.close()
                    playwright.stop()
                    return False

        except Exception as e:
            print(f"\n[ERROR] Error: {e}")
            if attempt < max_retries:
                print(f"   → リトライします...")
                try:
                    if context:
                        page = context.pages[0] if context.pages else context.new_page()
                        page.goto("https://gemini.google.com/app", wait_until="domcontentloaded", timeout=30000)
                        page.wait_for_timeout(3000)
                except:
                    pass
                continue  # Retry with SAME prompt
            else:
                print("   Try running with --show-browser to see what went wrong")
                if context:
                    context.close()
                if playwright:
                    playwright.stop()
                return False

    # All retries exhausted
    if context:
        context.close()
    if playwright:
        playwright.stop()
    return False

def main():
    parser = argparse.ArgumentParser(description="Generate images with Gemini")
    parser.add_argument(
        "--prompt",
        required=True,
        help="Image generation prompt"
    )
    parser.add_argument(
        "--output",
        default="output/generated_image.png",
        help="Output file path (default: output/generated_image.png)"
    )
    parser.add_argument(
        "--reference-image",
        help="Reference image path for style extraction (optional)"
    )
    parser.add_argument(
        "--attach-image",
        action="append",
        help="Image to attach to Gemini chat before prompt (for character consistency). Can be specified multiple times."
    )
    parser.add_argument(
        "--yaml-output",
        help="Save extracted YAML analysis to this path (optional)"
    )
    parser.add_argument(
        "--show-browser",
        action="store_true",
        help="Show browser window (useful for debugging)"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=180,
        help="Maximum wait time in seconds (default: 180)"
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=3,
        help="Maximum retry attempts on timeout (default: 3)"
    )

    args = parser.parse_args()

    # Check authentication
    if not check_authenticated():
        print("[ERROR] Not authenticated")
        print("   Run: python scripts/run.py auth_manager.py setup")
        return 1

    # Determine final prompt
    final_prompt = args.prompt

    # If reference image is provided, extract style and create optimized prompt
    if args.reference_image:
        print("\n" + "="*60)
        print("📷 Reference image mode enabled")
        print("="*60)

        # Step 1: Extract visual elements from reference image
        from prompt_extractor import extract_visual_prompt
        print("\n[Step 1/3] Extracting visual elements...")

        extract_result = extract_visual_prompt(
            image_path=args.reference_image,
            output_path=args.yaml_output,
            show_browser=args.show_browser,
            timeout=120
        )

        if not extract_result["success"]:
            print(f"[ERROR] Failed to extract from reference image: {extract_result['error']}")
            return 1

        yaml_content = extract_result["yaml"]
        print("   [OK] Visual analysis complete")

        # Step 2: Generate optimized meta-prompt
        from meta_prompt import load_yaml, generate_meta_prompt
        print("\n[Step 2/3] Generating optimized prompt...")

        try:
            yaml_data = load_yaml(yaml_text=yaml_content)
            final_prompt = generate_meta_prompt(yaml_data, args.prompt)
            print(f"   [OK] Optimized prompt: {final_prompt[:100]}...")
        except Exception as e:
            print(f"[WARN]  Warning: Could not parse YAML, using original prompt")
            print(f"   Error: {e}")

        print(f"\n[Step 3/3] Generating image...")
        print("="*60 + "\n")

    # Generate image
    success = generate_image(
        prompt=final_prompt,
        output_path=args.output,
        show_browser=args.show_browser,
        timeout=args.timeout,
        max_retries=args.max_retries,
        attach_image=args.attach_image
    )

    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
