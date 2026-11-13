#!/usr/bin/env bash
# Stop hook: runs the full test suite. Exit 2 on failure so Claude Code sends the errors back to the agent.
set -uo pipefail
cd "${CLAUDE_PROJECT_DIR:-$(dirname "$0")/../..}" || exit 2

# The hook already blocked once this turn: let Claude stop instead of looping forever.
[ -t 0 ] || input=$(cat)
case "${input:-}" in *'"stop_hook_active":true'*|*'"stop_hook_active": true'*) exit 0 ;; esac

# Nothing changed since the last commit on main: skip the 4-minute suite.
if git diff --quiet origin/main -- twin claim_check scripts site tests requirements.txt 2>/dev/null \
   && git diff --quiet -- twin claim_check scripts site tests requirements.txt \
   && [ -z "$(git ls-files --others --exclude-standard -- twin claim_check scripts site tests)" ]; then
  exit 0
fi

if ! out=$(python3 -m pytest -q -x 2>&1); then
  { echo "verify.sh: pytest failed:"; echo "$out" | tail -n 80; } >&2
  exit 2
fi
exit 0
