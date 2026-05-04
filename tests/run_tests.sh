#!/usr/bin/env bash
# run_tests.sh — Run offline tests (no FreeCAD, no LLM required)
#
# Usage:
#   ./tests/run_tests.sh           # default port 7978
#   FC_PORT=7979 ./tests/run_tests.sh

set -euo pipefail

PORT="${FC_PORT:-7978}"
MOCK_PID=""
FAILED=0

cd "$(dirname "$0")/.."

cleanup() {
  if [[ -n "$MOCK_PID" ]]; then
    kill "$MOCK_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT

echo "════════════════════════════════════════════════════"
echo " FreeCAD Skill — Offline Test Suite"
echo "════════════════════════════════════════════════════"

# ── Start mock server ─────────────────────────────────────────────────────────
echo ""
echo "Starting mock server on port $PORT..."
FC_PORT="$PORT" python3 tests/mock_server.py &
MOCK_PID=$!
sleep 0.4  # give it a moment to bind

if ! kill -0 "$MOCK_PID" 2>/dev/null; then
  echo "✗ Mock server failed to start"
  exit 1
fi
echo "✓ Mock server running (PID $MOCK_PID)"

# ── Protocol tests ────────────────────────────────────────────────────────────
echo ""
echo "── Protocol Tests ──────────────────────────────────"
if FC_HOST=127.0.0.1 FC_PORT="$PORT" python3 tests/test_protocol.py; then
  echo ""
  echo "✓ Protocol tests passed"
else
  echo ""
  echo "✗ Protocol tests failed"
  FAILED=1
fi

# ── Script library unit tests ─────────────────────────────────────────────────
echo ""
echo "── Script Library Tests ────────────────────────────"
if python3 tests/test_script_library.py; then
  echo ""
  echo "✓ Script library tests passed"
else
  echo ""
  echo "✗ Script library tests failed"
  FAILED=1
fi

# ── Summary ───────────────────────────────────────────────────────────────────
echo ""
echo "════════════════════════════════════════════════════"
if [[ $FAILED -eq 0 ]]; then
  echo " All offline tests passed ✓"
  echo ""
  echo " To run live tests against real FreeCAD:"
  echo "   FC_HOST=<windows-ip> python3 tests/test_protocol.py"
  echo "   Then in pi: /skill:freecad-tests"
else
  echo " Some tests failed ✗"
fi
echo "════════════════════════════════════════════════════"

exit $FAILED
