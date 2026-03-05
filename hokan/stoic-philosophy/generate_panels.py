import re, subprocess, os, time

PROMPTS_FILE = os.path.join(os.path.dirname(__file__), 'page_prompts.md')
CHARS_DIR = os.path.join(os.path.dirname(__file__), 'characters')
PANELS_DIR = os.path.join(os.path.dirname(__file__), 'panels')
NANOBANANA_DIR = os.path.join(os.path.dirname(__file__), '..', '.claude', 'skills', 'nanobanana-pro')

with open(PROMPTS_FILE, 'r', encoding='utf-8') as f:
    content = f.read()

pages = re.split(r'### Page (\d+)', content)
page_count = (len(pages) - 1) // 2

existing = set()
for f in os.listdir(PANELS_DIR):
    if f.startswith('page_') and f.endswith('.png'):
        num = int(f.replace('page_', '').replace('.png', ''))
        existing.add(num)

print(f'Already generated: {sorted(existing)}')
print(f'Remaining: {page_count - len(existing)}')

for i in range(1, page_count + 1):
    if i in existing:
        print(f'Page {i}: SKIP')
        continue

    idx = i * 2
    prompt_text = pages[idx].strip()
    output_path = os.path.abspath(os.path.join(PANELS_DIR, f'page_{i:02d}.png'))

    # Build attach-image args
    attach_args = []
    if 'ミナト' in prompt_text:
        attach_args += ['--attach-image', os.path.abspath(os.path.join(CHARS_DIR, 'ミナト.png'))]
    if 'テツロウ' in prompt_text:
        attach_args += ['--attach-image', os.path.abspath(os.path.join(CHARS_DIR, 'テツロウ.png'))]

    # Use relative output from nanobanana dir
    rel_output = os.path.relpath(output_path, NANOBANANA_DIR)

    cmd = ['python', 'scripts/run.py', 'image_generator.py',
           '--prompt', prompt_text,
           '--output', rel_output,
           '--timeout', '240'] + attach_args

    print(f'\n=== Page {i}/{page_count} ===')
    print(f'  Chars: {"ミナト " if "ミナト" in prompt_text else ""}{"テツロウ" if "テツロウ" in prompt_text else ""}')

    try:
        result = subprocess.run(cmd, capture_output=True, text=True,
                               cwd=NANOBANANA_DIR,
                               env={**os.environ, 'PYTHONIOENCODING': 'utf-8', 'PYTHONUTF8': '1'},
                               timeout=300)
        if result.returncode == 0:
            print(f'  OK')
        else:
            print(f'  FAIL (exit {result.returncode})')
            print(f'  {result.stdout[-200:] if result.stdout else ""}')
            print(f'  {result.stderr[-200:] if result.stderr else ""}')
    except subprocess.TimeoutExpired:
        print(f'  TIMEOUT')
    except Exception as e:
        print(f'  ERROR: {e}')

    time.sleep(2)

print(f'\n=== DONE ===')
generated = [f for f in os.listdir(PANELS_DIR) if f.endswith('.png')]
print(f'Total panels: {len(generated)}')
