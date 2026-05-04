#!/usr/bin/env python3
"""
Mock FreeCAD Server — simulates freecad_server.py for offline testing.

Listens on 127.0.0.1:7978 (or FC_PORT env var).
Matches incoming code against known patterns and returns scripted responses.
Unknown code returns a generic success response.

Usage:
    python3 tests/mock_server.py
    python3 tests/mock_server.py --port 7979
"""

import socket
import threading
import json
import sys
import re
import argparse

PORT = int(__import__("os").environ.get("FC_PORT", "7978"))


def handle(code: str) -> dict:
    """Return a scripted response based on the code content."""

    def ok(result=None, output=""):
        return {"result": result, "output": output, "stderr": "", "error": None}

    def err(msg: str):
        return {"result": None, "output": "", "stderr": "",
                "error": f"Traceback (most recent call last):\n  ...\n{msg}"}

    c = code.strip()

    # ── Connection checks ──────────────────────────────────────────────────
    if c in ("'ping'", '"ping"'):
        return ok("ping")

    if "FreeCAD.Version()" in c:
        return ok("0.21")

    # ── NameError when Part not imported ──────────────────────────────────
    if re.search(r"^\s*Part\.", c) and "import Part" not in c:
        return err("NameError: name 'Part' is not defined")

    # ── Document management ───────────────────────────────────────────────
    if "newDocument" in c:
        name = re.search(r'newDocument\(["\'](\w+)["\']', c)
        doc_name = name.group(1) if name else "Unnamed"
        return ok(doc_name, f"Document '{doc_name}' created")

    if "App.ActiveDocument.Name" in c or "ActiveDocument.Name" in c:
        return ok("MockDoc")

    if "listDocuments" in c:
        return ok(output="  MockDoc [aktiv]  — (ungespeichert)")

    # ── Object creation ───────────────────────────────────────────────────
    if "Part::Box" in c or ("makeBox" in c and "addObject" in c):
        # Extract dimensions if present
        w = re.search(r'\.Length\s*=\s*([0-9.]+)', c)
        d = re.search(r'\.Width\s*=\s*([0-9.]+)', c)
        h = re.search(r'\.Height\s*=\s*([0-9.]+)', c)
        dims = f"{w.group(1) if w else '10.0'} x {d.group(1) if d else '10.0'} x {h.group(1) if h else '10.0'}"
        return ok(output=f"Box created: {dims} mm")

    if "Part::Cylinder" in c:
        return ok(output="Cylinder created")

    # ── BoundBox checks ───────────────────────────────────────────────────
    if "BoundBox" in c:
        if "XLength" in c:
            return ok(100.0)
        if "YLength" in c:
            return ok(50.0)
        if "ZLength" in c:
            return ok(30.0)
        return ok(output="BoundBox(0, 0, 0, 100, 50, 30)")

    # ── Shape validity ────────────────────────────────────────────────────
    if "isValid" in c:
        return ok(True)
    if "ShapeType" in c:
        return ok("Solid")
    if "len(obj.Shape.Solids)" in c or "len(result.Solids)" in c:
        return ok(1)

    # ── makeBox (raw Part geometry, not via document) ─────────────────────
    if "makeBox" in c and "import Part" in c:
        return ok("<Solid object>", "Shape created in memory")

    # ── Spreadsheet ───────────────────────────────────────────────────────
    if "Spreadsheet::Sheet" in c:
        return ok(output="Spreadsheet created")
    if "setAlias" in c:
        return ok(output="Alias set")
    if ".set(" in c and "mm" in c:
        return ok(output="Cell value set")

    # ── Screenshot ───────────────────────────────────────────────────────
    if "saveImage" in c:
        path_match = re.search(r"saveImage\(['\"]([^'\"]+)['\"]", c)
        path = path_match.group(1) if path_match else "screenshot.png"
        return ok(output=f"Screenshot saved: {path}")

    # ── Objects list ─────────────────────────────────────────────────────
    if "doc.Objects" in c and "for" in c:
        return ok(output="Box  Part::Box  MockBox\nBody  PartDesign::Body  Body")

    # ── recompute ────────────────────────────────────────────────────────
    if c in ("App.ActiveDocument.recompute()", "doc.recompute()"):
        return ok(output="Recomputed")

    # ── Simple arithmetic (for basic eval test) ───────────────────────────
    try:
        result = eval(c, {"__builtins__": {}})
        if isinstance(result, (int, float, str, bool)):
            return ok(result)
    except Exception:
        pass

    # ── print() calls → capture output ───────────────────────────────────
    import io, contextlib
    m = re.match(r"^print\((.+)\)$", c.strip())
    if m:
        try:
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                exec(f"print({m.group(1)})", {"__builtins__": __builtins__})
            return ok(output=buf.getvalue())
        except Exception:
            pass

    # ── exec with _result ─────────────────────────────────────────────────
    if "_result" in c:
        try:
            ns: dict = {"__builtins__": __builtins__}
            exec(c, ns)
            val = ns.get("_result")
            if isinstance(val, (int, float, str, bool, list, dict, type(None))):
                return ok(val)
        except Exception:
            pass

    # ── Intentional error test ────────────────────────────────────────────
    if "RAISE_ERROR" in c:
        return err("RuntimeError: intentional test error")

    # ── Default: generic success ──────────────────────────────────────────
    return ok(output="(mock: code executed)")


def serve(port: int):
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("127.0.0.1", port))
    srv.listen(20)
    print(f"Mock FreeCAD server listening on 127.0.0.1:{port}", flush=True)

    while True:
        try:
            conn, _ = srv.accept()
            threading.Thread(target=client, args=(conn,), daemon=True).start()
        except KeyboardInterrupt:
            break
    srv.close()


def client(conn):
    try:
        raw = b""
        while True:
            chunk = conn.recv(4096)
            if not chunk:
                break
            raw += chunk
            if b"\n" in raw:
                break
        req = json.loads(raw.decode().strip())
        resp = handle(req.get("code", ""))
        conn.sendall(json.dumps(resp).encode() + b"\n")
    except Exception as e:
        try:
            conn.sendall(json.dumps({"error": str(e), "result": None,
                                     "output": "", "stderr": ""}).encode() + b"\n")
        except Exception:
            pass
    finally:
        conn.close()


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Mock FreeCAD server")
    p.add_argument("--port", type=int, default=PORT)
    args = p.parse_args()
    serve(args.port)
