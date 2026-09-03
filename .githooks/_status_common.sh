# Shared guard for the STATUS.md hooks. Sourced, not executed.
#
# Two things this has to get right:
#
#   1. Never fail the git operation that triggered it. A hook that can break a commit
#      or a merge is a hook that gets uninstalled within the hour. Every exit here is
#      0, and the generator is called with `|| true`.
#   2. Never run mid-operation. During a rebase, a cherry-pick, or a merge that stopped
#      on a conflict, the working tree is not a state anybody wants a report about -
#      and post-commit fires once per replayed commit during a rebase, which would mean
#      regenerating STATUS.md dozens of times for intermediate trees. Skip, silently.

status_hook_run() {
  GIT_DIR_PATH=$(git rev-parse --git-dir 2>/dev/null) || return 0

  # In-progress rebase / cherry-pick / revert / merge / bisect.
  for marker in rebase-merge rebase-apply MERGE_HEAD CHERRY_PICK_HEAD REVERT_HEAD BISECT_LOG; do
    if [ -e "$GIT_DIR_PATH/$marker" ]; then
      return 0
    fi
  done

  # A merge that stopped on conflicts leaves unmerged index entries behind.
  if [ -n "$(git ls-files --unmerged 2>/dev/null)" ]; then
    return 0
  fi

  # An explicit escape hatch, for the one time you need git to be quiet.
  if [ -n "${SKIP_STATUS_HOOK:-}" ]; then
    return 0
  fi

  TOPLEVEL=$(git rev-parse --show-toplevel 2>/dev/null) || return 0
  [ -f "$TOPLEVEL/scripts/update_status.py" ] || return 0

  # Prefer the repo venv if it is there, so the hook uses the same interpreter as
  # the tests. Fall back to whatever python is on PATH; Git Bash on Windows has
  # `python` but often not `python3`.
  PY=""
  for candidate in "$TOPLEVEL/.venv/bin/python" "$TOPLEVEL/.venv/Scripts/python.exe"; do
    if [ -x "$candidate" ]; then PY="$candidate"; break; fi
  done
  if [ -z "$PY" ]; then
    if command -v python >/dev/null 2>&1; then PY=python
    elif command -v python3 >/dev/null 2>&1; then PY=python3
    else return 0
    fi
  fi

  # Silent on success. On failure the generator's own stderr line is all you get,
  # and the git operation still succeeds.
  OUT=$("$PY" "$TOPLEVEL/scripts/update_status.py" 2>&1) || true
  case "$OUT" in
    *"could not"*|*Traceback*) printf 'update_status (hook): %s\n' "$OUT" >&2 ;;
  esac
  return 0
}
