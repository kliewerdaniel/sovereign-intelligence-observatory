#!/usr/bin/env bash
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"
PYTHON="$ROOT/.venv/bin/python3"
PYTEST="$ROOT/.venv/bin/pytest"
EXIT_CODE=0

echo "========================================="
echo " Sovereign Intelligence Observatory Tests"
echo "========================================="
echo ""

# Build per-component test commands
declare -A COMPONENTS
COMPONENTS["shared infrastructure"]="$PYTEST $ROOT/tests/test_shared_infrastructure.py -v"
COMPONENTS["agent-recipe-compiler"]="$PYTEST $ROOT/agent-recipe-compiler/tests/ -v"
COMPONENTS["expert-signal-router"]="cd $ROOT/expert-signal-router && $PYTEST tests/ -v"
COMPONENTS["autonomous-evaluation-loop"]="cd $ROOT/autonomous-evaluation-loop && $PYTEST tests/ -v"
COMPONENTS["sovereign-apprenticeship"]="cd $ROOT/sovereign-apprenticeship && $PYTEST tests/ -v"
COMPONENTS["intelligence-observatory"]="cd $ROOT/intelligence-observatory && $PYTEST tests/ -v"
COMPONENTS["tacit-judgment-extractor"]="cd $ROOT/tacit-judgment-extractor && $PYTEST tests/ -v"

for name in "shared infrastructure" "agent-recipe-compiler" "expert-signal-router" "autonomous-evaluation-loop" "sovereign-apprenticeship" "intelligence-observatory" "tacit-judgment-extractor"; do
    cmd="${COMPONENTS[$name]}"
    echo "--- $name ---"
    echo "$ $cmd"
    if eval "$cmd"; then
        echo "✅ $name PASSED"
    else
        echo "❌ $name FAILED"
        EXIT_CODE=1
    fi
    echo ""
done

echo "========================================="
if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ ALL TESTS PASSED"
else
    echo "❌ SOME TESTS FAILED"
fi
exit $EXIT_CODE
