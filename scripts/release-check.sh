#!/usr/bin/env bash
# Pre-release sanity checks: contracts, lint, version consistency, clean tree.
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

PASS=0
FAIL=0

run() {
    local label="$1"; shift
    echo "--- $label"
    if "$@"; then
        echo "    OK"
        ((PASS++))
    else
        echo "    FAIL"
        ((FAIL++))
    fi
}

# 1. Contract tests (tool/resource counts match source)
run "Contract tests" python -m pytest tests/mcp/test_contract.py -x -q

# 2. Ruff lint
run "Ruff lint" python -m ruff check src/ tests/

# 3. Version consistency (pyproject.toml vs ctx.__version__)
check_version() {
    local pyproject_ver
    pyproject_ver=$(python -c "
import tomllib, pathlib
d = tomllib.loads(pathlib.Path('pyproject.toml').read_text())
print(d['project']['version'])
")
    local code_ver
    code_ver=$(python -c "from ctx import __version__; print(__version__)")
    if [ "$pyproject_ver" = "$code_ver" ]; then
        echo "    Versions match: $pyproject_ver"
        return 0
    else
        echo "    Mismatch: pyproject.toml=$pyproject_ver, ctx.__version__=$code_ver"
        return 1
    fi
}
run "Version consistency" check_version

# 4. Clean worktree (no uncommitted changes in src/)
check_clean() {
    local dirty
    dirty=$(git diff --name-only -- src/)
    if [ -z "$dirty" ]; then
        return 0
    else
        echo "    Dirty files: $dirty"
        return 1
    fi
}
run "Clean worktree (src/)" check_clean

echo ""
echo "=== Results: $PASS passed, $FAIL failed ==="
[ "$FAIL" -eq 0 ]
