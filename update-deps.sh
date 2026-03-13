#!/bin/sh
set -e

VENV="venv/bin"
REQ="requirements.txt"
REQ_DEV="requirements-dev.txt"
LOCKED="requirements.locked.txt"

echo "=== Step 1: Unpin versions ==="
sed 's/==.*//g' "$REQ" > /tmp/req-unpinned.txt
# Filter out -r line from dev requirements (base deps are installed separately)
sed '/^-r /d; s/==.*//g' "$REQ_DEV" > /tmp/req-dev-unpinned.txt

echo "=== Step 2: Install latest versions ==="
$VENV/pip install --upgrade -r /tmp/req-unpinned.txt
$VENV/pip install --upgrade -r /tmp/req-dev-unpinned.txt

echo "=== Step 3: Freeze ==="
$VENV/pip freeze > "$LOCKED"

python3 -c "
import re

locked = {}
with open('$LOCKED') as f:
    for line in f:
        name = line.split('==')[0].strip().lower()
        locked[name] = line.strip()

for req_file in ['$REQ', '$REQ_DEV']:
    lines = open(req_file).readlines()
    new_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('-r ') or stripped == '' or stripped.startswith('#'):
            new_lines.append(line)
            continue
        name = re.split(r'[=<>!]', stripped)[0].strip().lower()
        if name in locked:
            new_lines.append(locked[name] + '\n')
        else:
            print(f'  WARNING: {name} not found in lock file, keeping as-is')
            new_lines.append(line)
    with open(req_file, 'w') as f:
        f.writelines(new_lines)
"

echo ""
echo "=== Changes ==="
git --no-pager diff --stat "$REQ" "$REQ_DEV" 2>/dev/null || true
echo ""
git --no-pager diff "$REQ" "$REQ_DEV" 2>/dev/null || true

echo ""
echo "=== Step 4: Running tests ==="
DATABASE_URL="${DATABASE_URL:-postgresql://opsdeck:opsdeck@localhost:5432/opsdeck}" \
    $VENV/pytest "$@"

echo ""
echo "Done. If tests pass, commit with:"
echo "  git add $REQ $REQ_DEV $LOCKED"
echo "  git commit -m 'chore: update dependencies'"
