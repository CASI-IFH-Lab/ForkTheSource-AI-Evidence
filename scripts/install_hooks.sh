#!/usr/bin/env bash
#
# One-time, per clone: point git at .githooks/ so STATUS.md regenerates itself.
#
# Idempotent - run it as often as you like. Works on macOS, Linux, and Git Bash on
# Windows. `core.hooksPath` is a repo-local config value, so this touches nothing
# outside this clone and nothing that is tracked in git.

set -euo pipefail

cd "$(dirname "$0")/.."

if ! git rev-parse --git-dir >/dev/null 2>&1; then
  echo "install_hooks: not inside a git repository." >&2
  exit 1
fi

git config core.hooksPath .githooks

# chmod is a no-op on Windows checkouts and harmless everywhere else. Git Bash
# executes hooks through the shebang regardless of the mode bit.
chmod +x .githooks/post-commit .githooks/post-merge 2>/dev/null || true

echo "install_hooks: core.hooksPath -> $(git config --get core.hooksPath)"
echo "install_hooks: post-commit and post-merge will regenerate STATUS.md."
echo "install_hooks: STATUS.md is generated - never hand-edit it, edit progress/<you>.md."
