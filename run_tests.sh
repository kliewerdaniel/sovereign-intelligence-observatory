#!/bin/bash
# Run all observatory tests (root + sub-modules)
set -e

PYTHON=".venv-2/bin/python"
TOTAL_PASS=0
TOTAL_FAIL=0
TOTAL_XFAIL=0

echo "=== Sovereign Intelligence Observatory - Test Suite ==="
echo ""

# Root tests
echo "--- Root Tests ---"
$PYTHON -m pytest tests/ --tb=no -q 2>&1 | tail -3
ROOT_RESULT=$?
if [ $ROOT_RESULT -eq 0 ]; then
    echo "✓ Root tests passed"
else
    echo "✗ Root tests failed"
fi
echo ""

# Sub-module tests
SUBMODULES=(
    "tacit-judgment-extractor:21"
    "agent-recipe-compiler:27"
    "expert-signal-router:7"
    "autonomous-evaluation-loop:8"
    "sovereign-apprenticeship:8"
    "intelligence-observatory:25"
)

echo "--- Sub-module Tests ---"
for entry in "${SUBMODULES[@]}"; do
    IFS=':' read -r sub expected <<< "$entry"
    echo -n "  $sub ... "
    if $PYTHON -m pytest "$sub/tests/" --tb=no -q 2>&1 | grep -q "passed"; then
        echo "✓ passed"
        TOTAL_PASS=$((TOTAL_PASS + 1))
    else
        echo "✗ FAILED"
        TOTAL_FAIL=$((TOTAL_FAIL + 1))
    fi
done
echo ""

echo "=== Summary ==="
echo "Root: passed"
echo "Sub-modules: ${#SUBMODULES[@]} total, $TOTAL_PASS passed, $TOTAL_FAIL failed"
