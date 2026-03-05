#!/bin/bash
set -e

# Use Windows-native paths via cygpath for Japanese directory names
NANO_DIR="$(cygpath -u 'C:\Users\baseb\dev\開発1\.claude\skills\nanobanana-pro')"
HOKAN_DIR="$(cygpath -u 'C:\Users\baseb\dev\開発1\hokan\stoic-philosophy')"
PROMPTS_FILE="$(cygpath -w 'C:\Users\baseb\dev\開発1\hokan\stoic-philosophy\page_prompts.md')"
CHARS_WIN='C:\Users\baseb\dev\開発1\hokan\stoic-philosophy\characters'

cd "$NANO_DIR"

for PAGE in $(seq 1 20); do
  PADDED=$(printf "%02d" $PAGE)
  OUTPUT="../../../hokan/stoic-philosophy/panels/page_${PADDED}.png"

  # Skip if already exists
  if [ -f "$HOKAN_DIR/panels/page_${PADDED}.png" ]; then
    echo "Page $PAGE: SKIP (exists)"
    continue
  fi

  # Extract prompt for this page using Windows path
  PYTHONIOENCODING=utf-8 python -c "
import re
with open(r'$PROMPTS_FILE', 'r', encoding='utf-8') as f:
    content = f.read()
pages = re.split(r'### Page (\d+)', content)
idx = $PAGE * 2
prompt = pages[idx].strip()
with open('_temp_prompt.txt', 'w', encoding='utf-8') as f:
    f.write(prompt)
# Detect characters
chars = []
if 'ミナト' in prompt: chars.append('minato')
if 'テツロウ' in prompt: chars.append('tetsuro')
with open('_temp_chars.txt', 'w') as f:
    f.write(' '.join(chars))
"

  CHARS_FLAGS=""
  CHARLIST=$(cat _temp_chars.txt)
  if echo "$CHARLIST" | grep -q "minato"; then
    CHARS_FLAGS="$CHARS_FLAGS --attach-image ${CHARS_WIN}\ミナト.png"
  fi
  if echo "$CHARLIST" | grep -q "tetsuro"; then
    CHARS_FLAGS="$CHARS_FLAGS --attach-image ${CHARS_WIN}\テツロウ.png"
  fi

  echo "=== Page $PAGE/20 === (chars: $CHARLIST)"

  PYTHONIOENCODING=utf-8 python scripts/run.py image_generator.py \
    --prompt "$(cat _temp_prompt.txt)" \
    $CHARS_FLAGS \
    --output "$OUTPUT" \
    --timeout 240 2>&1 | tail -5

  echo "Page $PAGE: DONE"
  sleep 2
done

echo "=== ALL DONE ==="
ls -1 "$HOKAN_DIR/panels/" | wc -l
