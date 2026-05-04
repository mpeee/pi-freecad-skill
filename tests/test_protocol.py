#!/usr/bin/env python3
"""
Protocol Tests — tests the TCP protocol against the mock server.
No FreeCAD, no pi, no LLM required.

Tests:
  - freecad_server.py protocol (send JSON, receive JSON)
  - mock_server.py response patterns
  - Error handling

Usage:
    # Against mock server (default):
    python3 tests/mock_server.py &
    python3 tests/test_protocol.py
    kill %1

    # Against real FreeCAD server:
    FC_HOST=<windows-ip> python3 tests/test_protocol.py
"""

import socket
import json
import os
import sys
import time

HOST = os.environ.get("FC_HOST", "127.0.0.1")
PORT = int(os.environ.get("FC_PORT", "7978"))
TIMEOUT = 8

PASS = "\033[32m✓\033[0m"
FAIL = "\033[31m✗\033[0m"
SKIP = "\033[33m~\033[0m"

results = {"pass": 0, "fail": 0, "skip": 0}


def send(code: str) -> dict:
    with socket.create_connection((HOST, PORT), timeout=TIMEOUT) as s:
        s.sendall(json.dumps({"code": code}).encode() + b"\n")
        buf = b""
        while True:
            chunk = s.recv(4096)
            if not chunk:
                break
            buf += chunk
            if b"\n" in buf:
                break
    return json.loads(buf.decode().strip())


def check(name: str, code: str, *, result=None, output_contains=None,
          error_contains=None, has_error=False):
    try:
        resp = send(code)
    except Exception as e:
        print(f"{FAIL} {name}  [connection error: {e}]")
        results["fail"] += 1
        return

    ok = True
    notes = []

    if result is not None and resp.get("result") != result:
        ok = False
        notes.append(f"result: expected {result!r}, got {resp.get('result')!r}")

    if output_contains and output_contains not in (resp.get("output") or ""):
        ok = False
        notes.append(f"output missing {output_contains!r}")

    if error_contains:
        err = resp.get("error") or ""
        if error_contains not in err:
            ok = False
            notes.append(f"error missing {error_contains!r}")

    if has_error and not resp.get("error"):
        ok = False
        notes.append("expected error but got none")

    if not has_error and resp.get("error") and error_contains is None:
        ok = False
        notes.append(f"unexpected error: {resp['error'][:120]}")

    sym = PASS if ok else FAIL
    suffix = f"  [{', '.join(notes)}]" if notes else ""
    print(f"{sym} {name}{suffix}")
    results["pass" if ok else "fail"] += 1


def section(title: str):
    print(f"\n── {title} {'─' * (50 - len(title))}")


# ── Check server is reachable ────────────────────────────────────────────────
print(f"Testing against {HOST}:{PORT}")
try:
    resp = send("'ping'")
    if resp.get("result") != "ping" and resp.get("result") is not None:
        pass  # mock returns "ping", real FreeCAD might differ
except Exception as e:
    print(f"\n{FAIL} Cannot connect to server at {HOST}:{PORT}: {e}")
    print("   Start the mock server first:  python3 tests/mock_server.py")
    sys.exit(1)

# ── T01 Connection ────────────────────────────────────────────────────────────
section("T01 — Connection")
check("ping",           "'ping'",                          result="ping")
check("version string", "'.'.join(FreeCAD.Version()[:2])", output_contains=None)

# ── T02 Basic Execution ───────────────────────────────────────────────────────
section("T02 — Basic Execution")
check("eval expression",    "2 + 2",                  result=4)
check("eval string",        "'hello'",                result="hello")
check("eval bool",          "1 == 1",                 result=True)
check("exec + _result",     "x = 21; _result = x * 2", result=42)
check("print output",       "print('hi')",            output_contains="hi")

# ── T03 Error Handling ────────────────────────────────────────────────────────
section("T03 — Error Handling")
check("missing import",
      "Part.makeBox(1,1,1)",
      has_error=True, error_contains="NameError")
check("intentional error",
      "RAISE_ERROR = True; raise RuntimeError('intentional test error')",
      has_error=True)

# ── T04 FreeCAD Namespace ─────────────────────────────────────────────────────
section("T04 — FreeCAD Namespace")
check("App available",      "App.ActiveDocument.Name",       )  # just no error
check("import Part works",  "import Part; Part.makeBox(1,1,1)")

# ── T05 Document & Objects ────────────────────────────────────────────────────
section("T05 — Document & Objects")
check("newDocument",        "doc = App.newDocument('Test'); _result = doc.Name" if HOST == "127.0.0.1"
                            else "App.newDocument('Test').Name")
check("list objects",
      "print('\\n'.join([o.Name for o in App.ActiveDocument.Objects]))",
      )

# ── T06 Geometry Creation ─────────────────────────────────────────────────────
section("T06 — Geometry (Part/CSG)")
check("create box",
      "import Part\nbox = Part.makeBox(100,50,30)\nprint(box.ShapeType)")
check("boolean cut",
      "import Part\nbox=Part.makeBox(100,50,30)\ncyl=Part.makeCylinder(10,35)\nresult=box.cut(cyl)\n_result=result.isValid()")
check("screenshot code",
      "FreeCADGui.ActiveDocument.ActiveView.saveImage('C:/tmp/test.png',1920,1080)",
      output_contains="test.png")

# ── T07 Response Format ───────────────────────────────────────────────────────
section("T07 — Response Format")
resp = send("2 + 2")
fields_ok = all(k in resp for k in ("result", "output", "stderr", "error"))
print(f"{'✓' if fields_ok else '✗'} response has all required fields")
results["pass" if fields_ok else "fail"] += 1

none_error = resp.get("error") is None
print(f"{'✓' if none_error else '✗'} error field is null on success")
results["pass" if none_error else "fail"] += 1

# ── T08 Large Response ────────────────────────────────────────────────────────
section("T08 — Large Response (chunked TCP)")
big_code = "print('x' * 5000)"
try:
    resp = send(big_code)
    big_ok = len(resp.get("output", "")) > 4000
    print(f"{'✓' if big_ok else '✗'} large output received correctly ({len(resp.get('output',''))} chars)")
    results["pass" if big_ok else "fail"] += 1
except Exception as e:
    print(f"{FAIL} large output failed: {e}")
    results["fail"] += 1

# ── Summary ───────────────────────────────────────────────────────────────────
total = results["pass"] + results["fail"]
print(f"\n{'═' * 55}")
print(f"Results: {results['pass']}/{total} passed"
      + (f"  ({results['fail']} failed)" if results["fail"] else "  ✓ all passed"))
sys.exit(0 if results["fail"] == 0 else 1)
