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
        PASS=$((PASS + 1))
    else
        echo "    FAIL"
        FAIL=$((FAIL + 1))
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

# 5. CHANGELOG.md exists and mentions the current version
check_changelog() {
    if [ ! -f CHANGELOG.md ]; then
        echo "    CHANGELOG.md not found"
        return 1
    fi
    local ver
    ver=$(python -c "from ctx import __version__; print(__version__)")
    if grep -q "\[$ver\]" CHANGELOG.md; then
        echo "    CHANGELOG.md contains [$ver]"
        return 0
    else
        echo "    CHANGELOG.md does not mention [$ver]"
        return 1
    fi
}
run "CHANGELOG" check_changelog

# 6. Minimum test count (collected, not executed)
check_test_count() {
    local count
    count=$(python -m pytest --co -q 2>/dev/null | tail -1 | grep -oP '^\d+')
    if [ -z "$count" ]; then
        echo "    Could not determine test count"
        return 1
    fi
    if [ "$count" -ge 900 ]; then
        echo "    Test count: $count (>= 900)"
        return 0
    else
        echo "    Test count too low: $count (need >= 900)"
        return 1
    fi
}
run "Minimum test count" check_test_count

# 7. Schema version consistency (source vs docs)
check_schema_version() {
    local src_ver
    src_ver=$(python -c "from ctx.core.migrations import SCHEMA_VERSION; print(SCHEMA_VERSION)")
    local doc_ver
    doc_ver=$(grep -oP 'current schema version is \*\*\K[0-9.]+' docs/reference/schema.md || true)
    if [ -z "$doc_ver" ]; then
        echo "    Could not extract schema version from docs/reference/schema.md"
        return 1
    fi
    if [ "$src_ver" = "$doc_ver" ]; then
        echo "    Schema versions match: $src_ver"
        return 0
    else
        echo "    Mismatch: source=$src_ver, docs=$doc_ver"
        return 1
    fi
}
run "Schema version consistency" check_schema_version

echo ""
echo "=== Results: $PASS passed, $FAIL failed ==="
[ "$FAIL" -eq 0 ]
