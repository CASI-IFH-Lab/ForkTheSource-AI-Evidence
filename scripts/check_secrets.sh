#!/usr/bin/env bash
#
# Pre-push secrets guard. Scans TRACKED files only - untracked scratch files are
# your business, but anything git knows about can reach GitHub.
#
# Two checks:
#   1. Any API-key-shaped literal (sk- followed by 8+ key characters), anywhere.
#   2. The AIR gateway host appearing outside .env.example.
#
# Check 2 deliberately reads the expected host OUT OF .env.example rather than
# hardcoding it. Hardcoding the host here would put the literal in a tracked file
# outside .env.example - which is exactly what this script exists to forbid.
#
# Exits non-zero on any hit. Wired into pytest via tests/test_no_secrets.py.
#
# If this script ever fires on a real key: rotate it in Voyager immediately.
# Rotation is the fix. Deleting the commit is not - assume the key is burned.

set -uo pipefail

cd "$(dirname "$0")/.." || exit 2

STATUS=0
TEMPLATE=".env.example"

say_hit() {
  printf '  %s\n' "$1"
}

# ---------------------------------------------------------------------------
# Check 1: key-shaped literals in any tracked file
# ---------------------------------------------------------------------------
echo "[1/2] scanning tracked files for key-shaped literals..."
KEY_HITS=$(git ls-files -z \
  | xargs -0 grep -InE 'sk-[A-Za-z0-9_-]{8,}' -- 2>/dev/null \
  || true)

if [ -n "$KEY_HITS" ]; then
  echo "FAIL: something key-shaped is in a tracked file:"
  while IFS= read -r line; do say_hit "$line"; done <<< "$KEY_HITS"
  echo "      -> rotate the key in Voyager NOW, then remove the literal."
  STATUS=1
else
  echo "      ok - no key-shaped literal in any tracked file."
fi

# ---------------------------------------------------------------------------
# Check 2: the gateway host outside the template
# ---------------------------------------------------------------------------
echo "[2/2] scanning for the gateway host outside $TEMPLATE..."

if [ ! -f "$TEMPLATE" ]; then
  echo "FAIL: $TEMPLATE is missing - it is the source of truth for this check."
  echo "      -> restore it with: git checkout -- $TEMPLATE"
  exit 1
fi

# Pull the host out of the template's AIR_BASE_URL line: strip the scheme, then
# everything from the first remaining slash onward.
HOST=$(grep -E '^AIR_BASE_URL=' "$TEMPLATE" \
  | head -1 \
  | sed -E 's|^AIR_BASE_URL=||; s|^[a-zA-Z]+://||; s|/.*$||')

if [ -z "$HOST" ]; then
  echo "      skipped - could not read a host from $TEMPLATE."
else
  HOST_HITS=$(git ls-files -z \
    | xargs -0 grep -InF "$HOST" -- 2>/dev/null \
    | grep -v "^${TEMPLATE}:" \
    || true)

  if [ -n "$HOST_HITS" ]; then
    echo "FAIL: the gateway host appears outside $TEMPLATE:"
    while IFS= read -r line; do say_hit "$line"; done <<< "$HOST_HITS"
    echo "      -> read it from AIR_BASE_URL instead of writing it down."
    STATUS=1
  else
    echo "      ok - gateway host appears only in $TEMPLATE."
  fi
fi

echo
if [ "$STATUS" -eq 0 ]; then
  echo "check_secrets: PASS"
else
  echo "check_secrets: FAIL"
fi
exit "$STATUS"
